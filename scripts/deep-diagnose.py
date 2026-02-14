#!/usr/bin/env python3
"""
深入诊断 Twitter API 问题
"""

import requests
import os
import json
import urllib.parse

bearer_token_raw = os.environ.get("X_BEARER_TOKEN", "")
consumer_key = os.environ.get("X_API_KEY", "")
consumer_secret = os.environ.get("X_API_SECRET", "")

print("=" * 70)
print("Twitter API 深度诊断")
print("=" * 70)

# 测试不同的 Bearer Token 变体
print("\n" + "=" * 70)
print("测试 1: Bearer Token 变体")
print("=" * 70)

bearer_tokens = {
    "原始 (Raw)": bearer_token_raw,
    "URL 解码": urllib.parse.unquote(bearer_token_raw),
    "URL 编码": urllib.parse.quote(bearer_token_raw, safe='')
}

session = requests.Session()
session.proxies = {
    'http': 'http://127.0.0.1:7890',
    'https': 'http://127.0.0.1:7890'
}

test_url = "https://api.twitter.com/2/users/by/username/elonmusk"

for name, token in bearer_tokens.items():
    print(f"\n{name}:")
    print(f"  Token: {token[:60]}...")
    print(f"  长度: {len(token)}")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = session.get(test_url, headers=headers, timeout=10)
        print(f"  状态码: {response.status_code}")
        
        if response.status_code == 200:
            print("  ✅ 成功！")
            data = response.json()
            print(f"  用户: {data.get('data', {}).get('name', '')}")
            print(f"  用户名: @{data.get('data', {}).get('username', '')}")
        else:
            print(f"  ❌ 失败: {response.text[:200]}")
    except Exception as e:
        print(f"  ❌ 错误: {e}")

print("\n" + "=" * 70)
print("测试 2: 不同的 API 端点")
print("=" * 70)

# 使用原始 token（用户说是可用的）
test_endpoints = [
    ("用户信息 (v2)", "https://api.twitter.com/2/users/by/username/elonmusk"),
    ("用户时间线 (v2)", "https://api.twitter.com/2/users/44196397/tweets?max_results=5"),
    ("公共样本流 (v2)", "https://api.twitter.com/2/tweets/sample/stream"),
    ("请求配额 (v1.1)", "https://api.twitter.com/1.1/application/rate_limit_status.json"),
]

headers = {
    "Authorization": f"Bearer {bearer_token_raw}",
    "Content-Type": "application/json"
}

for name, url in test_endpoints:
    print(f"\n{name}")
    print(f"  URL: {url}")
    
    try:
        if "stream" in url:
            print("  ⚠️ 流端点，跳过测试")
            continue
            
        response = session.get(url, headers=headers, timeout=10)
        print(f"  状态码: {response.status_code}")
        
        if response.status_code == 200:
            print("  ✅ 成功！")
            data = response.json()
            if isinstance(data, dict):
                print(f"  数据键: {list(data.keys())[:5]}")
        else:
            print(f"  ❌ 失败: {response.text[:200]}")
    except Exception as e:
        print(f"  ❌ 错误: {e}")

print("\n" + "=" * 70)
print("测试 3: 请求头变体")
print("=" * 70)

# 测试不同的请求头格式
header_variants = [
    ("标准", {
        "Authorization": f"Bearer {bearer_token_raw}",
        "Content-Type": "application/json"
    }),
    ("带前缀", {
        "Authorization": f"Bearer {bearer_token_raw}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }),
    ("简化", {
        "Authorization": f"Bearer {bearer_token_raw}"
    }),
    ("OAuth 风格", {
        "Authorization": f"Bearer {bearer_token_raw}",
        "Accept": "application/json"
    }),
]

for name, headers in header_variants:
    print(f"\n{name}")
    print(f"  请求头: {list(headers.keys())}")
    
    try:
        response = session.get(test_url, headers=headers, timeout=10)
        print(f"  状态码: {response.status_code}")
        
        if response.status_code == 200:
            print("  ✅ 成功！")
            break
        else:
            print(f"  ❌ 失败: {response.text[:100]}")
    except Exception as e:
        print(f"  ❌ 错误: {e}")

print("\n" + "=" * 70)
print("测试 4: 无代理直接连接")
print("=" * 70)

print("\n测试不使用代理（检查是否代理导致问题）")

session_no_proxy = requests.Session()

try:
    response = session_no_proxy.get(test_url, headers=headers, timeout=10)
    print(f"无代理状态码: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ 无代理成功！问题可能在代理")
    else:
        print(f"失败: {response.text[:200]}")
except Exception as e:
    print(f"连接错误（预期的）: {str(e)[:100]}")

print("\n" + "=" * 70)
print("测试 5: API v1.1 搜索")
print("=" * 70)

# v1.1 搜索端点（通常需要 OAuth 1.0a）
v1_search_url = "https://api.twitter.com/1.1/search/tweets.json?q=twitter&count=1"

print(f"\n测试 v1.1 搜索（使用 Bearer Token 可能不支持）")
print(f"URL: {v1_search_url}")

try:
    response = session.get(v1_search_url, headers=headers, timeout=10)
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ v1.1 搜索成功！")
    else:
        print(f"失败（预期的，v1.1 需要 OAuth 1.0a）: {response.text[:200]}")
except Exception as e:
    print(f"错误: {str(e)[:100]}")

print("\n" + "=" * 70)
print("总结和建议")
print("=" * 70)
print("""
如果所有测试都失败：
1. 确认 API Key 在 Twitter Developer Portal 显示为"活跃"
2. 确认 API 计划支持 v2 API
3. 尝试重新生成 Bearer Token
4. 检查是否有 IP 白名单限制

如果有特定端点成功：
- 说明代理和认证都正常
- 可能只是某些端点需要特定权限
""")
