# app/services/azure_document_service.py
import os
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from app.services.document_service import DocumentProcessor
from app.services.azure_search_service import azure_search_service
from app.core.config import settings


class AzureDocumentService:
    """集成 Azure AI Search 的文档处理服务"""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.document_processor = DocumentProcessor(chunk_size, chunk_overlap)
        self.azure_search = azure_search_service

    async def process_and_index_document(
        self,
        file_path: str,
        file_info: Dict[str, Any],
        return_best: Optional[int] = None
    ) -> Dict[str, Any]:
        """完整的文档处理流程：提取文本 -> 分割 -> 索引到 Azure AI Search"""
        try:
            # 1. 提取文本
            text = await self.document_processor.extract_text_from_file(file_path)

            if text.startswith("[Error]"):
                return {
                    "success": False,
                    "error": text,
                    "file_info": file_info
                }

            # 2. 分割文本为chunks
            chunks = self.document_processor.chunk_text(text)

            if not chunks:
                return {
                    "success": False,
                    "error": "No text content found in document",
                    "file_info": file_info
                }

            # 3. 计算chunk质量分数
            for chunk in chunks:
                chunk["quality_score"] = self.document_processor.calculate_chunk_quality(chunk)

            # 4. 筛选最佳chunks（如果指定了return_best）
            if return_best is not None and return_best > 0:
                best_chunks = self.document_processor.get_best_chunks(chunks, return_best)
                final_chunks = best_chunks
                quality_filtered = True
            else:
                final_chunks = chunks
                quality_filtered = False

            # 5. 准备索引文档
            index_documents = []
            for chunk in final_chunks:
                doc = {
                    "content": chunk["text"],
                    "title": file_info.get("original_name", Path(file_path).name),
                    "file_path": file_path,
                    "chunk_index": chunk["index"],
                    "quality_score": chunk["quality_score"],
                    "metadata": {
                        "file_info": file_info,
                        "chunk_length": chunk["length"],
                        "start_char": chunk.get("start_char", 0),
                        "end_char": chunk.get("end_char", chunk["length"]),
                        "processing_time": datetime.utcnow().isoformat()
                    }
                }
                index_documents.append(doc)

            # 6. 索引到 Azure AI Search
            doc_ids = await self.azure_search.add_documents(index_documents)

            if not doc_ids:
                return {
                    "success": False,
                    "error": "Failed to index documents to Azure AI Search",
                    "file_info": file_info
                }

            # 7. 获取索引统计
            index_stats = await self.azure_search.get_index_stats()

            return {
                "success": True,
                "file_info": file_info,
                "original_text": text,
                "text_length": len(text),
                "total_chunks": len(chunks),
                "indexed_chunks": len(final_chunks),
                "chunks": final_chunks,
                "document_ids": doc_ids,
                "quality_filtered": quality_filtered,
                "index_stats": index_stats,
                "processing_stats": {
                    "chunk_size": self.document_processor.chunk_size,
                    "chunk_overlap": self.document_processor.chunk_overlap,
                    "embedding_dimension": settings.embedding_dimension,
                    "return_best": return_best,
                    "azure_search_powered": True
                }
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Processing failed: {str(e)}",
                "file_info": file_info
            }

    async def search_documents(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.7,
        use_semantic_search: bool = True,
        file_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """搜索文档并返回详细结果"""
        try:
            # 搜索文档
            search_results = await self.azure_search.search_documents(
                query=query,
                top_k=top_k,
                min_score=min_score,
                use_semantic_search=use_semantic_search
            )

            # 如果指定了文件过滤器，过滤结果
            if file_filter:
                search_results = [
                    result for result in search_results
                    if file_filter.lower() in result["file_path"].lower()
                ]

            # 处理搜索结果
            processed_results = []
            for result in search_results:
                metadata = result.get("metadata", {})
                processed_result = {
                    "content": result["content"],
                    "title": result["title"],
                    "file_path": result["file_path"],
                    "chunk_index": result["chunk_index"],
                    "similarity_score": result["similarity"],
                    "quality_score": result["quality_score"],
                    "metadata": metadata,
                    "captions": result.get("captions", []),
                    "answers": result.get("answers", [])
                }
                processed_results.append(processed_result)

            return {
                "query": query,
                "results": processed_results,
                "total_found": len(processed_results),
                "search_parameters": {
                    "top_k": top_k,
                    "min_score": min_score,
                    "semantic_search": use_semantic_search,
                    "file_filter": file_filter
                },
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            return {
                "query": query,
                "error": f"Search failed: {str(e)}",
                "results": [],
                "total_found": 0
            }

    async def delete_document(self, file_path: str) -> bool:
        """删除指定文件的所有文档"""
        try:
            success = await self.azure_search.delete_documents_by_file(file_path)
            return success
        except Exception as e:
            print(f"❌ 删除文档失败: {str(e)}")
            return False

    async def get_document_stats(self) -> Dict[str, Any]:
        """获取文档统计信息"""
        try:
            index_stats = await self.azure_search.get_index_stats()
            return {
                "index_stats": index_stats,
                "service_info": {
                    "chunk_size": self.document_processor.chunk_size,
                    "chunk_overlap": self.document_processor.chunk_overlap,
                    "embedding_dimension": settings.embedding_dimension,
                    "azure_search_endpoint": settings.azure_search_endpoint,
                    "azure_search_index": settings.azure_search_index_name
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "error": f"Failed to get stats: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }

    async def clear_index(self) -> bool:
        """清空索引中的所有文档"""
        try:
            success = await self.azure_search.clear_index()
            return success
        except Exception as e:
            print(f"❌ 清空索引失败: {str(e)}")
            return False

    async def ensure_index_ready(self) -> bool:
        """确保搜索索引已准备就绪"""
        try:
            return await self.azure_search.ensure_index_exists()
        except Exception as e:
            print(f"❌ 索引初始化失败: {str(e)}")
            return False

    async def batch_process_documents(
        self,
        file_paths: List[str],
        batch_size: int = 5
    ) -> Dict[str, Any]:
        """批量处理多个文档"""
        results = {
            "successful": [],
            "failed": [],
            "total_processed": 0,
            "total_chunks_indexed": 0
        }

        # 确保索引存在
        await self.ensure_index_ready()

        for i in range(0, len(file_paths), batch_size):
            batch = file_paths[i:i + batch_size]

            for file_path in batch:
                try:
                    # 构建文件信息
                    file_info = {
                        "original_name": Path(file_path).name,
                        "file_size": os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                        "file_type": Path(file_path).suffix.lower(),
                        "upload_time": datetime.utcnow().isoformat()
                    }

                    # 处理文档
                    result = await self.process_and_index_document(file_path, file_info)

                    if result["success"]:
                        results["successful"].append({
                            "file_path": file_path,
                            "chunks_indexed": result["indexed_chunks"],
                            "document_ids": result["document_ids"]
                        })
                        results["total_chunks_indexed"] += result["indexed_chunks"]
                    else:
                        results["failed"].append({
                            "file_path": file_path,
                            "error": result["error"]
                        })

                    results["total_processed"] += 1

                except Exception as e:
                    results["failed"].append({
                        "file_path": file_path,
                        "error": f"Processing error: {str(e)}"
                    })
                    results["total_processed"] += 1

        return results


# 创建全局服务实例
azure_document_service = AzureDocumentService()


# 高级文档处理功能
async def process_document_with_azure_search(
    file_path: str,
    file_info: Dict[str, Any],
    return_best: Optional[int] = None
) -> Dict[str, Any]:
    """兼容性函数：处理文档并索引到 Azure AI Search"""
    return await azure_document_service.process_and_index_document(
        file_path, file_info, return_best
    )


async def search_documents_with_azure_search(
    query: str,
    top_k: int = 5,
    min_score: float = 0.7,
    use_semantic_search: bool = True
) -> List[Dict[str, Any]]:
    """兼容性函数：使用 Azure AI Search 搜索文档"""
    result = await azure_document_service.search_documents(
        query, top_k, min_score, use_semantic_search
    )
    return result.get("results", [])