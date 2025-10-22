# test_rag_system.py
import asyncio
import json
from app.services.document_service import process_document_complete
from app.services.vector_store import vector_store
from app.services.rag_service import rag_service

async def test_rag_system():
    """测试完整的RAG系统"""
    print("🧪 开始测试RAG系统...")

    # 1. 检查向量存储初始状态
    print("\n1. 向量存储初始状态:")
    stats = vector_store.get_stats()
    print(f"   总chunks: {stats['total_chunks']}")
    print(f"   总文件: {stats['total_files']}")

    # 2. 模拟文档处理（如果有上传的文件）
    import os
    upload_dir = "uploads"
    if os.path.exists(upload_dir):
        files = [f for f in os.listdir(upload_dir) if f.endswith('.pdf')]
        if files:
            print(f"\n2. 找到测试文件: {files[0]}")
            file_path = os.path.join(upload_dir, files[0])
            file_info = {
                "original_name": files[0],
                "file_path": file_path,
                "size": os.path.getsize(file_path)
            }

            # 处理文档
            result = await process_document_complete(file_path, file_info, return_best=5)

            if result["success"]:
                print(f"   ✅ 文档处理成功!")
                print(f"   - 总chunks: {result['total_chunks']}")
                print(f"   - 文本长度: {result['text_length']}")
                print(f"   - 向量存储统计: {result['vector_store_stats']}")
            else:
                print(f"   ❌ 文档处理失败: {result['error']}")
                return
        else:
            print("\n2. ⚠️ 没有找到PDF文件用于测试")
            return
    else:
        print("\n2. ⚠️ 上传目录不存在")
        return

    # 3. 测试RAG检索
    print("\n3. 测试RAG检索:")
    test_queries = [
        "什么是RBAC?",
        "用户权限是如何管理的?",
        "系统有什么功能?",
        "完全无关的问题测试"
    ]

    for query in test_queries:
        print(f"\n   查询: {query}")
        rag_result = await rag_service.process_query_with_rag(query)

        context_info = rag_result["context_info"]
        if context_info["has_context"]:
            print(f"   ✅ 找到 {context_info['chunk_count']} 个相关片段")
            print(f"   📝 上下文长度: {context_info['total_context_length']} 字符")

            # 显示来源信息
            for i, source in enumerate(context_info["sources"][:2]):  # 只显示前2个
                print(f"   📄 片段{i+1}: {source['original_name']} (相似度: {source['similarity']:.3f})")
        else:
            print(f"   ❌ 未找到相关内容")
            if "error" in context_info:
                print(f"   错误: {context_info['error']}")

if __name__ == "__main__":
    asyncio.run(test_rag_system())