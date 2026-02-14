#!/usr/bin/env python3
"""
获取正确的 URL 编码的 Bearer Token
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
    # 这是 URL 编码的 Token（正确的）
    bearer_token = result.get("access_token")
    
    print("正确的 Bearer Token（URL 编码）:")
    print(bearer_token)
else:
    print("失败")
    print(response.text)
