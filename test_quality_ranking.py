#!/usr/bin/env python3
# test_quality_ranking.py - 测试chunk质量排序功能

import requests
import tempfile
import os

BASE_URL = "http://127.0.0.1:8000/api/files"

def create_mixed_quality_document():
    """创建包含不同质量内容的测试文档"""
    content = """AI文档处理系统技术指南

第一章：系统概述
本系统是一个基于Python的智能文档处理平台，能够自动处理PDF、Word和文本文件。系统的核心功能包括文本提取、智能分割和向量嵌入生成。该系统具有以下特点：
1. 多格式文档支持
2. 智能文本分割
3. 本地embedding生成
4. 高效的批处理能力

第二章：技术架构详解
系统采用FastAPI作为Web框架，使用sentence-transformers进行本地embedding。文档处理流程包括：文件上传 → 文本提取 → 智能分割 → 向量生成。整个架构具有良好的扩展性和维护性。

一些简短的内容。

第三章：核心算法分析
文档分割算法采用段落边界检测技术，结合语义分析确保每个chunk的完整性。embedding生成使用预训练的多语言模型，支持中英文混合处理。质量评估算法考虑以下因素：
- 文本长度适中性
- 信息密度
- 结构化程度
- 句子完整性
- 内容唯一性

第四章：应用场景与案例
本系统适用于构建RAG系统、文档检索、知识库管理等应用。在实际项目中，系统能够处理大量文档并生成高质量的向量表示，为后续的语义搜索和问答系统提供基础。

随便写点东西填充。没什么意义。

第五章：性能优化与部署
系统支持本地部署，使用CPU版本的PyTorch，对硬件要求较低。通过合理的参数调优和算法优化，系统能够在普通服务器上稳定运行，处理速度能够满足大多数应用场景的需求。
"""

    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
    temp_file.write(content)
    temp_file.close()
    return temp_file.name

def test_default_quality_filtering():
    """测试默认质量筛选（top3）"""
    print("🧪 测试默认质量筛选（top3）...")

    test_file = create_mixed_quality_document()

    try:
        with open(test_file, 'rb') as f:
            files = {'files': ('quality_test.txt', f, 'text/plain')}
            params = {
                'chunk_size': '300',  # 较小的chunk让文档分割成更多片段
                'chunk_overlap': '50'
            }
            response = requests.post(f"{BASE_URL}/upload", files=files, params=params, timeout=60)

        print(f"状态码: {response.status_code}")

        if response.status_code == 200:
            result = response.json()

            if result.get('results'):
                processing_result = result['results'][0]

                if processing_result.get('success'):
                    total_chunks = processing_result.get('total_chunks', 0)
                    returned_chunks = processing_result.get('chunk_count', 0)
                    quality_filtered = processing_result.get('quality_filtered', False)

                    print(f"✅ 质量筛选成功")
                    print(f"总chunk数: {total_chunks}")
                    print(f"返回chunk数: {returned_chunks}")
                    print(f"已启用质量筛选: {quality_filtered}")

                    # 显示返回的chunks及其质量分数
                    chunks = processing_result.get('chunks', [])
                    for i, chunk in enumerate(chunks):
                        quality_score = chunk.get('quality_score', 0)
                        length = chunk.get('length', 0)
                        preview = chunk.get('text', '')[:50] + '...'
                        print(f"Chunk {i+1}: 质量分数={quality_score:.3f}, 长度={length}, 内容='{preview}'")

                    return True
                else:
                    print(f"❌ 处理失败: {processing_result.get('error')}")
                    return False
        else:
            print(f"❌ 请求失败: {response.text}")
            return False

    except Exception as e:
        print(f"❌ 测试异常: {e}")
        return False
    finally:
        os.unlink(test_file)

def test_custom_top_k():
    """测试自定义top-k值"""
    print("\n🧪 测试自定义top-k值（top5）...")

    test_file = create_mixed_quality_document()

    try:
        with open(test_file, 'rb') as f:
            files = {'files': ('top5_test.txt', f, 'text/plain')}
            params = {
                'chunk_size': '250',
                'chunk_overlap': '30',
                'return_best': '5'  # 返回top5
            }
            response = requests.post(f"{BASE_URL}/upload", files=files, params=params, timeout=60)

        print(f"状态码: {response.status_code}")

        if response.status_code == 200:
            result = response.json()

            if result.get('results'):
                processing_result = result['results'][0]

                if processing_result.get('success'):
                    total_chunks = processing_result.get('total_chunks', 0)
                    returned_chunks = processing_result.get('chunk_count', 0)

                    print(f"✅ 自定义top-k成功")
                    print(f"总chunk数: {total_chunks}")
                    print(f"返回chunk数: {returned_chunks}")

                    expected_k = min(5, total_chunks)
                    if returned_chunks == expected_k:
                        print(f"✅ 正确返回了top-{expected_k}结果")
                        return True
                    else:
                        print(f"❌ 期望返回{expected_k}个，实际返回{returned_chunks}个")
                        return False
                else:
                    print(f"❌ 处理失败: {processing_result.get('error')}")
                    return False
        else:
            print(f"❌ 请求失败: {response.text}")
            return False

    except Exception as e:
        print(f"❌ 测试异常: {e}")
        return False
    finally:
        os.unlink(test_file)

