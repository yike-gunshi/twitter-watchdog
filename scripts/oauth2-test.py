#!/usr/bin/env python3
"""
使用 OAuth 1.0a 完整流程测试
"""

import requests
import os
import base64
import hmac
import hashlib
import urllib.parse
import time
import random
import string

consumer_key = os.environ.get("X_API_KEY", "")
consumer_secret = os.environ.get("X_API_SECRET", "")

print("=" * 70)
print("OAuth 1.0a 完整流程")
print("=" * 70)

session = requests.Session()
session.proxies = {
    'http': 'http://127.0.0.1:7890',
    'https': 'http://127.0.0.1:7890'
}

def generate_nonce():
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(32))

def percent_encode(s):
    return urllib.parse.quote(s, safe='')

def create_signature(method, url, params, consumer_secret, token_secret=''):
    """创建 OAuth 签名"""
    # 编码参数
    encoded_params = {
        percent_encode(str(k)): percent_encode(str(v))
        for k, v in sorted(params.items())
    }
    
    # 参数字符串
    param_string = '&'.join([f"{k}={v}" for k, v in encoded_params.items()])
    
    # 基础字符串
    encoded_url = percent_encode(url)
    base_string = f"{method.upper()}&{encoded_url}&{percent_encode(param_string)}"
    
    # 签名密钥
    signing_key = f"{percent_encode(consumer_secret)}&{percent_encode(token_secret)}"
    
    # 签名
    signature = hmac.new(
        signing_key.encode('utf-8'),
        base_string.encode('utf-8'),
        hashlib.sha1
    ).digest()
    
    return base64.b64encode(signature).decode('utf-8')

def get_oauth_header(consumer_key, token='', params=None):
    """生成 OAuth 头"""
    if params is None:
        params = {}
    
    oauth_params = {
        'oauth_consumer_key': consumer_key,
        'oauth_nonce': generate_nonce(),
        'oauth_signature_method': 'HMAC-SHA1',
        'oauth_timestamp': str(int(time.time())),
        'oauth_version': '1.0'
    }
    
    if token:
        oauth_params['oauth_token'] = token
    
    # 合并所有参数
    all_params = {**oauth_params, **params}
    
    # 创建签名（URL 中不包含查询参数用于签名）
    signature = create_signature('GET', 'https://api.twitter.com/oauth2/token', all_params, consumer_secret)
    oauth_params['oauth_signature'] = signature
    
    # 生成 OAuth 头
    oauth_header = 'OAuth ' + ', '.join([
        f'{percent_encode(k)}="{percent_encode(v)}"'
        for k, v in sorted(oauth_params.items())
    ])
    
    return oauth_header

print("\n" + "=" * 70)
print("步骤 1: 获取 Bearer Token (使用 OAuth 2.0)")
print("=" * 70)

oauth_url = "https://api.twitter.com/oauth2/token"

# 使用 Basic Auth（Consumer Key:Secret 的 Base64 编码）
credentials = f"{consumer_key}:{consumer_secret}"
b64_credentials = base64.b64encode(credentials.encode()).decode()

print(f"Consumer Key: {consumer_key[:20]}...")
print(f"Consumer Secret: {consumer_secret[:20]}...")
print(f"Base64 编码: {b64_credentials[:50]}...")

headers = {
    "Authorization": f"Basic {b64_credentials}",
    "Content-Type": "application/x-www-form-urlencoded"
}

data = "grant_type=client_credentials"

print(f"\n发送请求到: {oauth_url}")

try:
    response = session.post(oauth_url, headers=headers, data=data, timeout=10)
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ OAuth 2.0 成功！")
        result = response.json()
        bearer_token = result.get("access_token")
        token_type = result.get("token_type")
        
        print(f"\nToken 类型: {token_type}")
        print(f"Bearer Token: {bearer_token[:60]}...")
        print(f"Token 长度: {len(bearer_token)}")
        
        print("\n" + "=" * 70)
        print("步骤 2: 使用新获取的 Bearer Token 测试 API")
        print("=" * 70)
        
        # 测试用户查询
        test_url = "https://api.twitter.com/2/users/by/username/elonmusk"
        
        headers = {
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json"
        }
        
        print(f"\n测试 URL: {test_url}")
        
        response = session.get(test_url, headers=headers, timeout=10)
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ API 认证成功！")
            data = response.json()
            user_data = data.get('data', {})
            print(f"\n用户信息:")
            print(f"  ID: {user_data.get('id', '')}")
            print(f"  名称: {user_data.get('name', '')}")
            print(f"  用户名: @{user_data.get('username', '')}")
            print(f"  描述: {user_data.get('description', '')[:100]}...")
            
            print("\n✅✅✅ 完全成功！Twitter API 配置正确！✅✅✅")
            print("\n现在可以正常使用 Twitter API 抓取数据了！")
        else:
            print(f"❌ API 认证失败: {response.text[:500]}")
            print("\n可能的原因:")
            print("  1. API 访问级别不支持 v2 API")
            print("  2. 需要升级到付费计划")
            print("  3. API 账户有问题")
    else:
        print(f"❌ OAuth Bearer Token 失败: {response.text[:500]}")
        
except Exception as e:
    print(f"❌ 错误: {e}")
