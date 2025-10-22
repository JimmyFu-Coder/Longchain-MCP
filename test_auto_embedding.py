#!/usr/bin/env python3
# test_auto_embedding.py - 测试自动embedding功能

import requests
import tempfile
import os

BASE_URL = "http://127.0.0.1:8000/api/files"

def create_test_document():
    """创建测试文档"""
    content = """人工智能文档处理系统

第一章：系统概述
本系统是一个基于Python的文档处理平台，能够自动处理PDF、Word和文本文件。
系统的核心功能包括文本提取、智能分割和向量嵌入生成。

第二章：技术架构
系统采用FastAPI作为Web框架，使用sentence-transformers进行本地embedding。
文档处理流程包括：文件上传 → 文本提取 → 智能分割 → 向量生成。

第三章：应用场景
适用于构建RAG系统、文档检索、知识库管理等应用。
支持中英文混合处理，具有良好的扩展性和性能。

第四章：部署说明
系统支持本地部署，使用CPU版本的PyTorch，对硬件要求较低。
可以轻松集成到现有的应用架构中。
"""

    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
    temp_file.write(content)
    temp_file.close()
    return temp_file.name, content

def test_auto_embedding_upload():
    """测试自动embedding的上传功能"""
    print("🧪 测试自动embedding上传...")

    test_file, original_content = create_test_document()

    try:
        with open(test_file, 'rb') as f:
            files = {'files': ('ai_document.txt', f, 'text/plain')}
            # 测试默认参数（自动处理）
            response = requests.post(f"{BASE_URL}/upload", files=files, timeout=60)

        print(f"状态码: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print("✅ 自动embedding处理成功")
            print(f"auto_process: {result.get('auto_process', 'unknown')}")

            if result.get('results'):
                processing_result = result['results'][0]

                if processing_result.get('success'):
                    print(f"✅ 文档处理成功")
                    print(f"原始文本长度: {processing_result.get('text_length', 'N/A')}")
                    print(f"分割片段数: {processing_result.get('chunk_count', 'N/A')}")

                    chunks = processing_result.get('chunks', [])
                    if chunks:
                        first_chunk = chunks[0]
                        print(f"第一个片段长度: {first_chunk.get('length', 'N/A')}")

                        if first_chunk.get('embedding'):
                            print(f"embedding维度: {len(first_chunk['embedding'])}")
                            print(f"embedding前3个值: {first_chunk['embedding'][:3]}")
                        else:
                            print("⚠️ 未生成embedding")

                    return True
                else:
                    print(f"❌ 文档处理失败: {processing_result.get('error', 'Unknown error')}")
                    return False
            else:
                print("❌ 没有处理结果")
                return False
        else:
            print(f"❌ 上传失败: {response.text}")
            return False

    except Exception as e:
        print(f"❌ 测试异常: {e}")
        return False
    finally:
        os.unlink(test_file)

def test_upload_without_processing():
    """测试禁用自动处理的上传"""
    print("\n🧪 测试禁用自动处理的上传...")

    test_file, _ = create_test_document()

    try:
        with open(test_file, 'rb') as f:
            files = {'files': ('no_process.txt', f, 'text/plain')}
            params = {'auto_process': 'false'}  # 禁用自动处理
            response = requests.post(f"{BASE_URL}/upload", files=files, params=params, timeout=30)

        print(f"状态码: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print("✅ 上传成功（无处理）")
            print(f"auto_process: {result.get('auto_process', 'unknown')}")

            if result.get('results'):
                upload_result = result['results'][0]
                if upload_result.get('success') and not upload_result.get('processed', True):
                    print("✅ 确认未进行文档处理")
                    return True
                else:
                    print("❌ 意外进行了文档处理")
                    return False
        else:
            print(f"❌ 上传失败: {response.text}")
            return False

    except Exception as e:
        print(f"❌ 测试异常: {e}")
        return False
    finally:
        os.unlink(test_file)

def test_upload_only_endpoint():
    """测试仅上传端点"""
    print("\n🧪 测试仅上传端点...")

    test_file, _ = create_test_document()

    try:
        with open(test_file, 'rb') as f:
            files = {'files': ('upload_only.txt', f, 'text/plain')}
            response = requests.post(f"{BASE_URL}/upload-only", files=files, timeout=30)

        print(f"状态码: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print("✅ 仅上传成功")

            if result.get('files'):
                file_info = result['files'][0]
                print(f"上传文件: {file_info.get('original_name')}")
                print(f"保存为: {file_info.get('saved_name')}")
                print(f"文件大小: {file_info.get('size')} bytes")
                return True
            else:
                print("❌ 未返回文件信息")
                return False
        else:
            print(f"❌ 仅上传失败: {response.text}")
            return False

    except Exception as e:
        print(f"❌ 测试异常: {e}")
        return False
    finally:
        os.unlink(test_file)

def test_custom_chunk_settings():
    """测试自定义分割参数"""
    print("\n🧪 测试自定义分割参数...")

    test_file, _ = create_test_document()

    try:
        with open(test_file, 'rb') as f:
            files = {'files': ('custom_chunk.txt', f, 'text/plain')}
            params = {
                'chunk_size': '300',
                'chunk_overlap': '50'
            }
            response = requests.post(f"{BASE_URL}/upload", files=files, params=params, timeout=60)

        print(f"状态码: {response.status_code}")

        if response.status_code == 200:
            result = response.json()

            if result.get('results'):
                processing_result = result['results'][0]

                if processing_result.get('success'):
                    chunk_count = processing_result.get('chunk_count', 0)
                    print(f"✅ 自定义分割成功，生成 {chunk_count} 个片段")

                    # 检查分割设置
                    stats = processing_result.get('processing_stats', {})
                    print(f"分割大小: {stats.get('chunk_size', 'N/A')}")
                    print(f"重叠大小: {stats.get('chunk_overlap', 'N/A')}")

                    return True
                else:
                    print(f"❌ 自定义分割失败: {processing_result.get('error')}")
                    return False
        else:
            print(f"❌ 请求失败: {response.text}")
            return False

    except Exception as e:
        print(f"❌ 测试异常: {e}")
        return False
    finally:
        os.unlink(test_file)

def test_server_health():
    """检查服务器状态"""
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

def main():
    print("🚀 测试自动embedding功能")
    print("=" * 60)

    # 检查服务器
    if not test_server_health():
        print("\n❌ 请先启动服务器: uvicorn app.main:app --reload")
        return

    # 运行测试
    test1 = test_auto_embedding_upload()
    test2 = test_upload_without_processing()
    test3 = test_upload_only_endpoint()
    test4 = test_custom_chunk_settings()

    print("\n" + "=" * 60)
    print("🎉 测试完成！")

    print("\n📊 测试结果:")
    print(f"  ✅ 自动embedding上传: {'通过' if test1 else '失败'}")
    print(f"  ✅ 禁用自动处理: {'通过' if test2 else '失败'}")
    print(f"  ✅ 仅上传端点: {'通过' if test3 else '失败'}")
    print(f"  ✅ 自定义分割参数: {'通过' if test4 else '失败'}")

    print("\n📋 新的API端点:")
    print(f"  🔄 自动处理上传: POST {BASE_URL}/upload (默认auto_process=true)")
    print(f"  📤 仅上传文件: POST {BASE_URL}/upload-only")
    print(f"  ⚙️ 手动处理: POST {BASE_URL}/process")

if __name__ == "__main__":
    main()