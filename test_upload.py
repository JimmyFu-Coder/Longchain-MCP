#!/usr/bin/env python3
# test_upload.py - 测试文件上传API

import requests
import os
import tempfile

# API端点
UPLOAD_URL = "http://127.0.0.1:8000/api/files/upload"

def create_test_files():
    """创建测试文件"""
    test_files = []

    # 创建测试txt文件
    txt_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
    txt_file.write("这是一个测试文本文件\nTest content for upload")
    txt_file.close()
    test_files.append(('test.txt', txt_file.name))

    # 创建另一个测试文件
    txt_file2 = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
    txt_file2.write("第二个测试文件\nSecond test file content")
    txt_file2.close()
    test_files.append(('test2.txt', txt_file2.name))

    return test_files

def test_upload_single_file():
    """测试单文件上传"""
    print("🧪 测试单文件上传...")

    test_files = create_test_files()
    filename, filepath = test_files[0]

    try:
        with open(filepath, 'rb') as f:
            files = {'files': (filename, f, 'text/plain')}
            response = requests.post(UPLOAD_URL, files=files, timeout=10)

        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")

        if response.status_code == 200:
            print("✅ 单文件上传成功")
        else:
            print("❌ 单文件上传失败")

    except requests.exceptions.RequestException as e:
        print(f"❌ 请求异常: {e}")
    finally:
        # 清理临时文件
        for _, temp_path in test_files:
            os.unlink(temp_path)

def test_upload_multiple_files():
    """测试多文件上传"""
    print("\n🧪 测试多文件上传...")

    test_files = create_test_files()

    try:
        files = []
        file_handles = []

        for filename, filepath in test_files:
            f = open(filepath, 'rb')
            file_handles.append(f)
            files.append(('files', (filename, f, 'text/plain')))

        response = requests.post(UPLOAD_URL, files=files, timeout=10)

        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")

        if response.status_code == 200:
            print("✅ 多文件上传成功")
        else:
            print("❌ 多文件上传失败")

    except requests.exceptions.RequestException as e:
        print(f"❌ 请求异常: {e}")
    finally:
        # 关闭文件句柄
        for f in file_handles:
            f.close()
        # 清理临时文件
        for _, temp_path in test_files:
            os.unlink(temp_path)

def test_upload_no_files():
    """测试无文件上传"""
    print("\n🧪 测试无文件上传...")

    try:
        response = requests.post(UPLOAD_URL, files={}, timeout=10)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")

        if response.status_code == 400:
            print("✅ 无文件上传正确返回400错误")
        else:
            print("❌ 无文件上传应该返回400错误")

    except requests.exceptions.RequestException as e:
        print(f"❌ 请求异常: {e}")

def test_upload_invalid_file_type():
    """测试不支持的文件类型"""
    print("\n🧪 测试不支持的文件类型...")

    # 创建一个.py文件（不在允许列表中）
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False)
    temp_file.write("print('test')")
    temp_file.close()

    try:
        with open(temp_file.name, 'rb') as f:
            files = {'files': ('test.py', f, 'text/plain')}
            response = requests.post(UPLOAD_URL, files=files, timeout=10)

        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")

        if response.status_code == 400:
            print("✅ 不支持的文件类型正确返回400错误")
        else:
            print("❌ 不支持的文件类型应该返回400错误")

    except requests.exceptions.RequestException as e:
        print(f"❌ 请求异常: {e}")
    finally:
        os.unlink(temp_file.name)

def test_server_health():
    """测试服务器是否运行"""
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
    print("🚀 开始测试文件上传API")
    print(f"📡 目标URL: {UPLOAD_URL}")
    print("=" * 50)

    # 首先检查服务器状态
    if not test_server_health():
        print("\n❌ 服务器未运行，请先启动服务器")
        print("运行命令: uvicorn app.main:app --reload")
        return

    # 运行各种测试
    test_upload_single_file()
    test_upload_multiple_files()
    test_upload_no_files()
    test_upload_invalid_file_type()

    print("\n" + "=" * 50)
    print("🎉 测试完成！")

if __name__ == "__main__":
    main()