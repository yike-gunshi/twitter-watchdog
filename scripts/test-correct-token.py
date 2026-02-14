#!/usr/bin/env python3
"""
使用正确的 Token 直接测试
"""

import requests
import json

# 正确的 Token（从用户提供的 URL 解码）
correct_token = "AAAAAAAAAAAAAAAAAAAAAE/L7QEAAAAApg4IBUqrV8TpuI/UkEMk/4hi+4U=TPQVuskNFWBON9ifZLNCl2Nzbnpzazs1eZw6Zy3ObsE8fXz9n1"

print("=" * 70)
print("使用正确的 Token 直接测试")
print("=" * 70)

print(f"\nToken: {correct_token[:60]}...")
print(f"长度: {len(correct_token)}")

session = requests.Session()
session.proxies = {
    'http': 'http://127.0.0.1:7890',
    'https': 'http://127.0.0.1:7890'
}

test_url = "https://api.twitter.com/2/users/by/username/elonmusk"

headers = {
    "Authorization": f"Bearer {correct_token}",
    "Content-Type": "application/json"
}

print(f"\n测试 URL: {test_url}")
print(f"Authorization 头: {headers['Authorization'][:80]}...")

try:
    response = session.get(test_url, headers=headers, timeout=10)
    print(f"\n状态码: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ 成功！API 认证正常！")
        data = response.json()
        print(f"\n用户信息:")
        print(f"  ID: {data.get('data', {}).get('id', '')}")
        print(f"  名称: {data.get('data', {}).get('name', '')}")
        print(f"  用户名: @{data.get('data', {}).get('username', '')}")
        print(f"  描述: {data.get('data', {}).get('description', '')[:100]}...")
        
        print("\n" + "=" * 70)
        print("测试获取推文")
        print("=" * 70)
        
        user_id = data.get('data', {}).get('id', '')
        tweets_url = f"https://api.twitter.com/2/users/{user_id}/tweets?max_results=5"
        
        response = session.get(tweets_url, headers=headers, timeout=10)
        print(f"\n状态码: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ 获取推文成功！")
            data = response.json()
            tweets = data.get('data', [])
            print(f"  获取到 {len(tweets)} 条推文")
            
            for i, tweet in enumerate(tweets, 1):
                print(f"\n  {i}. {tweet.get('text', '')[:100]}...")
        else:
            print(f"❌ 失败: {response.text[:500]}")
    else:
        print(f"❌ 失败: {response.text[:500]}")
        
except Exception as e:
    print(f"❌ 错误: {e}")

print("\n" + "=" * 70)
print("结论")
print("=" * 70)

print("\n如果这个测试成功，说明:")
print("  1. Token 本身是正确的")
print("  2. 代理工作正常")
print("  3. API 访问没问题")
print("\n环境变量中的 Token 可能需要手动更新或等待 Gateway 完全重启")
