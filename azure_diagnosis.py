#!/usr/bin/env python3
"""
Azure AI Search 完整诊断脚本
详细检查所有可能的问题
"""

import asyncio
import sys
import os
from pathlib import Path

# 确保可以导入应用模块
sys.path.append(str(Path(__file__).parent))

async def check_environment():
    """检查环境变量"""
    print("🔧 检查环境变量...")

    # 从.env文件读取
    env_file = Path(".env")
    if env_file.exists():
        print(f"✅ .env 文件存在: {env_file.absolute()}")

        with open(env_file, 'r', encoding='utf-8') as f:
            content = f.read()

        print("环境变量内容:")
        for line in content.strip().split('\n'):
            if line and not line.startswith('#'):
                key, value = line.split('=', 1)
                # 隐藏敏感信息
                if 'KEY' in key or 'key' in key:
                    display_value = value[:10] + "..." if len(value) > 10 else value
                else:
                    display_value = value
                print(f"   {key}: {display_value}")
    else:
        print(f"❌ .env 文件不存在: {env_file.absolute()}")

    return True

async def test_direct_azure_search():
    """直接测试Azure Search"""
    print("\n🔍 直接测试 Azure Search API...")

    try:
        import requests
        import json

        # 从环境变量获取配置
        search_endpoint = os.getenv('AZURE_SEARCH_ENDPOINT')
        search_key = os.getenv('AZURE_SEARCH_KEY')
        index_name = os.getenv('AZURE_SEARCH_INDEX_NAME', 'rag')

        if not search_endpoint or not search_key:
            print("❌ 缺少Azure Search配置")
            return False

        # 测试API调用
        url = f"{search_endpoint}/indexes/{index_name}?api-version=2023-11-01"
        headers = {
            "api-key": search_key,
            "Content-Type": "application/json"
        }

        response = requests.get(url, headers=headers, timeout=30)

        if response.status_code == 200:
            index_info = response.json()
            print(f"✅ Azure Search API 调用成功!")
            print(f"   索引名称: {index_info.get('name')}")
            print(f"   字段数量: {len(index_info.get('fields', []))}")
            return True
        elif response.status_code == 401:
            print(f"❌ API密钥认证失败 (401)")
            print(f"   使用的密钥: {search_key[:10]}...")
            return False
        elif response.status_code == 404:
            print(f"⚠️  索引 '{index_name}' 不存在 (404)")
            return "index_missing"
        else:
            print(f"❌ API调用失败: {response.status_code}")
            print(f"   响应: {response.text}")
            return False

    except Exception as e:
        print(f"❌ 直接API测试失败: {str(e)}")
        return False

async def test_direct_openai():
    """直接测试Azure OpenAI"""
    print("\n🔤 直接测试 Azure OpenAI API...")

    try:
        import requests
        import json

        # 从环境变量获取配置
        openai_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
        openai_key = os.getenv('AZURE_OPENAI_API_KEY')
        deployment = os.getenv('AZURE_OPENAI_EMBEDDING_DEPLOYMENT', 'text-embedding-ada-002')
        api_version = "2024-02-01"

        if not openai_endpoint or not openai_key:
            print("❌ 缺少Azure OpenAI配置")
            return False

        # 构建API URL
        url = f"{openai_endpoint}/openai/deployments/{deployment}/embeddings?api-version={api_version}"

        headers = {
            "api-key": openai_key,
            "Content-Type": "application/json"
        }

        data = {
            "input": "测试文本"
        }

        response = requests.post(url, headers=headers, json=data, timeout=30)

        if response.status_code == 200:
            result = response.json()
            if 'data' in result and len(result['data']) > 0:
                embedding = result['data'][0]['embedding']
                print(f"✅ Azure OpenAI API 调用成功!")
                print(f"   向量维度: {len(embedding)}")
                return True
            else:
                print("❌ API响应格式异常")
                return False
        elif response.status_code == 401:
            print(f"❌ API密钥认证失败 (401)")
            return False
        elif response.status_code == 404:
            print(f"❌ 部署 '{deployment}' 不存在 (404)")
            print(f"   请检查部署名称是否正确")
            return False
        else:
            print(f"❌ API调用失败: {response.status_code}")
            print(f"   响应: {response.text}")
            return False

    except Exception as e:
        print(f"❌ 直接API测试失败: {str(e)}")
        return False

