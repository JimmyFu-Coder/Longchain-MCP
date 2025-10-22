# debug_similarity.py
import asyncio
from app.services.vector_store import vector_store
from app.services.document_service import embedding_service

async def debug_similarity():
    """调试相似度计算"""
    print("🔍 调试相似度计算...")

    # 获取向量存储中的数据
    stats = vector_store.get_stats()
    print(f"向量存储统计: {stats}")

    if stats['total_chunks'] == 0:
        print("❌ 向量存储中没有chunks")
        return

    # 显示存储的chunks内容
    print("\n📄 存储的文档内容:")
    for file_path in stats['files']:
        chunks = vector_store.get_chunks_by_file(file_path)
        for i, chunk in enumerate(chunks):
            print(f"Chunk {i}: {chunk['text'][:200]}...")

    # 测试查询
    test_query = "RBAC"
    print(f"\n🔍 测试查询: '{test_query}'")

    # 生成查询embedding
    query_embedding = await embedding_service.generate_single_embedding(test_query)
    print(f"查询embedding维度: {len(query_embedding)}")

    # 获取所有相似度（不设阈值）
    similar_chunks = vector_store.search_similar_chunks(
        query_embedding=query_embedding,
        top_k=10,
        min_similarity=0.0  # 不设阈值，看所有结果
    )

    print(f"\n📊 相似度结果 (总计 {len(similar_chunks)} 个):")
    for chunk in similar_chunks:
        print(f"- 相似度: {chunk['similarity']:.4f}")
        print(f"  内容: {chunk['text'][:100]}...")
        print()

if __name__ == "__main__":
    asyncio.run(debug_similarity())