#!/usr/bin/env python3
"""
全面测试 Twitter API
"""

import requests
import os
import json

bearer_token = os.environ.get("X_BEARER_TOKEN", "")
consumer_key = os.environ.get("X_API_KEY", "")
consumer_secret = os.environ.get("X_API_SECRET", "")

print("=" * 60)
print("Twitter API 诊断")
print("=" * 60)

print(f"\n配置信息:")
print(f"  Consumer Key: {consumer_key[:20]}..." if consumer_key else "  Consumer Key: 未设置")
print(f"  Consumer Secret: {consumer_secret[:20]}..." if consumer_secret else "  Consumer Secret: 未设置")
print(f"  Bearer Token: {bearer_token[:50]}..." if bearer_token else "  Bearer Token: 未设置")

session = requests.Session()
session.proxies = {
    'http': 'http://127.0.0.1:7890',
    'https': 'http://127.0.0.1:7890'
}

headers = {
    "Authorization": f"Bearer {bearer_token}",
    "Content-Type": "application/json"
}

print("\n" + "=" * 60)
print("测试 1: API 连接性")
print("=" * 60)

# 测试基本连接
try:
    response = session.get("https://api.twitter.com/2/tweets/search/recent?query=test&max_results=1", headers=headers, timeout=10)
    print(f"\n搜索端点状态: {response.status_code}")
    
    if response.status_code == 401:
        print("❌ 401 Unauthorized - 认证失败")
        print("\n可能的原因:")
        print("  1. Bearer Token 不正确")
        print("  2. API 访问级别不支持此端点")
        print("  3. API 账户被暂停或有问题")
    elif response.status_code == 403:
        print("❌ 403 Forbidden - 禁止访问")
        print("\n可能的原因:")
        print("  1. 免费级 API 不支持搜索功能")
        print("  2. 需要升级到付费计划")
    elif response.status_code == 200:
        print("✅ 连接成功！")
        data = response.json()
        print(f"  返回数据: {json.dumps(data, indent=2, ensure_ascii=False)[:200]}...")
    
    print(f"\n完整响应: {response.text[:500]}")
    
except Exception as e:
    print(f"❌ 连接错误: {e}")

print("\n" + "=" * 60)
print("测试 2: 用户查询端点")
print("=" * 60)

try:
    response = session.get("https://api.twitter.com/2/users/by/username/elonmusk", headers=headers, timeout=10)
    print(f"\n用户查询状态: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ 用户查询成功！")
        data = response.json()
        print(f"  用户数据: {json.dumps(data, indent=2, ensure_ascii=False)[:300]}...")
    else:
        print(f"❌ 错误: {response.text[:500]}")
        
except Exception as e:
    print(f"❌ 错误: {e}")

print("\n" + "=" * 60)
print("测试 3: 使用 Consumer Key/Secret 生成 Bearer Token")
print("=" * 60)

import base64

if consumer_key and consumer_secret:
    try:
        key_secret = f"{consumer_key}:{consumer_secret}"
        b64_key_secret = base64.b64encode(key_secret.encode()).decode()
        
        oauth_url = "https://api.twitter.com/oauth2/token"
        oauth_headers = {
            "Authorization": f"Basic {b64_key_secret}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        oauth_data = "grant_type=client_credentials"
        
        response = session.post(oauth_url, headers=oauth_headers, data=oauth_data, timeout=10)
        
        print(f"\nOAuth 端点状态: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ OAuth 成功！")
            data = response.json()
            new_token = data.get("access_token")
            print(f"  新生成的 Bearer Token: {new_token[:50]}...")
            print(f"  当前使用的 Bearer Token: {bearer_token[:50]}...")
            
            if new_token != bearer_token:
                print("\n⚠️ 警告: 生成的 Token 与当前使用的 Token 不同")
                print("建议更新 Bearer Token")
            else:
                print("\n✅ Token 一致")
        else:
            print(f"❌ OAuth 失败: {response.text[:500]}")
            
    except Exception as e:
        print(f"❌ 错误: {e}")
else:
    print("❌ Consumer Key/Secret 未设置")

print("\n" + "=" * 60)
print("总结")
print("=" * 60)
print("\n如果看到 401 或 403 错误，可能需要:")
print("  1. 检查查 Twitter Developer Portal 的 API 访问级别")
print("  2. 某些功能（如搜索）可能需要付费计划")
print("  3. 访问 https://developer.twitter.com/en/portal/dashboard 查看详情")
