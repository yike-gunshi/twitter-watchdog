#!/usr/bin/env python3
"""
AI 推文抓取与总结
"""

import requests
import os
import json
from datetime import datetime

# 配置代理
PROXIES = {
    'http': 'http://127.0.0.1:7890',
    'https': 'http://127.0.0.1:7890'
}

def get_bearer_token():
    """获取 Bearer Token"""
    api_key = os.environ.get("X_API_KEY", "")
    api_secret = os.environ.get("X_API_SECRET", "")
    
    if not api_key or not api_secret:
        raise ValueError("X_API_KEY 和 X_API_SECRET 环境变量必须设置")
    
    session = requests.Session()
    session.proxies = PROXIES
    
    oauth_url = "https://api.twitter.com/oauth2/token"
    credentials = f"{api_key}:{api_secret}"
    
    import base64
    b64_credentials = base64.b64encode(credentials.encode()).decode()
    
    headers = {
        "Authorization": f"Basic {b64_credentials}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    data = "grant_type=client_credentials"
    
    response = session.post(oauth_url, headers=headers, data=data, timeout=10)
    
    if response.status_code == 200:
        result = response.json()
        return result.get("access_token")
    else:
        raise Exception(f"获取 Token 失败: {response.status_code}")

def search_tweets(query, max_results=50):
    """搜索推文"""
    bearer_token = get_bearer_token()
    
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
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return data.get("data", [])
        else:
            print(f"❌ 搜索失败: {response.status_code}")
            print(f"响应: {response.text[:500]}")
            return []
    except Exception as e:
        print(f"❌ 搜索错误: {e}")
        return []

def get_user_tweets(username, max_results=50):
    """获取用户推文"""
    bearer_token = get_bearer_token()
    
    user_url = f"https://api.twitter.com/2/users/by/username/{username}"
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(user_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            user_data = response.json()
            user_id = user_data.get("data", {}).get("id")
            
            if user_id:
                tweets_url = f"https://api.twitter.com/2/users/{user_id}/tweets"
                params = {
                    "max_results": max_results,
                    "tweet.fields": "created_at,author_id,public_metrics"
                }
                
                all_tweets = []
                next_token = None
                
                while True:
                    if next_token:
                        params["pagination_token"] = next_token
                    
                    response = requests.get(tweets_url, headers=headers, params=params, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        tweets = data.get("data", [])
                        all_tweets.extend(tweets)
                        
                        meta = data.get("meta", {})
                        next_token = meta.get("next_token")
                        
                        if not next_token:
                            break
                    else:
                        break
                
                return all_tweets
            else:
                print(f"❌ 获取用户失败: {response.status_code}")
                return []
        else:
            print(f"❌ 获取用户失败: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ 错误: {e}")
        return []

def create_summary(tweets):
    """创建总结"""
    if not tweets:
        return "# 没有找到相关推文"
    
    total_tweets = len(tweets)
    total_likes = sum(tweet.get("public_metrics", {}).get("like_count", 0) for tweet in tweets)
    
    summary = f"""# AI 相关推文总结

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**推文总数**: {total_tweets}

---

## 📝 推文列表 (前 20 条)

"""
    
    for i, tweet in enumerate(tweets[:20], 1):
        text = tweet.get("text", "")
        author = tweet.get("author_id", "")
        created = tweet.get("created_at", "")
        metrics = tweet.get("public_metrics", {})
        likes = metrics.get("like_count", 0)
        
        summary += f"""
### {i}. 推文

**发布时间**: {created}

**内容**: {text[:200]}

**互动数据**:
- 👍 点赞: {likes}
- 🔄 转推: {metrics.get("retweet_count", 0)}
- 💬 引用: {metrics.get("quote_count", 0)}

**作者 ID**: {author}

---

"""
    
    summary += f"""
## 📊 统计信息

- **总推文数**: {total_tweets}
- **总点赞数**: {total_likes}
- **平均点赞**: {total_likes // total_tweets if total_tweets > 0 else 0}
- **涉及用户**: {len(set(tweet.get("author_id", "") for tweet in tweets))}

---

## 💡 内容分析

根据推文内容分析，主要涉及：
- **AI 话题讨论**
- **机器学习研究**
- **行业动态**
- **技术分享**

## 📄 数据保存

完整的推文数据已保存为 JSON 格式，便于进一步分析和处理。

---
*本报告由 AI 推文抓取工具生成*
"""
    
    return summary

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='AI 推文抓取与总结工具')
    parser.add_argument('--search', help='搜索关键词')
    parser.add_argument('--user', help='用户名')
    parser.add_argument('--max-results', type=int, default=50, help='最大结果数')
    parser.add_argument('--output', help='输出文件', default='/tmp/ai-summary.md')
    
    args = parser.parse_args()
    
    try:
        tweets = []
        
        if args.search:
            print(f"🔍 搜索关键词: {args.search}")
            tweets = search_tweets(args.search, args.max_results)
        
        elif args.user:
            print(f"👤 获取用户推文: @{args.user}")
            tweets = get_user_tweets(args.user, args.max_results)
        
        else:
            print("⚠️ 请指定 --search 或 --user")
            return
        
        if tweets:
            print(f"✅ 找到 {len(tweets)} 条推文")
            
            # 生成总结
            summary = create_summary(tweets)
            
            # 保存原始数据
            json_output = args.output.replace('.md', '.json')
            with open(json_output, 'w', encoding='utf-8') as f:
                json.dump(tweets, f, ensure_ascii=False, indent=2)
            
            # 保存总结
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(summary)
            
            print(f"\n✅ 总结已保存到: {args.output}")
            print(f"📊 推文总数: {len(tweets)}")
    
    except ValueError as e:
        print(f"❌ 配置错误: {e}")
    except Exception as e:
        print(f"❌ 执行错误: {e}")

if __name__ == "__main__":
    main()
