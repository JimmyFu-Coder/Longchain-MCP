# app/services/vector_store.py
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import json
import uuid
from datetime import datetime

class VectorStore:
    """简单的内存向量存储，支持文档chunks的存储和检索"""

    def __init__(self):
        self.chunks: Dict[str, Dict[str, Any]] = {}  # chunk_id -> chunk_data
        self.embeddings: Dict[str, List[float]] = {}  # chunk_id -> embedding
        self.file_chunks: Dict[str, List[str]] = {}  # file_path -> [chunk_ids]

    def add_document_chunks(self, file_path: str, file_info: Dict[str, Any],
                           chunks: List[Dict[str, Any]]) -> List[str]:
        """添加文档的所有chunks到向量存储"""
        chunk_ids = []

        for chunk in chunks:
            chunk_id = str(uuid.uuid4())

            # 存储chunk数据
            self.chunks[chunk_id] = {
                "id": chunk_id,
                "file_path": file_path,
                "file_info": file_info,
                "text": chunk["text"],
                "index": chunk["index"],
                "length": chunk["length"],
                "quality_score": chunk.get("quality_score", 0.0),
                "created_at": datetime.now().isoformat()
            }

            # 存储embedding
            if "embedding" in chunk and chunk["embedding"]:
                self.embeddings[chunk_id] = chunk["embedding"]

            chunk_ids.append(chunk_id)

        # 记录文件的chunk映射
        self.file_chunks[file_path] = chunk_ids

        print(f"✅ 已将 {len(chunk_ids)} 个chunks添加到向量存储，文件: {file_path}")
        return chunk_ids

    def search_similar_chunks(self, query_embedding: List[float],
                             top_k: int = 5,
                             min_similarity: float = 0.3) -> List[Dict[str, Any]]:
        """基于embedding相似度搜索相关chunks"""
        if not self.embeddings:
            return []

        query_vector = np.array(query_embedding)
        similarities = []

        for chunk_id, embedding in self.embeddings.items():
            # 计算余弦相似度
            chunk_vector = np.array(embedding)

            # 避免除零错误
            query_norm = np.linalg.norm(query_vector)
            chunk_norm = np.linalg.norm(chunk_vector)

            if query_norm == 0 or chunk_norm == 0:
                similarity = 0.0
            else:
                similarity = np.dot(query_vector, chunk_vector) / (query_norm * chunk_norm)

            if similarity >= min_similarity:
                similarities.append((chunk_id, similarity))

        # 按相似度排序
        similarities.sort(key=lambda x: x[1], reverse=True)

        # 返回top_k个最相似的chunks
        results = []
        for chunk_id, similarity in similarities[:top_k]:
            chunk_data = self.chunks[chunk_id].copy()
            chunk_data["similarity"] = similarity
            results.append(chunk_data)

        print(f"🔍 搜索到 {len(results)} 个相关chunks，相似度阈值: {min_similarity}")
        return results

    def get_chunks_by_file(self, file_path: str) -> List[Dict[str, Any]]:
        """获取指定文件的所有chunks"""
        if file_path not in self.file_chunks:
            return []

        chunks = []
        for chunk_id in self.file_chunks[file_path]:
            if chunk_id in self.chunks:
                chunks.append(self.chunks[chunk_id])

        return chunks

    def remove_file_chunks(self, file_path: str) -> bool:
        """删除指定文件的所有chunks"""
        if file_path not in self.file_chunks:
            return False

        chunk_ids = self.file_chunks[file_path]

        # 删除chunks和embeddings
        for chunk_id in chunk_ids:
            if chunk_id in self.chunks:
                del self.chunks[chunk_id]
            if chunk_id in self.embeddings:
                del self.embeddings[chunk_id]

        # 删除文件映射
        del self.file_chunks[file_path]

        print(f"🗑️ 已删除文件 {file_path} 的 {len(chunk_ids)} 个chunks")
        return True

    def get_stats(self) -> Dict[str, Any]:
        """获取向量存储统计信息"""
        return {
            "total_chunks": len(self.chunks),
            "total_embeddings": len(self.embeddings),
            "total_files": len(self.file_chunks),
            "files": list(self.file_chunks.keys())
        }

    def clear(self):
        """清空所有数据"""
        self.chunks.clear()
        self.embeddings.clear()
        self.file_chunks.clear()
        print("🧹 向量存储已清空")

# 创建全局向量存储实例
vector_store = VectorStore()