#!/usr/bin/env python3
# test_azure_integration.py
"""
测试 Azure AI Search 集成
运行此脚本以验证所有组件是否正常工作
"""

import asyncio
import os
import tempfile
from datetime import datetime
from pathlib import Path

# 确保可以导入应用模块
import sys
sys.path.append(str(Path(__file__).parent))

from app.core.config import settings
from app.services.azure_search_service import azure_search_service
from app.services.azure_document_service import azure_document_service
from app.services.rag_service import rag_service
from app.services.llm_service import process_prompt, stream_prompt


class AzureIntegrationTester:
    """Azure AI Search 集成测试器"""

    def __init__(self):
        self.test_results = []
        self.start_time = datetime.now()

    def log_test(self, test_name: str, success: bool, message: str = "", data: dict = None):
        """记录测试结果"""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "data": data or {},
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)

        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")

        if data and success:
            for key, value in data.items():
                print(f"   - {key}: {value}")

    async def test_configuration(self):
        """测试配置"""
        print("\n🔧 Testing Configuration...")

        try:
            # 检查必需的配置项
            required_configs = [
                "azure_openai_endpoint",
                "azure_openai_api_key",
                "azure_search_endpoint",
                "azure_search_key",
                "azure_search_index_name"
            ]

            missing_configs = []
            for config in required_configs:
                if not hasattr(settings, config) or not getattr(settings, config):
                    missing_configs.append(config)

            if missing_configs:
                self.log_test(
                    "Configuration Check",
                    False,
                    f"Missing configurations: {', '.join(missing_configs)}"
                )
                return False

            self.log_test(
                "Configuration Check",
                True,
                "All required configurations present",
                {
                    "search_endpoint": settings.azure_search_endpoint,
                    "search_index": settings.azure_search_index_name,
                    "embedding_dimension": settings.embedding_dimension
                }
            )
            return True

        except Exception as e:
            self.log_test("Configuration Check", False, f"Error: {str(e)}")
            return False

    async def test_azure_search_connection(self):
        """测试 Azure AI Search 连接"""
        print("\n🔍 Testing Azure AI Search Connection...")

        try:
            # 尝试获取索引统计
            stats = await azure_search_service.get_index_stats()

            if "error" in str(stats).lower():
                self.log_test("Azure Search Connection", False, f"Connection failed: {stats}")
                return False

            self.log_test(
                "Azure Search Connection",
                True,
                "Successfully connected to Azure AI Search",
                stats
            )
            return True

        except Exception as e:
            self.log_test("Azure Search Connection", False, f"Connection error: {str(e)}")
            return False

    async def test_index_creation(self):
        """测试索引创建"""
        print("\n📊 Testing Index Creation...")

        try:
            # 确保索引存在
            success = await azure_search_service.ensure_index_exists()

            if success:
                self.log_test(
                    "Index Creation",
                    True,
                    f"Index '{settings.azure_search_index_name}' is ready"
                )
                return True
            else:
                self.log_test("Index Creation", False, "Failed to create or verify index")
                return False

        except Exception as e:
            self.log_test("Index Creation", False, f"Index creation error: {str(e)}")
            return False

    async def test_embedding_generation(self):
        """测试向量生成"""
        print("\n🔤 Testing Embedding Generation...")

        try:
            test_text = "This is a test document for embedding generation."

            # 生成单个embedding
            embedding = await azure_search_service.generate_single_embedding(test_text)

            if embedding and len(embedding) == settings.embedding_dimension:
                self.log_test(
                    "Embedding Generation",
                    True,
                    "Successfully generated embeddings",
                    {
                        "embedding_dimension": len(embedding),
                        "expected_dimension": settings.embedding_dimension,
                        "first_few_values": embedding[:5]
                    }
                )
                return True
            else:
                self.log_test(
                    "Embedding Generation",
                    False,
                    f"Invalid embedding: length={len(embedding) if embedding else 0}"
                )
                return False

        except Exception as e:
            self.log_test("Embedding Generation", False, f"Embedding error: {str(e)}")
            return False

    async def test_document_processing(self):
        """测试文档处理和索引"""
        print("\n📄 Testing Document Processing...")

        try:
            # 创建测试文档
            test_content = """
            Azure AI Search is a cloud search service that provides infrastructure,
            APIs, and tools for building a rich search experience over private,
            heterogeneous content in web, mobile, and enterprise applications.

            Key features include:
            - Full-text search with lexical analysis
            - AI-powered search with semantic search capabilities
            - Vector search for similarity-based retrieval
            - Hybrid search combining multiple search techniques
            """

            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(test_content)
                temp_file = f.name

            try:
                # 处理文档
                file_info = {
                    "original_name": "test_document.txt",
                    "file_size": len(test_content),
                    "file_type": ".txt",
                    "upload_time": datetime.now().isoformat()
                }

                result = await azure_document_service.process_and_index_document(
                    temp_file, file_info, return_best=3
                )

                if result["success"]:
                    self.log_test(
                        "Document Processing",
                        True,
                        "Successfully processed and indexed document",
                        {
                            "total_chunks": result["total_chunks"],
                            "indexed_chunks": result["indexed_chunks"],
                            "document_ids_count": len(result["document_ids"]),
                            "quality_filtered": result["quality_filtered"]
                        }
                    )
                    return True
                else:
                    self.log_test("Document Processing", False, f"Processing failed: {result['error']}")
                    return False

            finally:
                # 清理临时文件
                os.unlink(temp_file)

        except Exception as e:
            self.log_test("Document Processing", False, f"Processing error: {str(e)}")
            return False

    async def test_search_functionality(self):
        """测试搜索功能"""
        print("\n🔍 Testing Search Functionality...")

        try:
            # 测试语义搜索
            query = "What are the key features of Azure AI Search?"

            results = await azure_search_service.search_documents(
                query=query,
                top_k=3,
                min_score=0.1,  # 降低阈值以确保能找到结果
                use_semantic_search=True
            )

            if results:
                self.log_test(
                    "Search Functionality",
                    True,
                    f"Found {len(results)} relevant documents",
                    {
                        "query": query,
                        "results_count": len(results),
                        "top_score": max(r["similarity"] for r in results),
                        "semantic_search": True
                    }
                )
                return True
            else:
                self.log_test("Search Functionality", False, "No search results found")
                return False

        except Exception as e:
            self.log_test("Search Functionality", False, f"Search error: {str(e)}")
            return False

    async def test_rag_pipeline(self):
        """测试完整的RAG流水线"""
        print("\n🤖 Testing RAG Pipeline...")

        try:
            query = "Explain the key features of Azure AI Search"

            # 测试RAG上下文检索
            context_result = await rag_service.retrieve_relevant_context(query)

            if context_result["has_context"]:
                self.log_test(
                    "RAG Context Retrieval",
                    True,
                    "Successfully retrieved context",
                    {
                        "chunk_count": context_result["chunk_count"],
                        "context_length": context_result["total_context_length"],
                        "semantic_search_used": context_result.get("semantic_search_used", False)
                    }
                )

                # 测试完整的RAG流程
                rag_result = await rag_service.process_query_with_rag(query)

                if rag_result["enhanced_prompt"]:
                    self.log_test(
                        "RAG Pipeline",
                        True,
                        "Successfully processed query with RAG",
                        {
                            "original_query": query,
                            "enhanced_prompt_length": len(rag_result["enhanced_prompt"]),
                            "context_info": rag_result["context_info"]["has_context"]
                        }
                    )
                    return True
                else:
                    self.log_test("RAG Pipeline", False, "Failed to generate enhanced prompt")
                    return False
            else:
                self.log_test("RAG Context Retrieval", False, "No context retrieved")
                return False

        except Exception as e:
            self.log_test("RAG Pipeline", False, f"RAG error: {str(e)}")
            return False

    async def test_llm_integration(self):
        """测试LLM集成（仅测试非流式以避免token消耗）"""
        print("\n🧠 Testing LLM Integration...")

        try:
            # 注意：这将实际调用LLM，会消耗token
            print("   ⚠️  This test will consume Azure OpenAI tokens")

            query = "What is Azure AI Search in one sentence?"

            # 测试非流式处理
            result = await process_prompt(query, use_rag=True)

            if result["response"]:
                self.log_test(
                    "LLM Integration",
                    True,
                    "Successfully got LLM response with RAG",
                    {
                        "response_length": len(result["response"]),
                        "token_usage": result["token_usage"],
                        "context_used": result["context_info"]["has_context"]
                    }
                )
                return True
            else:
                self.log_test("LLM Integration", False, "No response from LLM")
                return False

        except Exception as e:
            self.log_test("LLM Integration", False, f"LLM error: {str(e)}")
            return False

    async def cleanup_test_data(self):
        """清理测试数据"""
        print("\n🧹 Cleaning up test data...")

        try:
            # 可选：清理测试索引数据
            # success = await azure_search_service.clear_index()
            # 为了安全起见，我们不自动清理数据

            self.log_test(
                "Cleanup",
                True,
                "Test completed (manual cleanup may be needed)"
            )

        except Exception as e:
            self.log_test("Cleanup", False, f"Cleanup error: {str(e)}")

    def print_summary(self):
        """打印测试摘要"""
        print("\n" + "="*60)
        print("🏁 TEST SUMMARY")
        print("="*60)

        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r["success"])
        failed_tests = total_tests - passed_tests

        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")

        duration = datetime.now() - self.start_time
        print(f"Duration: {duration.total_seconds():.2f} seconds")

        if failed_tests > 0:
            print("\n❌ Failed Tests:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"   - {result['test']}: {result['message']}")

        print("\n" + "="*60)

    async def run_all_tests(self, skip_llm: bool = True):
        """运行所有测试"""
        print("🚀 Starting Azure AI Search Integration Tests")
        print(f"Timestamp: {self.start_time.isoformat()}")

        # 基础测试
        await self.test_configuration()
        await self.test_azure_search_connection()
        await self.test_index_creation()
        await self.test_embedding_generation()

        # 功能测试
        await self.test_document_processing()
        await self.test_search_functionality()
        await self.test_rag_pipeline()

        # LLM集成测试（可选）
        if not skip_llm:
            await self.test_llm_integration()
        else:
            print("\n🧠 Skipping LLM Integration test (to avoid token consumption)")

        # 清理
        await self.cleanup_test_data()

        # 打印摘要
        self.print_summary()


async def main():
    """主函数"""
    tester = AzureIntegrationTester()

    # 运行测试，默认跳过LLM测试以避免消耗token
    await tester.run_all_tests(skip_llm=True)

    # 如果要测试LLM集成，取消下面的注释
    # await tester.run_all_tests(skip_llm=False)


if __name__ == "__main__":
    asyncio.run(main())