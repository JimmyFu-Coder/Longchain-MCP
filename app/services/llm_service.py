# app/services/llm_service.py
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.callbacks import get_openai_callback
from app.core.config import settings
from typing import List, Dict, Any
import tiktoken

# Initialize Azure LLM client
llm = AzureChatOpenAI(
    api_key=settings.azure_openai_api_key,
    azure_endpoint=settings.azure_openai_endpoint,
    model=settings.azure_deployment_name,
    api_version=settings.azure_api_version,
    temperature=0.7,
    stream_usage=True,  # 启用流式使用统计
)

# 全局对话历史存储
conversation_history: List[HumanMessage | AIMessage] = []

# Token计算工具函数
def count_tokens_for_messages(messages: List[HumanMessage | AIMessage], model: str = "gpt-4") -> int:
    """计算消息列表的token数量"""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("o200k_base")

    total_tokens = 0
    for message in messages:
        if message.content:  # 确保内容不为空
            # 每条消息基础开销约4个token
            total_tokens += 4
            total_tokens += len(encoding.encode(str(message.content)))

    # 对话结束标记
    total_tokens += 2
    return total_tokens

# 🔹 Non-streaming version (already working)
async def process_prompt(prompt: str) -> Dict[str, Any]:
    # 添加用户消息到历史
    user_message = HumanMessage(content=prompt)
    conversation_history.append(user_message)

    # 计算输入token
    input_tokens = count_tokens_for_messages(conversation_history)

    # 使用callback追踪token使用
    with get_openai_callback() as cb:
        response = await llm.ainvoke(conversation_history)

    # 添加AI回复到历史
    ai_message = AIMessage(content=response.content)
    conversation_history.append(ai_message)

    # 计算输出token (仅AI回复)
    output_tokens = count_tokens_for_messages([ai_message])

    return {
        "response": response.content,
        "token_usage": {
            "input_tokens": cb.prompt_tokens if hasattr(cb, 'prompt_tokens') else input_tokens,
            "output_tokens": cb.completion_tokens if hasattr(cb, 'completion_tokens') else output_tokens,
            "total_tokens": cb.total_tokens if hasattr(cb, 'total_tokens') else (input_tokens + output_tokens)
        }
    }

# ✨ Streaming version (typewriter effect)
async def stream_prompt(prompt: str):
    """
    Stream LLM output chunk by chunk (token by token).
    Used for StreamingResponse in FastAPI.
    """
    # 添加用户消息到历史
    user_message = HumanMessage(content=prompt)
    conversation_history.append(user_message)

    # 计算输入token
    input_tokens = count_tokens_for_messages(conversation_history)
    print(f"计算的输入token: {input_tokens}")  # 调试信息

    # 用于收集完整回复的变量
    full_response = ""
    usage_info = None

    try:
        # 使用完整历史进行流式推理
        async for chunk in llm.astream(conversation_history):
            if chunk.content:
                full_response += chunk.content
                # NOTE: must yield bytes when using StreamingResponse
                yield chunk.content.encode("utf-8")

            # 检查是否有usage信息（在流的最后）
            if hasattr(chunk, 'usage_metadata') and chunk.usage_metadata:
                usage_info = chunk.usage_metadata
                print(f"从LLM获取的usage信息: {usage_info}")  # 调试信息

        # 流式完成后，添加AI回复到历史
        if full_response:
            ai_message = AIMessage(content=full_response)
            conversation_history.append(ai_message)

            # 计算输出token
            output_tokens = count_tokens_for_messages([ai_message])
            print(f"计算的输出token: {output_tokens}")  # 调试信息

            # 发送token统计信息
            import json
            token_stats = {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens
            }
            print(f"最终token统计: {token_stats}")  # 调试信息

            # 以特殊格式发送token统计（可被前端识别）
            token_info = f"\n\n[TOKEN_USAGE]{json.dumps(token_stats)}[/TOKEN_USAGE]"
            yield token_info.encode("utf-8")

    except Exception as e:
        # Optional: log the error here
        error_msg = f"[Error] {str(e)}"
        yield error_msg.encode("utf-8")

# 获取token统计的流式版本（返回完整响应和token信息）
async def stream_prompt_with_stats(prompt: str) -> Dict[str, Any]:
    """
    流式处理并返回完整响应和token统计信息
    """
    # 添加用户消息到历史
    user_message = HumanMessage(content=prompt)
    conversation_history.append(user_message)

    # 计算输入token
    input_tokens = count_tokens_for_messages(conversation_history)

    # 用于收集完整回复的变量
    full_response = ""
    usage_info = None

    try:
        # 使用完整历史进行流式推理
        async for chunk in llm.astream(conversation_history):
            if chunk.content:
                full_response += chunk.content

            # 检查是否有usage信息
            if hasattr(chunk, 'usage_metadata') and chunk.usage_metadata:
                usage_info = chunk.usage_metadata

        # 流式完成后，添加AI回复到历史
        if full_response:
            ai_message = AIMessage(content=full_response)
            conversation_history.append(ai_message)

        # 计算输出token
        output_tokens = count_tokens_for_messages([ai_message]) if full_response else 0

        return {
            "response": full_response,
            "token_usage": {
                "input_tokens": usage_info.get('input_tokens', input_tokens) if usage_info else input_tokens,
                "output_tokens": usage_info.get('output_tokens', output_tokens) if usage_info else output_tokens,
                "total_tokens": usage_info.get('total_tokens', input_tokens + output_tokens) if usage_info else (input_tokens + output_tokens)
            }
        }

    except Exception as e:
        return {
            "response": f"[Error] {str(e)}",
            "token_usage": {
                "input_tokens": input_tokens,
                "output_tokens": 0,
                "total_tokens": input_tokens
            }
        }
