# app/services/llm_service.py
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.callbacks import get_openai_callback
from app.core.config import settings
from app.services.rag_service import rag_service
from app.services.azure_search_service import azure_search_service
from app.services.mcp_service import mcp_service
from typing import List, Dict, Any
import asyncio
import tiktoken
import json

# Initialize Azure LLM client
llm = AzureChatOpenAI(
    api_key=settings.azure_openai_api_key,
    azure_endpoint=settings.azure_openai_endpoint,
    model=settings.azure_deployment_name,
    api_version=settings.azure_api_version,
    temperature=0.7,
)

# 数据库工具定义
DATABASE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_database",
            "description": "ALWAYS use this tool when user asks about database content, tables, schemas, or data. Execute SQL queries to get table information, schema details, or retrieve data from the PostgreSQL database. For schema queries, use: SELECT schema_name FROM information_schema.schemata ORDER BY schema_name;",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Any SQL SELECT query to execute. You can query system tables for metadata, get schema info, or retrieve data."
                    },
                    "params": {
                        "type": "array",
                        "description": "Optional parameters for prepared statements",
                        "items": {"type": "string"}
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_tables",
            "description": "ALWAYS use this tool when user asks 'what tables are in the database', 'list tables', 'show tables', or similar questions. Lists all tables in the specified database schema.",
            "parameters": {
                "type": "object",
                "properties": {
                    "schema": {
                        "type": "string",
                        "description": "Schema name to list tables from (default: public)",
                        "default": "public"
                    }
                }
            }
        }
    }
]

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

