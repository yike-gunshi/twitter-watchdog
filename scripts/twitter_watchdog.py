#!/usr/bin/env python3
"""
Twitter Watchdog - 三层架构 AI 推文监控工具

架构（三层分离）：
  Layer 1 - 抓取 (scrape):  twitterapi.io → 原始推文 → output/raw/*.json
  Layer 2 - 分析 (analyze): raw JSON → Claude AI 筛选+总结 → output/analysis/*.json
  Layer 3 - 报告 (report):  analysis JSON → HTML/MD 报告 → output/reports/*.{html,md}

数据源：
  - X 官方 API (Bearer Token) → 获取关注列表（免费，带本地缓存）
  - twitterapi.io → 抓取推文内容（$0.15/1k，经济实惠）
  - Claude API → AI 智能筛选+总结

时区：Asia/Shanghai (UTC+8)

用法：
  # Layer 1: 只抓取，存原始数据
  python3 twitter_watchdog.py scrape [--hours-ago 6]

  # Layer 2: 分析原始数据，生成分析结果
  python3 twitter_watchdog.py analyze [--hours-ago 6]
  python3 twitter_watchdog.py analyze --source raw/20260212_140000.json
  python3 twitter_watchdog.py analyze --from "2026-02-12 08:00" --to "2026-02-12 14:00"

  # Layer 3: 从分析结果生成报告
  python3 twitter_watchdog.py report [--source analysis/20260212_143000.json]
  python3 twitter_watchdog.py report --daily 2026-02-12
  python3 twitter_watchdog.py report --weekly 2026-02-10
  python3 twitter_watchdog.py report --monthly 2026-02

  # 流水线模式（向后兼容，等价于 scrape + analyze + report）
  python3 twitter_watchdog.py [--hours-ago 6]
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
            # twitterapi.io 凭证（用于抓取推文 + 获取关注列表）
            self.twitterapi_io_key = self.config.get("twitterapi_io", {}).get("api_key", "")

            # X 官方 API 凭证（可选，作为获取关注列表的 fallback）
            api_config = self.config.get("twitter_api", {})
            self.consumer_key = api_config.get("consumer_key", "")
            self.consumer_secret = api_config.get("consumer_secret", "")

            # 仅在配置了 X 官方凭证时生成 Bearer Token
            self.bearer_token = None
            if self.consumer_key and self.consumer_secret:
                try:
                    self.bearer_token = self._generate_bearer_token()
                except Exception as e:
                    print(f"  X 官方 API 不可用（{e}），将使用 twitterapi.io 获取关注列表")

            self.timeout = self.advanced_config.get("timeout_seconds", 30)
            self.state = self.load_state()

        # 推文图片 URL 映射: tweet_url -> image_url（所有模式都需要）
        self.tweet_images = {}

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

    # ── 获取关注列表 ─────────────────────────────────────

    def _get_followings_twitterapiio(self):
        """通过 twitterapi.io 获取关注列表（无需 X 开发者账号、无需 VPN）"""
        username = self.twitter_config["username"]
        print(f"  从 twitterapi.io 获取 @{username} 的关注列表...")
        max_followings = self.advanced_config.get("max_followings", 0)
        all_followings = []
        cursor = ""
        page = 0
        while True:
            page += 1
            params = {"userName": username, "pageSize": 200}
            if cursor:
                params["cursor"] = cursor
            data = self._twitterapiio_get("user/followings", params)
            batch = data.get("followings", [])
            # 统一字段名为与 X 官方 API 兼容的格式
            for u in batch:
                u.setdefault("username", u.get("userName") or u.get("screen_name", ""))
                u.setdefault("name", u.get("name", u.get("username", "")))
                u.setdefault("description", u.get("description", ""))
                u.setdefault("public_metrics", {
                    "followers_count": u.get("followers_count", u.get("followers", 0))
                })
            all_followings.extend(batch)
            print(f"  第 {page} 页: +{len(batch)} (共 {len(all_followings)})")
            if max_followings > 0 and len(all_followings) >= max_followings:
                all_followings = all_followings[:max_followings]
                break
            if not data.get("has_next_page") or not data.get("next_cursor"):
                break
            cursor = data["next_cursor"]
        return all_followings

    def _get_followings_x_api(self):
        """通过 X 官方 API 获取关注列表（需要开发者账号 + 可能需要 VPN）"""
        username = self.twitter_config["username"]
        print(f"  从 X 官方 API 获取 @{username} 的关注列表...")
        headers = {"Authorization": f"Bearer {self.bearer_token}"}
        retry = self.advanced_config.get("retry_attempts", 3)

        def x_api_get(url, params=None):
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

        user_data = x_api_get(f"https://api.twitter.com/2/users/by/username/{username}")
        user_id = user_data["data"]["id"]

        max_followings = self.advanced_config.get("max_followings", 0)
        all_followings = []
        pagination_token = None
        while True:
            params = {"max_results": 1000, "user.fields": "username,name,description,public_metrics"}
            if pagination_token:
                params["pagination_token"] = pagination_token
            data = x_api_get(f"https://api.twitter.com/2/users/{user_id}/following", params)
            all_followings.extend(data.get("data", []))
            if max_followings > 0 and len(all_followings) >= max_followings:
                all_followings = all_followings[:max_followings]
                break
            pagination_token = data.get("meta", {}).get("next_token")
            if not pagination_token:
                break
        return all_followings

    def get_following(self):
        """获取关注列表（带缓存，优先 twitterapi.io，X 官方 API 作为 fallback）"""
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

        # 优先使用 twitterapi.io（无需 VPN、无需 X 开发者账号）
        all_followings = None
        if self.twitterapi_io_key:
            try:
                all_followings = self._get_followings_twitterapiio()
            except Exception as e:
                print(f"  twitterapi.io 关注列表获取失败: {e}")

        # Fallback: X 官方 API
        if all_followings is None and self.bearer_token:
            try:
                all_followings = self._get_followings_x_api()
            except Exception as e:
                print(f"  X 官方 API 获取关注列表失败: {e}")

        if all_followings is None:
            print("  错误: 无法获取关注列表")
            return []

        self.state["followings_cache"] = all_followings
        self.state["followings_updated"] = self.now().isoformat()

        exclude = set(self.twitter_config.get("exclude_users", []))
        if exclude:
            all_followings = [u for u in all_followings if u.get("username", "") not in exclude]
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
        """通过 twitterapi.io 获取指定用户的最新推文（支持分页）

        当设置了 hours_ago 时，会自动翻页直到推文时间超出时间窗口。
        返回 (filtered_tweets, api_call_count) 元组。
        """
        exclude_rt = self.twitter_config.get("exclude_retweets", True)
        exclude_reply = self.twitter_config.get("exclude_replies", True)
        max_tweets = self.twitter_config.get("tweets_per_user", 20)

        # 时间窗口 cutoff（用于决定是否继续翻页）
        cutoff = None
        if self.hours_ago is not None:
            cutoff = self.now() - timedelta(hours=self.hours_ago)

        filtered = []
        cursor = ""
        api_call_count = 0
        max_pages = 10  # 安全上限，防止无限翻页

        for _ in range(max_pages):
            params = {"userName": username}
            if cursor:
                params["cursor"] = cursor

            data = self._twitterapiio_get("user/last_tweets", params)
            api_call_count += 1

            tweets = data.get("data", {}).get("tweets", [])
            if not tweets:
                tweets = data.get("tweets", [])
            if not tweets:
                break

            oldest_in_page = None
            for t in tweets:
                if exclude_rt and (t.get("type") == "retweet" or t.get("text", "").startswith("RT @")):
                    continue
                if exclude_reply and t.get("isReply", False):
                    continue
                filtered.append(t)

                # 记录本页最旧推文时间
                created = self.parse_tweet_time(t.get("createdAt", ""))
                if created and (oldest_in_page is None or created < oldest_in_page):
                    oldest_in_page = created

            # 不需要分页的情况：没设置时间窗口，或已够数
            if cutoff is None:
                break

            # 本页最旧推文已超出时间窗口，不需要继续翻页
            if oldest_in_page and oldest_in_page < cutoff:
                break

            # 没有下一页
            has_next = data.get("data", {}).get("has_next_page", data.get("has_next_page", False))
            next_cursor = data.get("data", {}).get("next_cursor", data.get("next_cursor", ""))
            if not has_next or not next_cursor:
                break
            cursor = next_cursor

        return filtered[:max_tweets], api_call_count

    @staticmethod
    def extract_media_url(tweet):
        """从推文中提取第一张图片 URL"""
        media_list = tweet.get("extendedEntities", {}).get("media", [])
        if not media_list:
            media_list = tweet.get("entities", {}).get("media", [])
        if not media_list:
            media_list = tweet.get("media", [])
        for m in media_list:
            url = m.get("media_url_https") or m.get("media_url") or m.get("url", "")
            if url and any(ext in url for ext in [".jpg", ".png", ".jpeg", ".gif", ".webp"]):
                return url
        return None

    def collect_tweet_image(self, tweet):
        """收集推文的图片 URL 到 self.tweet_images"""
        tweet_url = tweet.get("url", "")
        if not tweet_url:
            return
        img = self.extract_media_url(tweet)
        if not img:
            # 引用推文的图片
            quoted = tweet.get("quoted_tweet") or tweet.get("quotedTweet")
            if quoted:
                img = self.extract_media_url(quoted)
        if img:
            self.tweet_images[tweet_url] = img

    def download_report_images(self, summary_text, output_path):
        """下载报告中出现的推文图片，返回 tweet_url -> relative_path 映射"""
        if not summary_text or not self.tweet_images:
            return {}
        # 解析报告中所有推文 URL
        report_urls = re.findall(r'\(https://x\.com/[^)]+\)', summary_text)
        report_urls = [u.strip('()') for u in report_urls]
        urls_to_download = {u: self.tweet_images[u] for u in report_urls if u in self.tweet_images}
        if not urls_to_download:
            return {}

        ts = self.now().strftime("%Y%m%d_%H%M%S")
        img_dir = output_path / "images" / ts
        img_dir.mkdir(parents=True, exist_ok=True)
        downloaded = {}
        for tweet_url, img_url in urls_to_download.items():
            try:
                r = requests.get(img_url, timeout=15)
                r.raise_for_status()
                tid = tweet_url.rstrip("/").split("/")[-1]
                ext = ".png" if ".png" in img_url else ".gif" if ".gif" in img_url else ".jpg"
                fname = f"{tid}{ext}"
                with open(img_dir / fname, "wb") as f:
                    f.write(r.content)
                downloaded[tweet_url] = f"images/{ts}/{fname}"
            except Exception:
                pass
        if downloaded:
            print(f"  下载图片: {len(downloaded)}/{len(urls_to_download)}")
        return downloaded

    @staticmethod
    def insert_images_into_summary(summary_text, downloaded):
        """在报告中每条推文后插入图片引用"""
        if not downloaded:
            return summary_text
        lines = summary_text.split("\n")
        new_lines = []
        for line in lines:
            new_lines.append(line)
            for tweet_url, img_path in downloaded.items():
                if f"]({tweet_url})" in line:
                    new_lines.append(f"\n  ![tweet]({img_path})\n")
                    break
        return "\n".join(new_lines)

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
        content_parts = self._build_tweet_lines(followings_data, trending_tweets, with_id=ai_filter)
        all_content = "\n".join(content_parts)

        window_desc = ""
        if self.hours_ago:
            window_desc = f"（本次覆盖最近 {self.hours_ago} 小时）"

        # 分类结构化 prompt（日报/ai_filter/非 ai_filter 共用）
        category_block = """输出结构（严格遵循）：