async def test_sdk_imports():
    """测试SDK导入"""
    print("\n📦 测试Python SDK...")

    sdks = [
        ("azure-search-documents", "azure.search.documents"),
        ("azure-core", "azure.core.credentials"),
        ("openai", "openai"),
        ("langchain-openai", "langchain_openai"),
        ("requests", "requests")
    ]

    all_good = True
    for package_name, import_name in sdks:
        try:
            __import__(import_name)
            print(f"   ✅ {package_name}")
        except ImportError:
            print(f"   ❌ {package_name} - 需要安装")
            all_good = False

    return all_good

async def create_minimal_index():
    """创建最小索引用于测试"""
    print("\n📊 尝试创建测试索引...")

    try:
        import requests
        import json

        search_endpoint = os.getenv('AZURE_SEARCH_ENDPOINT')
        search_key = os.getenv('AZURE_SEARCH_KEY')
        index_name = "test-index"

        if not search_endpoint or not search_key:
            print("❌ 缺少配置")
            return False

        # 简单的索引定义
        index_def = {
            "name": index_name,
            "fields": [
                {
                    "name": "id",
                    "type": "Edm.String",
                    "key": True,
                    "filterable": True
                },
                {
                    "name": "content",
                    "type": "Edm.String",
                    "searchable": True,
                    "retrievable": True
                }
            ]
        }

        url = f"{search_endpoint}/indexes/{index_name}?api-version=2023-11-01"
        headers = {
            "api-key": search_key,
            "Content-Type": "application/json"
        }

        # 先尝试删除（如果存在）
        requests.delete(url, headers=headers)

        # 创建新索引
        response = requests.post(
            f"{search_endpoint}/indexes?api-version=2023-11-01",
            headers=headers,
            json=index_def,
            timeout=30
        )

        if response.status_code in [200, 201]:
            print(f"✅ 成功创建测试索引 '{index_name}'")

            # 清理：删除测试索引
            delete_response = requests.delete(url, headers=headers)
            if delete_response.status_code in [200, 204]:
                print(f"✅ 已清理测试索引")

            return True
        else:
            print(f"❌ 创建索引失败: {response.status_code}")
            print(f"   响应: {response.text}")
            return False

    except Exception as e:
        print(f"❌ 索引创建测试失败: {str(e)}")
        return False

async def main():
    """主诊断函数"""
    print("🩺 Azure AI Search 完整诊断")
    print("=" * 70)

    # 确保加载环境变量
    from dotenv import load_dotenv
    load_dotenv()

    tests = [
        ("环境变量检查", check_environment),
        ("Python SDK", test_sdk_imports),
        ("Azure Search API", test_direct_azure_search),
        ("Azure OpenAI API", test_direct_openai),
        ("索引创建测试", create_minimal_index)
    ]

    results = {}

    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = await test_func()
            results[test_name] = result
        except Exception as e:
            print(f"❌ {test_name} 异常: {str(e)}")
            results[test_name] = False

    # 总结报告
    print("\n" + "=" * 70)
    print("🏁 诊断报告")
    print("=" * 70)

    for test_name, result in results.items():
        if result is True:
            status = "✅ 正常"
        elif result is False:
            status = "❌ 异常"
        else:
            status = f"⚠️  {result}"

        print(f"{status:<10} {test_name}")

    # 问题分析和建议
    print("\n🔧 问题分析:")

    if results.get("Azure Search API") is False:
        print("   1. Azure Search API密钥可能错误")
        print("      - 检查Azure门户中的搜索服务密钥")
        print("      - 确认使用的是Admin Key而不是Query Key")

    if results.get("Azure OpenAI API") is False:
        print("   2. Azure OpenAI配置问题")
        print("      - 检查部署名称是否正确")
        print("      - 确认API密钥有效")
        print("      - 验证端点URL格式")

    if "index_missing" in str(results.get("Azure Search API", "")):
        print("   3. 索引不存在")
        print("      - 运行完整的初始化脚本创建索引")

    success_count = sum(1 for r in results.values() if r is True)
    total_count = len(results)

    print(f"\n📊 总体状态: {success_count}/{total_count} 项正常")

    if success_count == total_count:
        print("🎉 所有组件工作正常！")
    else:
        print("⚠️  需要修复上述问题")

if __name__ == "__main__":
    asyncio.run(main())