# 处理函数调用
async def handle_function_call(function_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """处理LLM的函数调用"""
    try:
        # 确保MCP服务已启动
        if not mcp_service.process:
            startup_success = await asyncio.wait_for(mcp_service.start(), timeout=5.0)
            if not startup_success:
                return {"success": False, "error": "MCP service failed to start"}

        # 调用MCP服务
        result = await asyncio.wait_for(mcp_service.call_tool(function_name, arguments), timeout=10.0)
        return result
    except Exception as e:
        return {
            "success": False,
            "error": f"Function call failed: {str(e)}"
        }

# 🔹 Non-streaming version with RAG support
async def process_prompt(prompt: str, use_rag: bool = True, use_tools: bool = True) -> Dict[str, Any]:
    # RAG处理：检索相关文档并增强prompt
    if use_rag:
        rag_result = await rag_service.process_query_with_rag(prompt)
        enhanced_prompt = rag_result["enhanced_prompt"]
        context_info = rag_result["context_info"]
    else:
        enhanced_prompt = prompt
        context_info = {"has_context": False}

    # 添加原始用户消息到历史（用于记忆）
    user_message = HumanMessage(content=prompt)
    conversation_history.append(user_message)

    # 构建推理上下文（临时的，包含RAG增强）
    if use_rag and enhanced_prompt != prompt:
        # 用增强版本替换最后一条用户消息进行推理
        inference_context = conversation_history[:-1] + [HumanMessage(content=enhanced_prompt)]
    else:
        inference_context = conversation_history

    # 计算输入token
    input_tokens = count_tokens_for_messages(inference_context)

    # 使用callback追踪token使用，支持工具调用
    with get_openai_callback() as cb:
        if use_tools:
            response = await llm.ainvoke(inference_context, tools=DATABASE_TOOLS)
        else:
            response = await llm.ainvoke(inference_context)

    # 检查是否有工具调用
    if hasattr(response, 'tool_calls') and response.tool_calls:
        tool_results = []
        for tool_call in response.tool_calls:

            # 根据实际格式解析
            if isinstance(tool_call, dict) and 'name' in tool_call:
                function_name = tool_call['name']
                arguments = tool_call.get('args', {})
            elif hasattr(tool_call, 'function'):
                function_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)
            elif isinstance(tool_call, dict) and 'function' in tool_call:
                function_name = tool_call['function']['name']
                arguments = json.loads(tool_call['function']['arguments'])
            else:
                print(f"Unknown tool_call format: {tool_call}")
                continue

            # 执行工具调用
            tool_result = await handle_function_call(function_name, arguments)
            tool_results.append({
                "function_name": function_name,
                "arguments": arguments,
                "result": tool_result
            })

            # 将工具调用结果添加到对话历史
            tool_message = AIMessage(content=f"调用了函数 {function_name}，结果：{json.dumps(tool_result, ensure_ascii=False)}")
            conversation_history.append(tool_message)

        # 如果有工具调用，重新调用LLM生成最终回复
        final_response = await llm.ainvoke(conversation_history)
        ai_message = AIMessage(content=final_response.content)
        conversation_history.append(ai_message)

        return {
            "response": final_response.content,
            "context_info": context_info,
            "original_query": prompt,
            "enhanced_prompt": enhanced_prompt if use_rag else None,
            "tool_calls": tool_results,
            "token_usage": {
                "input_tokens": cb.prompt_tokens if hasattr(cb, 'prompt_tokens') else input_tokens,
                "output_tokens": cb.completion_tokens if hasattr(cb, 'completion_tokens') else output_tokens,
                "total_tokens": cb.total_tokens if hasattr(cb, 'total_tokens') else (input_tokens + output_tokens)
            }
        }

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
async def stream_prompt(prompt: str, use_rag: bool = True, use_tools: bool = True):
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

    # 添加原始用户消息到历史（用于记忆）
    user_message = HumanMessage(content=prompt)
    conversation_history.append(user_message)

    # 构建推理上下文（临时的，包含RAG增强）
    if use_rag and enhanced_prompt != prompt:
        # 用增强版本替换最后一条用户消息进行推理
        inference_context = conversation_history[:-1] + [HumanMessage(content=enhanced_prompt)]
    else:
        inference_context = conversation_history

    # 计算输入token
    input_tokens = count_tokens_for_messages(inference_context)
    print(f"计算的输入token: {input_tokens}")  # 调试信息
    print("开始LLM流式调用...")  # 调试信息

    # 用于收集完整回复的变量
    full_response = ""
    usage_info = None

    try:
        # 使用推理上下文进行流式推理
        if use_tools:
            tool_calls_collected = {}  # 收集完整的工具调用

            async for chunk in llm.astream(inference_context, tools=DATABASE_TOOLS):
                print(f"收到chunk: {chunk}")  # 调试信息

                # 收集工具调用信息
                if hasattr(chunk, 'tool_call_chunks') and chunk.tool_call_chunks:
                    for tool_chunk in chunk.tool_call_chunks:
                        call_id = tool_chunk.get('id')
                        if call_id and call_id not in tool_calls_collected:
                            tool_calls_collected[call_id] = {
                                'name': tool_chunk.get('name', ''),
                                'args': tool_chunk.get('args', ''),
                                'id': call_id
                            }
                        elif call_id and call_id in tool_calls_collected:
                            # 继续累积参数
                            tool_calls_collected[call_id]['args'] += tool_chunk.get('args', '')
                        elif not call_id:
                            # 处理没有call_id的参数片段（Azure OpenAI的分片传输）
                            # 这些应该属于最近的工具调用
                            if tool_calls_collected:
                                latest_call_id = list(tool_calls_collected.keys())[-1]
                                tool_calls_collected[latest_call_id]['args'] += tool_chunk.get('args', '')

                # 检查是否完成了工具调用（收到finish_reason）
                if hasattr(chunk, 'response_metadata') and chunk.response_metadata.get('finish_reason') == 'tool_calls':
                    print(f"工具调用完成，处理收集到的工具调用: {tool_calls_collected}")  # 调试信息
                    yield "[TOOL_CALLS_COMPLETE]".encode("utf-8")

                    # 处理所有收集到的工具调用
                    tool_results = []
                    for call_id, tool_info in tool_calls_collected.items():
                        if tool_info['name']:
                            try:
                                arguments = json.loads(tool_info['args']) if tool_info['args'] else {}
                            except json.JSONDecodeError:
                                arguments = {}

                            print(f"调用工具: {tool_info['name']} with args: {arguments}")  # 调试信息
                            tool_result = await handle_function_call(tool_info['name'], arguments)
                            print(f"工具调用结果: {tool_result}")  # 调试信息

                            tool_results.append({
                                "function_name": tool_info['name'],
                                "arguments": arguments,
                                "result": tool_result
                            })

                            # 发送工具调用结果给前端
                            result_msg = f"[TOOL_RESULT]{json.dumps(tool_result, ensure_ascii=False)}[/TOOL_RESULT]"
                            yield result_msg.encode("utf-8")

                    # 将工具调用结果添加到对话历史
                    for tool_result in tool_results:
                        tool_message = AIMessage(content=f"调用了函数 {tool_result['function_name']}，结果：{json.dumps(tool_result['result'], ensure_ascii=False)}")
                        conversation_history.append(tool_message)

                    # 重新调用LLM生成基于工具结果的最终回复
                    print("重新调用LLM生成最终回复...")  # 调试信息
                    yield "\n\n[GENERATING_FINAL_RESPONSE]".encode("utf-8")

                    async for final_chunk in llm.astream(conversation_history):
                        if final_chunk.content:
                            full_response += final_chunk.content
                            yield final_chunk.content.encode("utf-8")

                    # 跳出主循环，因为已经完成了完整的工具调用流程
                    break

                if chunk.content:
                    full_response += chunk.content
                    # NOTE: must yield bytes when using StreamingResponse
                    yield chunk.content.encode("utf-8")

                # 检查是否有usage信息（在流的最后）
                if hasattr(chunk, 'usage_metadata') and chunk.usage_metadata:
                    usage_info = chunk.usage_metadata
                    print(f"从LLM获取的usage信息: {usage_info}")  # 调试信息
        else:
            async for chunk in llm.astream(inference_context):
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