## 本期要点

用 3~5 个 bullet point 概括最重要的事件/发布/趋势，每条一句话，不带链接。

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
- [具体标题](推文URL)。陈述句描述，信息密度高。

示例：
- [Anthropic 发布 Claude Opus 4.5 安全风险报告](https://x.com/AnthropicAI/status/123)。Anthropic 因其下一代模型接近 AI Safety Level 4 阈值（即具备自主 AI 研发能力），主动发布评估报告，承诺为所有未来模型撰写破坏性风险报告，这是首家为单个模型发布此类文件的 AI 公司。"""

        rules_block = """规则：
- 标题具体精炼，描述用一到两个自然陈述句，把关键信息串在一起
- 有数据就写数据（用户量、价格、性能指标、Star 数等）
- 如果是工具或产品：写明怎么获取、有什么独特优势
- 如果是研究或报告：写明主要发现和实际意义
- 如果推文引用/转发了其他内容，描述原始内容
- 多条推文讲同一件事时合并为一条，综合所有信息源
- 每个分类内按重要性从高到低排列
- 如果某个分类下没有内容，省略该分类
- 不加前言或结尾总结段落"""

        model = summary_config.get("model", "claude-sonnet-4-5-20250929")
        max_tokens = summary_config.get("max_tokens", 4096)
        max_input_tokens = summary_config.get("max_input_tokens", 150000)
        api_url = f"{base_url.rstrip('/')}/v1/messages"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        if ai_filter:
            return self._filter_and_summarize(
                followings_data, trending_tweets, all_content, window_desc,
                category_block, rules_block, model, max_tokens, max_input_tokens,
                api_url, headers, base_url
            )
        else:
            return self._batched_summarize(
                all_content, window_desc, category_block, rules_block,
                model, max_tokens, max_input_tokens, api_url, headers, base_url
            )

    # ── Claude API 辅助方法 ──────────────────────────────

    @staticmethod
    def _estimate_tokens(text):
        """粗略估算文本 token 数（中英混合约 0.4 token/char）"""
        return int(len(text) * 0.4)

    def _call_claude_api(self, prompt, model, max_tokens, api_url, headers,
                         timeout=120, max_retries=3):
        """调用 Claude API，自动重试 + 超时递增，返回 (response_text, usage_dict)"""
        cur_timeout = timeout
        for attempt in range(1, max_retries + 1):
            try:
                resp = requests.post(
                    api_url, headers=headers,
                    json={
                        "model": model,
                        "max_tokens": max_tokens,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                    timeout=cur_timeout,
                )
                resp.raise_for_status()
                result = resp.json()
                return result["content"][0]["text"], result.get("usage", {})
            except Exception as e:
                if attempt < max_retries:
                    wait = 10 * attempt          # 10s, 20s
                    cur_timeout = int(cur_timeout * 1.5)  # 120→180→270
                    print(f"    ⚠ 重试 ({attempt}/{max_retries}, {wait}s 后, "
                          f"timeout→{cur_timeout}s): {type(e).__name__}")
                    time.sleep(wait)
                else:
                    raise

    def _batch_lines_by_tokens(self, lines, max_content_tokens):
        """将文本行列表按 token 数分批，确保每批不超过 max_content_tokens"""
        batches = []
        current_batch = []
        current_tokens = 0
        for line in lines:
            line_tokens = self._estimate_tokens(line)
            if current_tokens + line_tokens > max_content_tokens and current_batch:
                batches.append(current_batch)
                current_batch = []
                current_tokens = 0
            current_batch.append(line)
            current_tokens += line_tokens
        if current_batch:
            batches.append(current_batch)
        return batches

    @staticmethod
    def _parse_ai_tweet_ids(response_text):
        """从 Claude 响应中提取 AI 推文 ID 集合"""
        json_match = re.search(r'```json\s*\n(.*?)\n```', response_text, re.DOTALL)
        if not json_match:
            json_match = re.search(r'\{[^}]*"ai_tweet_ids"[^}]*\}', response_text, re.DOTALL)
            if json_match:
                id_data = json.loads(json_match.group(0))
            else:
                return None
        else:
            id_data = json.loads(json_match.group(1))
        return set(str(i) for i in id_data.get("ai_tweet_ids", []))

    def _build_tweet_lines(self, followings_data, trending_tweets, with_id=False):
        """构建推文文本行列表，返回 list of str"""
        lines = []
        if followings_data:
            lines.append("## 关注列表推文：")
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
                    id_prefix = f"[ID:{tid}] " if with_id else ""
                    lines.append(f"- {id_prefix}@{uname} ({views:,} views, {likes} likes): {text}{quoted_info}\n  URL: {url}")
        if trending_tweets:
            lines.append("\n## 全网热门 AI 推文：")
            for t in trending_tweets:
                tid = t.get("id", "")
                author = t.get("author", {}).get("userName", "?")
                likes = t.get("likeCount", 0)
                views = t.get("viewCount", 0)
                text = t.get("text", "")[:200]
                url = t.get("url", "")
                id_prefix = f"[ID:{tid}] " if with_id else ""
                lines.append(f"- {id_prefix}@{author} ({views:,} views, {likes:,} likes): {text}\n  URL: {url}")
        return lines

    def _filter_and_summarize(
        self, followings_data, trending_tweets, all_content, window_desc,
        category_block, rules_block, model, max_tokens, max_input_tokens,
        api_url, headers, base_url
    ):
        """ai_filter 模式：分批筛选 AI 推文 → 分批生成总结"""
        prompt_overhead = 2000  # 筛选 prompt 模板开销
        max_content_tokens = max_input_tokens - prompt_overhead

        # ── Pass 1: 分批筛选 ──
        tweet_lines = self._build_tweet_lines(followings_data, trending_tweets, with_id=True)
        batches = self._batch_lines_by_tokens(tweet_lines, max_content_tokens)
        total_batches = len(batches)

        ai_tweet_ids = set()
        total_input = 0
        total_output = 0

        filter_label = f"[Pass 1/2] 筛选 AI 推文" if total_batches == 1 else f"[Pass 1/2] 分批筛选 AI 推文（{total_batches} 批）"
        print(f"  {filter_label} ({model}) via {base_url}...")

        for bi, batch in enumerate(batches, 1):
            if total_batches > 1:
                print(f"    批次 {bi}/{total_batches}...", end=" ", flush=True)
            ids, inp, out = self._filter_batch_robust(
                batch, window_desc, model, max_tokens, api_url, headers
            )
            total_input += inp
            total_output += out
            ai_tweet_ids.update(ids)
            if total_batches > 1:
                print(f"{len(ids)} 条")

        print(f"  筛选完成（{total_input} + {total_output} tokens）→ {len(ai_tweet_ids)} 条 AI 相关")

        if not ai_tweet_ids:
            print("  警告: 未识别出 AI 推文，保留所有推文")
            return None, None

        # ── Pass 2: 用筛选后的推文生成总结 ──
        filtered_lines = self._build_filtered_lines(followings_data, trending_tweets, ai_tweet_ids)
        return self._batched_summarize_from_lines(
            filtered_lines, window_desc, category_block, rules_block,
            model, max_tokens, max_input_tokens, api_url, headers, base_url,
            ai_tweet_ids
        )

    def _filter_batch_robust(self, lines, window_desc, model, max_tokens,
                             api_url, headers, depth=0):
        """筛选单个批次，失败后自动拆分为子批次重试。
        返回 (ai_tweet_ids: set, input_tokens: int, output_tokens: int)"""
        batch_content = "\n".join(lines)
        filter_prompt = f"""你是一个 AI 行业信息筛选员。以下是从 Twitter 抓取的推文列表{window_desc}。

任务：从中找出所有与 AI 领域相关的推文（包括 AI 产品、模型、开发工具、行业动态、研究等）。

只输出 JSON，不要输出其他内容：
```json
{{"ai_tweet_ids": ["id1", "id2", ...]}}
```

---
{batch_content}"""
        try:
            resp_text, usage = self._call_claude_api(
                filter_prompt, model, max_tokens, api_url, headers)
            ids = self._parse_ai_tweet_ids(resp_text) or set()
            return ids, usage.get("input_tokens", 0), usage.get("output_tokens", 0)
        except Exception as e:
            # 行数太少无法继续拆分
            if len(lines) <= 10:
                indent = "  " * (depth + 2)
                print(f"\n    {indent}✗ 子批次仍失败且无法继续拆分（{len(lines)} 行）: {type(e).__name__}")
                return set(), 0, 0
            mid = len(lines) // 2
            indent = "  " * (depth + 2)
            print(f"\n    {indent}↳ 拆分为 2 个子批次重试（各 ~{mid} 行）...", end=" ", flush=True)
            ids1, in1, out1 = self._filter_batch_robust(
                lines[:mid], window_desc, model, max_tokens, api_url, headers, depth + 1)
            ids2, in2, out2 = self._filter_batch_robust(
                lines[mid:], window_desc, model, max_tokens, api_url, headers, depth + 1)
            return ids1 | ids2, in1 + in2, out1 + out2

    def _build_filtered_lines(self, followings_data, trending_tweets, ai_tweet_ids):
        """根据 AI 推文 ID 构建筛选后的内容行"""
        lines = []
        if followings_data:
            lines.append("## 关注列表推文：")
            for ud in followings_data:
                uname = ud["user"]["username"]
                for t in ud["tweets"]:
                    if str(t.get("id", "")) not in ai_tweet_ids:
                        continue
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
                    lines.append(f"- @{uname} ({views:,} views, {likes} likes): {text}{quoted_info}\n  URL: {url}")
        if trending_tweets:
            lines.append("\n## 全网热门 AI 推文：")
            for t in trending_tweets:
                if str(t.get("id", "")) not in ai_tweet_ids:
                    continue
                author = t.get("author", {}).get("userName", "?")
                likes = t.get("likeCount", 0)
                views = t.get("viewCount", 0)
                text = t.get("text", "")[:200]
                url = t.get("url", "")
                lines.append(f"- @{author} ({views:,} views, {likes:,} likes): {text}\n  URL: {url}")
        return lines

    def _batched_summarize(
        self, all_content, window_desc, category_block, rules_block,
        model, max_tokens, max_input_tokens, api_url, headers, base_url
    ):
        """非 ai_filter 模式：按 token 分批生成总结"""
        content_lines = all_content.split("\n")
        return self._batched_summarize_from_lines(
            content_lines, window_desc, category_block, rules_block,
            model, max_tokens, max_input_tokens, api_url, headers, base_url,
            ai_tweet_ids=None
        )

    def _batched_summarize_from_lines(
        self, content_lines, window_desc, category_block, rules_block,
        model, max_tokens, max_input_tokens, api_url, headers, base_url,
        ai_tweet_ids
    ):
        """通用分批总结：支持 ai_filter 和非 ai_filter 模式"""
        prompt_overhead = 3000  # 总结 prompt 模板开销
        max_content_tokens = max_input_tokens - prompt_overhead

        batches = self._batch_lines_by_tokens(content_lines, max_content_tokens)
        total_batches = len(batches)

        summary_label = "[Pass 2/2] 生成总结" if ai_tweet_ids is not None else "生成总结"
        if total_batches > 1:
            summary_label += f"（{total_batches} 批）"
        print(f"  {summary_label} ({model}) via {base_url}...")

        partial_summaries = []
        total_input = 0
        total_output = 0

        for bi, batch in enumerate(batches, 1):
            batch_label = f"（第 {bi}/{total_batches} 批）" if total_batches > 1 else ""
            if total_batches > 1:
                print(f"    批次 {bi}/{total_batches}...", end=" ", flush=True)

            summaries, inp, out = self._summarize_batch_robust(
                batch, window_desc, batch_label,
                category_block, rules_block, model, max_tokens, api_url, headers
            )
            total_input += inp
            total_output += out
            partial_summaries.extend(summaries)
            if total_batches > 1 and summaries:
                print(f"完成（{inp} + {out} tokens）")

        if not partial_summaries:
            print("  总结失败: 所有批次均失败")
            return None, ai_tweet_ids

        # 单份总结 → 直接进入校验
        if len(partial_summaries) == 1:
            print(f"  总结完成（{total_input} + {total_output} tokens）")
            final = self._validate_summary(
                partial_summaries[0], model, max_tokens, api_url, headers)
            return final, ai_tweet_ids

        # 多份总结 → 合并 + 校验（合并 prompt 本身包含去重，因此合并即校验）
        print(f"  批次总结完成（{total_input} + {total_output} tokens），合并校验中...")
        merge_content = "\n\n---\n\n".join(
            f"### 批次 {i+1} 总结：\n{s}" for i, s in enumerate(partial_summaries)
        )
        merge_prompt = f"""你是一个 AI 行业信息质量审核员。以下是分批处理产生的多份 AI 推文总结，请合并为一份高置信度的最终日报。

任务：
1. 合并报道同一事件的不同条目（保留最完整的描述，综合多个信息源）
2. 去除完全重复的条目
3. 检查高度相似的条目（同一产品/事件的不同角度），合并为一条综合描述
4. 确保每条都保留了有效的推文 URL（格式：[标题](URL)）
5. 确保分类准确，每个分类内按重要性排列
6. 保持格式一致：- [标题](URL)。描述。

规则：
- 保持原有的分类结构（本期要点、AI 产品与工具、AI 模型与技术等）
- 如果某个分类下没有内容，省略该分类
- 不要加前言或结尾总结段落
- 直接输出最终版本

{merge_content}"""

        merged_text, merge_usage = self._call_claude_api(
            merge_prompt, model, max_tokens, api_url, headers)
        total_input += merge_usage.get("input_tokens", 0)
        total_output += merge_usage.get("output_tokens", 0)
        print(f"  合并校验完成（总计 {total_input} + {total_output} tokens）")
        return merged_text, ai_tweet_ids

    def _summarize_batch_robust(self, lines, window_desc, batch_label,
                                category_block, rules_block,
                                model, max_tokens, api_url, headers, depth=0):
        """总结单个批次，失败后自动拆分为子批次重试。
        返回 (summaries: list[str], input_tokens: int, output_tokens: int)"""
        batch_content = "\n".join(lines)
        prompt = f"""你是一个 AI 行业信息整理员。以下是从 Twitter 抓取的 AI 相关推文{window_desc}{batch_label}。

任务：生成结构化的分类日报。

读者画像：关注 AI 前沿动态的从业者。他们想从每条新闻中快速了解：发生了什么、谁发布的、核心内容（功能/指标/数据/价格）、怎么获取或有什么意义。

{category_block}

{rules_block}

---
{batch_content}"""

        try:
            resp_text, usage = self._call_claude_api(
                prompt, model, max_tokens, api_url, headers)
            return [resp_text], usage.get("input_tokens", 0), usage.get("output_tokens", 0)
        except Exception as e:
            if len(lines) <= 10:
                indent = "  " * (depth + 2)
                print(f"\n    {indent}✗ 子批次仍失败且无法继续拆分（{len(lines)} 行）: {type(e).__name__}")
                return [], 0, 0
            mid = len(lines) // 2
            indent = "  " * (depth + 2)
            print(f"\n    {indent}↳ 拆分为 2 个子批次重试（各 ~{mid} 行）...", end=" ", flush=True)
            s1, in1, out1 = self._summarize_batch_robust(
                lines[:mid], window_desc, batch_label,
                category_block, rules_block, model, max_tokens, api_url, headers, depth + 1)
            s2, in2, out2 = self._summarize_batch_robust(
                lines[mid:], window_desc, batch_label,
                category_block, rules_block, model, max_tokens, api_url, headers, depth + 1)
            return s1 + s2, in1 + in2, out1 + out2

    def _validate_summary(self, summary_text, model, max_tokens, api_url, headers):
        """最终校验：去重、合并相似条目、格式一致性检查。
        返回校验后的总结文本。"""
        print("  [校验] 最终去重与合并检查...", end=" ", flush=True)
        validate_prompt = f"""你是一个 AI 信息质量审核员。以下是一份 AI 推文日报，请进行最终校验和优化。

校验任务：
1. 重复检测：找出描述同一事件/新闻的重复条目，只保留信息最完整的一条
2. 相似合并：将高度相关的条目（同一产品/事件的不同角度）合并为一条综合描述
3. URL 检查：确保每条都包含有效的推文链接，格式为 [标题](URL)
4. 分类校验：确认条目放在了正确的分类下，如有错误则调整
5. 格式统一：每条格式为 - [标题](URL)。描述。

规则：
- 如果内容已经很好，无需重复/合并问题，直接原样输出
- 如果有需要修正的，输出修正后的完整版本
- 保持原有分类结构
- 不要加任何说明、注释、前言或结尾
- 直接输出最终版本

---
{summary_text}"""

        try:
            validated, usage = self._call_claude_api(
                validate_prompt, model, max_tokens, api_url, headers)
            print(f"完成（{usage.get('input_tokens', 0)} + {usage.get('output_tokens', 0)} tokens）")
            return validated
        except Exception as e:
            print(f"跳过（{type(e).__name__}），使用原始总结")
            return summary_text

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

    # ── Layer 1: 抓取 ──────────────────────────────────────

    def run_scrape(self):
        """Layer 1: 纯数据抓取，保存原始推文（不做关键词/AI 过滤）"""
        username = self.twitter_config["username"]
        now = self.now()
        print(f"=== Twitter Watchdog — 抓取 ===")
        print(f"监控账户: @{username}")
        print(f"时间: {now.strftime('%Y-%m-%d %H:%M:%S')} (UTC+8)")
        if self.hours_ago:
            print(f"分页深度: 最近 {self.hours_ago} 小时")
        print()

        # 步骤1: 获取关注列表
        print("[1/3] 获取关注列表...")
        followings = self.get_following()
        print(f"  共 {len(followings)} 个关注账户")

        # 步骤2: 抓取推文（全量，不做关键词/AI 过滤）
        print(f"\n[2/3] 抓取推文（twitterapi.io）...")
        all_data = []
        total_tweets = 0
        api_calls = 0

        for i, user in enumerate(followings, 1):
            uname = user["username"]
            name = user["name"]
            print(f"  [{i}/{len(followings)}] @{uname} ({name})...", end=" ", flush=True)

            try:
                tweets, calls = self.get_tweets(uname)
                api_calls += calls

                new_tweets = []
                for tweet in tweets:
                    tweet_id = tweet.get("id", "")
                    if self.advanced_config.get("deduplicate", True) and self.is_tweet_seen(tweet_id):
                        continue
                    new_tweets.append(tweet)
                    self.mark_tweet_seen(tweet_id)
                    total_tweets += 1

                print(f"{len(new_tweets)} 条")

                if new_tweets:
                    all_data.append({"user": user, "tweets": new_tweets})

            except Exception as e:
                print(f"错误: {e}")

        # 步骤3: 全网热门 AI 搜索
        trending_config = self.config.get("trending_search", {})
        trending_tweets = []
        if trending_config.get("enabled", True):
            max_trending = trending_config.get("max_tweets", 20)
            print(f"\n[3/3] 搜索全网热门 AI 推文...")
            try:
                trending_tweets = self.search_trending_ai(max_tweets=max_trending)
                api_calls += 1
                # 去重（不做时间窗口过滤，保留全量）
                seen_ids = {t.get("id") for ud in all_data for t in ud["tweets"]}
                trending_tweets = [t for t in trending_tweets if t.get("id") not in seen_ids]
                print(f"  找到 {len(trending_tweets)} 条热门 AI 推文")
            except Exception as e:
                print(f"  搜索失败: {e}")
        else:
            print(f"\n[3/3] 热门搜索已禁用")

        self.save_state()

        # 保存原始数据
        output_path = Path(self.output_config["directory"])
        raw_dir = output_path / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)

        timestamp = now.strftime("%Y%m%d_%H%M%S")
        raw_file = raw_dir / f"{timestamp}.json"

        raw_data = {
            "metadata": {
                "scraped_at": now.isoformat(),
                "username": username,
                "hours_ago": self.hours_ago,
                "followings_count": len(followings),
                "total_tweets": total_tweets + len(trending_tweets),
                "api_calls": api_calls,
            },
            "followings": all_data,
            "trending": trending_tweets,
        }

        with open(raw_file, "w", encoding="utf-8") as f:
            json.dump(raw_data, f, ensure_ascii=False, indent=2, default=str)

        print(f"\n  原始数据: {raw_file}")
        print(f"  关注推文: {total_tweets} 条 | 热门推文: {len(trending_tweets)} 条 | API 调用: {api_calls} 次")

        return str(raw_file)

    # ── Layer 2: 分析 ──────────────────────────────────────

    def _find_raw_files(self, source=None, time_from=None, time_to=None):
        """定位 raw JSON 文件"""
        output_path = Path(self.output_config["directory"])
        raw_dir = output_path / "raw"

        if source:
            source_path = Path(source)
            if not source_path.is_absolute():
                source_path = output_path / source
            if not source_path.exists():
                print(f"  错误: 文件不存在 {source_path}")
                return []
            return [source_path]

        if not raw_dir.exists():
            print(f"  错误: raw 目录不存在 {raw_dir}")
            return []

        raw_files = sorted(raw_dir.glob("*.json"))
        if not raw_files:
            print(f"  错误: raw 目录中没有 JSON 文件")
            return []

        if time_from or time_to:
            matched = []
            for f in raw_files:
                try:
                    file_dt = datetime.strptime(f.stem, "%Y%m%d_%H%M%S").replace(tzinfo=TZ_CN)
                    if time_from and file_dt < time_from:
                        continue
                    if time_to and file_dt > time_to:
                        continue
                    matched.append(f)
                except ValueError:
                    continue
            return matched

        # 默认返回最新的 raw 文件
        return [raw_files[-1]]

    def run_analyze(self, source=None, time_from=None, time_to=None):
        """Layer 2: AI 分析原始数据"""
        now = self.now()
        print(f"=== Twitter Watchdog — 分析 ===")
        print(f"时间: {now.strftime('%Y-%m-%d %H:%M:%S')} (UTC+8)")
        print()

        # 步骤1: 定位 raw 文件
        print("[1/3] 定位原始数据...")
        raw_files = self._find_raw_files(source=source, time_from=time_from, time_to=time_to)
        if not raw_files:
            print("  未找到原始数据文件")
            return None

        print(f"  找到 {len(raw_files)} 个文件: {', '.join(f.name for f in raw_files)}")

        # 合并多个 raw 文件的数据
        all_followings = []
        all_trending = []
        source_filenames = []
        for rf in raw_files:
            with open(rf, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
            all_followings.extend(raw_data.get("followings", []))
            all_trending.extend(raw_data.get("trending", []))
            source_filenames.append(rf.name)

        # 步骤2: 时间窗口过滤 + 关键词预过滤
        print(f"\n[2/3] 过滤推文...")
        ai_filter = self.config.get("ai_summary", {}).get("ai_filter", False)

        # 时间窗口
        window_from = time_from
        window_to = time_to
        if self.hours_ago and not time_from and not time_to:
            window_to = now
            window_from = now - timedelta(hours=self.hours_ago)

        filtered_followings = []
        total_before = 0
        total_after_window = 0
        total_after_filter = 0

        for ud in all_followings:
            total_before += len(ud["tweets"])

            # 时间窗口过滤
            window_tweets = []
            for t in ud["tweets"]:
                if window_from or window_to:
                    created = self.parse_tweet_time(t.get("createdAt", ""))
                    if created:
                        if window_from and created < window_from:
                            continue
                        if window_to and created > window_to:
                            continue
                window_tweets.append(t)

            total_after_window += len(window_tweets)

            # 关键词预过滤（当 ai_filter=true 时跳过，交给 Claude）
            if not ai_filter:
                keyword_tweets = []
                for t in window_tweets:
                    passed, reason = self.filter_tweet(t)
                    if passed:
                        keyword_tweets.append(t)
                total_after_filter += len(keyword_tweets)
                if keyword_tweets:
                    filtered_followings.append({"user": ud["user"], "tweets": keyword_tweets})
            else:
                total_after_filter += len(window_tweets)
                if window_tweets:
                    filtered_followings.append({"user": ud["user"], "tweets": window_tweets})

        # trending 也做时间窗口 + 关键词过滤
        filtered_trending = []
        for t in all_trending:
            if window_from or window_to:
                created = self.parse_tweet_time(t.get("createdAt", ""))
                if created:
                    if window_from and created < window_from:
                        continue
                    if window_to and created > window_to:
                        continue
            if not ai_filter:
                passed, reason = self.filter_tweet(t)
                if not passed:
                    continue
            filtered_trending.append(t)

        time_desc = ""
        if window_from and window_to:
            time_desc = f" ({window_from.strftime('%m/%d %H:%M')} ~ {window_to.strftime('%m/%d %H:%M')})"
        print(f"  原始: {total_before} 条 → 时间窗口: {total_after_window} 条 → 过滤后: {total_after_filter} 条{time_desc}")
        print(f"  热门: {len(all_trending)} 条 → {len(filtered_trending)} 条")

        if not filtered_followings and not filtered_trending:
            print("  过滤后无推文，跳过分析")
            return None

        # 收集图片信息
        for ud in filtered_followings:
            for t in ud["tweets"]:
                self.collect_tweet_image(t)
        for t in filtered_trending:
            self.collect_tweet_image(t)

        # 步骤3: AI 分析
        print(f"\n[3/3] AI 分析...")
        ai_summary, ai_tweet_ids = self.generate_ai_summary(filtered_followings, filtered_trending)

        # AI 筛选后过滤
        final_followings = filtered_followings
        final_trending = filtered_trending
        if ai_tweet_ids is not None:
            final_followings = []
            filtered_count = 0
            for ud in filtered_followings:
                ft = [t for t in ud["tweets"] if str(t.get("id", "")) in ai_tweet_ids]
                if ft:
                    final_followings.append({"user": ud["user"], "tweets": ft})
                    filtered_count += len(ft)
            final_trending = [t for t in filtered_trending if str(t.get("id", "")) in ai_tweet_ids]
            print(f"  AI 筛选: {filtered_count} 条关注 + {len(final_trending)} 条热门")

        # 保存分析结果
        output_path = Path(self.output_config["directory"])
        analysis_dir = output_path / "analysis"
        analysis_dir.mkdir(parents=True, exist_ok=True)

        timestamp = now.strftime("%Y%m%d_%H%M%S")
        analysis_file = analysis_dir / f"{timestamp}.json"

        total_filtered = sum(len(ud["tweets"]) for ud in final_followings) + len(final_trending)
        analysis_data = {
            "metadata": {
                "analyzed_at": now.isoformat(),
                "source_files": source_filenames,
                "time_window": {
                    "from": window_from.isoformat() if window_from else None,
                    "to": window_to.isoformat() if window_to else None,
                },
                "total_tweets": total_before + len(all_trending),
                "filtered_count": total_filtered,
                "model": self.config.get("ai_summary", {}).get("model", "claude-sonnet-4-5-20250929"),
            },
            "ai_tweet_ids": list(ai_tweet_ids) if ai_tweet_ids else [],
            "summary": ai_summary,
            "filtered_followings": final_followings,
            "filtered_trending": final_trending,
        }

        with open(analysis_file, "w", encoding="utf-8") as f:
            json.dump(analysis_data, f, ensure_ascii=False, indent=2, default=str)

        print(f"\n  分析结果: {analysis_file}")
        print(f"  筛选: {total_before + len(all_trending)} 条 → {total_filtered} 条 AI 相关")

        return str(analysis_file)

    # ── Layer 3: 报告 ──────────────────────────────────────

    def _find_analysis_files(self, source=None, daily=None, weekly=None, monthly=None):
        """定位 analysis JSON 文件"""
        output_path = Path(self.output_config["directory"])
        analysis_dir = output_path / "analysis"

        if source:
            source_path = Path(source)
            if not source_path.is_absolute():
                source_path = output_path / source
            if not source_path.exists():
                print(f"  错误: 文件不存在 {source_path}")
                return []
            return [source_path]

        if not analysis_dir.exists():
            print(f"  错误: analysis 目录不存在 {analysis_dir}")
            return []

        analysis_files = sorted(analysis_dir.glob("*.json"))
        if not analysis_files:
            print(f"  错误: analysis 目录中没有 JSON 文件")
            return []

        if daily:
            date_prefix = daily.replace("-", "")
            return [f for f in analysis_files if f.stem.startswith(date_prefix)]

        if weekly:
            start_date = datetime.strptime(weekly, "%Y-%m-%d")
            end_date = start_date + timedelta(days=7)
            matched = []
            for f in analysis_files:
                try:
                    file_dt = datetime.strptime(f.stem[:8], "%Y%m%d")
                    if start_date <= file_dt < end_date:
                        matched.append(f)
                except ValueError:
                    continue
            return matched

        if monthly:
            month_prefix = monthly.replace("-", "")
            return [f for f in analysis_files if f.stem.startswith(month_prefix)]

        # 默认返回最新的 analysis 文件
        return [analysis_files[-1]]

    def run_report(self, source=None, daily=None, weekly=None, monthly=None):
        """Layer 3: 从分析结果生成报告"""
        now = self.now()
        print(f"=== Twitter Watchdog — 报告 ===")
        print(f"时间: {now.strftime('%Y-%m-%d %H:%M:%S')} (UTC+8)")
        print()

        # 步骤1: 定位 analysis 文件
        is_periodic = daily or weekly or monthly
        report_type = "日报" if daily else "周报" if weekly else "月报" if monthly else "报告"
        print(f"[1/3] 定位分析数据（{report_type}）...")

        analysis_files = self._find_analysis_files(
            source=source, daily=daily, weekly=weekly, monthly=monthly
        )
        if not analysis_files:
            print("  未找到分析数据文件")
            return

        print(f"  找到 {len(analysis_files)} 个文件")

        # 读取分析数据
        all_summaries = []
        all_followings = []
        all_trending = []
        for af in analysis_files:
            with open(af, "r", encoding="utf-8") as f:
                data = json.load(f)
            summary = data.get("summary", "")
            if summary:
                all_summaries.append(summary)
            all_followings.extend(data.get("filtered_followings", []))
            all_trending.extend(data.get("filtered_trending", []))

        if not all_summaries:
            print("  分析数据中无总结内容")
            return

        # 步骤2: 聚合（多文件时需要去重+合并）
        print(f"\n[2/3] 处理总结内容...")
        if len(all_summaries) == 1 and not is_periodic:
            final_summary = all_summaries[0]
            print(f"  单份分析，直接使用")
        else:
            # 聚合多份分析
            all_items = []
            for s in all_summaries:
                items = self._parse_summary_items(s)
                all_items.extend(items)
            print(f"  提取 {len(all_items)} 条（去重前）")

            unique_items = self._deduplicate_items(all_items)
            print(f"  去重后: {len(unique_items)} 条")

            if is_periodic and unique_items:
                period = "monthly" if monthly else "weekly"
                if monthly:
                    year, month_str = monthly.split("-")
                    period_label = f"{year} 年 {int(month_str)} 月"
                elif weekly:
                    start_d = datetime.strptime(weekly, "%Y-%m-%d")
                    end_d = start_d + timedelta(days=7)
                    period_label = f"{start_d.strftime('%m/%d')} ~ {end_d.strftime('%m/%d')}"
                else:
                    period_label = daily
                consolidated = self._claude_consolidate(unique_items, period, period_label)
                final_summary = consolidated or "\n\n".join(item["full_text"] for item in unique_items)
            else:
                # 多份非周期报告：直接合并
                final_summary = "\n\n".join(all_summaries)

        # 收集图片信息
        for ud in all_followings:
            for t in ud["tweets"]:
                self.collect_tweet_image(t)
        for t in all_trending:
            self.collect_tweet_image(t)

        # 步骤3: 生成报告文件
        print(f"\n[3/3] 生成报告文件...")
        output_path = Path(self.output_config["directory"])
        reports_dir = output_path / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)

        # 下载图片
        ai_summary_with_images = final_summary
        downloaded = self.download_report_images(final_summary, reports_dir)
        if downloaded:
            ai_summary_with_images = self.insert_images_into_summary(final_summary, downloaded)

        timestamp = now.strftime("%Y%m%d_%H%M%S")

        # 确定文件名
        if daily:
            base_name = f"daily_{daily.replace('-', '')}"
        elif weekly:
            base_name = f"weekly_{weekly.replace('-', '')}"
        elif monthly:
            base_name = f"monthly_{monthly.replace('-', '')}"
        else:
            base_name = timestamp

        # HTML 报告
        html_file = reports_dir / f"{base_name}.html"
        self.save_as_html(html_file, ai_summary_with_images, timestamp)
        print(f"  HTML: {html_file}")

        # 更新 latest.html
        latest_html = reports_dir / "latest.html"
        self.save_as_html(latest_html, ai_summary_with_images, timestamp)

        # Markdown 报告
        md_file = reports_dir / f"{base_name}.md"
        self._save_report_markdown(md_file, final_summary, all_followings, all_trending, report_type)
        print(f"  Markdown: {md_file}")

        # 通知
        total = sum(len(ud["tweets"]) for ud in all_followings) + len(all_trending)
        if total > 0:
            threshold = self.notifications_config.get("threshold", 1)
            if self.notifications_config.get("on_new_tweets", True) and total >= threshold:
                following_count = sum(len(ud["tweets"]) for ud in all_followings)
                self.send_notification(
                    "Twitter Watchdog",
                    f"发现 {following_count} 条关注 + {len(all_trending)} 条热门 AI 推文！",
                )

        return str(html_file)

    def _save_report_markdown(self, output_file, summary, followings_data, trending_tweets, report_type="报告"):
        """从分析数据生成 Markdown 报告"""
        now = self.now()
        ts = now.strftime("%Y-%m-%d %H:%M:%S")
        following_count = sum(len(ud["tweets"]) for ud in followings_data)
        total = following_count + len(trending_tweets)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"# AI 推文{report_type}\n\n")
            f.write(f"**生成时间**: {ts} (UTC+8)\n")
            if self.hours_ago:
                cutoff = now - timedelta(hours=self.hours_ago)
                if cutoff.date() == now.date():
                    win = f"{cutoff.strftime('%H:%M')} ~ {now.strftime('%H:%M')}"
                else:
                    win = f"{cutoff.strftime('%m月%d日 %H:%M')} ~ {now.strftime('%m月%d日 %H:%M')}"
                f.write(f"**时间窗口**: {win}\n")
            f.write(f"**AI 相关推文**: {following_count} 条关注 + {len(trending_tweets)} 条热门\n")
            f.write(f"**总计**: {total} 条\n\n")

            if summary:
                f.write("---\n\n")
                f.write(summary)
                f.write("\n\n")

            if followings_data:
                f.write("---\n\n")
                f.write("# 关注列表 AI 推文\n\n")
                for user_data in followings_data:
                    user = user_data["user"]
                    tweets = user_data["tweets"]
                    uname = user.get("username", "")
                    name = user.get("name", "")
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

    # ── 流水线（向后兼容）─────────────────────────────────

    def run_pipeline(self):
        """三步流水线（向后兼容旧的无子命令用法）"""
        raw_file = self.run_scrape()
        if not raw_file:
            print("\n抓取无数据，流水线终止")
            return

        analysis_file = self.run_analyze(source=raw_file)
        if not analysis_file:
            print("\n分析无结果，流水线终止")
            return

        self.run_report(source=analysis_file)

    # ── 报告输出 ──────────────────────────────────────────

    @staticmethod
    def _html_page(title, subtitle, body_html):
        """生成自包含 HTML 页面（sticky 导航 + 主题切换 + 暗色模式 + 回到顶部）"""
        return f"""<!DOCTYPE html>
<html lang="zh-CN" data-theme="auto">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  :root {{
    --font-sans: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
    --radius-sm: 8px; --radius-md: 12px; --radius-lg: 16px;
    --shadow-sm: 0 1px 2px rgba(0,0,0,0.04), 0 1px 3px rgba(0,0,0,0.03);
    --shadow-md: 0 2px 8px rgba(0,0,0,0.06), 0 1px 4px rgba(0,0,0,0.04);
    --transition-fast: 0.15s cubic-bezier(0.4, 0, 0.2, 1);
    --transition-med: 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  }}
  [data-theme="light"], :root {{
    --bg-primary: #fafaf9; --bg-secondary: #ffffff; --bg-tertiary: #f5f5f4;
    --bg-nav: rgba(250,250,249,0.82);
    --text-primary: #1c1917; --text-secondary: #57534e; --text-tertiary: #a8a29e;
    --border-primary: #e7e5e4; --border-secondary: #d6d3d1;
    --accent: #4338ca; --accent-hover: #3730a3; --accent-subtle: rgba(67,56,202,0.08);
    --highlight-bg: linear-gradient(135deg, #faf5ff 0%, #f0f9ff 50%, #f0fdf4 100%);
    --highlight-border: #e9d5ff;
    --tag-product-bg: #eff6ff; --tag-product-text: #1e40af; --tag-product-border: #bfdbfe;
    --tag-model-bg: #fdf2f8; --tag-model-text: #9d174d; --tag-model-border: #fbcfe8;
    --tag-dev-bg: #ecfdf5; --tag-dev-text: #065f46; --tag-dev-border: #a7f3d0;
    --tag-industry-bg: #fffbeb; --tag-industry-text: #92400e; --tag-industry-border: #fde68a;
    --tag-research-bg: #f5f3ff; --tag-research-text: #5b21b6; --tag-research-border: #ddd6fe;
    --dot-1: #6366f1; --dot-2: #8b5cf6; --dot-3: #a78bfa; --dot-4: #c084fc; --dot-5: #6366f1;
    --back-top-bg: rgba(255,255,255,0.9); --back-top-shadow: 0 2px 12px rgba(0,0,0,0.1);
    --scrollbar-thumb: #d6d3d1;
  }}
  [data-theme="dark"] {{
    --bg-primary: #0c0a09; --bg-secondary: #1c1917; --bg-tertiary: #292524;
    --bg-nav: rgba(12,10,9,0.82);
    --text-primary: #fafaf9; --text-secondary: #a8a29e; --text-tertiary: #78716c;
    --border-primary: #292524; --border-secondary: #44403c;
    --accent: #818cf8; --accent-hover: #a5b4fc; --accent-subtle: rgba(129,140,248,0.1);
    --highlight-bg: linear-gradient(135deg, rgba(88,28,135,0.15) 0%, rgba(30,58,138,0.15) 50%, rgba(6,78,59,0.12) 100%);
    --highlight-border: #581c87;
    --tag-product-bg: rgba(37,99,235,0.15); --tag-product-text: #93c5fd; --tag-product-border: rgba(37,99,235,0.3);
    --tag-model-bg: rgba(219,39,119,0.15); --tag-model-text: #f9a8d4; --tag-model-border: rgba(219,39,119,0.3);
    --tag-dev-bg: rgba(5,150,105,0.15); --tag-dev-text: #6ee7b7; --tag-dev-border: rgba(5,150,105,0.3);
    --tag-industry-bg: rgba(217,119,6,0.15); --tag-industry-text: #fcd34d; --tag-industry-border: rgba(217,119,6,0.3);
    --tag-research-bg: rgba(124,58,237,0.15); --tag-research-text: #c4b5fd; --tag-research-border: rgba(124,58,237,0.3);
    --dot-1: #818cf8; --dot-2: #a78bfa; --dot-3: #c084fc; --dot-4: #e879f9; --dot-5: #818cf8;
    --back-top-bg: rgba(28,25,23,0.9); --back-top-shadow: 0 2px 12px rgba(0,0,0,0.4);
    --scrollbar-thumb: #44403c;
  }}
  @media (prefers-color-scheme: dark) {{
    [data-theme="auto"] {{
      --bg-primary: #0c0a09; --bg-secondary: #1c1917; --bg-tertiary: #292524;
      --bg-nav: rgba(12,10,9,0.82);
      --text-primary: #fafaf9; --text-secondary: #a8a29e; --text-tertiary: #78716c;
      --border-primary: #292524; --border-secondary: #44403c;
      --accent: #818cf8; --accent-hover: #a5b4fc; --accent-subtle: rgba(129,140,248,0.1);
      --highlight-bg: linear-gradient(135deg, rgba(88,28,135,0.15) 0%, rgba(30,58,138,0.15) 50%, rgba(6,78,59,0.12) 100%);
      --highlight-border: #581c87;
      --tag-product-bg: rgba(37,99,235,0.15); --tag-product-text: #93c5fd; --tag-product-border: rgba(37,99,235,0.3);
      --tag-model-bg: rgba(219,39,119,0.15); --tag-model-text: #f9a8d4; --tag-model-border: rgba(219,39,119,0.3);
      --tag-dev-bg: rgba(5,150,105,0.15); --tag-dev-text: #6ee7b7; --tag-dev-border: rgba(5,150,105,0.3);
      --tag-industry-bg: rgba(217,119,6,0.15); --tag-industry-text: #fcd34d; --tag-industry-border: rgba(217,119,6,0.3);
      --tag-research-bg: rgba(124,58,237,0.15); --tag-research-text: #c4b5fd; --tag-research-border: rgba(124,58,237,0.3);
      --dot-1: #818cf8; --dot-2: #a78bfa; --dot-3: #c084fc; --dot-4: #e879f9; --dot-5: #818cf8;
      --back-top-bg: rgba(28,25,23,0.9); --back-top-shadow: 0 2px 12px rgba(0,0,0,0.4);
      --scrollbar-thumb: #44403c;
    }}
  }}
  *, *::before, *::after {{ margin: 0; padding: 0; box-sizing: border-box; }}
  html {{ scroll-behavior: smooth; -webkit-text-size-adjust: 100%; }}
  body {{
    font-family: var(--font-sans); background: var(--bg-primary); color: var(--text-primary);
    line-height: 1.7; -webkit-font-smoothing: antialiased; overflow-x: hidden;
  }}
  ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
  ::-webkit-scrollbar-track {{ background: transparent; }}
  ::-webkit-scrollbar-thumb {{ background: var(--scrollbar-thumb); border-radius: 3px; }}
  .page-container {{ max-width: 860px; margin: 0 auto; padding: 0 28px; }}
  .sticky-nav {{
    position: sticky; top: 0; z-index: 1000;
    background: var(--bg-nav); backdrop-filter: blur(16px) saturate(180%);
    -webkit-backdrop-filter: blur(16px) saturate(180%);
    border-bottom: 1px solid var(--border-primary); transition: box-shadow var(--transition-med);
  }}
  .sticky-nav.scrolled {{ box-shadow: 0 1px 8px rgba(0,0,0,0.06); }}
  .sticky-nav-inner {{
    max-width: 860px; margin: 0 auto; padding: 0 28px;
    display: flex; align-items: center; gap: 6px; height: 52px;
    overflow-x: auto; -webkit-overflow-scrolling: touch; scrollbar-width: none;
  }}
  .sticky-nav-inner::-webkit-scrollbar {{ display: none; }}
  .nav-brand {{ font-size: 14px; font-weight: 700; letter-spacing: -0.3px; color: var(--text-primary); white-space: nowrap; flex-shrink: 0; padding-right: 8px; }}
  .nav-divider {{ width: 1px; height: 18px; background: var(--border-secondary); flex-shrink: 0; margin: 0 4px; }}
  .nav-link {{
    display: inline-flex; align-items: center; padding: 10px 14px; border-radius: 99px;
    font-size: 13px; font-weight: 500; text-decoration: none; color: var(--text-secondary);
    background: transparent; border: 1px solid transparent; white-space: nowrap;
    flex-shrink: 0; cursor: pointer; transition: all var(--transition-fast); user-select: none;
    min-height: 44px;
  }}
  .nav-link:hover {{ color: var(--text-primary); background: var(--bg-tertiary); }}
  .nav-link.active {{ color: var(--accent); background: var(--accent-subtle); font-weight: 600; }}
  .nav-actions {{ margin-left: auto; flex-shrink: 0; display: flex; align-items: center; gap: 4px; }}
  .theme-toggle {{
    width: 34px; height: 34px; border-radius: 50%; border: 1px solid var(--border-primary);
    background: var(--bg-secondary); color: var(--text-secondary); cursor: pointer;
    display: flex; align-items: center; justify-content: center; transition: all var(--transition-fast); flex-shrink: 0;
  }}
  .theme-toggle:hover {{ border-color: var(--border-secondary); color: var(--text-primary); box-shadow: var(--shadow-sm); }}
  .theme-toggle svg {{ width: 16px; height: 16px; }}
  .theme-toggle .icon-moon, .theme-toggle .icon-sun {{ display: none; }}
  [data-resolved-theme="light"] .theme-toggle .icon-moon {{ display: block; }}
  [data-resolved-theme="dark"] .theme-toggle .icon-sun {{ display: block; }}
  .page-header {{ padding: 48px 0 40px; border-bottom: 1px solid var(--border-primary); margin-bottom: 40px; }}
  .page-header h1 {{ font-size: 32px; font-weight: 800; letter-spacing: -0.8px; line-height: 1.2; }}
  .page-header .subtitle {{ margin-top: 10px; font-size: 15px; color: var(--text-secondary); }}
  .page-header .date-badge {{
    display: inline-flex; align-items: center; gap: 6px; margin-top: 14px;
    padding: 5px 12px; border-radius: 99px; background: var(--accent-subtle);
    color: var(--accent); font-size: 12px; font-weight: 600; letter-spacing: 0.2px;
  }}
  .page-header .date-badge svg {{ width: 14px; height: 14px; }}
  .highlights-section {{ margin-bottom: 48px; }}
  .highlights-card {{
    background: var(--highlight-bg); border: 1px solid var(--highlight-border);
    border-radius: var(--radius-lg); padding: 28px 28px 20px; position: relative; overflow: hidden;
  }}
  .highlights-card::before {{
    content: ""; position: absolute; top: 0; left: 0; right: 0; height: 3px;
    background: linear-gradient(90deg, #6366f1, #8b5cf6, #a78bfa, #c084fc, #e879f9);
    border-radius: 3px 3px 0 0;
  }}
  .highlights-title {{ font-size: 16px; font-weight: 700; margin-bottom: 18px; display: flex; align-items: center; gap: 8px; }}
  .highlights-title svg {{ width: 18px; height: 18px; color: var(--accent); }}
  .highlights-list {{ list-style: none; display: flex; flex-direction: column; }}
  .highlights-list li {{
    position: relative; padding: 12px 0 12px 24px; font-size: 14.5px; line-height: 1.65;
    border-bottom: 1px solid rgba(0,0,0,0.06);
  }}
  [data-resolved-theme="dark"] .highlights-list li {{ border-bottom-color: rgba(255,255,255,0.06); }}
  .highlights-list li:last-child {{ border-bottom: none; padding-bottom: 4px; }}
  .highlights-list li::before {{ content: ""; position: absolute; left: 2px; top: 19px; width: 7px; height: 7px; border-radius: 50%; }}
  .highlights-list li:nth-child(1)::before {{ background: var(--dot-1); }}
  .highlights-list li:nth-child(2)::before {{ background: var(--dot-2); }}
  .highlights-list li:nth-child(3)::before {{ background: var(--dot-3); }}
  .highlights-list li:nth-child(4)::before {{ background: var(--dot-4); }}
  .highlights-list li:nth-child(5)::before {{ background: var(--dot-5); }}
  .category-section {{ margin-bottom: 48px; }}
  .category-section-header {{
    display: flex; align-items: center; gap: 12px;
    margin-bottom: 20px; padding-bottom: 14px; border-bottom: 1px solid var(--border-primary);
  }}
  .category-section-header h2 {{ font-size: 20px; font-weight: 700; letter-spacing: -0.3px; }}
  .cat-tag {{
    font-size: 11px; font-weight: 600; padding: 3px 10px; border-radius: 99px;
    letter-spacing: 0.4px; text-transform: uppercase; border: 1px solid;
  }}
  .cat-tag-product {{ background: var(--tag-product-bg); color: var(--tag-product-text); border-color: var(--tag-product-border); }}
  .cat-tag-model {{ background: var(--tag-model-bg); color: var(--tag-model-text); border-color: var(--tag-model-border); }}
  .cat-tag-dev {{ background: var(--tag-dev-bg); color: var(--tag-dev-text); border-color: var(--tag-dev-border); }}
  .cat-tag-industry {{ background: var(--tag-industry-bg); color: var(--tag-industry-text); border-color: var(--tag-industry-border); }}
  .cat-tag-research {{ background: var(--tag-research-bg); color: var(--tag-research-text); border-color: var(--tag-research-border); }}
  .category-section-header .item-count {{ font-size: 12px; color: var(--text-tertiary); margin-left: auto; }}
  .news-card {{
    background: var(--bg-secondary); border: 1px solid var(--border-primary);
    border-radius: var(--radius-md); padding: 22px 24px; margin-bottom: 14px;
    transition: all var(--transition-fast); position: relative;
  }}
  .news-card:hover {{ border-color: var(--border-secondary); box-shadow: var(--shadow-md); transform: translateY(-1px); }}
  .news-card:last-child {{ margin-bottom: 0; }}
  .news-card-title {{ font-size: 15.5px; font-weight: 600; line-height: 1.5; margin-bottom: 8px; letter-spacing: -0.2px; }}
  .news-card-title a {{ color: var(--accent); text-decoration: none; transition: all var(--transition-fast); }}
  .news-card-title a:hover {{ text-decoration: underline; text-underline-offset: 3px; text-decoration-thickness: 1.5px; }}
  .news-card-title a::after {{ content: " \\2197"; font-size: 12px; color: var(--text-tertiary); font-weight: 400; transition: color var(--transition-fast); }}
  .news-card-title a:hover::after {{ color: var(--accent); }}
  .news-card-desc {{ font-size: 14px; line-height: 1.7; color: var(--text-secondary); }}
  .news-card-img {{ margin-top: 16px; border-radius: var(--radius-sm); overflow: hidden; text-align: center; }}
  .news-card-img img {{ max-width: 100%; max-height: 400px; object-fit: contain; border-radius: var(--radius-sm); display: block; margin: 0 auto; }}
  .page-footer {{ margin-top: 56px; padding: 24px 0; border-top: 1px solid var(--border-primary); text-align: center; }}
  .page-footer p {{ font-size: 13px; color: var(--text-tertiary); line-height: 1.6; }}
  .footer-dot {{ display: inline-block; width: 3px; height: 3px; background: var(--text-tertiary); border-radius: 50%; vertical-align: middle; margin: 0 10px; }}
  .back-to-top {{
    position: fixed; bottom: 28px; right: 28px; width: 40px; height: 40px;
    border-radius: 50%; background: var(--back-top-bg); border: 1px solid var(--border-primary);
    color: var(--text-secondary); cursor: pointer; display: flex; align-items: center; justify-content: center;
    box-shadow: var(--back-top-shadow); backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px);
    transition: all var(--transition-fast); opacity: 0; visibility: hidden; transform: translateY(8px); z-index: 999;
  }}
  .back-to-top.visible {{ opacity: 1; visibility: visible; transform: translateY(0); }}
  .back-to-top:hover {{ border-color: var(--border-secondary); color: var(--accent); transform: translateY(-2px); box-shadow: 0 4px 20px rgba(0,0,0,0.12); }}
  .back-to-top svg {{ width: 18px; height: 18px; }}
  @media (max-width: 640px) {{
    .page-container {{ padding: 0 16px; }}
    .sticky-nav-inner {{ padding: 0 16px; height: 52px; }}
    .page-header {{ padding: 28px 0 24px; margin-bottom: 24px; }}
    .page-header h1 {{ font-size: 22px; }}
    .page-header .subtitle {{ font-size: 14px; }}
    .highlights-card {{ padding: 20px 18px 14px; }}
    .highlights-list li {{ font-size: 14px; }}
    .category-section {{ margin-bottom: 32px; }}
    .category-section-header h2 {{ font-size: 18px; }}
    .news-card {{ padding: 16px; margin-bottom: 12px; }}
    .news-card-title {{ font-size: 15px; }}
    .news-card-desc {{ font-size: 14px; }}
    .news-card-img img {{ max-height: 300px; }}
    .back-to-top {{ bottom: 20px; right: 16px; width: 44px; height: 44px; }}
    .theme-toggle {{ width: 44px; height: 44px; }}
    .nav-actions {{ margin-left: 4px; }}
  }}
  @media print {{
    .sticky-nav, .back-to-top, .theme-toggle {{ display: none !important; }}
    body {{ background: #fff; color: #000; }}
    .news-card {{ break-inside: avoid; border: 1px solid #ddd; }}
  }}
</style>
</head>
<body>
<nav class="sticky-nav" id="sticky-nav">
  <div class="sticky-nav-inner" id="sticky-nav-inner">
    <span class="nav-brand">AI 日报</span>
    <span class="nav-divider"></span>
    <div class="nav-actions">
      <button class="theme-toggle" id="theme-toggle" type="button" aria-label="切换主题" title="切换深色/浅色模式">
        <svg class="icon-moon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
        <svg class="icon-sun" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>
      </button>
    </div>
  </div>
</nav>
<div class="page-container">
<header class="page-header">
  <h1>{title}</h1>
  <div class="subtitle">人工智能领域今日要闻速览</div>
  <div class="date-badge">
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
    {subtitle}
  </div>
</header>
{body_html}
</div>
<footer class="page-footer">
  <div class="page-container">
    <p>由 Twitter Watchdog 自动生成<span class="footer-dot"></span>数据来源: Twitter 关注列表 + 全网热门</p>
  </div>
</footer>
<button class="back-to-top" id="back-to-top" type="button" aria-label="返回顶部" title="返回顶部">
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="18 15 12 9 6 15"/></svg>
</button>
<script>
(function() {{
  var html = document.documentElement;
  var themeBtn = document.getElementById('theme-toggle');
  function getSystemTheme() {{ return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'; }}
  function resolveTheme() {{ var t = html.getAttribute('data-theme'); return t === 'auto' ? getSystemTheme() : t; }}
  function applyResolvedTheme() {{ html.setAttribute('data-resolved-theme', resolveTheme()); }}
  applyResolvedTheme();
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function() {{ applyResolvedTheme(); }});
  themeBtn.addEventListener('click', function() {{
    var next = resolveTheme() === 'light' ? 'dark' : 'light';
    html.setAttribute('data-theme', next); applyResolvedTheme();
  }});
  var navOuter = document.getElementById('sticky-nav');
  var navInner = document.getElementById('sticky-nav-inner');
  var sections = document.querySelectorAll('[data-nav]');
  var navActions = navInner.querySelector('.nav-actions');
  sections.forEach(function(sec) {{
    var a = document.createElement('a');
    a.className = 'nav-link'; a.href = '#' + sec.id;
    a.textContent = sec.getAttribute('data-nav');
    a.setAttribute('data-target', sec.id);
    a.addEventListener('click', function(e) {{
      e.preventDefault();
      var target = document.getElementById(this.getAttribute('data-target'));
      if (target) {{
        var navH = navOuter.offsetHeight;
        var top = target.getBoundingClientRect().top + window.pageYOffset - navH - 16;
        window.scrollTo({{ top: top, behavior: 'smooth' }});
      }}
    }});
    navInner.insertBefore(a, navActions);
  }});
  var navLinks = navInner.querySelectorAll('.nav-link[data-target]');
  function scrollNavTo(el) {{
    var r = navInner.getBoundingClientRect(), e = el.getBoundingClientRect();
    navInner.scrollBy({{ left: e.left - r.left - (r.width / 2) + (e.width / 2), behavior: 'smooth' }});
  }}
  if (navLinks.length) {{
    var observer = new IntersectionObserver(function(entries) {{
      entries.forEach(function(entry) {{
        if (entry.isIntersecting) {{
          navLinks.forEach(function(l) {{ l.classList.remove('active'); }});
          var active = navInner.querySelector('.nav-link[data-target="' + entry.target.id + '"]');
          if (active) {{ active.classList.add('active'); scrollNavTo(active); }}
        }}
      }});
    }}, {{ rootMargin: '-80px 0px -60% 0px', threshold: 0 }});
    sections.forEach(function(sec) {{ observer.observe(sec); }});
  }}
  window.addEventListener('scroll', function() {{
    if (window.pageYOffset > 10) navOuter.classList.add('scrolled');
    else navOuter.classList.remove('scrolled');
  }}, {{ passive: true }});
  var btt = document.getElementById('back-to-top');
  window.addEventListener('scroll', function() {{
    if (window.pageYOffset > 400) btt.classList.add('visible');
    else btt.classList.remove('visible');
  }}, {{ passive: true }});
  btt.addEventListener('click', function(e) {{ e.preventDefault(); window.scrollTo({{ top: 0, behavior: 'smooth' }}); }});
}})();
</script>
</body>
</html>"""

    def save_as_html(self, output_file, ai_summary_with_images, timestamp):
        """将 AI 总结转为自包含 HTML 页面"""
        now = self.now()
        date_str = now.strftime("%Y 年 %m 月 %d 日")
        window_desc = ""
        if self.hours_ago:
            cutoff = now - timedelta(hours=self.hours_ago)
            if cutoff.date() == now.date():
                window_desc = f"{cutoff.strftime('%H:%M')} ~ {now.strftime('%H:%M')}"
            else:
                window_desc = f"{cutoff.strftime('%m月%d日 %H:%M')} ~ {now.strftime('%m月%d日 %H:%M')}"

        body_html = self._summary_md_to_html(ai_summary_with_images or "暂无内容")
        title = f"AI 日报 — {date_str}"
        subtitle = f"{date_str} {window_desc}"
        html = self._html_page(title, subtitle, body_html)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html)

    def _summary_md_to_html(self, md_text):
        """将分类结构的 markdown 总结转为 HTML（匹配新版 UI 模板）"""
        import html as html_mod

        # 星标 SVG 图标
        star_svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>'

        category_tags = {
            "AI 产品与工具": ("product", "cat-tag-product", "Product"),
            "AI 模型与技术": ("model", "cat-tag-model", "Model"),
            "AI 开发者生态": ("dev", "cat-tag-dev", "Dev"),
            "AI 行业动态": ("industry", "cat-tag-industry", "Industry"),
            "AI 研究与观点": ("research", "cat-tag-research", "Research"),
        }

        short_labels = {
            "AI 产品与工具": "产品与工具",
            "AI 模型与技术": "模型与技术",
            "AI 开发者生态": "开发者生态",
            "AI 行业动态": "行业动态",
            "AI 研究与观点": "研究与观点",
        }

        sections = []
        current_title = None
        current_lines = []

        for line in md_text.split("\n"):
            if line.startswith("## "):
                if current_title is not None:
                    sections.append((current_title, current_lines))
                current_title = line[3:].strip()
                current_lines = []
            else:
                current_lines.append(line)
        if current_title is not None:
            sections.append((current_title, current_lines))

        parts = []

        for title, lines in sections:
            if title == "本期要点":
                bullets = [l.lstrip("- ").strip() for l in lines if l.strip().startswith("- ")]
                if bullets:
                    parts.append(f'<section class="highlights-section" id="highlights" data-nav="本期要点">')
                    parts.append(f'<div class="highlights-card">')
                    parts.append(f'<div class="highlights-title">{star_svg} 本期要点</div>')
                    parts.append('<ul class="highlights-list">')
                    for b in bullets:
                        parts.append(f"<li>{html_mod.escape(b)}</li>")
                    parts.append("</ul></div></section>")
                continue

            tag_info = category_tags.get(title)
            if not tag_info:
                continue
            tag_id, tag_class, tag_label = tag_info
            anchor = f"cat-{tag_id}"
            nav_label = short_labels.get(title, title)

            # 统计条目数
            item_count = sum(1 for l in lines if l.strip().startswith("- ["))

            parts.append(f'<section class="category-section" id="{anchor}" data-nav="{html_mod.escape(nav_label)}">')
            parts.append(f'<div class="category-section-header">'
                         f'<h2>{html_mod.escape(title)}</h2>'
                         f'<span class="cat-tag {tag_class}">{tag_label}</span>'
                         f'<span class="item-count">{item_count} 条</span></div>')

            i = 0
            while i < len(lines):
                line = lines[i].strip()
                if line.startswith("- ["):
                    m = re.match(r'^- \[(.+?)\]\((.+?)\)[。，,.]\s*(.*)$', line, re.DOTALL)
                    if m:
                        item_title, item_url, item_desc = m.groups()
                        img_html = ""
                        j = i + 1
                        while j < len(lines):
                            sl = lines[j].strip()
                            if sl.startswith("!["):
                                img_m = re.match(r'!\[.*?\]\((.+?)\)', sl)
                                if img_m:
                                    img_src = img_m.group(1)
                                    img_html = f'<div class="news-card-img"><img src="{html_mod.escape(img_src)}" alt="" loading="lazy"></div>'
                                j += 1
                            elif sl == "":
                                j += 1
                            else:
                                break
                        i = j

                        parts.append('<div class="news-card">')
                        parts.append(f'<div class="news-card-title"><a href="{html_mod.escape(item_url)}" target="_blank" rel="noopener">{html_mod.escape(item_title)}</a></div>')
                        if item_desc.strip():
                            parts.append(f'<div class="news-card-desc">{html_mod.escape(item_desc.strip())}</div>')
                        if img_html:
                            parts.append(img_html)
                        parts.append('</div>')
                        continue
                i += 1

            parts.append("</section>")

        return "\n".join(parts)

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

    # ── 周报/月报辅助 ────────────────────────────────────────

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



