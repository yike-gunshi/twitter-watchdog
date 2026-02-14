#!/usr/bin/env python3
"""
使用原始 Token 测试
"""

import requests
import urllib.parse

# 用户提供的原始 Token（URL 编码）
user_token_raw = "AAAAAAAAAAAAAAAAAAAAAAE%2FL7QEAAAAApg4IBUqrV8TpuI%2FUkEMk%2F4hi%2B4U%3DTPQVuskNFWBON9ifZLNCl2Nzbnpzazs1eZw6Zy3ObsE8fXz9n1"

# 解码后的 Token
user_token_decoded = urllib.parse.unquote(user_token_raw)

print("=" * 70)
print("使用用户原始 Token 测试")
print("=" * 70)

print(f"\n原始 Token: {user_token_raw}")
print(f"解码后: {user_token_decoded}")
print(f"长度: {len(user_token_decoded)}")

session = requests.Session()
session.proxies = {
    'http': 'http://127.0.0.1:7890',
    'https': 'http://127.0.0.1:7890'
}

test_url = "https://api.twitter.com/2/users/by/username/elonmusk"

print(f"\n测试 URL: {test_url}")

# 测试原始 Token（URL 编码）
print("\n" + "=" * 70)
print("测试 1: 使用原始 URL 编码的 Token")
print("=" * 70)

headers = {
    "Authorization": f"Bearer {user_token_raw}",
    "Content-Type": "application/json"
}

print(f"Authorization 头: {headers['Authorization'][:80]}...")

try:
    response = session.get(test_url, headers=headers, timeout=10)
    print(f"\n状态码: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ 成功！")
        print(f"响应: {response.text[:500]}")
    else:
        print(f"❌ 失败: {response.text[:500]}")
except Exception as e:
    print(f"❌ 错误: {e}")

# 测试解码后的 Token
print("\n" + "=" * 70)
print("测试 2: 使用解码后的 Token")
print("=" * 70)

headers = {
    "Authorization": f"Bearer {user_token_decoded}",
    "Content-Type": "application/json"
}

print(f"Authorization 头: {headers['Authorization'][:80]}...")

try:
    response = session.get(test_url, headers=headers, timeout=10)
    print(f"\n状态码: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ 成功！")
        print(f"响应: {response.text[:500]}")
    else:
        print(f"❌ 失败: {response.text[:500]}")
except Exception as e:
    print(f"❌ 错误: {e}")

# 测试环境变量中的 Token
print("\n" + "=" * 70)
print("测试 3: 使用环境变量中的 Token")
print("=" * 70)

import os
env_token = os.environ.get("X_BEARER_TOKEN", "")
print(f"环境变量 Token: {env_token[:60]}...")
print(f"长度: {len(env_token)}")

headers = {
    "Authorization": f"Bearer {env_token}",
    "Content-Type": "application/json"
}

try:
    response = session.get(test_url, headers=headers, timeout=10)
    print(f"\n状态码: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ 成功！")
        print(f"响应: {response.text[:500]}")
    else:
        print(f"❌ 失败: {response.text[:500]}")
except Exception as e:
    print(f"❌ 错误: {e}")

print("\n" + "=" * 70)
print("分析")
print("=" * 70)

print(f"\n原始 Token 是否 == 解码后: {user_token_raw == user_token_decoded}")
print(f"原始 Token 是否 == 环境变量: {user_token_raw == env_token}")
print(f"解码后 是否 == 环境变量: {user_token_decoded == env_token}")

# 检查差异
if user_token_decoded != env_token:
    print(f"\n⚠️ 解码后的 Token 与环境变量不同！")
    print(f"  解码后以...结尾: {user_token_decoded[-20:]}")
    print(f"  环境变量以...结尾: {env_token[-20:]}")
