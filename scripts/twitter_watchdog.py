#!/usr/bin/env python3
"""
Twitter Watchdog - 定时抓取 Twitter 关注列表中的 AI 相关推文

架构：
  - X 官方 API (Bearer Token) → 获取关注列表（免费，带本地缓存）
  - twitterapi.io → 抓取推文内容（$0.15/1k，经济实惠）
  - Claude API → AI 智能总结（可选）

时区：Asia/Shanghai (UTC+8)

调度策略（建议通过 OpenClaw 或 launchd 实现）：
  08:00  --hours-ago 8    # 推送 00:00~08:00 的推文
  12:00  --hours-ago 4    # 推送 08:00~12:00 的推文
  18:00  --hours-ago 6    # 推送 12:00~18:00 的推文
  21:00  --hours-ago 3    # 推送 18:00~21:00 的推文
  00:00  --hours-ago 3    # 推送 21:00~00:00 的推文

用法：
  python3 twitter_watchdog.py [选项]

  --hours-ago N           只保留最近 N 小时内的推文（配合调度使用）
  --max-followings N      关注列表抓取范围（0=全部）
  --tweets-per-user N     每个用户最多推文数
  --trending-count N      热门推文最多条数
  --trending-query "..."  热门搜索关键词（Twitter 搜索语法）
  --min-faves N           热门推文最低点赞数
  --language LANG         语言过滤（all/en/zh/ja...）
  --exclude-users "a,b"   排除的用户名（逗号分隔）
  --output-dir PATH       输出目录
  --reset-state           重置去重状态，重新拉取全量
  --no-trending           禁用热门搜索
  --no-summary            禁用 AI 总结
"""

import os
import json
import yaml
import requests
import base64
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path
import subprocess
import hashlib
import time
import re

# 上海时区 UTC+8
TZ_CN = timezone(timedelta(hours=8))


