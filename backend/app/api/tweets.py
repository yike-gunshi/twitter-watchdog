"""推文数据 API 路由

提供推文查询、作者查询、统计信息和手动导入接口。
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.tweet_store import TweetStore

router = APIRouter(prefix="/api/tweets", tags=["tweets"])
author_router = APIRouter(prefix="/api/authors", tags=["authors"])


# ── Pydantic 模型 ──────────────────────────────────────────


class AuthorOut(BaseModel):
    author_id: str
    username: str
    display_name: str
    description: Optional[str] = ""
    profile_picture: Optional[str] = ""
    followers_count: int = 0
    following_count: int = 0
    is_verified: bool = False
    verified_type: Optional[str] = ""

    model_config = {"from_attributes": True}


class TweetOut(BaseModel):
    tweet_id: str
    url: str
    text: str
    author_id: str
    lang: Optional[str] = ""
    source_device: Optional[str] = ""
    like_count: int = 0
    retweet_count: int = 0
    reply_count: int = 0
    quote_count: int = 0
    view_count: int = 0
    bookmark_count: int = 0
    is_reply: bool = False
    quoted_tweet_id: Optional[str] = None
    media_urls: Optional[list] = []
    source_type: str = "following"
    tweet_created_at: Optional[datetime] = None
    scraped_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TweetDetailOut(TweetOut):
    raw_json: Optional[dict] = None
    author: Optional[AuthorOut] = None


class PaginatedTweets(BaseModel):
    items: list[TweetOut]
    total: int
    page: int
    page_size: int


class PaginatedAuthors(BaseModel):
    items: list[AuthorOut]
    total: int
    page: int
    page_size: int


class StatsOut(BaseModel):
    total_tweets: int
    total_authors: int
    total_analyses: int
    ai_related_tweets: int
    urgent_tweets: int
    latest_tweet_at: Optional[str] = None
    earliest_tweet_at: Optional[str] = None


class ImportRequest(BaseModel):
    file_path: str
    file_type: str = "raw"  # "raw" or "analysis"


class ImportResult(BaseModel):
    tweets_added: int = 0
    tweets_updated: int = 0
    analyses_added: int = 0
    authors_count: int = 0


# ── 推文路由 ──────────────────────────────────────────────


@router.get("", response_model=PaginatedTweets)
async def list_tweets(
    author: Optional[str] = Query(None, description="按作者用户名筛选"),
    keyword: Optional[str] = Query(None, description="按关键词搜索推文内容"),
    source_type: Optional[str] = Query(None, description="来源类型: following/trending"),
    start_date: Optional[str] = Query(None, description="起始时间 (ISO 格式)"),
    end_date: Optional[str] = Query(None, description="结束时间 (ISO 格式)"),
    ai_only: bool = Query(False, description="仅显示 AI 相关推文"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取推文列表（分页 + 筛选）"""
    store = TweetStore(db)

    start_dt = datetime.fromisoformat(start_date) if start_date else None
    end_dt = datetime.fromisoformat(end_date) if end_date else None

    tweets, total = await store.get_tweets(
        author_username=author,
        keyword=keyword,
        source_type=source_type,
        start_date=start_dt,
        end_date=end_dt,
        ai_only=ai_only,
        page=page,
        page_size=page_size,
    )

    return PaginatedTweets(
        items=[TweetOut.model_validate(t) for t in tweets],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/stats", response_model=StatsOut)
async def get_stats(db: AsyncSession = Depends(get_db)):
    """获取数据库统计信息"""
    store = TweetStore(db)
    stats = await store.get_stats()
    return StatsOut(**stats)


@router.get("/{tweet_id}", response_model=TweetDetailOut)
async def get_tweet(tweet_id: str, db: AsyncSession = Depends(get_db)):
    """获取单条推文详情"""
    store = TweetStore(db)
    tweet = await store.get_tweet_by_id(tweet_id)
    if not tweet:
        raise HTTPException(status_code=404, detail="推文不存在")

    # 加载作者信息
    from app.models.db import Author
    author = await db.get(Author, tweet.author_id)

    data = TweetOut.model_validate(tweet).model_dump()
    data["raw_json"] = tweet.raw_json
    data["author"] = AuthorOut.model_validate(author) if author else None
    return TweetDetailOut(**data)


@router.post("/import", response_model=ImportResult)
async def import_tweets(req: ImportRequest, db: AsyncSession = Depends(get_db)):
    """手动导入推文数据"""
    store = TweetStore(db)
    try:
        if req.file_type == "analysis":
            result = await store.import_from_analysis_json(req.file_path)
        else:
            result = await store.import_from_raw_json(req.file_path)
        return ImportResult(**result)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")


# ── 作者路由 ──────────────────────────────────────────────


@author_router.get("", response_model=PaginatedAuthors)
async def list_authors(
    keyword: Optional[str] = Query(None, description="按用户名或显示名搜索"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取作者列表"""
    store = TweetStore(db)
    authors, total = await store.get_authors(
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return PaginatedAuthors(
        items=[AuthorOut.model_validate(a) for a in authors],
        total=total,
        page=page,
        page_size=page_size,
    )


@author_router.get("/{username}/tweets", response_model=PaginatedTweets)
async def get_author_tweets(
    username: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取某作者的所有推文"""
    store = TweetStore(db)
    tweets, total = await store.get_tweets(
        author_username=username,
        page=page,
        page_size=page_size,
    )
    return PaginatedTweets(
        items=[TweetOut.model_validate(t) for t in tweets],
        total=total,
        page=page,
        page_size=page_size,
    )
