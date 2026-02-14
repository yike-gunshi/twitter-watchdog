#!/usr/bin/env python3
"""
生成 Twitter Bearer Token
"""

import base64
import requests
import os

consumer_key = os.environ.get("X_API_KEY", "")
consumer_secret = os.environ.get("X_API_SECRET", "")

print(f"Consumer Key: {consumer_key[:20]}...")
print(f"Consumer Secret: {consumer_secret[:20]}...")

# 将 Consumer Key 和 Secret 组合并 base64 编码
key_secret = f"{consumer_key}:{consumer_secret}"
b64_key_secret = base64.b64encode(key_secret.encode()).decode()

print(f"Base64 编码: {b64_key_secret[:50]}...")

# 发送请求获取 Bearer Token
url = "https://api.twitter.com/oauth2/token"

session = requests.Session()
session.proxies = {
    'http': 'http://127.0.0.1:7890',
    'https': 'http://127.0.0.1:7890'
}

headers = {
    "Authorization": f"Basic {b64_key_secret}",
    "Content-Type": "application/x-www-form-urlencoded"
}

data = "grant_type=client_credentials"

print(f"\n发送请求到: {url}")
response = session.post(url, headers=headers, data=data)

print(f"状态码: {response.status_code}")
print(f"响应: {response.text}")

if response.status_code == 200:
    result = response.json()
    new_bearer_token = result.get("access_token")
    print(f"\n✅ 新的 Bearer Token: {new_bearer_token[:50]}...")
    print(f"请更新 X_BEARER_TOKEN 环境变量")
