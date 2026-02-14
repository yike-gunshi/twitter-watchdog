#!/usr/bin/env python3
"""
Twitter API 客户端 - 独立工作版本
每次请求动态获取正确的 URL 编码 Bearer Token
"""

import requests
import os
import base64
import json

def get_oauth_bearer_token():
    """获取 OAuth 2.0 Bearer Token（URL 编码版本）"""
    consumer_key = os.environ.get("X_API_KEY", "")
    consumer_secret = os.environ.get("X_API_SECRET", "")
    
    if not consumer_key or not consumer_secret:
        raise ValueError("X_API_KEY 和 X_API_SECRET 环境变量必须设置")
    
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
        # 返回 URL 编码的 Token（这是正确的）
        return result.get("access_token"), session
    else:
        raise Exception(f"获取 Bearer Token 失败: {response.text}")

def get_user_by_username(username):
    """获取用户信息"""
    bearer_token, session = get_oauth_bearer_token()
    
    url = f"https://api.twitter.com/2/users/by/username/{username}"
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json"
    }
    
    response = session.get(url, headers=headers, timeout=10)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"获取用户失败: {response.text}")

def get_user_tweets(user_id, max_results=100):
    """获取用户推文"""
    bearer_token, session = get_oauth_bearer_token()
    
    url = f"https://api.twitter.com/2/users/{user_id}/tweets"
    params = {
        "max_results": max_results,
        "tweet.fields": "created_at,author_id,public_metrics"
    }
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json"
    }
    
    all_tweets = []
    next_token = None
    
    while True:
        if next_token:
            params["pagination_token"] = next_token
        
        response = session.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            tweets = data.get("data", [])
            all_tweets.extend(tweets)
            
            meta = data.get("meta", {})
            next_token = meta.get("next_token")
            
            if not next_token:
                break
                
            print(f"✅ 已获取 {len(all_tweets)} 条推文...")
        else:
            raise Exception(f"获取推文失败: {response.text}")
    
    return all_tweets

def search_tweets(query, max_results=100):
    """搜索推文"""
    bearer_token, session = get_oauth_bearer_token()
    
    url = "https://api.twitter.com/2/tweets/search/recent"
    params = {
        "query": query,
        "max_results": max_results,
        "tweet.fields": "created_at,author_id,public_metrics"
    }
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json"
    }
    
    response = session.get(url, headers=headers, params=params, timeout=10)
    
    if response.status_code == 200:
        data = response.json()
        return data.get("data", [])
    else:
        raise Exception(f"搜索失败: {response.text}")

def save_json(data, filename):
    """保存 JSON"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ 已保存到 {filename}")

def save_csv(tweets, filename):
    """保存 CSV"""
    import csv
    
    if not tweets:
        print("⚠️ 没有数据可保存")
        return
    
    fieldnames = ['id', 'text', 'created_at', 'author_id']
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for tweet in tweets:
            writer.writerow({
                'id': tweet.get('id', ''),
                'text': tweet.get('text', ''),
                'created_at': tweet.get('created_at', ''),
                'author_id': tweet.get('author_id', '')
            })
    
    print(f"✅ 已保存到 {filename}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Twitter API 抓取器')
    parser.add_argument('--username', help='用户名')
    parser.add_argument('--search', help='搜索关键词')
    parser.add_argument('--max-results', type=int, default=100, help='最大结果数')
    parser.add_argument('--output', help='输出文件')
    
    args = parser.parse_args()
    
    try:
        if args.search:
            print(f"🔍 搜索: {args.search}")
            tweets = search_tweets(args.search, args.max_results)
            
            if tweets:
                print(f"✅ 找到 {len(tweets)} 条推文")
                
                for i, tweet in enumerate(tweets[:5], 1):
                    text = tweet.get('text', '')
                    created = tweet.get('created_at', '')
                    print(f"\n{i}. [{created}] {text[:100]}...")
                
                if args.output:
                    if args.output.endswith('.csv'):
                        save_csv(tweets, args.output)
                    else:
                        save_json(tweets, args.output)
            else:
                print("⚠️ 没有找到结果")
        
        elif args.username:
            print(f"👤 获取用户: @{args.username}")
            
            user_data = get_user_by_username(args.username)
            user_info = user_data.get('data', {})
            
            print(f"✅ 用户 ID: {user_info.get('id')}")
            print(f"   名称: {user_info.get('name')}")
            print(f"   用户名: @{user_info.get('username')}")
            
            user_id = user_info.get('id')
            
            if user_id:
                tweets = get_user_tweets(user_id, args.max_results)
                
                if tweets:
                    print(f"\n✅ 获取到 {len(tweets)} 条推文")
                    
                    for i, tweet in enumerate(tweets[:5], 1):
                        text = tweet.get('text', '')
                        created = tweet.get('created_at', '')
                        print(f"\n{i}. [{created}] {text[:100]}...")
                    
                    if args.output:
                        if args.output.endswith('.csv'):
                            save_csv(tweets, args.output)
                        else:
                            save_json(tweets, args.output)
        
        else:
            print("⚠️ 请指定 --username 或 --search")
            print("示例:")
            print("  python3 scripts/twitter-api.py --username elonmusk --output elon.json")
            print("  python3 scripts/twitter-api.py --search 'AI' --max-results 10")
    
    except Exception as e:
        print(f"❌ 错误: {e}")
