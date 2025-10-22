# app/test_stream.py
import asyncio
from app.services.llm_service import stream_prompt

async def main():
    print("🚀 Streaming from LLM:")
    async for chunk in stream_prompt("Hello, can you explain what photosynthesis is?"):
        print(chunk.decode("utf-8"), end="", flush=True)
    print("\n✅ Done")

if __name__ == "__main__":
    asyncio.run(main())
