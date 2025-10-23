# app/services/azure_search_service.py
import json
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime

from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.models import VectorizedQuery
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchField,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    SemanticConfiguration,
    SemanticSearch,
    SemanticPrioritizedFields,
    SemanticField,
    SearchFieldDataType,
)
from azure.core.credentials import AzureKeyCredential
from langchain_openai import AzureOpenAIEmbeddings

from app.core.config import settings


class AzureSearchService:
    """Azure AI Search 服务，包含 embedding 生成和向量搜索功能"""

    def __init__(self):
        # Azure AI Search 客户端
        self.search_client = SearchClient(
            endpoint=settings.azure_search_endpoint,
            index_name=settings.azure_search_index_name,
            credential=AzureKeyCredential(settings.azure_search_key)
        )

        self.index_client = SearchIndexClient(
            endpoint=settings.azure_search_endpoint,
            credential=AzureKeyCredential(settings.azure_search_key)
        )

        # Azure OpenAI Embedding 客户端
        self.embedding_client = AzureOpenAIEmbeddings(
            api_key=settings.azure_openai_api_key,
            azure_endpoint=settings.azure_openai_endpoint,
            deployment=settings.azure_openai_embedding_deployment,
            api_version=settings.azure_openai_embedding_api_version,
            chunk_size=1000
        )

    async def ensure_index_exists(self) -> bool:
        """确保搜索索引存在，如果不存在则创建"""
        try:
            # 检查索引是否存在
            try:
                self.index_client.get_index(settings.azure_search_index_name)
                print(f"✅ 索引 '{settings.azure_search_index_name}' 已存在")
                return True
            except Exception:
                print(f"索引 '{settings.azure_search_index_name}' 不存在，正在创建...")

            # 创建索引
            fields = [
                SimpleField(
                    name="id",
                    type=SearchFieldDataType.String,
                    key=True,
                    filterable=True,
                ),
                SearchableField(
                    name="content",
                    type=SearchFieldDataType.String,
                    searchable=True,
                    retrievable=True,
                ),
                SearchField(
                    name="content_vector",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    searchable=True,
                    vector_search_dimensions=settings.embedding_dimension,
                    vector_search_profile_name="my-vector-config",
                ),
                SimpleField(
                    name="title",
                    type=SearchFieldDataType.String,
                    filterable=True,
                    searchable=True,
                ),
                SimpleField(
                    name="file_path",
                    type=SearchFieldDataType.String,
                    filterable=True,
                ),
                SimpleField(
                    name="chunk_index",
                    type=SearchFieldDataType.Int32,
                    filterable=True,
                ),
                SimpleField(
                    name="quality_score",
                    type=SearchFieldDataType.Double,
                    filterable=True,
                    sortable=True,
                ),
                SimpleField(
                    name="created_at",
                    type=SearchFieldDataType.DateTimeOffset,
                    filterable=True,
                    sortable=True,
                ),
                SimpleField(
                    name="metadata",
                    type=SearchFieldDataType.String,
                    retrievable=True,
                ),
            ]

            # 向量搜索配置
            vector_search = VectorSearch(
                algorithms=[
                    HnswAlgorithmConfiguration(
                        name="my-hnsw-config",
                        parameters={
                            "m": 4,
                            "efConstruction": 400,
                            "efSearch": 500,
                            "metric": "cosine"
                        }
                    )
                ],
                profiles=[
                    VectorSearchProfile(
                        name="my-vector-config",
                        algorithm_configuration_name="my-hnsw-config",
                    )
                ]
            )

            # 语义搜索配置
            semantic_config = SemanticConfiguration(
                name="my-semantic-config",
                prioritized_fields=SemanticPrioritizedFields(
                    content_fields=[
                        SemanticField(field_name="content")
                    ],
                    title_field=SemanticField(field_name="title")
                )
            )

            semantic_search = SemanticSearch(
                configurations=[semantic_config]
            )

            # 创建索引
            index = SearchIndex(
                name=settings.azure_search_index_name,
                fields=fields,
                vector_search=vector_search,
                semantic_search=semantic_search,
            )

            result = self.index_client.create_index(index)
            print(f"✅ 成功创建索引: {result.name}")
            return True

        except Exception as e:
            print(f"❌ 创建索引失败: {str(e)}")
            return False

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """使用 Azure OpenAI 生成文本向量"""
        try:
            embeddings = await self.embedding_client.aembed_documents(texts)
            return embeddings
        except Exception as e:
            print(f"❌ 生成embeddings失败: {str(e)}")
            return [[0.0] * settings.embedding_dimension for _ in texts]

    async def generate_single_embedding(self, text: str) -> List[float]:
        """生成单个文本的向量"""
        try:
            embedding = await self.embedding_client.aembed_query(text)
            return embedding
        except Exception as e:
            print(f"❌ 生成单个embedding失败: {str(e)}")
            return [0.0] * settings.embedding_dimension

    async def add_documents(self, documents: List[Dict[str, Any]]) -> List[str]:
        """添加文档到搜索索引"""
        try:
            # 确保索引存在
            await self.ensure_index_exists()

            # 准备文档数据
            search_documents = []
            doc_ids = []

            for doc in documents:
                doc_id = str(uuid.uuid4())
                doc_ids.append(doc_id)

                # 生成内容向量
                content = doc.get("content", "")
                content_vector = await self.generate_single_embedding(content)

                search_doc = {
                    "id": doc_id,
                    "content": content,
                    "content_vector": content_vector,
                    "title": doc.get("title", ""),
                    "file_path": doc.get("file_path", ""),
                    "chunk_index": doc.get("chunk_index", 0),
                    "quality_score": doc.get("quality_score", 0.0),
                    "created_at": datetime.utcnow().isoformat() + "Z",
                    "metadata": json.dumps(doc.get("metadata", {}))
                }
                search_documents.append(search_doc)

            # 批量上传文档
            result = self.search_client.upload_documents(search_documents)

            successful_uploads = [doc_id for doc_id, success in zip(doc_ids, result) if success.succeeded]
            print(f"✅ 成功上传 {len(successful_uploads)}/{len(documents)} 个文档到搜索索引")

            return successful_uploads

        except Exception as e:
            print(f"❌ 添加文档到搜索索引失败: {str(e)}")
            return []

    async def search_documents(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.7,
        use_semantic_search: bool = True
    ) -> List[Dict[str, Any]]:
        """搜索相关文档"""
        try:
            # 生成查询向量
            query_vector = await self.generate_single_embedding(query)

            # 创建向量查询
            vector_query = VectorizedQuery(
                vector=query_vector,
                k_nearest_neighbors=top_k,
                fields="content_vector"
            )

            # 执行搜索
            search_params = {
                "search_text": query if use_semantic_search else None,
                "vector_queries": [vector_query],
                "select": ["id", "content", "title", "file_path", "chunk_index", "quality_score", "metadata"],
                "top": top_k,
            }

            if use_semantic_search:
                search_params["query_type"] = "semantic"
                search_params["semantic_configuration_name"] = "my-semantic-config"
                search_params["query_caption"] = "extractive"
                search_params["query_answer"] = "extractive"

            results = self.search_client.search(**search_params)

            # 处理搜索结果
            documents = []
            for result in results:
                # 计算相似度分数
                score = result.get("@search.score", 0.0)
                if score >= min_score:
                    documents.append({
                        "id": result["id"],
                        "content": result["content"],
                        "title": result["title"],
                        "file_path": result["file_path"],
                        "chunk_index": result["chunk_index"],
                        "quality_score": result["quality_score"],
                        "similarity": score,
                        "metadata": json.loads(result.get("metadata", "{}")),
                        "captions": result.get("@search.captions", []),
                        "answers": result.get("@search.answers", [])
                    })

            print(f"🔍 找到 {len(documents)} 个相关文档，分数阈值: {min_score}")
            return documents

        except Exception as e:
            print(f"❌ 搜索文档失败: {str(e)}")
            return []

    async def delete_documents_by_file(self, file_path: str) -> bool:
        """删除指定文件的所有文档"""
        try:
            # 搜索该文件的所有文档
            results = self.search_client.search(
                search_text="*",
                filter=f"file_path eq '{file_path}'",
                select=["id"]
            )

            # 获取文档ID列表
            doc_ids = [result["id"] for result in results]

            if not doc_ids:
                print(f"未找到文件 {file_path} 的文档")
                return True

            # 删除文档
            delete_docs = [{"id": doc_id} for doc_id in doc_ids]
            result = self.search_client.delete_documents(delete_docs)

            successful_deletes = sum(1 for r in result if r.succeeded)
            print(f"✅ 成功删除 {successful_deletes}/{len(doc_ids)} 个文档")

            return successful_deletes == len(doc_ids)

        except Exception as e:
            print(f"❌ 删除文档失败: {str(e)}")
            return False

    async def get_index_stats(self) -> Dict[str, Any]:
        """获取索引统计信息"""
        try:
            # 获取文档总数
            results = self.search_client.search(
                search_text="*",
                include_total_count=True,
                top=0
            )

            total_docs = results.get_count()

            # 获取索引信息
            index_info = self.index_client.get_index(settings.azure_search_index_name)

            return {
                "index_name": settings.azure_search_index_name,
                "total_documents": total_docs,
                "index_size": index_info.name,
                "embedding_dimension": settings.embedding_dimension,
                "created_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            print(f"❌ 获取索引统计失败: {str(e)}")
            return {}

    async def clear_index(self) -> bool:
        """清空索引中的所有文档"""
        try:
            # 获取所有文档ID
            results = self.search_client.search(
                search_text="*",
                select=["id"]
            )

            doc_ids = [result["id"] for result in results]

            if not doc_ids:
                print("索引中没有文档需要清空")
                return True

            # 批量删除文档
            delete_docs = [{"id": doc_id} for doc_id in doc_ids]
            result = self.search_client.delete_documents(delete_docs)

            successful_deletes = sum(1 for r in result if r.succeeded)
            print(f"✅ 成功清空索引，删除了 {successful_deletes} 个文档")

            return successful_deletes == len(doc_ids)

        except Exception as e:
            print(f"❌ 清空索引失败: {str(e)}")
            return False


# 创建全局服务实例
azure_search_service = AzureSearchService()