#!/usr/bin/env python3
"""
X (Twitter) API Scraper - 稳定版本
每次请求时动态获取 Bearer Token
"""

import requests
import json
import os
import base64
from datetime import datetime
from typing import List, Dict, Optional

class XAPIClient:
    """X API v2 客户端"""
    
    def __init__(self):
        self.base_url = "https://api.twitter.com/2"
        self.consumer_key = os.environ.get("X_API_KEY", "")
        self.consumer_secret = os.environ.get("X_API_SECRET", "")
        
        if not self.consumer_key or not self.consumer_secret:
            raise ValueError("X_API_KEY 和 X_API_SECRET 环境变量必须设置")
        
        # 配置代理
        self.session = requests.Session()
        self.session.proxies = {
            'http': 'http://127.0.0.1:7890',
            'https': 'http://127.0.0.1:7890'
        }
    
    def _get_fresh_bearer_token(self) -> str:
        """每次请求时动态获取新的 Bearer Token"""
        oauth_url = "https://api.twitter.com/oauth2/token"
        
        credentials = f"{self.consumer_key}:{self.consumer_secret}"
        b64_credentials = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            "Authorization": f"Basic {b64_credentials}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = "grant_type=client_credentials"
        
        try:
            response = self.session.post(oauth_url, headers=headers, data=data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                bearer_token = result.get("access_token")
                return bearer_token
            return ""
        except Exception as e:
            print(f"❌ 获取 Bearer Token 失败: {e}")
            return ""
    
    def get_user_id_by_username(self, username: str) -> Optional[str]:
        """通过用户名获取用户 ID"""
        url = f"{self.base_url}/users/by/username/{username}"
        
        bearer_token = self._get_fresh_bearer_token()
        if not bearer_token:
            print("❌ 无法获取 Bearer Token")
            return None
        
        headers = {
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json"
        }
        
        response = self.session.get(url, headers=headers)
        
        print(f"请求URL: {url}")
        print(f"响应状态: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            return data.get("data", {}).get("id")
        else:
            print(f"❌ 获取用户 ID 失败: {response.status_code}")
            print(f"响应内容: {response.text}")
            return None
    
    def get_user_tweets(
        self, 
        user_id: str, 
        max_results: int = 100,
        pagination_fields: List[str] = None
    ) -> List[Dict]:
        """获取用户的推文（支持分页）"""
        if pagination_fields is None:
            pagination_fields = ["created_at", "author_id"]
        
        url = f"{self.base_url}/users/{user_id}/tweets"
        params = {
            "max_results": max_results,
            "tweet.fields": ",".join(pagination_fields)
        }
        
        all_tweets = []
        next_token = None
        
        while True:
            bearer_token = self._get_fresh_bearer_token()
            if not bearer_token:
                print("❌ 无法获取 Bearer Token")
                break
            
            headers = {
                "Authorization": f"Bearer {bearer_token}",
                "Content-Type": "application/json"
            }
            
            if next_token:
                params["pagination_token"] = next_token
            
            response = self.session.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                tweets = data.get("data", [])
                all_tweets.extend(tweets)
                
                # 检查是否有下一页
                meta = data.get("meta", {})
                next_token = meta.get("next_token")
                
                if not next_token:
                    break
                    
                print(f"✅ 已获取 {len(all_tweets)} 条推文...")
            else:
                print(f"❌ 获取推文失败: {response.status_code}")
                print(f"响应内容: {response.text}")
                break
        
        return all_tweets
    
    def search_tweets(
        self,
        query: str,
        max_results: int = 100
    ) -> List[Dict]:
        """搜索推文"""
        url = f"{self.base_url}/tweets/search/recent"
        params = {
            "query": query,
            "max_results": max_results,
            "tweet.fields": "created_at,author_id,public_metrics"
        }
        
        bearer_token = self._get_fresh_bearer_token()
        if not bearer_token:
            print("❌ 无法获取 Bearer Token")
            return []
        
        headers = {
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json"
        }
        
        try:
            response = self.session.get(url, headers=headers, params=params)
            
            print(f"搜索URL: {response.url}")
            print(f"响应状态: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                return data.get("data", [])
            else:
                print(f"❌ 搜索失败: {response.status_code}")
                print(f"响应内容: {response.text}")
                return []
        except Exception as e:
            print(f"❌ 搜索错误: {e}")
            return []
    
    def save_to_json(self, tweets: List[Dict], filename: str):
        """保存推到 JSON 文件"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(tweets, f, ensure_ascii=False, indent=2)
        print(f"✅ 已保存 {len(tweets)} 条推文到 {filename}")
    
    def save_to_csv(self, tweets: List[Dict], filename: str):
        """保存推文到 CSV 文件"""
        import csv
        
        if not tweets:
            print("⚠️ 没有推文可保存")
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
        
        print(f"✅ 已保存 {len(tweets)} 条推文到 {filename}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='X (Twitter) API Scraper - 稳定版')
    parser.add_argument('--username', help='要抓取的用户名')
    parser.add_argument('--user-id', help='用户 ID（如果已知）')
    parser.add_argument('--search', help='搜索查询')
    parser.add_argument('--max-results', type=int, default=100, help='最大结果数')
    parser.add_argument('--output', help='输出文件名（JSON 或 CSV）')
    
    args = parser.parse_args()
    
    try:
        client = XAPIClient()
        print("✅ X API 客户端初始化成功")
        
        if args.search:
            print(f"🔍 搜索: {args.search}")
            tweets = client.search_tweets(args.search, args.max_results)
            
            if tweets:
                print(f"✅ 找到 {len(tweets)} 条推文")
                
                if args.output:
                    if args.output.endswith('.csv'):
                        client.save_to_csv(tweets, args.output)
                    else:
                        client.save_to_json(tweets, args.output)
                else:
                    for i, tweet in enumerate(tweets[:5], 1):
                        print(f"\n{i}. {tweet.get('text', '')[:100]}...")
        
        elif args.username:
            print(f"👤 获取用户: @{args.username}")
            
            user_id = client.get_user_id_by_username(args.username)
            
            if user_id:
                print(f"✅ 用户 ID: {user_id}")
                
                tweets = client.get_user_tweets(user_id, args.max_results)
                
                if tweets:
                    print(f"✅ 获取到 {len(tweets)} 条推文")
                    
                    if args.output:
                        if args.output.endswith('.csv'):
                            client.save_to_csv(tweets, args.output)
                        else:
                            client.save_to_json(tweets, args.output)
                    else:
                        for i, tweet in enumerate(tweets[:5], 1):
                            print(f"\n{i}. {tweet.get('text', '')[:100]}...")
        
        elif args.user_id:
            print(f"👤 用户 ID: {args.user_id}")
            tweets = client.get_user_tweets(args.user_id, args.max_results)
            
            if tweets:
                print(f"✅ 获取到 {len(tweets)} 条推文")
                
                if args.output:
                    if args.output.endswith('.csv'):
                        client.save_to_csv(tweets, args.output)
                    else:
                        client.save_to_json(tweets, args.output)
                else:
                    for i, tweet in enumerate(tweets[:5], 1):
                        print(f"\n{i}. {tweet.get('text', '')[:100]}...")
        
        else:
            print("⚠️ 请指定 --username, --user-id 或 --search")
            print("示例:")
            print("  python3 scripts/x-api-scraper.py --username elonmusk --output elon_tweets.json")
            print("  python3 scripts/x-api-scraper.py --search 'python AI' --max-results 50")
    
    except ValueError as e:
        print(f"❌ 配置错误: {e}")
        print("请确保已设置 X_API_KEY 和 X_API_SECRET 环境变量")
    except Exception as e:
        print(f"❌ 错误: {e}")


if __name__ == "__main__":
    main()
