"""API for listing available data files (raw scrapes + analysis results)."""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from app.core.config import DEFAULT_CONFIG_FILE

router = APIRouter(prefix="/data", tags=["data"])

# Resolve output directory from the same config used by the engine
_OUTPUT_DIR: Path | None = None


def _get_output_dir() -> Path:
    global _OUTPUT_DIR
    if _OUTPUT_DIR is None:
        import yaml
        try:
            with open(DEFAULT_CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
            _OUTPUT_DIR = Path(cfg.get("output", {}).get(
                "directory",
                str(Path.home() / ".claude" / "skills" / "twitter-watchdog" / "output"),
            ))
        except Exception:
            _OUTPUT_DIR = Path.home() / ".claude" / "skills" / "twitter-watchdog" / "output"
    return _OUTPUT_DIR


def _file_info(file_path: Path, count_key: str | None = None) -> dict:
    """Build a dict describing a data file."""
    info = {
        "filename": file_path.name,
        "path": str(file_path),
        "size_bytes": file_path.stat().st_size,
        "modified_at": file_path.stat().st_mtime,
    }
    # Try to read count from JSON metadata
    if count_key:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            meta = data.get("metadata", {})
            if count_key in meta:
                info["count"] = meta[count_key]
            elif count_key == "filtered_count":
                # fallback: count from filtered data
                info["count"] = meta.get("filtered_count", 0)
        except Exception:
            pass
    return info


@router.get("/raw-files")
async def list_raw_files():
    """List files in output/raw/ with tweet count."""
    raw_dir = _get_output_dir() / "raw"
    if not raw_dir.exists():
        return {"files": []}
    files = sorted(raw_dir.glob("*.json"), reverse=True)
    return {
        "files": [_file_info(f, count_key="total_tweets") for f in files],
    }


@router.get("/analysis-files")
async def list_analysis_files():
    """List files in output/analysis/ with filtered count."""
    analysis_dir = _get_output_dir() / "analysis"
    if not analysis_dir.exists():
        return {"files": []}
    files = sorted(analysis_dir.glob("*.json"), reverse=True)
    return {
        "files": [_file_info(f, count_key="filtered_count") for f in files],
    }


@router.get("/analysis-files/{filename}")
async def get_analysis_file_content(
    filename: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    source: str = Query("all", regex="^(all|followings|trending)$"),
):
    """Return filtered tweet data from an analysis JSON file with pagination."""
    analysis_dir = _get_output_dir() / "analysis"
    file_path = analysis_dir / filename
    if not file_path.exists() or not file_path.suffix == ".json":
        raise HTTPException(status_code=404, detail="File not found")

    try:
        file_path.resolve().relative_to(analysis_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to read file")

    metadata = data.get("metadata", {})
    ai_tweet_ids = data.get("ai_tweet_ids", [])

    tweets = []

    if source in ("all", "followings"):
        for following in data.get("filtered_followings", []):
            user = following.get("user", {})
            user_info = {
                "username": user.get("userName") or user.get("screen_name", ""),
                "name": user.get("name", ""),
                "avatar": user.get("profileImageUrl") or user.get("avatar", ""),
            }
            for tweet in following.get("tweets", []):
                tweets.append({
                    "id": tweet.get("id"),
                    "text": tweet.get("text", ""),
                    "url": tweet.get("url") or tweet.get("twitterUrl", ""),
                    "created_at": tweet.get("createdAt", ""),
                    "like_count": tweet.get("likeCount", 0),
                    "retweet_count": tweet.get("retweetCount", 0),
                    "reply_count": tweet.get("replyCount", 0),
                    "view_count": tweet.get("viewCount", 0),
                    "quote_count": tweet.get("quoteCount", 0),
                    "lang": tweet.get("lang", ""),
                    "source_type": "following",
                    "author": user_info,
                    "has_media": bool(tweet.get("extendedEntities")),
                    "is_reply": tweet.get("isReply", False),
                    "is_ai_selected": True,
                })

    if source in ("all", "trending"):
        for tweet in data.get("filtered_trending", []):
            author = tweet.get("author", {})
            user_info = {
                "username": author.get("userName") or author.get("screen_name", ""),
                "name": author.get("name", ""),
                "avatar": author.get("profileImageUrl") or author.get("avatar", ""),
            }
            tweets.append({
                "id": tweet.get("id"),
                "text": tweet.get("text", ""),
                "url": tweet.get("url") or tweet.get("twitterUrl", ""),
                "created_at": tweet.get("createdAt", ""),
                "like_count": tweet.get("likeCount", 0),
                "retweet_count": tweet.get("retweetCount", 0),
                "reply_count": tweet.get("replyCount", 0),
                "view_count": tweet.get("viewCount", 0),
                "quote_count": tweet.get("quoteCount", 0),
                "lang": tweet.get("lang", ""),
                "source_type": "trending",
                "author": user_info,
                "has_media": bool(tweet.get("extendedEntities")),
                "is_reply": tweet.get("isReply", False),
                "is_ai_selected": True,
            })

    tweets.sort(key=lambda t: t.get("view_count", 0) or 0, reverse=True)

    total = len(tweets)
    start = (page - 1) * page_size
    end = start + page_size
    page_tweets = tweets[start:end]

    following_count = sum(1 for t in tweets if t["source_type"] == "following")
    trending_count = sum(1 for t in tweets if t["source_type"] == "trending")

    return {
        "metadata": metadata,
        "ai_tweet_ids": ai_tweet_ids,
        "tweets": page_tweets,
        "total": total,
        "following_count": following_count,
        "trending_count": trending_count,
        "page": page,
        "page_size": page_size,
    }


@router.get("/raw-files/{filename}")
async def get_raw_file_content(
    filename: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    source: str = Query("all", regex="^(all|followings|trending)$"),
    analysis_file: str | None = Query(None),
):
    """Return tweet data from a raw JSON file with pagination.

    source: 'all' | 'followings' | 'trending'
    """
    raw_dir = _get_output_dir() / "raw"
    file_path = raw_dir / filename
    if not file_path.exists() or not file_path.suffix == ".json":
        raise HTTPException(status_code=404, detail="File not found")

    # Security: ensure file is within raw directory
    try:
        file_path.resolve().relative_to(raw_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to read file")

    metadata = data.get("metadata", {})

    # Build flat list of tweets with user info
    tweets = []

    if source in ("all", "followings"):
        for following in data.get("followings", []):
            user = following.get("user", {})
            user_info = {
                "username": user.get("userName") or user.get("screen_name", ""),
                "name": user.get("name", ""),
                "avatar": user.get("profileImageUrl") or user.get("avatar", ""),
            }
            for tweet in following.get("tweets", []):
                tweets.append({
                    "id": tweet.get("id"),
                    "text": tweet.get("text", ""),
                    "url": tweet.get("url") or tweet.get("twitterUrl", ""),
                    "created_at": tweet.get("createdAt", ""),
                    "like_count": tweet.get("likeCount", 0),
                    "retweet_count": tweet.get("retweetCount", 0),
                    "reply_count": tweet.get("replyCount", 0),
                    "view_count": tweet.get("viewCount", 0),
                    "quote_count": tweet.get("quoteCount", 0),
                    "lang": tweet.get("lang", ""),
                    "source_type": "following",
                    "author": user_info,
                    "has_media": bool(tweet.get("extendedEntities")),
                    "is_reply": tweet.get("isReply", False),
                })

    if source in ("all", "trending"):
        for tweet in data.get("trending", []):
            author = tweet.get("author", {})
            user_info = {
                "username": author.get("userName") or author.get("screen_name", ""),
                "name": author.get("name", ""),
                "avatar": author.get("profileImageUrl") or author.get("avatar", ""),
            }
            tweets.append({
                "id": tweet.get("id"),
                "text": tweet.get("text", ""),
                "url": tweet.get("url") or tweet.get("twitterUrl", ""),
                "created_at": tweet.get("createdAt", ""),
                "like_count": tweet.get("likeCount", 0),
                "retweet_count": tweet.get("retweetCount", 0),
                "reply_count": tweet.get("replyCount", 0),
                "view_count": tweet.get("viewCount", 0),
                "quote_count": tweet.get("quoteCount", 0),
                "lang": tweet.get("lang", ""),
                "source_type": "trending",
                "author": user_info,
                "has_media": bool(tweet.get("extendedEntities")),
                "is_reply": tweet.get("isReply", False),
            })

    # Add AI selection markers if analysis file provided
    if analysis_file:
        ai_ids = set()
        af_path = _get_output_dir() / "analysis" / analysis_file
        if af_path.exists():
            try:
                with open(af_path, "r", encoding="utf-8") as f:
                    af_data = json.load(f)
                ai_ids = set(af_data.get("ai_tweet_ids", []))
            except Exception:
                pass
        for tweet in tweets:
            tweet["is_ai_selected"] = tweet.get("id") in ai_ids

    # Sort by view_count descending
    tweets.sort(key=lambda t: t.get("view_count", 0) or 0, reverse=True)

    total = len(tweets)
    start = (page - 1) * page_size
    end = start + page_size
    page_tweets = tweets[start:end]

    # Count by source type
    following_count = sum(1 for t in tweets if t["source_type"] == "following")
    trending_count = sum(1 for t in tweets if t["source_type"] == "trending")

    return {
        "metadata": metadata,
        "tweets": page_tweets,
        "total": total,
        "following_count": following_count,
        "trending_count": trending_count,
        "page": page,
        "page_size": page_size,
    }
