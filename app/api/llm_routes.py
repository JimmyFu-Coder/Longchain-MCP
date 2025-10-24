# app/api/llm_routes.py
from fastapi import APIRouter
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
from app.services.llm_service import stream_prompt, process_prompt, stream_prompt_with_stats

router = APIRouter()

# 📩 Request body model
class PromptRequest(BaseModel):
    prompt: str
    use_rag: bool = True
    use_tools: bool = True

# 🪄 非流式接口（调试备用）
@router.post("/chat")
async def chat(req: PromptRequest):
    result = await process_prompt(req.prompt, use_rag=req.use_rag, use_tools=req.use_tools)
    return result

@router.post("/chat/stream")
async def chat_stream(req: PromptRequest):
    return StreamingResponse(
        stream_prompt(req.prompt, use_rag=req.use_rag, use_tools=req.use_tools),
        media_type="text/plain"   #
    )

# 🔢 获取带token统计的流式处理结果
@router.post("/chat/stream/stats")
async def chat_stream_stats(req: PromptRequest):
    result = await stream_prompt_with_stats(req.prompt)
    return result

