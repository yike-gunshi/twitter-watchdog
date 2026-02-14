#!/usr/bin/env python3
"""
测试 X API 连接
"""

import requests
import os

bearer_token = os.environ.get("X_BEARER_TOKEN", "")

print(f"Bearer Token 长度: {len(bearer_token)}")
print(f"Bearer Token: {bearer_token[:50]}...")

# 尝试不同的方式
session = requests.Session()
session.proxies = {
    'http': 'http://127.0.0.1:7890',
    'https': 'http://127.0.0.1:7890'
}

# 测试 API v2 端点
url = "https://api.twitter.com/2/users/by/username/elonmusk"

print(f"\n测试 URL: {url}")

response = session.get(url, headers={
    "Authorization": f"Bearer {bearer_token}",
    "Content-Type": "application/json"
})

print(f"状态码: {response.status_code}")
print(f"响应: {response.text[:500]}")
