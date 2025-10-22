# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import llm_routes, file_routes

app = FastAPI(
    title="LongChain Backend",
    description="FastAPI + LangChain + Azure OpenAI",
    version="0.1.0",
)

# ✅ CORS 设置
origins = [
    "http://localhost:5173",  # React Vite 默认端口
    "http://127.0.0.1:5173",
    "http://localhost:3000",  # 如果你也用其他端口
    "http://127.0.0.1:3000"

]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,           # 允许的前端域名
    allow_credentials=True,
    allow_methods=["*"],            # 允许的 HTTP 方法
    allow_headers=["*"],            # 允许的 Header
)

# 注册路由
app.include_router(llm_routes.router, prefix="/api/llm", tags=["LLM"])
app.include_router(file_routes.router, prefix="/api/files", tags=["Files"])

@app.get("/")
def health_check():
    return {"status": "ok"}

