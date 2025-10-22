#!/usr/bin/env python3
# test_document_processing.py - 测试文档处理和embedding功能

import requests
import json
import tempfile
import os

# API端点
BASE_URL = "http://127.0.0.1:8000/api/files"
UPLOAD_URL = f"{BASE_URL}/upload"
PROCESS_URL = f"{BASE_URL}/process"
UPLOAD_AND_PROCESS_URL = f"{BASE_URL}/upload-and-process"

def create_test_document():
    """创建测试文档"""
    content = """这是一个测试文档，用于验证文档处理功能。

第一章：介绍
这个系统可以处理PDF、Word和文本文件。它会将文档分割成较小的片段，并为每个片段生成向量嵌入。

第二章：功能特性
1. 文档上传和存储
2. 文本提取和清理
3. 智能分割（支持重叠）
4. 向量嵌入生成
5. 结构化数据返回

第三章：技术细节
系统使用Azure OpenAI的embedding API来生成高质量的文本向量。
分割算法会智能地处理段落边界，确保语义的连贯性。
每个文档片段都包含原始文本、位置信息和对应的向量嵌入。

结论
这个文档处理系统为构建RAG（检索增强生成）应用提供了完整的基础设施。
"""

    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
    temp_file.write(content)
    temp_file.close()
    return temp_file.name

def test_server_health():
    """测试服务器状态"""
    print("🏥 检查服务器状态...")
    try:
        response = requests.get("http://127.0.0.1:8000/", timeout=5)
        if response.status_code == 200:
            print("✅ 服务器运行正常")
            return True
        else:
            print(f"❌ 服务器状态异常: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ 无法连接到服务器: {e}")
        return False

def test_upload_only():
    """测试仅上传功能"""
    print("\n🧪 测试文件上传...")

    test_file = create_test_document()

    try:
        with open(test_file, 'rb') as f:
            files = {'files': ('test_document.txt', f, 'text/plain')}
            response = requests.post(UPLOAD_URL, files=files, timeout=30)

        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print("✅ 文件上传成功")
            print(f"上传的文件: {result['files'][0]['saved_name']}")
            return result['files'][0]['file_path']
        else:
            print(f"❌ 上传失败: {response.text}")
            return None

    except Exception as e:
        print(f"❌ 上传异常: {e}")
        return None
    finally:
        os.unlink(test_file)

def test_process_uploaded_file(file_path):
    """测试处理已上传的文件"""
    print("\n🧪 测试文档处理...")

    try:
        payload = {
            "file_path": file_path,
            "chunk_size": 500,
            "chunk_overlap": 100
        }

        response = requests.post(PROCESS_URL, json=payload, timeout=60)
        print(f"状态码: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print("✅ 文档处理成功")

            processing_result = result['result']
            print(f"原始文本长度: {processing_result['text_length']}")
            print(f"分割片段数量: {processing_result['chunk_count']}")

            # 显示第一个片段的信息
            if processing_result['chunks']:
                first_chunk = processing_result['chunks'][0]
                print(f"第一个片段长度: {first_chunk['length']}")
                print(f"第一个片段文本预览: {first_chunk['text'][:100]}...")

                if first_chunk.get('embedding'):
                    print(f"嵌入向量维度: {len(first_chunk['embedding'])}")
                    print(f"嵌入向量前5个值: {first_chunk['embedding'][:5]}")
                else:
                    print("⚠️ 未生成嵌入向量")

            return True
        else:
            print(f"❌ 处理失败: {response.text}")
            return False

    except Exception as e:
        print(f"❌ 处理异常: {e}")
        return False

def test_upload_and_process():
    """测试一步上传并处理"""
    print("\n🧪 测试一步上传并处理...")

    test_file = create_test_document()

    try:
        with open(test_file, 'rb') as f:
            files = {'files': ('test_document.txt', f, 'text/plain')}
            params = {
                'chunk_size': 300,
                'chunk_overlap': 50
            }
            response = requests.post(UPLOAD_AND_PROCESS_URL, files=files, params=params, timeout=60)

        print(f"状态码: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print("✅ 一步上传并处理成功")

            if result['results']:
                processing_result = result['results'][0]
                if processing_result['success']:
                    print(f"原始文本长度: {processing_result['text_length']}")
                    print(f"分割片段数量: {processing_result['chunk_count']}")

                    # 显示分割统计
                    chunks = processing_result['chunks']
                    avg_chunk_size = sum(chunk['length'] for chunk in chunks) / len(chunks)
                    print(f"平均片段长度: {avg_chunk_size:.1f}")

                    # 检查嵌入向量
                    embedded_chunks = [chunk for chunk in chunks if chunk.get('embedding')]
                    print(f"成功生成嵌入的片段: {len(embedded_chunks)}/{len(chunks)}")

                else:
                    print(f"❌ 处理失败: {processing_result['error']}")

            return True
        else:
            print(f"❌ 一步处理失败: {response.text}")
            return False

    except Exception as e:
        print(f"❌ 一步处理异常: {e}")
        return False
    finally:
        os.unlink(test_file)

def test_error_cases():
    """测试错误情况"""
    print("\n🧪 测试错误处理...")

    # 测试处理不存在的文件
    try:
        payload = {"file_path": "uploads/nonexistent.txt"}
        response = requests.post(PROCESS_URL, json=payload, timeout=10)

        if response.status_code == 404:
            print("✅ 正确处理不存在文件的情况")
        else:
            print(f"⚠️ 处理不存在文件返回状态码: {response.status_code}")

    except Exception as e:
        print(f"❌ 错误测试异常: {e}")

def main():
    print("🚀 开始测试文档处理和embedding功能")
    print("=" * 60)

    # 检查服务器状态
    if not test_server_health():
        print("\n❌ 服务器未运行，请先启动服务器")
        return

    # 测试上传
    uploaded_file_path = test_upload_only()

    if uploaded_file_path:
        # 测试处理已上传的文件
        test_process_uploaded_file(uploaded_file_path)

    # 测试一步上传并处理
    test_upload_and_process()

    # 测试错误情况
    test_error_cases()

    print("\n" + "=" * 60)
    print("🎉 测试完成！")

    print("\n📋 可用的API端点:")
    print(f"  📤 上传文件: POST {UPLOAD_URL}")
    print(f"  ⚙️  处理文件: POST {PROCESS_URL}")
    print(f"  🚀 上传并处理: POST {UPLOAD_AND_PROCESS_URL}")

if __name__ == "__main__":
    main()