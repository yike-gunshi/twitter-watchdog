#!/usr/bin/env python3
"""
X (Twitter) API 获取关注列表
使用 OAuth 1.0a Access Token 访问用户自己的关注列表
"""

import requests
import json
import os
import base64
import hmac
import hashlib
import urllib.parse
import time
import random
import string

# 用户提供的 OAuth 1.0a 凭据
ACCESS_TOKEN = "1723554628498030592-xdxt0NPedA2vwy6SbdBjPYNAxbfEdA"
ACCESS_TOKEN_SECRET = "ktUDSv4JBOlUlpn2R3q7yPBwGnnJoJ1gCSWE7ceKRUGDP"
CONSUMER_KEY = "k1aM91JgDj4obSMSsM2KWGSss"
CONSUMER_SECRET = "yNha9rF5VcF5aMBkWrY5wWO9En1BWtEQWa4KVJzBsCfpJuo"

# 配置代理
PROXIES = {
    'http': 'http://127.0.0.1:7890',
    'https': 'http://127.0.0.1:7890'
}

def generate_nonce():
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(32))

def percent_encode(s):
    return urllib.parse.quote(s, safe='')

def create_oauth_signature(method, url, params, consumer_secret, access_token_secret=''):
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
    signing_key = f"{percent_encode(consumer_secret)}&{percent_encode(access_token_secret)}"
    
    # 签名
    signature = hmac.new(
        signing_key.encode('utf-8'),
        base_string.encode('utf-8'),
        hashlib.sha1
    ).digest()
    
    return base64.b64encode(signature).decode('utf-8')

def get_oauth_header(url, params=None):
    """生成 OAuth 1.0a 头"""
    if params is None:
        params = {}
    
    oauth_params = {
        'oauth_consumer_key': CONSUMER_KEY,
        'oauth_nonce': generate_nonce(),
        'oauth_signature_method': 'HMAC-SHA1',
        'oauth_timestamp': str(int(time.time())),
        'oauth_token': ACCESS_TOKEN,
        'oauth_version': '1.0'
    }
    
    # 合并所有参数
    all_params = {**oauth_params, **params}
    
    # 创建签名（URL 中不包含查询参数用于签名）
    signature = create_oauth_signature('GET', url, all_params, CONSUMER_SECRET, ACCESS_TOKEN_SECRET)
    oauth_params['oauth_signature'] = signature
    
    # 生成 OAuth 头
    oauth_header = 'OAuth ' + ', '.join([
        f'{percent_encode(k)}="{percent_encode(v)}"'
        for k, v in sorted(oauth_params.items())
    ])
    
    return oauth_header

def get_own_user_info():
    """获取当前用户信息"""
    url = "https://api.twitter.com/1.1/account/verify_credentials.json"
    
    session = requests.Session()
    session.proxies = PROXIES
    
    oauth_header = get_oauth_header(url)
    
    headers = {
        'Authorization': oauth_header
    }
    
    print("获取当前用户信息...")
    
    try:
        response = session.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            user_data = response.json()
            print(f"✅ 用户: @{user_data.get('screen_name')} ({user_data.get('name')})")
            print(f"   用户 ID: {user_data.get('id_str')}")
            print(f"   关注数: {user_data.get('friends_count')}")
            print(f"   粉丝数: {user_data.get('followers_count')}")
            return user_data
        else:
            print(f"❌ 获取用户信息失败: {response.status_code}")
            print(f"   响应: {response.text[:500]}")
            return None
    except Exception as e:
        print(f"❌ 错误: {e}")
        return None

def get_following_list(screen_name, count=5, cursor=-1):
    """获取关注列表"""
    url = f"https://api.twitter.com/1.1/friends/list.json"
    
    params = {
        'screen_name': screen_name,
        'count': str(count),
        'cursor': str(cursor)
    }
    
    # 添加查询参数到 URL
    param_string = '&'.join([f"{k}={urllib.parse.quote(str(v), safe='')}" for k, v in params.items()])
    full_url = f"{url}?{param_string}"
    
    session = requests.Session()
    session.proxies = PROXIES
    
    oauth_header = get_oauth_header(url, params)
    
    headers = {
        'Authorization': oauth_header
    }
    
    print(f"\n获取 @{screen_name} 的关注列表（最多 {count} 条）...")
    
    try:
        response = session.get(full_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # 获取关注列表
            following = data.get('users', [])
            
            # 获取游标（用于分页）
            next_cursor = data.get('next_cursor', 0)
            
            print(f"✅ 获取到 {len(following)} 个关注")
            
            return {
                'following': following,
                'next_cursor': next_cursor,
                'raw': data
            }
        else:
            print(f"❌ 获取关注列表失败: {response.status_code}")
            print(f"   响应: {response.text[:500]}")
            return None
    except Exception as e:
        print(f"❌ 错误: {e}")
        return None

def save_to_json(data, filename):
    """保存到 JSON"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ 已保存到 {filename}")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='获取 Twitter 关注列表')
    parser.add_argument('--username', help='用户名（默认为当前登录用户）')
    parser.add_argument('--count', type=int, default=5, help='获取数量（默认: 5）')
    parser.add_argument('--output', help='输出文件名')
    
    args = parser.parse_args()
    
    # 获取当前用户信息
    user_info = get_own_user_info()
    
    if not user_info:
        print("❌ 无法获取用户信息，退出")
        return
    
    # 确定要查询的用户名
    username = args.username if args.username else user_info.get('screen_name')
    
    # 获取关注列表
    result = get_following_list(username, args.count)
    
    if result:
        following = result.get('following', [])
        
        if following:
            print(f"\n{'=' * 70}")
            print(f"关注列表: @{username}")
            print(f"{'=' * 70}")
            
            for i, user in enumerate(following, 1):
                print(f"\n{i}. {user.get('name', '')} (@{user.get('screen_name', '')})")
                print(f"   ID: {user.get('id_str', '')}")
                print(f"   描述: {(user.get('description', '') or '无描述')[:100]}")
                print(f"   关注: {user.get('friends_count', 0)} | 粉丝: {user.get('followers_count', 0)}")
            
            # 保存结果
            if args.output:
                save_to_json({
                    'username': username,
                    'count': len(following),
                    'next_cursor': result.get('next_cursor'),
                    'following': following
                }, args.output)
            
            print(f"\n{'=' * 70}")
            print(f"完成！获取到 {len(following)} 个关注")
            print(f"{'=' * 70}")

if __name__ == "__main__":
    main()