def test_disable_quality_filtering():
    """测试禁用质量筛选（返回所有chunks）"""
    print("\n🧪 测试禁用质量筛选...")

    test_file = create_mixed_quality_document()

    try:
        with open(test_file, 'rb') as f:
            files = {'files': ('no_filter_test.txt', f, 'text/plain')}
            params = {
                'chunk_size': '300',
                'chunk_overlap': '50',
                'return_best': '0'  # 0表示返回所有chunks
            }
            response = requests.post(f"{BASE_URL}/upload", files=files, params=params, timeout=60)

        print(f"状态码: {response.status_code}")

        if response.status_code == 200:
            result = response.json()

            if result.get('results'):
                processing_result = result['results'][0]

                if processing_result.get('success'):
                    total_chunks = processing_result.get('total_chunks', 0)
                    returned_chunks = processing_result.get('chunk_count', 0)
                    quality_filtered = processing_result.get('quality_filtered', True)

                    print(f"✅ 禁用筛选成功")
                    print(f"总chunk数: {total_chunks}")
                    print(f"返回chunk数: {returned_chunks}")
                    print(f"质量筛选状态: {quality_filtered}")

                    if total_chunks == returned_chunks and not quality_filtered:
                        print("✅ 正确返回了所有chunks")
                        return True
                    else:
                        print("❌ 未正确禁用质量筛选")
                        return False
                else:
                    print(f"❌ 处理失败: {processing_result.get('error')}")
                    return False
        else:
            print(f"❌ 请求失败: {response.text}")
            return False

    except Exception as e:
        print(f"❌ 测试异常: {e}")
        return False
    finally:
        os.unlink(test_file)

def test_process_endpoint_quality():
    """测试/process端点的质量筛选"""
    print("\n🧪 测试/process端点的质量筛选...")

    # 先上传文件
    test_file = create_mixed_quality_document()

    try:
        # 1. 先仅上传
        with open(test_file, 'rb') as f:
            files = {'files': ('process_test.txt', f, 'text/plain')}
            upload_response = requests.post(f"{BASE_URL}/upload-only", files=files, timeout=30)

        if upload_response.status_code != 200:
            print(f"❌ 上传失败: {upload_response.text}")
            return False

        upload_result = upload_response.json()
        file_path = upload_result['files'][0]['file_path']

        # 2. 再处理
        process_request = {
            "file_path": file_path,
            "chunk_size": 300,
            "chunk_overlap": 50,
            "return_best": 2  # 只返回top2
        }

        process_response = requests.post(f"{BASE_URL}/process", json=process_request, timeout=60)
        print(f"处理状态码: {process_response.status_code}")

        if process_response.status_code == 200:
            result = process_response.json()
            processing_result = result.get('result', {})

            if processing_result.get('success'):
                total_chunks = processing_result.get('total_chunks', 0)
                returned_chunks = processing_result.get('chunk_count', 0)

                print(f"✅ /process端点质量筛选成功")
                print(f"总chunk数: {total_chunks}")
                print(f"返回chunk数: {returned_chunks}")

                if returned_chunks == min(2, total_chunks):
                    print("✅ 正确返回了top2结果")
                    return True
                else:
                    print(f"❌ 期望返回2个，实际返回{returned_chunks}个")
                    return False
            else:
                print(f"❌ 处理失败: {processing_result.get('error')}")
                return False
        else:
            print(f"❌ 处理请求失败: {process_response.text}")
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
    print("🚀 测试chunk质量排序功能")
    print("=" * 60)

    # 检查服务器
    if not test_server_health():
        print("\n❌ 请先启动服务器: uvicorn app.main:app --reload")
        return

    # 运行测试
    test1 = test_default_quality_filtering()
    test2 = test_custom_top_k()
    test3 = test_disable_quality_filtering()
    test4 = test_process_endpoint_quality()

    print("\n" + "=" * 60)
    print("🎉 测试完成！")

    print("\n📊 测试结果:")
    print(f"  ✅ 默认质量筛选(top3): {'通过' if test1 else '失败'}")
    print(f"  ✅ 自定义top-k(top5): {'通过' if test2 else '失败'}")
    print(f"  ✅ 禁用质量筛选: {'通过' if test3 else '失败'}")
    print(f"  ✅ /process端点筛选: {'通过' if test4 else '失败'}")

    print("\n📋 质量排序API参数:")
    print("  🔄 return_best=3 (默认返回top3最佳chunks)")
    print("  🔄 return_best=5 (返回top5)")
    print("  🔄 return_best=0 (返回所有chunks，禁用筛选)")

if __name__ == "__main__":
    main()