import json
from datetime import datetime, timezone, timedelta
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base

TZ_CN = timezone(timedelta(hours=8))


def now_cn():
    return datetime.now(TZ_CN)


class Config(Base):
    __tablename__ = "configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), nullable=True, default=None, index=True)
    twitter_username = Column(String(128), nullable=False, default="")
    custom_accounts = Column(Text, nullable=False, default="[]")  # JSON list
    style = Column(String(32), nullable=False, default="standard")
    custom_prompt = Column(Text, nullable=False, default="")
    filter_keywords = Column(Text, nullable=False, default="[]")  # JSON list
    push_config = Column(Text, nullable=False, default="{}")  # JSON object
    created_at = Column(DateTime(timezone=True), default=now_cn)
    updated_at = Column(DateTime(timezone=True), default=now_cn, onupdate=now_cn)

    def get_custom_accounts(self):
        return json.loads(self.custom_accounts) if self.custom_accounts else []

    def get_filter_keywords(self):
        return json.loads(self.filter_keywords) if self.filter_keywords else []

    def get_push_config(self):
        return json.loads(self.push_config) if self.push_config else {}


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String(32), nullable=False)  # scrape / analyze / report / pipeline
    status = Column(String(32), nullable=False, default="pending")  # pending / running / completed / failed / cancelled
    params = Column(Text, nullable=False, default="{}")  # JSON
    log = Column(Text, nullable=False, default="")
    result_file = Column(String(512), nullable=True, default=None)
    error = Column(Text, nullable=True, default=None)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=now_cn)

    def get_params(self):
        return json.loads(self.params) if self.params else {}


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String(32), nullable=False, default="single")  # single / daily / weekly / monthly
    file_path = Column(String(512), nullable=False)
    summary = Column(Text, nullable=True, default="")
    tweet_count = Column(Integer, nullable=False, default=0)
    period_start = Column(DateTime(timezone=True), nullable=True, default=None)
    period_end = Column(DateTime(timezone=True), nullable=True, default=None)
    created_at = Column(DateTime(timezone=True), default=now_cn)


# ── 推文数据模型 ──────────────────────────────────────────


class Author(Base):
    """Twitter 用户/作者表 — 以 Twitter user_id 为主键，全局共享"""
    __tablename__ = "authors"

    author_id = Column(String(64), primary_key=True)  # Twitter user ID
    username = Column(String(128), nullable=False, index=True)
    display_name = Column(String(256), nullable=False, default="")
    description = Column(Text, nullable=True, default="")
    profile_picture = Column(String(512), nullable=True, default="")
    cover_picture = Column(String(512), nullable=True, default="")
    followers_count = Column(Integer, nullable=False, default=0)
    following_count = Column(Integer, nullable=False, default=0)
    is_verified = Column(Boolean, nullable=False, default=False)
    verified_type = Column(String(32), nullable=True, default="")
    location = Column(String(256), nullable=True, default="")
    twitter_created_at = Column(DateTime(timezone=True), nullable=True)  # Twitter 账号创建时间
    created_at = Column(DateTime(timezone=True), default=now_cn)  # 入库时间
    updated_at = Column(DateTime(timezone=True), default=now_cn, onupdate=now_cn)

    # Relationships
    tweets = relationship("Tweet", back_populates="author", lazy="dynamic")


class Tweet(Base):
    """推文表 — 以 tweet_id 为主键，全局去重共享"""
    __tablename__ = "tweets"

    tweet_id = Column(String(64), primary_key=True)  # Twitter 推文 ID
    url = Column(String(512), nullable=False, default="")
    text = Column(Text, nullable=False, default="")
    author_id = Column(String(64), ForeignKey("authors.author_id"), nullable=False, index=True)
    lang = Column(String(16), nullable=True, default="")
    source = Column(String(128), nullable=True, default="")  # 来源设备

    # 互动数据
    like_count = Column(Integer, nullable=False, default=0)
    retweet_count = Column(Integer, nullable=False, default=0)
    reply_count = Column(Integer, nullable=False, default=0)
    quote_count = Column(Integer, nullable=False, default=0)
    view_count = Column(Integer, nullable=False, default=0)
    bookmark_count = Column(Integer, nullable=False, default=0)

    # 回复/对话
    is_reply = Column(Boolean, nullable=False, default=False)
    in_reply_to_id = Column(String(64), nullable=True)
    conversation_id = Column(String(64), nullable=True)

    # 引用推文
    quoted_tweet_id = Column(String(64), nullable=True)

    # 媒体
    media_urls = Column(JSON, nullable=True, default=list)  # ["url1", "url2", ...]

    # 原始数据备份
    raw_json = Column(JSON, nullable=True)

    # 时间
    tweet_created_at = Column(DateTime(timezone=True), nullable=True)  # 推文发布时间
    scraped_at = Column(DateTime(timezone=True), default=now_cn)  # 入库时间
    updated_at = Column(DateTime(timezone=True), default=now_cn, onupdate=now_cn)

    # 来源标记
    source_type = Column(String(32), nullable=False, default="following")  # following / trending / search

    # Relationships
    author = relationship("Author", back_populates="tweets")
    analyses = relationship("TweetAnalysis", back_populates="tweet", lazy="dynamic")


class TweetAnalysis(Base):
    """推文分析结果表 — 记录每次 AI 分析的结果"""
    __tablename__ = "tweet_analyses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tweet_id = Column(String(64), ForeignKey("tweets.tweet_id"), nullable=False, index=True)
    analysis_batch_id = Column(String(64), nullable=False, index=True)  # 同一批次分析标识
    category = Column(String(64), nullable=True, default="")  # research / product / model / developer / industry
    summary_text = Column(Text, nullable=True, default="")  # AI 生成的中文摘要
    is_ai_related = Column(Boolean, nullable=False, default=True)  # 是否 AI 相关
    is_urgent = Column(Boolean, nullable=False, default=False)  # 是否突发
    relevance_score = Column(Float, nullable=True)  # AI 相关性评分
    model_used = Column(String(128), nullable=True, default="")  # 使用的 AI 模型
    analyzed_at = Column(DateTime(timezone=True), default=now_cn)

    # Relationships
    tweet = relationship("Tweet", back_populates="analyses")


class UserSubscription(Base):
    """用户订阅表 — 记录不同用户/部署订阅的 Twitter 账号"""
    __tablename__ = "user_subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(128), nullable=False, index=True)  # 平台用户 ID
    twitter_username = Column(String(128), nullable=False)  # 订阅的 Twitter 用户名
    created_at = Column(DateTime(timezone=True), default=now_cn)

    __table_args__ = (
        UniqueConstraint("user_id", "twitter_username", name="uq_user_subscription"),
    )
