#!/usr/bin/env python3
"""
简化版 Twitter OAuth 1.0a 测试
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

# 凭据
ACCESS_TOKEN = "1723554628498030592-xdxt0NPedA2vwy6SbdBjPYNAxbfEdA"
ACCESS_TOKEN_SECRET = "ktUDSv4JBOlUlpn2R3q7yPBwGnnJoJ1gCSWE7ceKRUGDP"
CONSUMER_KEY = "k1aM91JgDj4obSMSsM2KWGSss"
CONSUMER_SECRET = "yNha9rF5VcF5mD5aMBkWrY5wWO9En1BWtEQWa4KVJzBsCfpJuo"

PROXIES = {
    'http': 'http://127.0.0.1:7890',
    'https': 'http://127.0.0.1:7890'
}

def escape(s):
    return urllib.parse.quote(s, safe='')

def generate_oauth_header(method, url, params):
    """生成 OAuth 头"""
    # OAuth 参数
    oauth_params = {
        'oauth_consumer_key': CONSUMER_KEY,
        'oauth_nonce': ''.join(random.choices(string.ascii_letters + string.digits, k=32)),
        'oauth_signature_method': 'HMAC-SHA1',
        'oauth_timestamp': str(int(time.time())),
        'oauth_token': ACCESS_TOKEN,
        'oauth_version': '1.0'
    }
    
    # 合并所有参数用于签名
    all_params = {**oauth_params, **params}
    
    # 编码和排序所有参数
    encoded_params = []
    for key in sorted(all_params.keys()):
        encoded_params.append(f"{escape(key)}={escape(all_params[key])}")
    
    param_string = '&'.join(encoded_params)
    
    # 创建基础字符串
    base_string = f"{method.upper()}&{escape(url)}&{escape(param_string)}"
    
    # 创建签名密钥
    signing_key = f"{escape(CONSUMER_SECRET)}&{escape(ACCESS_TOKEN_SECRET)}"
    
    # 生成签名
    signature = hmac.new(
        signing_key.encode('utf-8'),
        base_string.encode('utf-8'),
        hashlib.sha1
    ).digest()
    
    # Base64 编码签名
    signature_b64 = base64.b64encode(signature).decode('utf-8')
    
    # 添加签名到 OAuth 参数
    oauth_params['oauth_signature'] = signature_b64
    
    # 生成 OAuth 头
    oauth_header_parts = []
    for key in sorted(oauth_params.keys()):
        oauth_header_parts.append(f"{escape(key)}=\"{escape(oauth_params[key])}\"")
    
    return 'OAuth ' + ', '.join(oauth_header_parts)

# 测试 1: 获取用户信息
print("=" * 70)
print("测试 1: 使用 OAuth 1.0a 获取用户信息")
print("=" * 70)

url = "https://api.twitter.com/1.1/account/verify_credentials.json"
oauth_header = generate_oauth_header('GET', url, {})

print(f"\nURL: {url}")
print(f"OAuth 头（前 100 字符）: {oauth_header[:100]}...")

session = requests.Session()
session.proxies = PROXIES

headers = {
    'Authorization': oauth_header
}

try:
    response = session.get(url, headers=headers, timeout=10)
    print(f"\n状态码: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ OAuth 1.0a 认证成功！")
        user_data = response.json()
        print(f"\n用户信息:")
        print(f"  用户名: @{user_data.get('screen_name')}")
        print(f"  名称: {user_data.get('name')}")
        print(f"  ID: {user_data.get('id_str')}")
        print(f"  关注数: {user_data.get('friends_count')}")
        print(f"  粉丝数: {user_data.get('followers_count')}")
        
        # 测试 2: 获取关注列表
        print("\n" + "=" * 70)
        print("测试 2: 获取关注列表")
        print("=" * 70)
        
        screen_name = user_data.get('screen_name')
        friends_url = "https://api.twitter.com/1.1/friends/list.json"
        params = {
            'screen': screen_name,
            'count': '5'
        }
        
        oauth_header = generate_oauth_header('GET', friends_url, params)
        
        print(f"\nURL: {friends_url}")
        print(f"参数: {params}")
        
        headers = {
            'Authorization': oauth_header
        }
        
        # 添加参数到 URL
        param_string = '&'.join([f"{escape(k)}={escape(v)}" for k, v in params.items()])
        full_url = f"{friends_url}?{param_string}"
        
        print(f"完整 URL: {full_url}")
        
        response = session.get(full_url, headers=headers, timeout=10)
        print(f"\n状态码: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ 获取关注列表成功！")
            data = response.json()
            users = data.get('users', [])
            
            print(f"\n获取到 {len(users)} 个关注:")
            for i, user in enumerate(users, 1):
                print(f"\n{i}. {user.get('name', '')} (@{user.get('screen_name', '')})")
                print(f"   ID: {user.get('id_str', '')}")
                print(f"   描述: {(user.get('description', '') or '无描述')[:80]}...")
            
            # 保存到文件
            if users:
                with open('/tmp/following.json', 'w', encoding='utf-8') as f:
                    json.dump({
                        'count': len(users),
                        'users': users,
                        'next_cursor': data.get('next_cursor')
                    }, f, ensure_ascii=False, indent=2)
                print(f"\n✅ 已保存到 /tmp/following.json")
        else:
            print(f"❌ 获取关注列表失败: {response.status_code}")
            print(f"响应: {response.text[:500]}")
    else:
        print(f"❌ 认证失败")
        print(f"响应: {response.text[:500]}")
        
except Exception as e:
    print(f"❌ 错误: {e}")

print("\n" + "=" * 70)
print("完成")
print("=" * 70)
