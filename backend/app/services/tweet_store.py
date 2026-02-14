"""推文数据库存储服务

负责将抓取/分析的推文数据存入数据库，并提供查询接口。
核心设计：
- 推文以 tweet_id 为主键全局去重，不同用户查同一条推文共享数据
- 作者以 author_id 为主键全局共享
- 互动数据(like/view/retweet)取最新值更新
"""

import json
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from sqlalchemy import select, func, or_, update, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.sqlite import insert as sqlite_upsert

from app.models.db import Author, Tweet, TweetAnalysis, UserSubscription, TZ_CN, now_cn

# ── 数据解析工具 ──────────────────────────────────────────


def _parse_tweet_time(created_at: str) -> Optional[datetime]:
    """解析 Twitter 的 createdAt 字段"""
    if not created_at:
        return None
    try:
        dt = datetime.strptime(created_at, "%a %b %d %H:%M:%S %z %Y")
        return dt.astimezone(TZ_CN)
    except ValueError:
        pass
    try:
        dt = datetime.fromisoformat(created_at)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(TZ_CN)
    except ValueError:
        return None


def _extract_media_urls(tweet: dict) -> list[str]:
    """从推文中提取所有媒体 URL"""
    urls = []
    media_sources = [
        tweet.get("extendedEntities", {}).get("media", []),
        tweet.get("entities", {}).get("media", []),
        tweet.get("media", []),
    ]
    for media_list in media_sources:
        if not media_list:
            continue
        for m in media_list:
            url = m.get("media_url_https") or m.get("media_url") or m.get("url", "")
            if url and url not in urls:
                urls.append(url)
        if urls:
            break
    return urls


def _extract_author(tweet: dict) -> dict:
    """从推文数据中提取作者信息"""
    author = tweet.get("author", {})
    if not author:
        return {}

    twitter_created = None
    if author.get("createdAt"):
        twitter_created = _parse_tweet_time(author["createdAt"])

    return {
        "author_id": str(author.get("id", "")),
        "username": author.get("userName") or author.get("username", ""),
        "display_name": author.get("name", ""),
        "description": author.get("description", ""),
        "profile_picture": author.get("profilePicture") or author.get("profile_image_url", ""),
        "cover_picture": author.get("coverPicture", ""),
        "followers_count": author.get("followers") or author.get("public_metrics", {}).get("followers_count", 0),
        "following_count": author.get("following") or author.get("public_metrics", {}).get("following_count", 0),
        "is_verified": author.get("isVerified", False) or author.get("isBlueVerified", False),
        "verified_type": author.get("verifiedType", ""),
        "location": author.get("location", ""),
        "twitter_created_at": twitter_created,
    }


def _extract_tweet(tweet: dict, source_type: str = "following") -> dict:
    """从原始推文数据中提取标准化字段"""
    author_info = _extract_author(tweet)
    quoted = tweet.get("quoted_tweet") or tweet.get("quotedTweet")

    return {
        "tweet_id": str(tweet.get("id", "")),
        "url": tweet.get("url", ""),
        "text": tweet.get("text", ""),
        "author_id": author_info.get("author_id", ""),
        "lang": tweet.get("lang", ""),
        "source": tweet.get("source", ""),
        "like_count": tweet.get("likeCount", 0),
        "retweet_count": tweet.get("retweetCount", 0),
        "reply_count": tweet.get("replyCount", 0),
        "quote_count": tweet.get("quoteCount", 0),
        "view_count": tweet.get("viewCount", 0),
        "bookmark_count": tweet.get("bookmarkCount", 0),
        "is_reply": tweet.get("isReply", False),
        "in_reply_to_id": tweet.get("inReplyToId"),
        "conversation_id": tweet.get("conversationId"),
        "quoted_tweet_id": str(quoted["id"]) if quoted and quoted.get("id") else None,
        "media_urls": _extract_media_urls(tweet),
        "raw_json": tweet,
        "tweet_created_at": _parse_tweet_time(tweet.get("createdAt", "")),
        "source_type": source_type,
        "_author_info": author_info,
    }


# ── 存储服务 ──────────────────────────────────────────────


