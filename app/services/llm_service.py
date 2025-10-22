# app/services/llm_service.py
from app.core.config import settings
from langchain_openai import AzureChatOpenAI# 如果你用的是 langchain_openai，也行
from langchain_core.messages import HumanMessage


# 初始化 LLM 客户端
llm = AzureChatOpenAI(
    openai_api_key=settings.azure_openai_api_key,
    azure_endpoint=settings.azure_openai_endpoint,
    deployment_name=settings.azure_deployment_name,
    openai_api_version=settings.azure_api_version,
    temperature=0.7,
)

# 核心方法
async def process_prompt(prompt: str) -> str:
    """
    核心方法：把用户 prompt 发给 Azure OpenAI 并返回回复
    """
    messages = [HumanMessage(content=prompt)]
    response = await llm.ainvoke(messages)
    return response.content
