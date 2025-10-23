# app/services/llm_service.py
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.callbacks import get_openai_callback
from app.core.config import settings
from app.services.rag_service import rag_service
from app.services.azure_search_service import azure_search_service
from typing import List, Dict, Any
import tiktoken
import json

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

# 🔹 Non-streaming version with RAG support
async def process_prompt(prompt: str, use_rag: bool = True) -> Dict[str, Any]:
    # RAG处理：检索相关文档并增强prompt
    if use_rag:
        rag_result = await rag_service.process_query_with_rag(prompt)
        enhanced_prompt = rag_result["enhanced_prompt"]
        context_info = rag_result["context_info"]
    else:
        enhanced_prompt = prompt
        context_info = {"has_context": False}

    # 添加用户消息到历史
    user_message = HumanMessage(content=enhanced_prompt)
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
        "context_info": context_info,
        "original_query": prompt,
        "enhanced_prompt": enhanced_prompt if use_rag else None,
        "token_usage": {
            "input_tokens": cb.prompt_tokens if hasattr(cb, 'prompt_tokens') else input_tokens,
            "output_tokens": cb.completion_tokens if hasattr(cb, 'completion_tokens') else output_tokens,
            "total_tokens": cb.total_tokens if hasattr(cb, 'total_tokens') else (input_tokens + output_tokens)
        }
    }

# ✨ Streaming version with RAG support
async def stream_prompt(prompt: str, use_rag: bool = True):
    """
    Stream LLM output chunk by chunk with RAG support.
    Used for StreamingResponse in FastAPI.
    """
    # RAG处理：检索相关文档并增强prompt
    if use_rag:
        rag_result = await rag_service.process_query_with_rag(prompt)
        enhanced_prompt = rag_result["enhanced_prompt"]
        context_info = rag_result["context_info"]

        # 发送上下文信息给前端（可选）
        if context_info.get("has_context", False):
            semantic_info = " (with semantic search)" if context_info.get("semantic_search_used", False) else ""
            context_notice = f"[CONTEXT_FOUND]Found {context_info.get('chunk_count', 0)} relevant document chunks{semantic_info}[/CONTEXT_FOUND]\n\n"
            yield context_notice.encode("utf-8")
    else:
        enhanced_prompt = prompt
        context_info = {"has_context": False}

    # 添加用户消息到历史
    user_message = HumanMessage(content=enhanced_prompt)
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

            # 发送token统计信息和上下文信息
            token_stats = {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "rag_used": use_rag,
                "context_found": context_info.get("has_context", False),
                "source_chunks": len(context_info.get("sources", [])),
                "semantic_search_used": context_info.get("semantic_search_used", False),
                "azure_search_powered": True
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
        ai_message = None
        if full_response:
            ai_message = AIMessage(content=full_response)
            conversation_history.append(ai_message)

        # 计算输出token
        output_tokens = count_tokens_for_messages([ai_message]) if ai_message else 0

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
