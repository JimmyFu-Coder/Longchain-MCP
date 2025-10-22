# app/api/llm_routes.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.llm_service import process_prompt


router = APIRouter()

class PromptRequest(BaseModel):
    prompt: str

@router.post("/chat")
async def chat_with_llm(req: PromptRequest):
    try:
        result = await process_prompt(req.prompt)
        return {"response": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