def main():
    parser = argparse.ArgumentParser(
        description="Twitter Watchdog - AI 推文监控工具（三层架构：抓取 → 分析 → 报告）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
用法示例：
  # Layer 1: 只抓取，存原始数据
  python3 twitter_watchdog.py scrape --hours-ago 6

  # Layer 2: 分析原始数据，生成分析结果
  python3 twitter_watchdog.py analyze --hours-ago 6
  python3 twitter_watchdog.py analyze --source raw/20260212_140000.json
  python3 twitter_watchdog.py analyze --from "2026-02-12 08:00" --to "2026-02-12 14:00"

  # Layer 3: 从分析结果生成报告
  python3 twitter_watchdog.py report
  python3 twitter_watchdog.py report --source analysis/20260212_143000.json
  python3 twitter_watchdog.py report --daily 2026-02-12
  python3 twitter_watchdog.py report --weekly 2026-02-10
  python3 twitter_watchdog.py report --monthly 2026-02

  # 流水线模式（向后兼容，等价于 scrape + analyze + report）
  python3 twitter_watchdog.py --hours-ago 6
""",
    )
    # 顶层参数（兼容旧用法 + 所有子命令共用）
    parser.add_argument("--config", help="配置文件路径")
    parser.add_argument("--output-dir", help="输出目录")
    parser.add_argument("--hours-ago", type=int, help="时间窗口（小时）")
    parser.add_argument("--max-followings", type=int, help="关注列表抓取范围（0=全部）")
    parser.add_argument("--tweets-per-user", type=int, help="每个用户最多推文数")
    parser.add_argument("--trending-count", type=int, help="热门推文最多条数")
    parser.add_argument("--trending-query", help="热门搜索关键词（Twitter 搜索语法）")
    parser.add_argument("--min-faves", type=int, help="热门推文最低浏览量")
    parser.add_argument("--language", help="语言过滤（all/en/zh/ja...）")
    parser.add_argument("--exclude-users", help="排除的用户名（逗号分隔）")
    parser.add_argument("--reset-state", action="store_true", help="重置去重状态")
    parser.add_argument("--no-trending", action="store_true", help="禁用热门搜索")
    parser.add_argument("--no-summary", action="store_true", help="禁用 AI 总结")

    subparsers = parser.add_subparsers(dest="command")

    # scrape
    subparsers.add_parser("scrape", help="Layer 1: 抓取推文原始数据")

    # analyze
    sp_analyze = subparsers.add_parser("analyze", help="Layer 2: AI 分析原始数据")
    sp_analyze.add_argument("--source", help="指定 raw JSON 文件路径")
    sp_analyze.add_argument("--from", dest="time_from", help="起始时间（如 '2026-02-12 08:00'）")
    sp_analyze.add_argument("--to", dest="time_to", help="结束时间（如 '2026-02-12 14:00'）")

    # report
    sp_report = subparsers.add_parser("report", help="Layer 3: 生成报告")
    sp_report.add_argument("--source", help="指定 analysis JSON 文件路径")
    sp_report.add_argument("--daily", metavar="YYYY-MM-DD", help="生成日报")
    sp_report.add_argument("--weekly", metavar="YYYY-MM-DD", help="生成周报（从指定日期起 7 天）")
    sp_report.add_argument("--monthly", metavar="YYYY-MM", help="生成月报")

    args = parser.parse_args()

    # 重置状态
    if args.reset_state:
        state_file = ".twitter_watchdog_state.json"
        if os.path.exists(state_file):
            os.remove(state_file)
            print("已重置去重状态")
        else:
            print("无状态文件，无需重置")

    # 路由
    if args.command == "scrape":
        watchdog = TwitterWatchdog(config_file=args.config, cli_args=args)
        watchdog.run_scrape()

    elif args.command == "analyze":
        watchdog = TwitterWatchdog(config_file=args.config, cli_args=args, report_only=True)
        time_from = None
        time_to = None
        if getattr(args, "time_from", None):
            time_from = datetime.strptime(args.time_from, "%Y-%m-%d %H:%M").replace(tzinfo=TZ_CN)
        if getattr(args, "time_to", None):
            time_to = datetime.strptime(args.time_to, "%Y-%m-%d %H:%M").replace(tzinfo=TZ_CN)
        watchdog.run_analyze(
            source=getattr(args, "source", None),
            time_from=time_from,
            time_to=time_to,
        )

    elif args.command == "report":
        watchdog = TwitterWatchdog(config_file=args.config, cli_args=args, report_only=True)
        watchdog.run_report(
            source=getattr(args, "source", None),
            daily=getattr(args, "daily", None),
            weekly=getattr(args, "weekly", None),
            monthly=getattr(args, "monthly", None),
        )

    else:
        # 无子命令 → 流水线（向后兼容）
        watchdog = TwitterWatchdog(config_file=args.config, cli_args=args)
        watchdog.run_pipeline()

    print("\n=== 完成 ===")


if __name__ == "__main__":
    main()
