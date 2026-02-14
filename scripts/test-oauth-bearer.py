#!/usr/bin/env python3
"""
直接使用 OAuth 2.0 响应的 Bearer Token 测试
"""

import requests
import json
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

print("获取 Bearer Token...")
response = session.post(oauth_url, headers=headers, data=data, timeout=10)

if response.status_code == 200:
    result = response.json()
    bearer_token = result.get("access_token")
    
    print(f"Bearer Token: {bearer_token[:60]}...")
    print(f"Token 长度: {len(bearer_token)}")
    
    # 测试 API
    print("\n测试用户查询...")
    test_url = "https://api.twitter.com/2/users/by/username/elonmusk"
    
    api_headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json"
    }
    
    response = session.get(test_url, headers=api_headers, timeout=10)
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ 成功！")
        data = response.json()
        user_data = data.get('data', {})
        print(f"\n用户信息:")
        print(f"  ID: {user_data.get('id', '')}")
        print(f"  名称: {user_data.get('name', '')}")
        print(f"  用户名: @{user_data.get('username', '')}")
    else:
        print(f"❌ 失败: {response.text[:500]}")
