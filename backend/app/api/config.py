import json

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.db import Config
from app.models.schemas import ConfigOut, ConfigUpdate

router = APIRouter(prefix="/config", tags=["config"])


async def _get_or_create_config(db: AsyncSession) -> Config:
    """Return the single config row, creating it with defaults if absent."""
    result = await db.execute(select(Config).limit(1))
    cfg = result.scalar_one_or_none()
    if cfg is None:
        cfg = Config(
            twitter_username="",
            custom_accounts="[]",
            style="standard",
            custom_prompt="",
            filter_keywords="[]",
            push_config=json.dumps({
                "telegram_bot_token": "",
                "telegram_chat_id": "",
                "min_engagement": 0,
                "hours_ago": 8,
            }),
        )
        db.add(cfg)
        await db.commit()
        await db.refresh(cfg)
    return cfg


def _row_to_out(cfg: Config) -> ConfigOut:
    push = cfg.get_push_config()
    return ConfigOut(
        id=cfg.id,
        twitter_username=cfg.twitter_username,
        custom_accounts=cfg.get_custom_accounts(),
        style=cfg.style,
        custom_prompt=cfg.custom_prompt,
        keywords=cfg.get_filter_keywords(),
        min_engagement=push.get("min_engagement", 0),
        hours_ago=push.get("hours_ago", 8),
        telegram_bot_token=push.get("telegram_bot_token", ""),
        telegram_chat_id=push.get("telegram_chat_id", ""),
        updated_at=cfg.updated_at,
    )


@router.get("", response_model=ConfigOut)
async def get_config(db: AsyncSession = Depends(get_db)):
    cfg = await _get_or_create_config(db)
    return _row_to_out(cfg)


@router.put("", response_model=ConfigOut)
async def update_config(body: ConfigUpdate, db: AsyncSession = Depends(get_db)):
    cfg = await _get_or_create_config(db)

    if body.twitter_username is not None:
        cfg.twitter_username = body.twitter_username
    if body.custom_accounts is not None:
        cfg.custom_accounts = json.dumps(body.custom_accounts, ensure_ascii=False)
    if body.style is not None:
        cfg.style = body.style
    if body.custom_prompt is not None:
        cfg.custom_prompt = body.custom_prompt
    if body.keywords is not None:
        cfg.filter_keywords = json.dumps(body.keywords, ensure_ascii=False)

    # Update push_config fields
    push = cfg.get_push_config()
    if body.min_engagement is not None:
        push["min_engagement"] = body.min_engagement
    if body.hours_ago is not None:
        push["hours_ago"] = body.hours_ago
    if body.telegram_bot_token is not None:
        push["telegram_bot_token"] = body.telegram_bot_token
    if body.telegram_chat_id is not None:
        push["telegram_chat_id"] = body.telegram_chat_id
    cfg.push_config = json.dumps(push, ensure_ascii=False)

    await db.commit()
    await db.refresh(cfg)
    return _row_to_out(cfg)
