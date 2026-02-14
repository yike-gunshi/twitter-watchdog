#!/usr/bin/env python3
"""
测试 Twitter OAuth 1.0a 认证
"""

import requests
import json
import base64
import hmac
import hashlib
import urllib.parse
import time
import random
import string

# 用户提供的凭据
ACCESS_TOKEN = "1723554628498030592-xdxt0NPedA2vwy6SbdBjPYNAxbfEdA"
ACCESS_TOKEN_SECRET = "ktUDSv4JBOlUlpn2R3q7yPBwGnnJoJ1gCSWE7ceKRUGDP"
CONSUMERAKY = "k1aM91JgDj4obSMSsM2KWGSss"
CONSUMER_SECRET = "yNha9rF5VcF5mD5aMBkWrY5wWO9En1BWtEQWa4KVJzBsCfpJuo"

PROXIES = {
    'http': 'http://127.0.0.1:7890',
    'https': 'http://127.0.0.1:7890'
}

def generate_nonce():
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(32))

def percent_encode(s):
    return urllib.parse.quote(str(s), safe='')

def create_oauth_signature(method, url, params, consumer_secret, access_token_secret=''):
    # 编码所有参数
    encoded_params = {}
    for k, v in params.items():
        encoded_params[percent_encode(k)] = percent_encode(v)
    
    # 参数字符串（排序后连接）
    param_pairs = [f"{k}={v}" for k, v in sorted(encoded_params.items())]
    param_string = '&'.join(param_pairs)
    
    # 基础字符串
    encoded_url = percent_encode(url)
    base_string = f"{method.upper()}&{encoded_url}&{percent_encode(param_string)}"
    
    # 签名密钥
    signing_key = f"{percent_encode(consumer_secret)}&{percent_encode(access_token_secret)}"
    
    # 生成 HMAC-SHA1 签名
    signature = hmac.new(
        signing_key.encode('utf-8'),
        base_string.encode('utf-8'),
        hashlib.sha1
    ).digest()
    
    # Base64 编码
    return base64.b64encode(signature).decode('utf-8')

def get_oauth_header(method, url, params):
    # 添加 OAuth 参数
    oauth_params = {
        'oauth_consumer_key': CONSUMERAKY,
        'oauth_nonce': generate_nonce(),
        'oauth_signature_method': 'HMAC-SHA1',
        'oauth_timestamp': str(int(time.time())),
        'oauth_token': ACCESS_TOKEN,
        'oauth_version': '1.0'
    }
    
    # 合并所有参数（OAuth + 请求参数）
    all_params = {**oauth_params, **params}
    
    # 创建签名
    signature = create_oauth_signature(method, url, all_params, CONSUMER_SECRET, ACCESS_TOKEN_SECRET)
    oauth_params['oauth_signature'] = signature
    
    # 生成 OAuth 头
    oauth_header_parts = []
    for k, v in sorted(oauth_params.items()):
        oauth_header_parts.append(f'{percent_encode(k)}="{percent_encode(v)}"')
    
    return 'OAuth ' + ', '.join(oauth_header_parts)

# 测试获取用户信息
print("=" * 70)
print("测试 Twitter OAuth 1.0a 认证")
print("=" * 70)

url = "https://api.twitter.com/1.1/account/verify_credentials.json"
params = {}

oauth_header = get_oauth_header('GET', url, params)

print(f"\n请求 URL: {url}")
print(f"OAuth 头: {oauth_header[:100]}...")

session = requests.Session()
session.proxies = PROXIES

headers = {
    'Authorization': oauth_header
}

try:
    response = session.get(url, headers=headers, timeout=10)
    print(f"\n状态码: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ 认证成功！")
        user_data = response.json()
        print(f"\n用户信息:")
        print(f"  ID: {user_data.get('id_str')}")
        print(f"  用户名: @{user_data.get('screen_name')}")
        print(f"  名称: {user_data.get('name')}")
        print(f"  关注数: {user_data.get('friends_count')}")
        print(f"  粉丝数: {user_data.get('followers_count')}")
    else:
        print(f"❌ 认证失败")
        print(f"响应: {response.text[:500]}")
        
except Exception as e:
    print(f"❌ 错误: {e}")
