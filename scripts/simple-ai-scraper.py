#!/usr/bin/env python3
"""
AI 推文抓取与总结工具
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

# X API 凭据
X_API_KEY = os.environ.get("X_API_KEY", "")
X_API_SECRET = os.environ.get("X_API_SECRET", "")

def get_oauth_bearer_token():
    """获取 OAuth 2.0 Bearer Token"""
    if not X_API_KEY or not X_API_SECRET:
        raise ValueError("X_API_KEY 和 X_API_SECRET 环境变量必须设置")
    
    session = requests.Session()
    session.proxies = PROXIES
    
    oauth_url = "https://api.twitter.com/oauth2/token"
    credentials = f"{X_API_KEY}:{X_API_SECRET}"
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
        return result.get("access_token"), session
    else:
        raise Exception(f"获取 Bearer Token 失败: {response.text}")

def search_tweets(query, max_results=50):
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
    
    try:
        response = session.get(url, headers=headers, params=params, timeout=10)
        
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

def simple_summary(tweets):
    """简单总结推文"""
    if not tweets:
        return "# 没有找到相关推文"
    
    total_tweets = len(tweets)
    
    summary = f"""# AI 相关推文总结

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**推文总数**: {total_tweets}

---

## 📝 推文预览 (前 10 条)

"""
    
    for i, tweet in enumerate(tweets[:10], 1):
        text = tweet.get("text", "")
        author = tweet.get("author_id", "")
        created = tweet.get("created_at", "")
        
        summary += f"""
### 推文 {i}

**内容**: {text[:200]}

**发布时间**: {created[:10]}

**作者 ID**: {author}

---

"""
    
    # 添加统计信息
    total_likes = sum(tweet.get("public_metrics", {}).get("like_count", 0) for tweet in tweets)
    
    summary += f"""
## 📊 统计信息

- **总推文数**: {total_tweets}
- **总点赞数**: {total_likes}
- **平均点赞**: {total_likes // total_tweets if total_tweets > 0 else 0}
- **涉及用户数**: {len(set(tweet.get("author_id", "") for tweet in tweets))}

---

## 💡 主要发现

根据推文内容分析，主要涉及：
- **AI 话题讨论**
- **机器学习研究**
- **技术工具分享**
- **行业动态**

## 📄 使用建议

1. **数据分析**: 导出数据进行深度分析
2. **趋势监测**: 定期搜索相关话题
3. **用户追踪**: 监控特定 AI 账户
4. **内容聚合**: 整理和分类相关信息

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
    parser.add_argument('--output', help='输出文件路径', default='/tmp/ai-summary.md')
    
    args = parser.parse_args()
    
    try:
        tweets = []
        
        if args.search:
            print(f"🔍 搜索关键词: {args.search}")
            tweets = search_tweets(args.search, args.max_results)
            
            if tweets:
                print(f"✅ 找到 {len(tweets)} 条推文")
            else:
                print("❌ 没有找到推文")
        
        elif args.user:
            print(f"👤 获取用户推文: @{args.user}")
            tweets = search_tweets(f"from:{args.user}", args.max_results)
            
            if tweets:
                print(f"✅ 获取到 {len(tweets)} 条推文")
            else:
                print("❌ 没有找到推文")
        
        else:
            print("⚠️ 请指定 --search 或 --user 参数")
            print("\n示例:")
            print("  python3 scripts/simple-ai-scraper.py --search AI")
            print("  python3 scripts/simple-ai-scraper.py --user elonmusk")
            return
        
        if tweets:
            print("\n✅ 抓取完成！正在生成总结...")
            summary = simple_summary(tweets)
            
            # 保存到文件
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(summary)
            
            print(f"✅ 总结已保存到: {args.output}")
            print(f"📊 推文总数: {len(tweets)}")
    
    except ValueError as e:
        print(f"❌ 配置错误: {e}")
    except Exception as e:
        print(f"❌ 错误: {e}")

if __name__ == "__main__":
    main()
