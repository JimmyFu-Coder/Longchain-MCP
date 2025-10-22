import asyncio
from app.services.llm_service import process_prompt

async def main():
    print("🚀 发送请求到 Azure OpenAI ...")
    response = await process_prompt("Hello, who are you?")
    print("✅ 模型回复：", response)

if __name__ == "__main__":
    asyncio.run(main())
