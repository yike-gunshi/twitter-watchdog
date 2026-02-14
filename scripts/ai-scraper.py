#!/usr/bin/env python3
"""
AI 相关推文抓取与总结工具
"""

import requests
import os
import base64
import json
import argparse
from datetime import datetime

# 配置代理
PROXIES = {
    'http': 'http://127.0.0.1:7890',
    'https': 'http://127.0.0.1:7890'
}

# X API 凭据
CONSUMER_KEY = os.environ.get("X_API_KEY", "")
CONSUMER_SECRET = os.environ.get("X_API_SECRET", "")
ACCESS_TOKEN = os.environ.get("X_ACCESS_TOKEN", "")

def get_oauth_bearer_token():
    """获取 OAuth 2.0 Bearer Token"""
    if not CONSUMER_KEY or not CONSUMER_SECRET:
        raise ValueError("X_API_KEY 和 X_API_SECRET 环境变量必须设置")
    
    session = requests.Session()
    session.proxies = PROXIES
    
    oauth_url = "https://api.twitter.com/oauth2/token"
    credentials = f"{CONSUMER_KEY}:{CONSUMER_SECRET}"
    b64_credentials = base64.b64encode(credentials.encode()).decode()
    
    headers = {
        "Authorization": f"Basic {b64_credentials}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    data = "grant_type=client_credentials"
    
    response = session.post(oauth_url, headers=headers, data=data, timeout=10)
    
    if response.status_code == 200:
        result = response.json()
        return result.get("access_token"), session
    else:
        raise Exception(f"获取 Bearer Token 失败: {response.text}")

def search_ai_tweets(query, max_results=50):
    """搜索 AI 相关推文"""
    bearer_token, session = get_oauth_bearer_token()
    
    url = "https://api.twitter.com/2/tweets/search/recent"
    params = {
        "query": query,
        "max_results": max_results,
        "tweet.fields": "created_at,author_id,public_metrics,lang,context_annotations"
    }
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = session.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            tweets = data.get("data", [])
            print(f"✅ 找到 {len(tweets)} 条推文")
            return tweets
        else:
            print(f"❌ 搜索失败: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ 搜索错误: {e}")
        return []

def get_user_tweets(username, max_results=50):
    """获取用户推文"""
    bearer_token, session = get_oauth_bearer_token()
    
    # 获取用户 ID
    user_url = f"https://api.twitter.com/2/users/by/username/{username}"
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = session.get(user_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            user_data = response.json()
            user_id = user_data.get("data", {}).get("id")
            
            if user_id:
                print(f"✅ 用户 ID: {user_id}")
                
                # 获取用户推文
                tweets_url = f"https://api.twitter.com/2/users/{user_id}/tweets"
                params = {
                    "max_results": max_results,
                    "tweet.fields": "created_at,author_id,public_metrics,lang,context_annotations"
                }
                
                tweets = []
                next_token = None
                
                while True:
                    if next_token:
                        params["pagination_token"] = next_token
                    
                    response = session.get(tweets_url, headers=headers, params=params, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        batch_tweets = data.get("data", [])
                        tweets.extend(batch_tweets)
                        
                        meta = data.get("meta", {})
                        next_token = meta.get("next_token")
                        
                        print(f"✅ 已获取 {len(tweets)} 条推文...")
                    else:
                        break
                
                print(f"✅ 总共获取到 {len(tweets)} 条推文")
                return tweets
            else:
                print(f"❌ 获取用户失败: {response.status_code}")
                return []
    except Exception as e:
        print(f"❌ 错误: {e}")
        return []

def summarize_to_markdown(tweets, output_file):
    """总结推文为 Markdown 文档"""
    if not tweets:
        print("⚠️ 没有推文可总结")
        return
    
    # 按主题分类
    themes = {
        "AI 人工智能": [],
        "机器学习 Machine Learning": [],
        "深度学习 Deep Learning": [],
        "自然语言处理 NLP": [],
        "计算机视觉 Computer Vision": [],
        "加密 Cryptocurrency": [],
        "区块链 Blockchain": [],
        "云计算 Cloud Computing": [],
        "其他 Others": []
    }
    
    for tweet in tweets:
        text = tweet.get("text", "").lower()
        author_id = tweet.get("author_id", "")
        created_at = tweet.get("created_at", "")
        metrics = tweet.get("public_metrics", {})
        
        # 分类推文
        categorized = False
        
        if any(keyword in text for keyword in themes["AI 人工智能"]):
            themes["AI 人工智能"].append(text)
            categorized = True
        elif any(keyword in text for keyword in themes["机器学习 Machine Learning"]):
            themes["机器学习 Machine Learning"].append(text)
            categorized = True
        elif any(keyword in text for keyword in themes["深度学习 Deep Learning"]):
            themes["深度学习 Deep Learning"].append(text)
            categorized = True
        elif any(keyword in text for keyword in themes["自然语言处理 NLP"]):
            themes["自然语言处理 NLP"].append(text)
            categorized = True
        elif any(keyword in text for keyword in themes["计算机视觉 Computer Vision"]):
            themes["计算机视觉 Computer Vision"].append(text)
            categorized = True
        elif any(keyword in text for keyword in themes["加密 Cryptocurrency"]):
            themes["加密 Cryptocurrency"].append(text)
            categorized = True
        elif any(keyword in text for keyword in themes["区块链 Blockchain"]):
            themes["区块链 Blockchain"].append(text)
            categorized = True
        elif any(keyword in text for keyword in themes["云计算 Cloud Computing"]):
            themes["云计算 Cloud Computing"].append(text)
            categorized = True
        
        if not categorized:
            themes["其他 Others"].append(text)
    
    # 生成 Markdown 报告
    markdown = f"""# AI 相关推文总结报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**推文总数**: {len(tweets)}

---

## 📊 主题分布

| 主题 | 推文数 | 占比 |
|------|--------|------|
"""
    
    total = len(tweets)
    for theme, tweets_list in themes.items():
        count = len(tweets_list)
        percentage = (count / total * 100) if total > 0 else 0
        markdown += f"| {theme} | {count} | {percentage:.1f}% |\n"
    
    markdown += f"""| 总计 | {total} | 100% |
"""

    # 展示前 5 条推文预览
    markdown += """
---

## 📝 推文预览 (前 5 条)

"""
    for i, tweet in enumerate(tweets[:5], 1):
        text = tweet.get("text", "")[:100]
        author = tweet.get("author_id", "")
        created = tweet.get("created_at", "")[:10]
        likes = metrics.get("like_count", 0)
        metrics.get("retweet_count", 0)
        retweets = metrics.get("quote_count", 0)
        
        markdown += f"""
### {i}. {created}

**推文内容**: {text}

**互动数据**:
- 👍 点赞: {likes}
- 🔄 转推: {retweets}
- 💬 引用: {retweets}

**作者 ID**: {author}

---

"""
    
    # 保存 Markdown 文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(markdown)
    
    print(f"✅ 总结已保存到: {output_file}")
    print(f"📊 推文总数: {len(tweets)}")
    print(f"📝 主题分类: {len(themes)}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='AI 推文抓取与总结工具')
    parser.add_argument('--search', help='搜索关键词（如 "AI", "人工智能"）')
    parser.add_argument('--user', help='用户名（如 elonmusk）')
    parser.add_argument('--max-results', type=int, default=50, help='最大结果数')
    parser.add_argument('--output', help='输出 Markdown 文件路径', default='/tmp/ai-summary.md')
    
    args = parser.parse_args()
    
    try:
        if args.search:
            print(f"🔍 搜索关键词: {args.search}")
            tweets = search_ai_tweets(args.search, args.max_results)
            
        elif args.user:
            print(f"👤 获取用户推文: @{args.user}")
            tweets = get_user_tweets(args.user, args.max_results)
        
        else:
            print("⚠️ 请指定 --search 或 --user 参数")
            print("\n示例:")
            print("  python3 scripts/ai-scraper.py --search 'AI' --max-results 50")
            print("  python3 scripts/ai-scraper.py --user elonmusk --max-results 50")
            return
        
        if tweets:
            summarize_to_markdown(tweets, args.output)
            print(f"\n✅ 抓取完成！")
            print(f"📄 总结文件: {args.output}")
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        print(f"\n💡 提示: 确保 X_API_KEY 和 X_API_SECRET 环境变量已设置")

if __name__ == "__main__":
    main()
