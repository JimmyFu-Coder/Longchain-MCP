# app/api/file_routes.py
import os
import uuid
from typing import List
from fastapi import APIRouter, File, UploadFile, HTTPException, Path
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from app.services.document_service import process_document_complete
from app.services.vector_store import vector_store

router = APIRouter()

UPLOAD_DIR = "uploads"
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# 确保上传目录存在
os.makedirs(UPLOAD_DIR, exist_ok=True)

def validate_file(file: UploadFile) -> bool:
    # 检查文件扩展名
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        return False
    return True

@router.post("/upload")
async def upload_files(
    files: List[UploadFile] = File(...),
    auto_process: bool = True,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    return_best: int = 3
):
    """上传文件，默认自动进行embedding处理"""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    results = []

    for file in files:
        # 验证文件类型
        if not validate_file(file):
            results.append({
                "file_name": file.filename,
                "success": False,
                "error": f"File type not allowed: {file.filename}. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
            })
            continue

        # 读取文件内容并检查大小
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            results.append({
                "file_name": file.filename,
                "success": False,
                "error": f"File {file.filename} too large. Maximum size: {MAX_FILE_SIZE/1024/1024}MB"
            })
            continue

        # 生成唯一文件名并保存
        file_ext = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)

        with open(file_path, "wb") as f:
            f.write(content)

        # 准备文件信息
        file_info = {
            "original_name": file.filename,
            "saved_name": unique_filename,
            "file_path": file_path,
            "size": len(content),
            "type": file.content_type
        }

        if auto_process:
            # 自动处理文档：提取文本 + 分割 + embedding
            from app.services.document_service import document_processor
            document_processor.chunk_size = chunk_size
            document_processor.chunk_overlap = chunk_overlap

            processing_result = await process_document_complete(file_path, file_info, return_best)
            results.append(processing_result)
        else:
            # 仅上传，不处理
            results.append({
                "success": True,
                "file_info": file_info,
                "processed": False,
                "message": "File uploaded successfully, no processing performed"
            })

    return JSONResponse(
        status_code=200,
        content={
            "message": f"Processed {len(results)} file(s)",
            "auto_process": auto_process,
            "results": results
        }
    )

@router.post("/upload-only")
async def upload_files_only(files: List[UploadFile] = File(...)):
    """仅上传文件，不进行任何处理"""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    uploaded_files = []

    for file in files:
        # 验证文件类型
        if not validate_file(file):
            raise HTTPException(
                status_code=400,
                detail=f"File type not allowed: {file.filename}. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
            )

        # 读取文件内容并检查大小
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File {file.filename} too large. Maximum size: {MAX_FILE_SIZE/1024/1024}MB"
            )

        # 生成唯一文件名
        file_ext = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)

        # 保存文件
        with open(file_path, "wb") as f:
            f.write(content)

        uploaded_files.append({
            "original_name": file.filename,
            "saved_name": unique_filename,
            "file_path": file_path,
            "size": len(content),
            "type": file.content_type
        })

    return JSONResponse(
        status_code=200,
        content={
            "message": f"Successfully uploaded {len(uploaded_files)} file(s)",
            "files": uploaded_files
        }
    )

class ProcessRequest(BaseModel):
    file_path: str
    chunk_size: int = 1000
    chunk_overlap: int = 200
    return_best: int = 3

@router.post("/process")
async def process_uploaded_file(request: ProcessRequest):
    """处理已上传的文件：提取文本、分割、生成embeddings"""

    # 检查文件是否存在
    if not os.path.exists(request.file_path):
        raise HTTPException(status_code=404, detail="File not found")

    # 检查文件是否在uploads目录中（安全检查）
    abs_file_path = os.path.abspath(request.file_path)
    abs_upload_dir = os.path.abspath(UPLOAD_DIR)
    if not abs_file_path.startswith(abs_upload_dir):
        raise HTTPException(status_code=400, detail="Invalid file path")

    # 获取文件信息
    file_info = {
        "file_path": request.file_path,
        "file_name": os.path.basename(request.file_path),
        "file_size": os.path.getsize(request.file_path),
        "file_ext": os.path.splitext(request.file_path)[1].lower()
    }

    # 设置文档处理器参数
    from app.services.document_service import document_processor
    document_processor.chunk_size = request.chunk_size
    document_processor.chunk_overlap = request.chunk_overlap

    # 处理文档
    result = await process_document_complete(request.file_path, file_info, request.return_best)

    if result["success"]:
        return JSONResponse(
            status_code=200,
            content={
                "message": "Document processed successfully",
                "result": result
            }
        )
    else:
        raise HTTPException(
            status_code=500,
            detail=f"Processing failed: {result.get('error', 'Unknown error')}"
        )

@router.post("/upload-and-process")
async def upload_and_process_files(
    files: List[UploadFile] = File(...),
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    return_best: int = 3
):
    """上传文件并立即处理：一步完成上传、提取文本、分割、生成embeddings"""

    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    results = []

    for file in files:
        # 验证文件类型
        if not validate_file(file):
            results.append({
                "file_name": file.filename,
                "success": False,
                "error": f"File type not allowed: {file.filename}. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
            })
            continue

        # 读取文件内容并检查大小
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            results.append({
                "file_name": file.filename,
                "success": False,
                "error": f"File {file.filename} too large. Maximum size: {MAX_FILE_SIZE/1024/1024}MB"
            })
            continue

        # 生成唯一文件名并保存
        file_ext = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)

        with open(file_path, "wb") as f:
            f.write(content)

        # 准备文件信息
        file_info = {
            "original_name": file.filename,
            "saved_name": unique_filename,
            "file_path": file_path,
            "size": len(content),
            "type": file.content_type
        }

        # 设置文档处理器参数
        from app.services.document_service import document_processor
        document_processor.chunk_size = chunk_size
        document_processor.chunk_overlap = chunk_overlap

        # 处理文档
        processing_result = await process_document_complete(file_path, file_info, return_best)
        results.append(processing_result)

    return JSONResponse(
        status_code=200,
        content={
            "message": f"Processed {len(results)} file(s)",
            "results": results
        }
    )

# 向量存储管理端点
@router.get("/vector-store/stats")
async def get_vector_store_stats():
    """获取向量存储统计信息"""
    stats = vector_store.get_stats()
    return JSONResponse(
        status_code=200,
        content={
            "message": "Vector store statistics",
            "stats": stats
        }
    )

@router.delete("/vector-store/file/{file_path:path}")
async def remove_file_from_vector_store(file_path: str):
    """从向量存储中删除指定文件的chunks"""
    success = vector_store.remove_file_chunks(file_path)
    if success:
        return JSONResponse(
            status_code=200,
            content={
                "message": f"Successfully removed chunks for file: {file_path}",
                "stats": vector_store.get_stats()
            }
        )
    else:
        raise HTTPException(
            status_code=404,
            detail=f"File not found in vector store: {file_path}"
        )

@router.post("/vector-store/clear")
async def clear_vector_store():
    """清空整个向量存储"""
    vector_store.clear()
    return JSONResponse(
        status_code=200,
        content={
            "message": "Vector store cleared successfully",
            "stats": vector_store.get_stats()
        }
    )