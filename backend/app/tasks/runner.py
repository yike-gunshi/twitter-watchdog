"""Background task runner.

When a Job is created via the API, an asyncio task is spawned here.
It updates the Job row's status, log, result_file, and timestamps in real-time.
"""

import asyncio
import traceback
from datetime import datetime, timezone, timedelta

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session
from app.models.db import Job, Report
from app.services.watchdog_service import WatchdogService, LogCapture

TZ_CN = timezone(timedelta(hours=8))


def _now():
    return datetime.now(TZ_CN)


async def _run_in_thread(func, *args, **kwargs):
    """Run a blocking function in a thread so we don't block the event loop."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: func(*args, **kwargs))


async def _update_job(job_id: int, **fields):
    """Update a job row with the given fields."""
    async with async_session() as session:
        await session.execute(
            update(Job).where(Job.id == job_id).values(**fields)
        )
        await session.commit()


async def _poll_log(job_id: int, log_buf: LogCapture, stop_event: asyncio.Event):
    """Periodically flush log_buf contents to the Job DB row."""
    while not stop_event.is_set():
        await asyncio.sleep(2)
        text = log_buf.getvalue()
        if text:
            await _update_job(job_id, log=text)


async def _save_report(result_file: str, report_type: str, log_text: str):
    """Create a Report row if a report file was produced."""
    if not result_file:
        return
    # Extract a short summary from the log (first meaningful lines)
    summary_lines = []
    for line in log_text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("===") and not stripped.startswith("["):
            summary_lines.append(stripped)
        if len(summary_lines) >= 5:
            break
    summary = "\n".join(summary_lines) if summary_lines else ""

    # Count tweets from log
    tweet_count = 0
    for line in log_text.splitlines():
        if "条" in line and ("关注" in line or "热门" in line or "总计" in line):
            import re
            nums = re.findall(r"(\d+)\s*条", line)
            for n in nums:
                tweet_count += int(n)
            break

    async with async_session() as session:
        report = Report(
            type=report_type,
            file_path=result_file,
            summary=summary,
            tweet_count=tweet_count,
        )
        session.add(report)
        await session.commit()


async def execute_job(job_id: int, job_type: str, params: dict):
    """Entry point called via asyncio.create_task when a job is created."""
    service = WatchdogService()
    log_buf = LogCapture()
    stop_event = asyncio.Event()

    # Mark running
    await _update_job(job_id, status="running", started_at=_now())

    # Start log polling coroutine
    poll_task = asyncio.create_task(_poll_log(job_id, log_buf, stop_event))

    # Extract extra params to pass through to the service layer
    extra = {}
    for key in ("style", "custom_prompt", "max_tweets", "min_views"):
        if key in params:
            extra[key] = params[key]

    # Map report_type/report_date to daily/weekly/monthly params
    report_type_param = params.get("report_type")
    report_date = params.get("report_date")
    daily_val = params.get("daily")
    weekly_val = params.get("weekly")
    monthly_val = params.get("monthly")
    if report_type_param and report_date:
        if report_type_param == "daily":
            daily_val = report_date
        elif report_type_param == "weekly":
            weekly_val = report_date
        elif report_type_param == "monthly":
            monthly_val = report_date

    try:
        if job_type == "scrape":
            result_file, log_text = await _run_in_thread(
                service.run_scrape,
                hours_ago=params.get("hours_ago"),
                log_buf=log_buf,
                **extra,
            )
        elif job_type == "analyze":
            result_file, log_text = await _run_in_thread(
                service.run_analyze,
                source=params.get("source"),
                hours_ago=params.get("hours_ago"),
                log_buf=log_buf,
                **extra,
            )
        elif job_type == "report":
            result_file, log_text = await _run_in_thread(
                service.run_report,
                source=params.get("source"),
                daily=daily_val,
                weekly=weekly_val,
                monthly=monthly_val,
                log_buf=log_buf,
                **extra,
            )
            # Determine report type
            report_type = "single"
            if daily_val:
                report_type = "daily"
            elif weekly_val:
                report_type = "weekly"
            elif monthly_val:
                report_type = "monthly"
            await _save_report(result_file, report_type, log_text)
        elif job_type == "pipeline":
            result_file, log_text = await _run_in_thread(
                service.run_pipeline,
                hours_ago=params.get("hours_ago"),
                log_buf=log_buf,
                **extra,
            )
            await _save_report(result_file, "single", log_text)
        else:
            raise ValueError(f"Unknown job type: {job_type}")

        # Stop log polling and do final update
        stop_event.set()
        await poll_task

        await _update_job(
            job_id,
            status="completed",
            log=log_text,
            result_file=result_file,
            finished_at=_now(),
        )

    except Exception as exc:
        stop_event.set()
        await poll_task

        tb = traceback.format_exc()
        final_log = log_buf.getvalue() + "\n\n" + tb
        await _update_job(
            job_id,
            status="failed",
            log=final_log,
            error=str(exc),
            finished_at=_now(),
        )
