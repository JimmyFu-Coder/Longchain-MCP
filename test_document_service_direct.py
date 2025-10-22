#!/usr/bin/env python3
# test_document_service_direct.py - 直接测试文档处理服务

import asyncio
import tempfile
import os
from app.services.document_service import document_processor, embedding_service, process_document_complete

async def test_text_extraction():
    """测试文本提取"""
    print("🧪 测试文本提取...")

    # 创建测试文件
    content = """这是一个测试文档。

第一段：介绍
这个系统可以处理PDF、Word和文本文件。

第二段：功能
系统会将文档分割成较小的片段，并生成向量嵌入。

第三段：技术
使用本地embedding模型进行向量化处理。"""

    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
    temp_file.write(content)
    temp_file.close()

    try:
        # 测试文本提取
        extracted_text = await document_processor.extract_text_from_file(temp_file.name)
        print(f"✅ 文本提取成功，长度: {len(extracted_text)}")
        print(f"提取的文本预览: {extracted_text[:100]}...")
        return temp_file.name, extracted_text
    except Exception as e:
        print(f"❌ 文本提取失败: {e}")
        return None, None
    finally:
        pass  # 暂时不删除，供后续测试使用

def test_text_chunking():
    """测试文本分割"""
    print("\n🧪 测试文本分割...")

    text = """这是第一段内容，包含一些基本信息和介绍。这段内容应该被分割成一个chunk。

这是第二段内容，描述了系统的主要功能。这段内容也应该被合理地分割。

这是第三段内容，说明了技术实现细节。分割算法会根据段落边界进行智能分割。

这是第四段内容，包含了更多的详细信息。系统会确保每个chunk的大小在合理范围内。

这是最后一段内容，总结了整个文档的要点。分割时会考虑语义的连贯性。"""

    try:
        chunks = document_processor.chunk_text(text)
        print(f"✅ 文本分割成功，共生成 {len(chunks)} 个chunks")

        for i, chunk in enumerate(chunks):
            print(f"Chunk {i}: 长度={chunk['length']}, 内容预览='{chunk['text'][:50]}...'")

        return chunks
    except Exception as e:
        print(f"❌ 文本分割失败: {e}")
        return []

async def test_embedding_generation():
    """测试embedding生成"""
    print("\n🧪 测试embedding生成...")

    test_texts = [
        "这是第一个测试文本，用于验证embedding功能。",
        "这是第二个测试文本，内容与第一个不同。",
        "This is an English text for testing multilingual embedding."
    ]

    try:
        # 首先测试模型加载
        print("正在加载embedding模型...")
        model = embedding_service._load_model()

        if model is None:
            print("⚠️ 模型未加载，将使用模拟embedding")
        else:
            print(f"✅ 模型加载成功: {embedding_service.model_name}")
            print(f"Embedding维度: {embedding_service.embedding_dim}")

        # 生成embeddings
        embeddings = await embedding_service.generate_embeddings(test_texts)
        print(f"✅ Embedding生成成功")
        print(f"生成了 {len(embeddings)} 个embedding向量")

        if embeddings:
            print(f"每个向量的维度: {len(embeddings[0])}")
            print(f"第一个向量的前5个值: {embeddings[0][:5]}")

        return embeddings
    except Exception as e:
        print(f"❌ Embedding生成失败: {e}")
        return []

async def test_complete_process():
    """测试完整处理流程"""
    print("\n🧪 测试完整处理流程...")

    # 创建测试文件
    content = """文档处理系统测试

概述
这是一个完整的文档处理测试。系统会提取文本、进行分割，并生成embedding向量。

功能特性
1. 支持多种文件格式：PDF、Word、TXT
2. 智能文本分割，保持语义连贯
3. 本地embedding生成，保护数据隐私
4. 高效的批处理能力

技术架构
系统采用模块化设计，包含文档处理器和embedding服务两个核心组件。
文档处理器负责文本提取和分割，embedding服务负责向量化。

应用场景
适用于构建RAG系统、文档检索、语义搜索等应用。
可以处理大量文档并生成高质量的向量表示。"""

    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
    temp_file.write(content)
    temp_file.close()

    file_info = {
        "original_name": "test_complete.txt",
        "saved_name": os.path.basename(temp_file.name),
        "file_path": temp_file.name,
        "size": len(content.encode('utf-8')),
        "type": "text/plain"
    }

    try:
        result = await process_document_complete(temp_file.name, file_info)

        if result["success"]:
            print("✅ 完整处理流程成功")
            print(f"原始文本长度: {result['text_length']}")
            print(f"分割chunk数量: {result['chunk_count']}")

            if result['chunks']:
                first_chunk = result['chunks'][0]
                print(f"第一个chunk长度: {first_chunk['length']}")
                print(f"embedding维度: {len(first_chunk['embedding']) if first_chunk.get('embedding') else 'None'}")

            return True
        else:
            print(f"❌ 完整处理失败: {result['error']}")
            return False

    except Exception as e:
        print(f"❌ 完整处理异常: {e}")
        return False
    finally:
        os.unlink(temp_file.name)

async def main():
    print("🚀 开始直接测试文档处理服务")
    print("=" * 60)

    # 测试各个组件
    file_path, text = await test_text_extraction()
    chunks = test_text_chunking()
    embeddings = await test_embedding_generation()
    complete_success = await test_complete_process()

    # 清理测试文件
    if file_path and os.path.exists(file_path):
        os.unlink(file_path)

    print("\n" + "=" * 60)
    print("🎉 测试完成！")

    # 总结结果
    print("\n📊 测试结果:")
    print(f"  ✅ 文本提取: {'成功' if text else '失败'}")
    print(f"  ✅ 文本分割: {'成功' if chunks else '失败'}")
    print(f"  ✅ Embedding生成: {'成功' if embeddings else '失败'}")
    print(f"  ✅ 完整流程: {'成功' if complete_success else '失败'}")

if __name__ == "__main__":
    asyncio.run(main())