class TwitterWatchdog:
    def __init__(self, config_file=None, cli_args=None, report_only=False):
        """初始化 Twitter Watchdog

        Args:
            report_only: True 时跳过 Twitter API 初始化（仅用于生成周报/月报）
        """
        self.config = self.load_config(config_file)
        self.hours_ago = None

        # 应用 CLI 参数覆盖
        if cli_args:
            self.apply_cli_overrides(cli_args)

        self.twitter_config = self.config["twitter"]
        self.output_config = self.config["output"]
        self.filters_config = self.config.get("filters", {})
        self.notifications_config = self.config.get("notifications", {})
        self.advanced_config = self.config.get("advanced", {})

        if not report_only:
            # X 官方 API 凭证（仅用于获取关注列表）
            api_config = self.config.get("twitter_api", {})
            self.consumer_key = api_config.get("consumer_key", "")
            self.consumer_secret = api_config.get("consumer_secret", "")

            # twitterapi.io 凭证（用于抓取推文）
            self.twitterapi_io_key = self.config.get("twitterapi_io", {}).get("api_key", "")

            # 生成 X 官方 Bearer Token
            self.bearer_token = self._generate_bearer_token()

            self.timeout = self.advanced_config.get("timeout_seconds", 30)
            self.state = self.load_state()

    def apply_cli_overrides(self, args):
        """将 CLI 参数覆盖到 config"""
        if getattr(args, "hours_ago", None) is not None:
            self.hours_ago = args.hours_ago
        if getattr(args, "max_followings", None) is not None:
            self.config.setdefault("advanced", {})["max_followings"] = args.max_followings
        if getattr(args, "tweets_per_user", None) is not None:
            self.config.setdefault("twitter", {})["tweets_per_user"] = args.tweets_per_user
        if getattr(args, "trending_count", None) is not None:
            self.config.setdefault("trending_search", {})["max_tweets"] = args.trending_count
        if getattr(args, "trending_query", None) is not None:
            self.config.setdefault("trending_search", {})["query"] = args.trending_query
        if getattr(args, "min_faves", None) is not None:
            self.config.setdefault("trending_search", {})["min_views"] = args.min_faves
        if getattr(args, "language", None) is not None:
            self.config.setdefault("filters", {})["language"] = args.language
        if getattr(args, "exclude_users", None):
            self.config.setdefault("twitter", {})["exclude_users"] = [
                u.strip() for u in args.exclude_users.split(",")
            ]
        if getattr(args, "output_dir", None) is not None:
            self.config.setdefault("output", {})["directory"] = args.output_dir
        if getattr(args, "no_trending", False):
            self.config.setdefault("trending_search", {})["enabled"] = False
        if getattr(args, "no_summary", False):
            self.config.setdefault("ai_summary", {})["enabled"] = False

    def _generate_bearer_token(self):
        """通过 Consumer Key/Secret 生成 Bearer Token（X 官方 API）"""
        credentials = base64.b64encode(
            f"{self.consumer_key}:{self.consumer_secret}".encode()
        ).decode()
        resp = requests.post(
            "https://api.twitter.com/oauth2/token",
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            },
            data="grant_type=client_credentials",
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    # ── 时间工具 ──────────────────────────────────────────

    @staticmethod
    def now():
        """当前时间（UTC+8）"""
        return datetime.now(TZ_CN)

    @staticmethod
    def parse_tweet_time(created_at):
        """解析 twitterapi.io 的 createdAt 字段，返回 aware datetime"""
        if not created_at:
            return None
        # 格式: "Sat Feb 07 11:01:48 +0000 2026"
        try:
            dt = datetime.strptime(created_at, "%a %b %d %H:%M:%S %z %Y")
            return dt.astimezone(TZ_CN)
        except ValueError:
            pass
        # ISO 格式兜底
        try:
            dt = datetime.fromisoformat(created_at)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(TZ_CN)
        except ValueError:
            return None

    def is_tweet_in_window(self, tweet):
        """检查推文是否在 --hours-ago 时间窗口内"""
        if self.hours_ago is None:
            return True
        created = self.parse_tweet_time(tweet.get("createdAt", ""))
        if created is None:
            return True  # 无法解析时间则保留
        cutoff = self.now() - timedelta(hours=self.hours_ago)
        return created >= cutoff

    # ── 配置与状态 ────────────────────────────────────────

    def load_config(self, config_file=None):
        if config_file is None:
            config_file = Path(__file__).parent.parent / "config" / "config.yaml"
        with open(config_file, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def load_state(self):
        state_file = Path(
            self.advanced_config.get("state_file", ".twitter_watchdog_state.json")
        )
        if state_file.exists():
            with open(state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                data["seen_tweets"] = set(data.get("seen_tweets", []))
                return data
        return {"seen_tweets": set(), "followings_cache": None, "followings_updated": None}

    def save_state(self):
        state_file = self.advanced_config.get(
            "state_file", ".twitter_watchdog_state.json"
        )
        state_to_save = {
            "seen_tweets": list(self.state["seen_tweets"]),
            "followings_cache": self.state.get("followings_cache"),
            "followings_updated": self.state.get("followings_updated"),
        }
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state_to_save, f, ensure_ascii=False, indent=2)

    # ── 去重 ──────────────────────────────────────────────

    def get_tweet_hash(self, tweet_id):
        return hashlib.md5(str(tweet_id).encode()).hexdigest()

    def is_tweet_seen(self, tweet_id):
        return self.get_tweet_hash(tweet_id) in self.state["seen_tweets"]

    def mark_tweet_seen(self, tweet_id):
        self.state["seen_tweets"].add(self.get_tweet_hash(tweet_id))

    # ── X 官方 API（仅获取关注列表）──────────────────────

    def _x_api_get(self, url, params=None):
        """X 官方 API 请求"""
        headers = {"Authorization": f"Bearer {self.bearer_token}"}
        retry = self.advanced_config.get("retry_attempts", 3)
        for attempt in range(retry):
            resp = requests.get(url, headers=headers, params=params, timeout=self.timeout)
            if resp.status_code == 429:
                reset = int(resp.headers.get("x-rate-limit-reset", 0))
                wait = max(reset - int(time.time()), 10)
                print(f"  X API 速率限制，等待 {wait}s...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()
        raise Exception("X API 请求失败")

    def get_following(self):
        """获取关注列表（带24小时本地缓存，减少 X API 调用）"""
        cache_hours = self.advanced_config.get("followings_cache_hours", 24)
        cached_time = self.state.get("followings_updated")
        cached_data = self.state.get("followings_cache")

        if cached_data and cached_time:
            try:
                updated = datetime.fromisoformat(cached_time)
                if self.now() - updated.astimezone(TZ_CN) < timedelta(hours=cache_hours):
                    print(f"  使用缓存的关注列表（{len(cached_data)} 人）")
                    return cached_data
            except (ValueError, TypeError):
                pass

        username = self.twitter_config["username"]
        print(f"  从 X API 获取 @{username} 的关注列表...")

        user_data = self._x_api_get(
            f"https://api.twitter.com/2/users/by/username/{username}"
        )
        user_id = user_data["data"]["id"]

        max_followings = self.advanced_config.get("max_followings", 0)
        all_followings = []
        pagination_token = None

        while True:
            params = {
                "max_results": 1000,
                "user.fields": "username,name,description,public_metrics",
            }
            if pagination_token:
                params["pagination_token"] = pagination_token

            data = self._x_api_get(
                f"https://api.twitter.com/2/users/{user_id}/following", params
            )
            all_followings.extend(data.get("data", []))

            if max_followings > 0 and len(all_followings) >= max_followings:
                all_followings = all_followings[:max_followings]
                break

            pagination_token = data.get("meta", {}).get("next_token")
            if not pagination_token:
                break

        self.state["followings_cache"] = all_followings
        self.state["followings_updated"] = self.now().isoformat()

        exclude = set(self.twitter_config.get("exclude_users", []))
        if exclude:
            all_followings = [u for u in all_followings if u["username"] not in exclude]
            print(f"  排除 {len(exclude)} 个用户后剩余 {len(all_followings)} 人")

        return all_followings

    # ── twitterapi.io（抓取推文）──────────────────────────

    def _twitterapiio_get(self, endpoint, params=None):
        """twitterapi.io API 请求"""
        url = f"https://api.twitterapi.io/twitter/{endpoint}"
        headers = {"X-API-Key": self.twitterapi_io_key}
        retry = self.advanced_config.get("retry_attempts", 3)
        for attempt in range(retry):
            resp = requests.get(url, headers=headers, params=params, timeout=self.timeout)
            if resp.status_code == 429:
                print(f"  twitterapi.io 速率限制，等待 10s...")
                time.sleep(10)
                continue
            resp.raise_for_status()
            return resp.json()
        raise Exception("twitterapi.io 请求失败")

    def get_tweets(self, username):
        """通过 twitterapi.io 获取指定用户的最新推文"""
        data = self._twitterapiio_get(
            "user/last_tweets",
            params={"userName": username},
        )
        tweets = data.get("data", {}).get("tweets", [])

        filtered = []
        for t in tweets:
            if self.twitter_config.get("exclude_retweets", True):
                if t.get("type") == "retweet" or t.get("text", "").startswith("RT @"):
                    continue
            if self.twitter_config.get("exclude_replies", True):
                if t.get("isReply", False):
                    continue
            filtered.append(t)

        max_tweets = self.twitter_config.get("tweets_per_user", 20)
        return filtered[:max_tweets]

    # ── 全网热门 AI 搜索 ───────────────────────────────────

    def search_trending_ai(self, max_tweets=20):
        """通过 Advanced Search 搜索全网热门 AI 推文"""
        search_config = self.config.get("trending_search", {})
        query = search_config.get(
            "query",
            "(AI OR LLM OR GPT OR Claude OR OpenAI OR AGI OR 大模型) min_faves:50 -is:retweet -is:reply",
        )
        min_views = search_config.get("min_views", 2000)

        data = self._twitterapiio_get(
            "tweet/advanced_search",
            params={"query": query, "queryType": "Top"},
        )
        tweets = data.get("tweets", []) or data.get("data", {}).get("tweets", [])

        result = [t for t in tweets if t.get("viewCount", 0) >= min_views]
        result.sort(key=lambda t: t.get("viewCount", 0), reverse=True)
        return result[:max_tweets]

    # ── 过滤 ──────────────────────────────────────────────

    def filter_tweet(self, tweet):
        """根据配置过滤推文"""
        if not self.filters_config.get("enabled", True):
            return True, "no_filters"

        lang_filter = self.filters_config.get("language", "all")
        if lang_filter != "all" and tweet.get("lang") != lang_filter:
            return False, "language_filter"

        min_likes = self.filters_config.get("min_likes", 0)
        min_retweets = self.filters_config.get("min_retweets", 0)
        if tweet.get("likeCount", 0) < min_likes:
            return False, "engagement_filter"
        if tweet.get("retweetCount", 0) < min_retweets:
            return False, "engagement_filter"

        # AI 过滤模式：跳过关键词匹配，由 Claude 判断相关性
        ai_filter = self.config.get("ai_summary", {}).get("ai_filter", False)
        if ai_filter:
            return True, "ai_filter_mode"

        text = tweet.get("text", "").lower()
        exclude_keywords = self.filters_config.get("keywords", {}).get("exclude", [])
        for kw in exclude_keywords:
            if kw.lower() in text:
                return False, f"excluded_keyword:{kw}"

        include_keywords = self.filters_config.get("keywords", {}).get("include", [])
        if include_keywords:
            if not any(kw.lower() in text for kw in include_keywords):
                return False, "no_include_keyword"

        return True, "passed"

    # ── Claude AI 总结 + 智能筛选 ──────────────────────────

    def generate_ai_summary(self, followings_data, trending_tweets):
        """调用 Claude API 生成智能总结，可选同时进行 AI 相关性判断

        Returns:
            (summary_text, ai_tweet_ids) - ai_tweet_ids 为 set 或 None
        """
        summary_config = self.config.get("ai_summary", {})
        if not summary_config.get("enabled", True):
            return None, None

        api_key = (
            summary_config.get("api_key", "")
            or os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
            or os.environ.get("ANTHROPIC_API_KEY", "")
        )
        if not api_key:
            print("  跳过 AI 总结（未配置 Anthropic API Key）")
            return None, None

        base_url = (
            summary_config.get("base_url", "")
            or os.environ.get("ANTHROPIC_BASE_URL", "")
            or "https://api.anthropic.com"
        )

        ai_filter = summary_config.get("ai_filter", False)

        # 构建推文内容
        content_parts = []
        if followings_data:
            content_parts.append("## 关注列表推文：")
            for ud in followings_data:
                uname = ud["user"]["username"]
                for t in ud["tweets"]:
                    tid = t.get("id", "")
                    likes = t.get("likeCount", 0)
                    views = t.get("viewCount", 0)
                    text = t.get("text", "")[:200]
                    url = t.get("url", "")
                    quoted = t.get("quoted_tweet")
                    quoted_info = ""
                    if quoted:
                        q_author = quoted.get("author", {}).get("userName", "?")
                        q_text = quoted.get("text", "")[:150]
                        quoted_info = f"\n  [引用 @{q_author}]: {q_text}"
                    id_prefix = f"[ID:{tid}] " if ai_filter else ""
                    content_parts.append(f"- {id_prefix}@{uname} ({views:,} views, {likes} likes): {text}{quoted_info}\n  URL: {url}")

        if trending_tweets:
            content_parts.append("\n## 全网热门 AI 推文：")
            for t in trending_tweets:
                tid = t.get("id", "")
                author = t.get("author", {}).get("userName", "?")
                likes = t.get("likeCount", 0)
                views = t.get("viewCount", 0)
                text = t.get("text", "")[:200]
                url = t.get("url", "")
                id_prefix = f"[ID:{tid}] " if ai_filter else ""
                content_parts.append(f"- {id_prefix}@{author} ({views:,} views, {likes:,} likes): {text}\n  URL: {url}")

        all_content = "\n".join(content_parts)

        window_desc = ""
        if self.hours_ago:
            window_desc = f"（本次覆盖最近 {self.hours_ago} 小时）"

        if ai_filter:
            prompt = f"""你是一个 AI 行业信息整理员。以下是从 Twitter 抓取的推文列表{window_desc}。

任务：
1. 从所有推文中筛选出与 AI 领域、AI 工具、AI 行业相关的推文
2. 将筛选出的推文整理为信息清单

输出格式（严格遵循）：
每条为一个列表项，标题本身就是链接，后跟客观描述：

- [具体标题](推文URL)。客观描述。

示例：
- [Claude Code 新增 /insights 命令](https://x.com/xxx/status/123)。分析过去一个月的历史记录、项目情况和使用习惯，给出工作流优化建议。
- [Mistral AI 发布 Voxtral Transcribe 2](https://x.com/xxx/status/456)。包括批量转录 V2 和实时 Realtime 两个版本，V2 支持 13 种语言、说话人识别和词级时间戳，Realtime 延迟低于 200ms。

规则：
- 标题要具体精炼：说清是什么工具/产品/事件，不加多余修饰
- 描述包含关键数据、核心功能、具体特点，去除空泛表述和重复修饰
- 如果推文引用/转发了其他内容，描述原始内容
- 多条推文讲同一件事时，合并为一条，综合所有信息
- 按信息价值排序，输出扁平列表，不分类分组
- 不加总结段落或结尾语

最后，输出你筛选出的所有 AI 相关推文的 ID 列表（JSON 格式）：
```json
{{"ai_tweet_ids": ["id1", "id2"]}}
```

---
{all_content}"""
        else:
            prompt = f"""你是一个 AI 行业信息整理员。以下是从 Twitter 抓取的 AI 相关推文{window_desc}。

将推文整理为信息清单，输出格式：

- [具体标题](推文URL)。客观描述。

示例：
- [Claude Code 新增 /insights 命令](https://x.com/xxx/status/123)。分析过去一个月的历史记录、项目情况和使用习惯，给出工作流优化建议。
- [Mistral AI 发布 Voxtral Transcribe 2](https://x.com/xxx/status/456)。包括批量转录 V2 和实时 Realtime 两个版本，V2 支持 13 种语言、说话人识别和词级时间戳，Realtime 延迟低于 200ms。

规则：
- 标题要具体精炼：说清是什么工具/产品/事件，不加多余修饰
- 描述包含关键数据、核心功能、具体特点，去除空泛表述和重复修饰
- 如果推文引用/转发了其他内容，描述原始内容
- 多条推文讲同一件事时，合并为一条，综合所有信息
- 按信息价值排序，输出扁平列表，不分类分组
- 不加总结段落或结尾语

---
{all_content}"""

        model = summary_config.get("model", "claude-sonnet-4-5-20250929")
        max_tokens = summary_config.get("max_tokens", 4096)

        print(f"  调用 Claude ({model}) via {base_url}...")
        try:
            api_url = f"{base_url.rstrip('/')}/v1/messages"
            resp = requests.post(
                api_url,
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": model,
                    "max_tokens": max_tokens,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=120,
            )
            resp.raise_for_status()
            result = resp.json()
            response_text = result["content"][0]["text"]
            usage = result.get("usage", {})
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
            print(f"  AI 总结完成（{input_tokens} + {output_tokens} tokens）")

            ai_tweet_ids = None
            summary_text = response_text

            if ai_filter:
                json_match = re.search(r'```json\s*\n(.*?)\n```', response_text, re.DOTALL)
                if json_match:
                    try:
                        id_data = json.loads(json_match.group(1))
                        ai_tweet_ids = set(str(i) for i in id_data.get("ai_tweet_ids", []))
                        print(f"  Claude 识别出 {len(ai_tweet_ids)} 条 AI 相关推文")
                    except json.JSONDecodeError:
                        print("  警告: 无法解析 AI 筛选结果，保留所有推文")
                    summary_text = response_text[:json_match.start()].strip()
                else:
                    print("  警告: AI 未返回筛选结果，保留所有推文")

            return summary_text, ai_tweet_ids
        except Exception as e:
            print(f"  AI 总结失败: {e}")
            return None, None

    # ── 通知 ──────────────────────────────────────────────

    def send_notification(self, title, message):
        if not self.notifications_config.get("enabled", True):
            return
        sound = self.notifications_config.get("sound", "Glass")
        try:
            subprocess.run(
                [
                    "osascript", "-e",
                    f'display notification "{message}" with title "{title}" sound name "{sound}"',
                ],
                check=True, capture_output=True,
            )
        except Exception as e:
            print(f"  通知失败: {e}")

    # ── 主流程 ────────────────────────────────────────────

    def scrape_followings_tweets(self):
        """主流程：抓取 → 过滤 → 时间窗口 → AI 总结/筛选 → 报告"""
        username = self.twitter_config["username"]
        ai_filter = self.config.get("ai_summary", {}).get("ai_filter", False)
        now = self.now()
        print(f"=== Twitter Watchdog ===")
        print(f"监控账户: @{username}")
        print(f"时间: {now.strftime('%Y-%m-%d %H:%M:%S')} (UTC+8)")
        if self.hours_ago:
            cutoff = now - timedelta(hours=self.hours_ago)
            print(f"时间窗口: {cutoff.strftime('%H:%M')} ~ {now.strftime('%H:%M')}（最近 {self.hours_ago} 小时）")
        print()

        # 步骤1: 获取关注列表
        print("[1/5] 获取关注列表...")
        followings = self.get_following()
        print(f"  共 {len(followings)} 个关注账户")

        # 步骤2: 抓取推文
        print(f"\n[2/5] 抓取推文（twitterapi.io）...")
        output_path = Path(self.output_config["directory"])
        output_path.mkdir(parents=True, exist_ok=True)

        all_data = []
        new_tweets_count = 0
        api_calls = 0

        for i, user in enumerate(followings, 1):
            uname = user["username"]
            name = user["name"]
            print(f"  [{i}/{len(followings)}] @{uname} ({name})...", end=" ", flush=True)

            try:
                tweets = self.get_tweets(uname)
                api_calls += 1

                filtered_tweets = []
                for tweet in tweets:
                    tweet_id = tweet.get("id", "")
                    if self.advanced_config.get("deduplicate", True) and self.is_tweet_seen(tweet_id):
                        continue
                    if not self.is_tweet_in_window(tweet):
                        continue

                    passed, reason = self.filter_tweet(tweet)
                    if passed:
                        filtered_tweets.append(tweet)
                        self.mark_tweet_seen(tweet_id)
                        new_tweets_count += 1

                label = "条" if ai_filter else "条 AI 相关"
                print(f"{len(filtered_tweets)} {label}")

                if filtered_tweets:
                    all_data.append({"user": user, "tweets": filtered_tweets})

            except Exception as e:
                print(f"错误: {e}")

        # 步骤3: 全网热门 AI 搜索
        trending_config = self.config.get("trending_search", {})
        trending_tweets = []
        if trending_config.get("enabled", True):
            max_trending = trending_config.get("max_tweets", 20)
            print(f"\n[3/5] 搜索全网热门 AI 推文...")
            try:
                trending_tweets = self.search_trending_ai(max_tweets=max_trending)
                api_calls += 1
                # 去重 + 时间窗口
                seen_ids = {t.get("id") for ud in all_data for t in ud["tweets"]}
                trending_tweets = [
                    t for t in trending_tweets
                    if t.get("id") not in seen_ids and self.is_tweet_in_window(t)
                ]
                print(f"  找到 {len(trending_tweets)} 条热门 AI 推文")
            except Exception as e:
                print(f"  搜索失败: {e}")

        # 步骤4: AI 智能总结（+ AI 相关性判断）
        ai_summary = None
        total_collected = new_tweets_count  # 记录筛选前总数
        if all_data or trending_tweets:
            step_desc = "AI 智能总结 + 相关性判断" if ai_filter else "AI 智能总结"
            print(f"\n[4/5] {step_desc}...")
            ai_summary, ai_tweet_ids = self.generate_ai_summary(all_data, trending_tweets)

            # AI 筛选模式：根据 Claude 判断过滤推文
            if ai_tweet_ids is not None:
                filtered_data = []
                new_tweets_count = 0
                for ud in all_data:
                    ft = [t for t in ud["tweets"] if str(t.get("id", "")) in ai_tweet_ids]
                    if ft:
                        filtered_data.append({"user": ud["user"], "tweets": ft})
                        new_tweets_count += len(ft)
                all_data = filtered_data
                trending_tweets = [t for t in trending_tweets if str(t.get("id", "")) in ai_tweet_ids]
                print(f"  AI 筛选: {new_tweets_count} 条关注 + {len(trending_tweets)} 条热门（总抓取 {total_collected} 条）")

        # 步骤5: 输出报告
        print(f"\n[5/5] 生成报告...")
        print(f"  twitterapi.io 调用: {api_calls} 次")
        print(f"  关注列表 AI 推文: {new_tweets_count} 条")
        if trending_tweets:
            print(f"  全网热门 AI 推文: {len(trending_tweets)} 条")

        total = new_tweets_count + len(trending_tweets)
        if total > 0:
            threshold = self.notifications_config.get("threshold", 1)
            if self.notifications_config.get("on_new_tweets", True) and total >= threshold:
                self.send_notification(
                    "Twitter Watchdog",
                    f"发现 {new_tweets_count} 条关注 + {len(trending_tweets)} 条热门 AI 推文！",
                )

        self.save_state()

        if all_data or trending_tweets:
            self.save_results(all_data, trending_tweets, username, {
                "new_tweets_count": new_tweets_count,
                "trending_count": len(trending_tweets),
            }, ai_summary)
        else:
            print("  没有新的 AI 相关推文")

        return all_data

    # ── 报告输出 ──────────────────────────────────────────

    def save_results(self, data, trending_tweets, source_username, stats, ai_summary=None):
        output_path = Path(self.output_config["directory"])
        timestamp = self.now().strftime("%Y%m%d_%H%M%S")

        if "json" in self.output_config.get("formats", ["json"]):
            json_file = output_path / f"ai_tweets_{timestamp}.json"
            json_data = {
                "followings": data,
                "trending": trending_tweets,
                "ai_summary": ai_summary,
            }
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2, default=str)
            print(f"  JSON: {json_file}")

        if "markdown" in self.output_config.get("formats", ["markdown"]):
            md_file = output_path / f"ai_tweets_{timestamp}.md"
            self.save_as_markdown(data, trending_tweets, md_file, source_username, stats, ai_summary)
            print(f"  Markdown: {md_file}")

        if self.output_config.get("create_summary", False):
            summary_file = output_path / "latest_summary.md"
            self.create_summary(summary_file, source_username, data, trending_tweets, stats, ai_summary)
            print(f"  汇总: {summary_file}")

    def _write_tweet_md(self, f, tweet):
        """写入单条推文的 Markdown"""
        created_raw = tweet.get("createdAt", "")
        created_cn = self.parse_tweet_time(created_raw)
        time_str = created_cn.strftime("%Y-%m-%d %H:%M") if created_cn else created_raw

        text = tweet.get("text", "")
        likes = tweet.get("likeCount", 0)
        retweets = tweet.get("retweetCount", 0)
        replies = tweet.get("replyCount", 0)
        views = tweet.get("viewCount", 0)
        url = tweet.get("url", "")
        author = tweet.get("author", {})
        author_name = author.get("userName", "") or author.get("name", "")

        f.write(f"### {time_str}")
        if author_name:
            f.write(f" · @{author_name}")
        f.write("\n\n")
        f.write(f"{text}\n\n")
        f.write(f"*{replies} replies | {retweets} retweets | {likes} likes | {views} views*")
        if url:
            f.write(f"  [原文链接]({url})")
        f.write("\n\n")

    def save_as_markdown(self, data, trending_tweets, output_file, source_username, stats, ai_summary=None):
        """生成 Markdown 报告"""
        now = self.now()
        ts = now.strftime("%Y-%m-%d %H:%M:%S")
        total = stats['new_tweets_count'] + stats.get('trending_count', 0)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"# AI 推文日报\n\n")
            f.write(f"**监控账户**: @{source_username}\n")
            f.write(f"**抓取时间**: {ts} (UTC+8)\n")
            if self.hours_ago:
                cutoff = now - timedelta(hours=self.hours_ago)
                f.write(f"**时间窗口**: {cutoff.strftime('%H:%M')} ~ {now.strftime('%H:%M')}\n")
            f.write(f"**关注列表 AI 推文**: {stats['new_tweets_count']} 条\n")
            if trending_tweets:
                f.write(f"**全网热门 AI 推文**: {stats.get('trending_count', 0)} 条\n")
            f.write(f"**总计**: {total} 条\n\n")

            if ai_summary:
                f.write("---\n\n")
                f.write("# AI 智能总结\n\n")
                f.write(ai_summary)
                f.write("\n\n")

            if data:
                f.write("---\n\n")
                f.write("# 关注列表 AI 推文\n\n")

                for user_data in data:
                    user = user_data["user"]
                    tweets = user_data["tweets"]
                    uname = user["username"]
                    name = user["name"]
                    desc = user.get("description", "")
                    followers = user.get("public_metrics", {}).get("followers_count", 0)

                    f.write(f"## @{uname} ({name})\n\n")
                    if desc:
                        f.write(f"> {desc}\n\n")
                    f.write(f"**粉丝**: {followers:,}\n\n")

                    for tweet in tweets:
                        self._write_tweet_md(f, tweet)

                    f.write("---\n\n")

            if trending_tweets:
                f.write("---\n\n")
                f.write("# 全网热门 AI 推文\n\n")

                for tweet in trending_tweets:
                    self._write_tweet_md(f, tweet)
                    f.write("---\n\n")

    def create_summary(self, output_file, source_username, data, trending_tweets, stats, ai_summary=None):
        now = self.now()
        ts = now.strftime("%Y-%m-%d %H:%M:%S")
        total = stats['new_tweets_count'] + stats.get('trending_count', 0)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"# Twitter Watchdog - AI 推文汇总\n\n")
            f.write(f"**更新时间**: {ts} (UTC+8)\n")
            f.write(f"**监控账户**: @{source_username}\n")
            if self.hours_ago:
                cutoff = now - timedelta(hours=self.hours_ago)
                f.write(f"**时间窗口**: {cutoff.strftime('%H:%M')} ~ {now.strftime('%H:%M')}\n")
            f.write(f"**关注列表 AI 推文**: {stats['new_tweets_count']}\n")
            if trending_tweets:
                f.write(f"**全网热门 AI 推文**: {stats.get('trending_count', 0)}\n")
            f.write(f"**总计**: {total}\n\n")

            if ai_summary:
                f.write("## AI 智能总结\n\n")
                f.write(ai_summary)
                f.write("\n\n")

            if data:
                f.write("## 关注列表\n\n")
                f.write("| 用户 | AI 推文数 |\n")
                f.write("|------|----------|\n")
                for ud in sorted(data, key=lambda x: len(x["tweets"]), reverse=True):
                    f.write(f"| @{ud['user']['username']} | {len(ud['tweets'])} |\n")
                f.write("\n")

            if trending_tweets:
                f.write("## 全网热门 TOP\n\n")
                f.write("| 用户 | 内容摘要 | views | likes |\n")
                f.write("|------|----------|-------|-------|\n")
                for t in trending_tweets[:10]:
                    author = t.get("author", {}).get("userName", "?")
                    text = t.get("text", "")[:60].replace("\n", " ").replace("|", "/")
                    views = t.get("viewCount", 0)
                    likes = t.get("likeCount", 0)
                    f.write(f"| @{author} | {text}... | {views:,} | {likes:,} |\n")
                f.write("\n")

            f.write(f"*详见最新的 `ai_tweets_*.md` 文件*\n")

    # ── 周报/月报 ──────────────────────────────────────────

    def _parse_summary_items(self, summary_text):
        """解析 AI 总结文本，提取每条新闻条目"""
        items = []
        if not summary_text:
            return items
        for para in summary_text.split("\n\n"):
            para = para.strip()
            if not para.startswith("- ["):
                continue
            match = re.match(r'^- \[(.+?)\]\((.+?)\)[，。,.]\s*(.+)$', para, re.DOTALL)
            if match:
                title, url, desc = match.groups()
                items.append({
                    "title": title,
                    "url": url,
                    "description": desc.strip(),
                    "full_text": para,
                })
        return items

    def _deduplicate_items(self, all_items):
        """按 URL 去重，保留描述最长的版本"""
        url_map = {}
        for item in all_items:
            url = item["url"]
            if url not in url_map or len(item["full_text"]) > len(url_map[url]["full_text"]):
                url_map[url] = item
        return list(url_map.values())

    def _claude_consolidate(self, items, period, period_label):
        """调用 Claude 将去重后的条目整合为周报/月报"""
        summary_config = self.config.get("ai_summary", {})
        api_key = (
            summary_config.get("api_key", "")
            or os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
            or os.environ.get("ANTHROPIC_API_KEY", "")
        )
        if not api_key:
            print("  跳过 Claude 整合（未配置 API Key）")
            return None

        base_url = (
            summary_config.get("base_url", "")
            or os.environ.get("ANTHROPIC_BASE_URL", "")
            or "https://api.anthropic.com"
        )

        label = "月报" if period == "monthly" else "周报"
        content = "\n".join(item["full_text"] for item in items)

        prompt = f"""你是一个 AI 行业信息整理员。以下是 {period_label} 期间每日 AI 推文总结中汇总的信息条目（已按 URL 初步去重，共 {len(items)} 条）。

任务：将这些条目整合为一份结构化的{label}。

输出结构（严格遵循）：

## 本期要点

用 3~5 个bullet point 概括本期最重要的事件/发布/趋势，每条一句话，不带链接。

## AI 产品与工具

新产品发布、产品重大更新、工具推荐等。

## AI 模型与技术

新模型发布、模型评测、技术架构、算法突破等。

## AI 开发者生态

开发框架、API、SDK、开源项目、开发者工具链等。

## AI 行业动态

公司战略、融资收购、人事变动、政策法规、行业合作等。

## AI 研究与观点

学术论文、实验结果、行业观察、趋势分析等。

每个分类下的条目格式：
- [具体标题](推文URL)。客观描述，信息齐全但不冗余。

规则：
- 合并报道同一事件/产品的不同条目，保留最完整的描述
- 每个分类内按重要性从高到低排列
- 每条描述应包含关键数据、核心功能、具体特点，去除重复修饰和空泛表述
- 只描述客观事实，不做主观评价
- 如果某个分类下没有内容，省略该分类
- 不要加统计数据或结尾总结

---
{content}"""

        model = summary_config.get("model", "claude-sonnet-4-5-20250929")
        max_tokens = summary_config.get("max_tokens", 4096)
        if period == "monthly":
            max_tokens = max(max_tokens, 8192)

        print(f"  调用 Claude ({model}) 整合{label}...")
        try:
            api_url = f"{base_url.rstrip('/')}/v1/messages"
            resp = requests.post(
                api_url,
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": model,
                    "max_tokens": max_tokens,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=180,
            )
            resp.raise_for_status()
            result = resp.json()
            text = result["content"][0]["text"]
            usage = result.get("usage", {})
            print(f"  Claude 整合完成（{usage.get('input_tokens', 0)} + {usage.get('output_tokens', 0)} tokens）")
            return text
        except Exception as e:
            print(f"  Claude 整合失败: {e}")
            return None

    def generate_periodic_report(self, period, date_str):
        """生成周报或月报

        Args:
            period: "monthly" or "weekly"
            date_str: "YYYY-MM" for monthly, "YYYY-MM-DD" for weekly
        """
        output_path = Path(self.output_config["directory"])

        if period == "monthly":
            year, month = date_str.split("-")
            period_label = f"{year} 年 {int(month)} 月"
            output_file = output_path / f"monthly_report_{year}_{month}.md"
        else:
            start_date = datetime.strptime(date_str, "%Y-%m-%d")
            end_date = start_date + timedelta(days=7)
            period_label = f"{start_date.strftime('%m/%d')} ~ {end_date.strftime('%m/%d')}"
            output_file = output_path / f"weekly_report_{date_str.replace('-', '_')}.md"

        label = "月报" if period == "monthly" else "周报"
        print(f"=== 生成{label} ===")
        print(f"期间: {period_label}")
        print(f"数据目录: {output_path}")

        # 扫描历史 JSON 文件
        json_files = sorted(output_path.glob("ai_tweets_*.json"))
        if not json_files:
            print("  未找到历史报告文件")
            return

        # 按日期范围过滤
        matched_files = []
        for f in json_files:
            parts = f.stem.split("_")  # ai_tweets_20260211_095245
            if len(parts) >= 3:
                file_date_str = parts[2]  # 20260211
                if period == "monthly":
                    if file_date_str.startswith(f"{year}{month}"):
                        matched_files.append(f)
                else:
                    try:
                        file_date = datetime.strptime(file_date_str, "%Y%m%d")
                        if start_date <= file_date < end_date:
                            matched_files.append(f)
                    except ValueError:
                        pass

        if not matched_files:
            print(f"  在指定期间内未找到报告文件")
            return

        print(f"  找到 {len(matched_files)} 个报告文件")

        # 提取所有 AI 总结条目
        all_items = []
        for f in matched_files:
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                summary = data.get("ai_summary", "")
                if summary:
                    items = self._parse_summary_items(summary)
                    all_items.extend(items)
                    print(f"  {f.name}: {len(items)} 条")
            except Exception as e:
                print(f"  {f.name}: 读取失败 - {e}")

        if not all_items:
            print("  未提取到任何信息条目")
            return

        print(f"  共提取 {len(all_items)} 条（去重前）")

        # 去重
        unique_items = self._deduplicate_items(all_items)
        print(f"  去重后: {len(unique_items)} 条")

        # Claude 整合
        consolidated = self._claude_consolidate(unique_items, period, period_label)

        # 生成报告
        report_title = f"AI 推文{label}"
        output_path.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"# {report_title} — {period_label}\n\n")
            if consolidated:
                f.write(consolidated)
            else:
                # Fallback: 直接输出去重后的条目
                f.write("\n\n".join(item["full_text"] for item in unique_items))
            f.write("\n")

        print(f"\n报告已保存: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Twitter Watchdog - AI 推文监控工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
调度策略（UTC+8，建议通过 OpenClaw 实现）：
  08:00  python3 twitter_watchdog.py --hours-ago 8
  12:00  python3 twitter_watchdog.py --hours-ago 4
  18:00  python3 twitter_watchdog.py --hours-ago 6
  21:00  python3 twitter_watchdog.py --hours-ago 3
  00:00  python3 twitter_watchdog.py --hours-ago 3
""",
    )
    parser.add_argument("--config", help="配置文件路径")
    parser.add_argument("--hours-ago", type=int, help="只保留最近 N 小时内的推文")
    parser.add_argument("--max-followings", type=int, help="关注列表抓取范围（0=全部）")
    parser.add_argument("--tweets-per-user", type=int, help="每个用户最多推文数")
    parser.add_argument("--trending-count", type=int, help="热门推文最多条数")
    parser.add_argument("--trending-query", help="热门搜索关键词（Twitter 搜索语法）")
    parser.add_argument("--min-faves", type=int, help="热门推文最低浏览量（默认 2000）")
    parser.add_argument("--language", help="语言过滤（all/en/zh/ja...）")
    parser.add_argument("--exclude-users", help="排除的用户名（逗号分隔）")
    parser.add_argument("--output-dir", help="输出目录")
    parser.add_argument("--reset-state", action="store_true", help="重置去重状态")
    parser.add_argument("--no-trending", action="store_true", help="禁用热门搜索")
    parser.add_argument("--no-summary", action="store_true", help="禁用 AI 总结")
    parser.add_argument("--monthly", metavar="YYYY-MM", help="生成月报（如 2026-02）")
    parser.add_argument("--weekly", metavar="YYYY-MM-DD", help="生成周报（从指定日期起 7 天）")

    args = parser.parse_args()

    # 周报/月报模式：不需要 Twitter API，只需要配置和历史数据
    if args.monthly or args.weekly:
        watchdog = TwitterWatchdog(config_file=args.config, cli_args=args, report_only=True)
        period = "monthly" if args.monthly else "weekly"
        date_str = args.monthly or args.weekly
        watchdog.generate_periodic_report(period, date_str)
        print("\n=== 完成 ===")
        return

    if args.reset_state:
        state_file = ".twitter_watchdog_state.json"
        if os.path.exists(state_file):
            os.remove(state_file)
            print("已重置去重状态")
        else:
            print("无状态文件，无需重置")

    watchdog = TwitterWatchdog(config_file=args.config, cli_args=args)
    watchdog.scrape_followings_tweets()
    print("\n=== 完成 ===")


if __name__ == "__main__":
    main()
