from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


# ── Config ──

class ConfigOut(BaseModel):
    id: int
    twitter_username: str
    custom_accounts: list[str]
    style: str
    custom_prompt: str
    keywords: list[str]
    min_engagement: int
    hours_ago: int
    telegram_bot_token: str
    telegram_chat_id: str
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ConfigUpdate(BaseModel):
    twitter_username: Optional[str] = None
    custom_accounts: Optional[list[str]] = None
    style: Optional[str] = None
    custom_prompt: Optional[str] = None
    keywords: Optional[list[str]] = None
    min_engagement: Optional[int] = None
    hours_ago: Optional[int] = None
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None


# ── Job ──

class JobCreate(BaseModel):
    type: str  # scrape / analyze / report / pipeline
    params: Optional[dict] = None


class JobOut(BaseModel):
    id: int
    type: str
    status: str
    params: dict
    log: str
    result_file: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class JobListOut(BaseModel):
    id: int
    type: str
    status: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── Report ──

class ReportOut(BaseModel):
    id: int
    type: str
    file_path: str
    summary: Optional[str] = None
    tweet_count: int
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ReportListOut(BaseModel):
    id: int
    type: str
    summary: Optional[str] = None
    tweet_count: int
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── Pagination ──

class PaginatedJobs(BaseModel):
    items: list[JobListOut]
    total: int
    page: int
    page_size: int


class PaginatedReports(BaseModel):
    items: list[ReportListOut]
    total: int
    page: int
    page_size: int
