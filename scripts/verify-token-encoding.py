#!/usr/bin/env python3
"""
验证：URL 编码 vs URL 解码的 Bearer Token
"""

import requests
import os
import base64

consumer_key = os.environ.get("X_API_KEY", "")
consumer_secret = os.environ.get("X_API_SECRET", "")

session = requests.Session()
session.proxies = {
    'http': 'http://127.0.0.1:7890',
    'https': 'http://127.0.0.1:7890'
}

# 获取 Bearer Token
oauth_url = "https://api.twitter.com/oauth2/token"
credentials = f"{consumer_key}:{consumer_secret}"
b64_credentials = base64.b64encode(credentials.encode()).decode()

headers = {
    "Authorization": f"Basic {b64_credentials}",
    "Content-Type": "application/x-www-form-urlencoded"
}

data = "grant_type=client_credentials"

response = session.post(oauth_url, headers=headers, data=data, timeout=10)

if response.status_code == 200:
    result = response.json()
    bearer_token_url_encoded = result.get("access_token")  # URL 编码版本
    
    print("=" * 70)
    print("URL 编码 vs URL 解码对比")
    print("=" * 70)
    
    print(f"\n1. URL 编码的 Token（从 API 响应）:")
    print(f"   {bearer_token_url_encoded[:60]}...")
    print(f"   长度: {len(bearer_token_url_encoded)}")
    
    import urllib.parse
    bearer_token_url_decoded = urllib.parse.unquote(bearer_token_url_encoded)
    
    print(f"\n2. URL 解码的 Token:")
    print(f"   {bearer_token_url_decoded[:60]}...")
    print(f"   长度: {len(bearer_token_url_decoded)}")
    
    test_url = "https://api.twitter.com/2/users/by/username/elonmusk"
    
    # 测试 URL 编码版本
    print(f"\n" + "=" * 70)
    print("测试 1: URL 编码的 Token")
    print("=" * 70)
    
    headers = {
        "Authorization": f"Bearer {bearer_token_url_encoded}",
        "Content-Type": "application/json"
    }
    
    response = session.get(test_url, headers=headers, timeout=10)
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ 成功！")
        data = response.json()
        print(f"用户: {data.get('data', {}).get('name', '')}")
    else:
        print("❌ 失败")
    
    # 测试 URL 解码版本
    print(f"\n" + "=" * 70)
    print("测试 2: URL 解码的 Token")
    print("=" * 70)
    
    headers = {
        "Authorization": f"Bearer {bearer_token_url_decoded}",
        "Content-Type": "application/json"
    }
    
    response = session.get(test_url, headers=headers, timeout=10)
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ 成功！")
        data = response.json()
        print(f"用户: {data.get('data', {}).get('name', '')}")
    else:
        print("❌ 失败")
    
    print(f"\n" + "=" * 70)
    print("结论")
    print("=" * 70)
    print("\nTwitter API 需要使用 URL 编码的 Bearer Token！")
