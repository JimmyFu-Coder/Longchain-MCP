# app/services/rag_service.py
from typing import List, Dict, Any, Optional
from app.services.azure_search_service import azure_search_service

class RAGService:
    """RAG (Retrieval-Augmented Generation) 服务"""

    def __init__(self,
                 max_context_chunks: int = 5,
                 min_similarity: float = 0.7,
                 max_context_length: int = 4000,
                 use_semantic_search: bool = True):
        self.max_context_chunks = max_context_chunks
        self.min_similarity = min_similarity
        self.max_context_length = max_context_length
        self.use_semantic_search = use_semantic_search

    async def retrieve_relevant_context(self, query: str) -> Dict[str, Any]:
        """检索与查询相关的文档上下文"""
        try:
            # 使用 Azure AI Search 搜索相关文档
            search_results = await azure_search_service.search_documents(
                query=query,
                top_k=self.max_context_chunks,
                min_score=self.min_similarity,
                use_semantic_search=self.use_semantic_search
            )

            if not search_results:
                return {
                    "has_context": False,
                    "context": "",
                    "sources": [],
                    "message": "No relevant documents found"
                }

            # 构建上下文文本
            context_parts = []
            sources = []
            total_length = 0

            for i, doc in enumerate(search_results):
                doc_content = doc["content"]

                # 检查是否超过最大长度限制
                if total_length + len(doc_content) > self.max_context_length:
                    # 截断最后一个文档
                    remaining_length = self.max_context_length - total_length
                    if remaining_length > 100:  # 至少保留100个字符
                        doc_content = doc_content[:remaining_length] + "..."
                        context_parts.append(f"Document Chunk {i+1} (score: {doc['similarity']:.3f}):\n{doc_content}")
                    break

                context_parts.append(f"Document Chunk {i+1} (score: {doc['similarity']:.3f}):\n{doc_content}")
                total_length += len(doc_content)

                # 记录来源信息
                metadata = doc.get("metadata", {})
                source_info = {
                    "file_path": doc["file_path"],
                    "title": doc["title"],
                    "chunk_index": doc["chunk_index"],
                    "similarity": doc["similarity"],
                    "quality_score": doc["quality_score"],
                    "metadata": metadata,
                    "captions": doc.get("captions", []),
                    "answers": doc.get("answers", [])
                }
                sources.append(source_info)

            context_text = "\n\n".join(context_parts)

            return {
                "has_context": True,
                "context": context_text,
                "sources": sources,
                "chunk_count": len(search_results),
                "total_context_length": len(context_text),
                "semantic_search_used": self.use_semantic_search
            }

        except Exception as e:
            print(f"❌ RAG检索失败: {str(e)}")
            return {
                "has_context": False,
                "context": "",
                "sources": [],
                "error": str(e)
            }

    def format_prompt_with_context(self, user_query: str, context_info: Dict[str, Any]) -> str:
        """将用户查询和检索到的上下文格式化为完整的prompt"""

        if not context_info.get("has_context", False):
            # 没有相关上下文时的提示
            return f"""User question: {user_query}

Note: No relevant document content was found to answer this question. Please answer based on your general knowledge and indicate that this answer is not based on the user's uploaded documents."""

        # 有上下文时的完整prompt
        context = context_info["context"]
        sources = context_info["sources"]

        source_list = "\n".join([
            f"- {source['title'] or source['file_path']} (chunk {source['chunk_index']}, score: {source['similarity']:.3f})"
            for source in sources
        ])

        semantic_info = " (Enhanced with Azure AI semantic search)" if context_info.get("semantic_search_used", False) else ""

        prompt = f"""Answer the user's question based on the following document content{semantic_info}.

Relevant document chunks:
{context}

User question: {user_query}

Please answer based on the above document content. If the documents do not contain directly relevant information, please indicate this.

Sources:
{source_list}"""

        return prompt

    async def process_query_with_rag(self, user_query: str) -> Dict[str, Any]:
        """完整的RAG处理流程：检索 + 格式化prompt"""
        # 1. 检索相关上下文
        context_info = await self.retrieve_relevant_context(user_query)

        # 2. 格式化prompt
        enhanced_prompt = self.format_prompt_with_context(user_query, context_info)

        return {
            "enhanced_prompt": enhanced_prompt,
            "context_info": context_info,
            "original_query": user_query
        }

# 创建全局RAG服务实例 (暂时关闭语义搜索，因为服务不支持)
rag_service = RAGService(use_semantic_search=False)