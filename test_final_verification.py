#!/usr/bin/env python3
"""
最终验证脚本 - 测试所有Azure AI Search功能
不依赖语义搜索功能
"""

import asyncio
import sys
import tempfile
import os
from pathlib import Path
from datetime import datetime

# 确保可以导入应用模块
sys.path.append(str(Path(__file__).parent))

from app.core.config import settings
from app.services.azure_search_service import azure_search_service

async def test_basic_vector_search():
    """测试基础向量搜索（不使用语义搜索）"""
    print("🔍 测试基础向量搜索...")

    try:
        # 首先添加一些测试文档
        test_documents = [
            {
                "content": "Azure AI Search is a powerful cloud search service that provides full-text search capabilities.",
                "title": "Azure AI Search Overview",
                "file_path": "test/overview.txt",
                "chunk_index": 0,
                "quality_score": 0.9,
                "metadata": {"source": "test", "type": "overview"}
            },
            {
                "content": "Vector search allows you to find similar documents using embeddings and similarity calculations.",
                "title": "Vector Search Guide",
                "file_path": "test/vector_guide.txt",
                "chunk_index": 0,
                "quality_score": 0.8,
                "metadata": {"source": "test", "type": "guide"}
            }
        ]

        # 添加文档
        doc_ids = await azure_search_service.add_documents(test_documents)

        if doc_ids and len(doc_ids) > 0:
            print(f"✅ 成功添加 {len(doc_ids)} 个测试文档")

            # 等待索引更新
            import asyncio
            await asyncio.sleep(2)

            # 测试向量搜索（不使用语义搜索）
            query = "What is Azure search service?"

            results = await azure_search_service.search_documents(
                query=query,
                top_k=5,
                min_score=0.0,  # 降低阈值
                use_semantic_search=False  # 关闭语义搜索
            )

            if results:
                print(f"✅ 向量搜索成功，找到 {len(results)} 个结果")
                for i, result in enumerate(results, 1):
                    print(f"   结果{i}: 相似度={result['similarity']:.3f}, 标题='{result['title']}'")
                return True
            else:
                print("❌ 向量搜索没有找到结果")
                return False
        else:
            print("❌ 添加文档失败")
            return False

    except Exception as e:
        print(f"❌ 向量搜索测试失败: {str(e)}")
        return False

async def test_document_processing_workflow():
    """测试完整的文档处理工作流"""
    print("\n📄 测试文档处理工作流...")

    try:
        # 创建测试文档
        test_content = """
        Azure Cognitive Search is a cloud-based search service that offers the following features:

        1. Full-text search with advanced query capabilities
        2. AI-powered search with cognitive skills
        3. Vector search for semantic similarity
        4. Faceted navigation and filtering
        5. Auto-complete and suggestions

        This service integrates with various data sources and provides REST APIs
        for easy integration into applications.
        """

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(test_content)
            temp_file = f.name

        try:
            # 处理文档 (模拟document service功能)
            from app.services.azure_document_service import azure_document_service

            file_info = {
                "original_name": "azure_search_features.txt",
                "file_size": len(test_content),
                "file_type": ".txt",
                "upload_time": datetime.now().isoformat()
            }

            result = await azure_document_service.process_and_index_document(
                temp_file, file_info, return_best=3
            )

            if result["success"]:
                print(f"✅ 文档处理成功")
                print(f"   总块数: {result['total_chunks']}")
                print(f"   索引块数: {result['indexed_chunks']}")
                print(f"   文档ID数: {len(result['document_ids'])}")
                return True
            else:
                print(f"❌ 文档处理失败: {result['error']}")
                return False

        finally:
            # 清理临时文件
            os.unlink(temp_file)

    except Exception as e:
        print(f"❌ 文档处理测试失败: {str(e)}")
        return False

async def test_rag_context_retrieval():
    """测试RAG上下文检索"""
    print("\n🤖 测试RAG上下文检索...")

    try:
        from app.services.rag_service import rag_service

        query = "What are the features of Azure Cognitive Search?"

        # 获取相关上下文
        context_result = await rag_service.retrieve_relevant_context(query)

        if context_result["has_context"]:
            print(f"✅ RAG上下文检索成功")
            print(f"   上下文块数: {context_result['chunk_count']}")
            print(f"   上下文长度: {context_result['total_context_length']}")
            print(f"   语义搜索: {context_result.get('semantic_search_used', False)}")

            # 测试RAG处理
            rag_result = await rag_service.process_query_with_rag(query)

            if rag_result["enhanced_prompt"]:
                print(f"✅ RAG查询处理成功")
                print(f"   增强提示长度: {len(rag_result['enhanced_prompt'])}")
                return True
            else:
                print("❌ RAG查询处理失败")
                return False
        else:
            print("❌ 未检索到相关上下文")
            return False

    except Exception as e:
        print(f"❌ RAG测试失败: {str(e)}")
        return False

async def test_index_stats():
    """测试索引统计"""
    print("\n📊 测试索引统计...")

    try:
        stats = await azure_search_service.get_index_stats()

        if stats:
            print(f"✅ 索引统计获取成功")
            print(f"   索引名称: {stats.get('index_name')}")
            print(f"   文档总数: {stats.get('total_documents')}")
            print(f"   向量维度: {stats.get('embedding_dimension')}")
            return True
        else:
            print("❌ 无法获取索引统计")
            return False

    except Exception as e:
        print(f"❌ 索引统计测试失败: {str(e)}")
        return False

async def main():
    """主测试函数"""
    print("🎯 Azure AI Search 最终验证测试")
    print("🔕 不使用语义搜索功能")
    print("=" * 60)

    tests = [
        ("索引统计", test_index_stats),
        ("基础向量搜索", test_basic_vector_search),
        ("文档处理工作流", test_document_processing_workflow),
        ("RAG上下文检索", test_rag_context_retrieval)
    ]

    results = {}

    for test_name, test_func in tests:
        print(f"\n{'=' * 20} {test_name} {'=' * 20}")
        try:
            result = await test_func()
            results[test_name] = result
        except Exception as e:
            print(f"❌ {test_name} 测试异常: {str(e)}")
            results[test_name] = False

    # 总结报告
    print("\n" + "=" * 60)
    print("🏁 最终验证报告")
    print("=" * 60)

    passed = 0
    total = len(results)

    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status:<10} {test_name}")
        if result:
            passed += 1

    print(f"\n📊 总体状态: {passed}/{total} 项通过")

    if passed == total:
        print("🎉 所有测试通过！Azure AI Search 服务完全正常")
        print("\n🚀 你的Azure AI Search系统现在可以正常使用了！")
        print("包括的功能:")
        print("   ✅ 向量搜索")
        print("   ✅ 文档处理和索引")
        print("   ✅ RAG上下文检索")
        print("   ✅ Embedding生成")
        print("   ⚠️  语义搜索 (需要Azure Search高级服务)")
    else:
        print("⚠️  部分功能需要进一步调试")

if __name__ == "__main__":
    asyncio.run(main())