import json
from datetime import datetime, timezone, timedelta
from sqlalchemy import Column, Integer, String, Text, DateTime
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
    created_at = Column(DateTime(timezone=True), default=now_cn)
