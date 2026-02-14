#!/usr/bin/env python3
"""
尝试使用 Twitter API v1.1
"""

import requests
import os
import base64
import hashlib
import hmac
import urllib.parse
import time
import random
import string

consumer_key = os.environ.get("X_API_KEY", "")
consumer_secret = os.environ.get("X_API_SECRET", "")

print("=" * 60)
print("Twitter API v1.1 测试")
print("=" * 60)

# 生成随机 nonce
def generate_nonce():
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(32))

def create_oauth_signature(consumer_key, consumer_secret, http_method, base_url, params):
    """创建 OAuth 签名"""
    # 编码参数
    encoded_params = {
        urllib.parse.quote(key, safe=''): urllib.parse.quote(str(value), safe='')
        for key, value in sorted(params.items())
    }
    
    # 创建参数字符串
    param_string = '&'.join([f"{k}={v}" for k, v in encoded_params.items()])
    
    # 创建基础字符串
    encoded_base_url = urllib.parse.quote(base_url, safe='')
    base_string = f"{http_method.upper()}&{encoded_base_url}&{urllib.parse.quote(param_string, safe='')}"
    
    # 创建签名密钥
    signing_key = f"{urllib.parse.quote(consumer_secret, safe='')}&"
    
    # 生成签名
    signature = hmac.new(
        signing_key.encode('utf-8'),
        base_string.encode('utf-8'),
        hashlib.sha1
    ).digest()
    
    return base64.b64encode(signature).decode('utf-8')

# 配置代理
session = requests.Session()
session.proxies = {
    'http': 'http://127.0.0.1:7890',
    'https': 'http://127.0.0.1:7890'
}

# 测试 v1.1 API
print("\n测试 1: v1.1 公共时间线")

url = "https://api.twitter.com/1.1/statuses/home_timeline.json"
http_method = "GET"

# OAuth 参数
oauth_params = {
    'oauth_consumer_key': consumer_key,
    'oauth_nonce': generate_nonce(),
    'oauth_signature_method': 'HMAC-SHA1',
    'oauth_timestamp': str(int(time.time())),
    'oauth_token': '',
    'oauth_version': '1.0'
}

# 创建签名
signature = create_oauth_signature(consumer_key, consumer_secret, http_method, url, oauth_params)
oauth_params['oauth_signature'] = signature

# 创建 OAuth 头
oauth_header = 'OAuth ' + ', '.join([
    f'{urllib.parse.quote(k, safe="")}="{urllib.parse.quote(v, safe="")}"'
    for k, v in oauth_params.items()
    if k != 'oauth_token' or v  # 跳过空的 token
])

headers = {
    'Authorization': oauth_header
}

print(f"\n请求 URL: {url}")
print(f"OAuth 头: {oauth_header[:100]}...")

try:
    response = session.get(url, headers=headers, timeout=10)
    print(f"\n状态码: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ v1.1 API 连接成功！")
        data = response.json()
        print(f"  获取到 {len(data)} 条推文")
        if data:
            print(f"  示例推文: {data[0].get('text', '')[:100]}...")
    else:
        print(f"❌ 错误: {response.text[:500]}")
        
except Exception as e:
    print(f"❌ 错误: {e}")

print("\n" + "=" * 60)
print("测试 2: v1.1 用户搜索")
print("=" * 60)

search_url = "https://api.twitter.com/1.1/users/search.json?q=elonmusk&count=1"
http_method = "GET"

oauth_params = {
    'oauth_consumer_key': consumer_key,
    'oauth_nonce': generate_nonce(),
    'oauth_signature_method': 'HMAC-SHA1',
    'oauth_timestamp': str(int(time.time())),
    'oauth_token': '',
    'oauth_version': '1.0'
}

signature = create_oauth_signature(consumer_key, consumer_secret, http_method, search_url, oauth_params)
oauth_params['oauth_signature'] = signature

oauth_header = 'OAuth ' + ', '.join([
    f'{urllib.parse.quote(k, safe="")}="{urllib.parse.quote(v, safe="")}"'
    for k, v in oauth_params.items()
    if k != 'oauth_token' or v
])

headers = {
    'Authorization': oauth_header
}

try:
    response = session.get(search_url, headers=headers, timeout=10)
    print(f"\n状态码: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ 用户搜索成功！")
        data = response.json()
        print(f"  找到 {len(data)} 个用户")
        if data:
            print(f"  用户: {data[0].get('screen_name', '')} - {data[0].get('name', '')}")
    else:
        print(f"❌ 错误: {response.text[:500]}")
        
except Exception as e:
    print(f"❌ 错误: {e}")

print("\n总结:")
print("如果 v1.1 API 能工作，说明代理和认证都没问题。")
print("v2 API 的 401 错误可能是访问级别限制。")
