#!/usr/bin/env python3
# debug_422_error.py - 调试422错误

import requests
import tempfile
import os

def test_upload_with_different_params():
    """测试不同参数组合找出422错误原因"""

    # 创建测试文件
    content = "测试内容，用于调试422错误"
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
    temp_file.write(content)
    temp_file.close()

    url = "http://127.0.0.1:8000/api/files/upload"

    test_cases = [
        {
            "name": "基本上传",
            "files": {'files': ('test.txt', open(temp_file.name, 'rb'), 'text/plain')},
            "params": {}
        },
        {
            "name": "带auto_process参数",
            "files": {'files': ('test.txt', open(temp_file.name, 'rb'), 'text/plain')},
            "params": {'auto_process': 'true'}
        },
        {
            "name": "带所有参数",
            "files": {'files': ('test.txt', open(temp_file.name, 'rb'), 'text/plain')},
            "params": {
                'auto_process': 'true',
                'chunk_size': '500',
                'chunk_overlap': '100',
                'return_best': '3'
            }
        },
        {
            "name": "错误的参数类型",
            "files": {'files': ('test.txt', open(temp_file.name, 'rb'), 'text/plain')},
            "params": {
                'auto_process': 'invalid',  # 应该是bool
                'chunk_size': 'abc',        # 应该是int
                'return_best': 'xyz'        # 应该是int
            }
        }
    ]

    for test_case in test_cases:
        print(f"\n🧪 测试: {test_case['name']}")

        try:
            response = requests.post(
                url,
                files=test_case['files'],
                params=test_case['params'],
                timeout=30
            )

            print(f"状态码: {response.status_code}")

            if response.status_code == 422:
                print(f"❌ 422错误详情: {response.text}")
            elif response.status_code == 200:
                print(f"✅ 成功")
            else:
                print(f"⚠️ 其他错误: {response.text}")

        except Exception as e:
            print(f"❌ 请求异常: {e}")

        # 重新打开文件句柄（因为上面的请求会关闭它）
        test_case['files'] = {'files': ('test.txt', open(temp_file.name, 'rb'), 'text/plain')}

    # 清理
    os.unlink(temp_file.name)

def test_pdf_upload_specifically():
    """专门测试PDF文件上传"""
    print("\n🧪 测试PDF文件上传...")

    pdf_path = "uploads/feeecb26-ab8d-4038-aaf5-0104d1141363.pdf"

    if not os.path.exists(pdf_path):
        print(f"❌ PDF文件不存在: {pdf_path}")
        return

    url = "http://127.0.0.1:8000/api/files/upload"

    try:
        with open(pdf_path, 'rb') as f:
            files = {'files': ('RaptorOS-RBAC.pdf', f, 'application/pdf')}
            params = {
                'auto_process': 'true',
                'chunk_size': '500',
                'chunk_overlap': '100',
                'return_best': '3'
            }

            response = requests.post(url, files=files, params=params, timeout=60)

            print(f"状态码: {response.status_code}")

            if response.status_code == 422:
                print(f"❌ 422错误详情: {response.text}")
            elif response.status_code == 200:
                result = response.json()
                print(f"✅ PDF上传成功")
                if result.get('results'):
                    proc_result = result['results'][0]
                    if proc_result.get('success'):
                        print(f"文档处理成功，chunk数: {proc_result.get('chunk_count', 0)}")
                    else:
                        print(f"文档处理失败: {proc_result.get('error', 'Unknown')}")
            else:
                print(f"⚠️ 其他错误 {response.status_code}: {response.text}")

    except Exception as e:
        print(f"❌ 请求异常: {e}")

def check_server_status():
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
    except Exception as e:
        print(f"❌ 无法连接服务器: {e}")
        return False

def main():
    print("🚀 调试422错误")
    print("=" * 50)

    if not check_server_status():
        return

    test_upload_with_different_params()
    test_pdf_upload_specifically()

if __name__ == "__main__":
    main()