class TweetStore:
    """推文存储服务（异步）"""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ── 写入 ──

    async def upsert_author(self, author_info: dict) -> Optional[str]:
        """插入或更新作者，返回 author_id"""
        author_id = author_info.get("author_id")
        if not author_id:
            return None

        existing = await self.session.get(Author, author_id)
        if existing:
            # 更新可变字段
            for field in ["username", "display_name", "description", "profile_picture",
                          "cover_picture", "followers_count", "following_count",
                          "is_verified", "verified_type", "location"]:
                val = author_info.get(field)
                if val is not None and val != "":
                    setattr(existing, field, val)
            existing.updated_at = now_cn()
        else:
            author_obj = Author(**{k: v for k, v in author_info.items() if k != "_author_info"})
            self.session.add(author_obj)

        return author_id

    async def upsert_tweet(self, tweet_data: dict) -> Optional[str]:
        """插入或更新推文，返回 tweet_id"""
        tweet_id = tweet_data.get("tweet_id")
        if not tweet_id:
            return None

        # 先处理作者
        author_info = tweet_data.pop("_author_info", {})
        if author_info and author_info.get("author_id"):
            await self.upsert_author(author_info)

        existing = await self.session.get(Tweet, tweet_id)
        if existing:
            # 更新互动数据（取较大值）
            for field in ["like_count", "retweet_count", "reply_count",
                          "quote_count", "view_count", "bookmark_count"]:
                new_val = tweet_data.get(field, 0)
                if new_val > getattr(existing, field, 0):
                    setattr(existing, field, new_val)
            # 更新原始数据
            if tweet_data.get("raw_json"):
                existing.raw_json = tweet_data["raw_json"]
            existing.updated_at = now_cn()
        else:
            # 移除不属于 Tweet 模型的字段
            clean = {k: v for k, v in tweet_data.items() if hasattr(Tweet, k)}
            tweet_obj = Tweet(**clean)
            self.session.add(tweet_obj)

        return tweet_id

    async def save_analysis(self, tweet_id: str, batch_id: str,
                            category: str = "", summary: str = "",
                            is_urgent: bool = False, model: str = "") -> int:
        """保存分析结果，返回分析 ID"""
        analysis = TweetAnalysis(
            tweet_id=tweet_id,
            analysis_batch_id=batch_id,
            category=category,
            summary_text=summary,
            is_ai_related=True,
            is_urgent=is_urgent,
            model_used=model,
        )
        self.session.add(analysis)
        await self.session.flush()
        return analysis.id

    # ── 批量导入 ──

    async def import_from_raw_json(self, raw_json_path: str) -> dict:
        """从 Layer 1 raw JSON 导入推文和作者数据

        Returns:
            {"tweets_added": int, "tweets_updated": int, "authors_added": int}
        """
        path = Path(raw_json_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {raw_json_path}")

        with open(path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        stats = {"tweets_added": 0, "tweets_updated": 0, "authors_count": 0}

        # 导入关注列表推文
        for user_data in raw_data.get("followings", []):
            for tweet in user_data.get("tweets", []):
                tweet_info = _extract_tweet(tweet, source_type="following")
                if not tweet_info["tweet_id"]:
                    continue

                existing = await self.session.get(Tweet, tweet_info["tweet_id"])
                await self.upsert_tweet(tweet_info)
                if existing:
                    stats["tweets_updated"] += 1
                else:
                    stats["tweets_added"] += 1

        # 导入热门推文
        for tweet in raw_data.get("trending", []):
            tweet_info = _extract_tweet(tweet, source_type="trending")
            if not tweet_info["tweet_id"]:
                continue

            existing = await self.session.get(Tweet, tweet_info["tweet_id"])
            await self.upsert_tweet(tweet_info)
            if existing:
                stats["tweets_updated"] += 1
            else:
                stats["tweets_added"] += 1

        await self.session.commit()

        # 统计作者数
        result = await self.session.execute(select(func.count(Author.author_id)))
        stats["authors_count"] = result.scalar()

        return stats

    async def import_from_analysis_json(self, analysis_json_path: str) -> dict:
        """从 Layer 2 analysis JSON 导入推文 + 分析结果

        Returns:
            {"tweets_added": int, "tweets_updated": int, "analyses_added": int}
        """
        path = Path(analysis_json_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {analysis_json_path}")

        with open(path, "r", encoding="utf-8") as f:
            analysis_data = json.load(f)

        stats = {"tweets_added": 0, "tweets_updated": 0, "analyses_added": 0}
        batch_id = str(uuid.uuid4())[:8] + "_" + path.stem
        metadata = analysis_data.get("metadata", {})
        model = metadata.get("model", "")
        ai_tweet_ids = set(analysis_data.get("ai_tweet_ids", []))
        urgent_ids = set(analysis_data.get("urgent_ids", []))

        # 导入筛选后的关注推文
        for user_data in analysis_data.get("filtered_followings", []):
            for tweet in user_data.get("tweets", []):
                tweet_info = _extract_tweet(tweet, source_type="following")
                tid = tweet_info["tweet_id"]
                if not tid:
                    continue

                existing = await self.session.get(Tweet, tid)
                await self.upsert_tweet(tweet_info)
                if existing:
                    stats["tweets_updated"] += 1
                else:
                    stats["tweets_added"] += 1

                # 保存分析结果
                is_urgent = tid in urgent_ids
                await self.save_analysis(
                    tweet_id=tid,
                    batch_id=batch_id,
                    is_urgent=is_urgent,
                    model=model,
                )
                stats["analyses_added"] += 1

        # 导入筛选后的热门推文
        for tweet in analysis_data.get("filtered_trending", []):
            tweet_info = _extract_tweet(tweet, source_type="trending")
            tid = tweet_info["tweet_id"]
            if not tid:
                continue

            existing = await self.session.get(Tweet, tid)
            await self.upsert_tweet(tweet_info)
            if existing:
                stats["tweets_updated"] += 1
            else:
                stats["tweets_added"] += 1

            is_urgent = tid in urgent_ids
            await self.save_analysis(
                tweet_id=tid,
                batch_id=batch_id,
                is_urgent=is_urgent,
                model=model,
            )
            stats["analyses_added"] += 1

        await self.session.commit()
        return stats

    # ── 查询 ──

    async def get_tweets(
        self,
        author_username: Optional[str] = None,
        keyword: Optional[str] = None,
        source_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        ai_only: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Tweet], int]:
        """查询推文（分页 + 筛选）

        Returns:
            (tweets, total_count)
        """
        query = select(Tweet)
        count_query = select(func.count(Tweet.tweet_id))

        # 按作者
        if author_username:
            query = query.join(Author).where(Author.username == author_username)
            count_query = count_query.join(Author).where(Author.username == author_username)

        # 按关键词
        if keyword:
            pattern = f"%{keyword}%"
            query = query.where(Tweet.text.ilike(pattern))
            count_query = count_query.where(Tweet.text.ilike(pattern))

        # 按来源类型
        if source_type:
            query = query.where(Tweet.source_type == source_type)
            count_query = count_query.where(Tweet.source_type == source_type)

        # 按时间范围
        if start_date:
            query = query.where(Tweet.tweet_created_at >= start_date)
            count_query = count_query.where(Tweet.tweet_created_at >= start_date)
        if end_date:
            query = query.where(Tweet.tweet_created_at <= end_date)
            count_query = count_query.where(Tweet.tweet_created_at <= end_date)

        # 仅 AI 相关（有分析记录的）
        if ai_only:
            query = query.where(Tweet.tweet_id.in_(
                select(TweetAnalysis.tweet_id).where(TweetAnalysis.is_ai_related == True)
            ))
            count_query = count_query.where(Tweet.tweet_id.in_(
                select(TweetAnalysis.tweet_id).where(TweetAnalysis.is_ai_related == True)
            ))

        # 排序 + 分页
        query = query.order_by(Tweet.tweet_created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.session.execute(query)
        tweets = list(result.scalars().all())

        total_result = await self.session.execute(count_query)
        total = total_result.scalar()

        return tweets, total

    async def get_tweet_by_id(self, tweet_id: str) -> Optional[Tweet]:
        """获取单条推文（含作者信息）"""
        result = await self.session.execute(
            select(Tweet).where(Tweet.tweet_id == tweet_id)
        )
        return result.scalar_one_or_none()

    async def get_authors(
        self,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Author], int]:
        """查询作者列表"""
        query = select(Author)
        count_query = select(func.count(Author.author_id))

        if keyword:
            pattern = f"%{keyword}%"
            query = query.where(or_(
                Author.username.ilike(pattern),
                Author.display_name.ilike(pattern),
            ))
            count_query = count_query.where(or_(
                Author.username.ilike(pattern),
                Author.display_name.ilike(pattern),
            ))

        query = query.order_by(Author.followers_count.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.session.execute(query)
        authors = list(result.scalars().all())

        total_result = await self.session.execute(count_query)
        total = total_result.scalar()

        return authors, total

    async def get_stats(self) -> dict:
        """获取数据库统计信息"""
        tweets_count = (await self.session.execute(
            select(func.count(Tweet.tweet_id))
        )).scalar()

        authors_count = (await self.session.execute(
            select(func.count(Author.author_id))
        )).scalar()

        analyses_count = (await self.session.execute(
            select(func.count(TweetAnalysis.id))
        )).scalar()

        ai_tweets_count = (await self.session.execute(
            select(func.count(func.distinct(TweetAnalysis.tweet_id))).where(
                TweetAnalysis.is_ai_related == True
            )
        )).scalar()

        urgent_count = (await self.session.execute(
            select(func.count(TweetAnalysis.id)).where(
                TweetAnalysis.is_urgent == True
            )
        )).scalar()

        # 最新推文时间
        latest_tweet = (await self.session.execute(
            select(Tweet.tweet_created_at).order_by(Tweet.tweet_created_at.desc()).limit(1)
        )).scalar()

        # 最早推文时间
        earliest_tweet = (await self.session.execute(
            select(Tweet.tweet_created_at).order_by(Tweet.tweet_created_at.asc()).limit(1)
        )).scalar()

        return {
            "total_tweets": tweets_count,
            "total_authors": authors_count,
            "total_analyses": analyses_count,
            "ai_related_tweets": ai_tweets_count,
            "urgent_tweets": urgent_count,
            "latest_tweet_at": latest_tweet.isoformat() if latest_tweet else None,
            "earliest_tweet_at": earliest_tweet.isoformat() if earliest_tweet else None,
        }
