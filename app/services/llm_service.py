# app/services/llm_service.py
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import HumanMessage
from app.core.config import settings

# Initialize Azure LLM client
llm = AzureChatOpenAI(
    api_key=settings.azure_openai_api_key,
    azure_endpoint=settings.azure_openai_endpoint,
    model=settings.azure_deployment_name,
    api_version=settings.azure_api_version,
    temperature=0.7,
)

# 🔹 Non-streaming version (already working)
async def process_prompt(prompt: str) -> str:
    messages = [HumanMessage(content=prompt)]
    response = await llm.ainvoke(messages)
    return response.content

# ✨ Streaming version (typewriter effect)
async def stream_prompt(prompt: str):
    """
    Stream LLM output chunk by chunk (token by token).
    Used for StreamingResponse in FastAPI.
    """
    messages = [HumanMessage(content=prompt)]
    try:
        async for chunk in llm.astream(messages):
            if chunk.content:
                # NOTE: must yield bytes when using StreamingResponse
                yield chunk.content.encode("utf-8")
    except Exception as e:
        # Optional: log the error here
        yield f"[Error] {str(e)}".encode("utf-8")
