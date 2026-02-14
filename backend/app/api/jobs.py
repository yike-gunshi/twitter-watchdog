import asyncio
import json
import threading

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.db import Job
from app.models.schemas import JobCreate, JobOut, JobListOut, PaginatedJobs
from app.tasks.runner import execute_job

router = APIRouter(prefix="/jobs", tags=["jobs"])

VALID_JOB_TYPES = {"scrape", "analyze", "report", "pipeline"}

# Global dict to track cancellation events for running jobs
_cancel_events: dict[int, threading.Event] = {}


@router.post("", response_model=JobOut, status_code=201)
async def create_job(body: JobCreate, db: AsyncSession = Depends(get_db)):
    if body.type not in VALID_JOB_TYPES:
        raise HTTPException(400, f"Invalid job type. Must be one of: {VALID_JOB_TYPES}")

    params = body.params or {}
    job = Job(
        type=body.type,
        status="pending",
        params=json.dumps(params, ensure_ascii=False),
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Launch background execution
    asyncio.create_task(execute_job(job.id, body.type, params))

    return _job_to_out(job)


@router.get("", response_model=PaginatedJobs)
async def list_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    # Count
    count_result = await db.execute(select(func.count(Job.id)))
    total = count_result.scalar_one()

    # Fetch page (most recent first)
    offset = (page - 1) * page_size
    result = await db.execute(
        select(Job).order_by(Job.id.desc()).offset(offset).limit(page_size)
    )
    jobs = result.scalars().all()

    return PaginatedJobs(
        items=[
            JobListOut(
                id=j.id,
                type=j.type,
                status=j.status,
                started_at=j.started_at,
                finished_at=j.finished_at,
                created_at=j.created_at,
            )
            for j in jobs
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{job_id}", response_model=JobOut)
async def get_job(job_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(404, "Job not found")
    return _job_to_out(job)


@router.delete("/{job_id}", status_code=204)
async def delete_job(job_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(404, "Job not found")
    await db.execute(delete(Job).where(Job.id == job_id))
    await db.commit()


@router.post("/{job_id}/cancel")
async def cancel_job(job_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(404, "Job not found")
    if job.status not in ("pending", "running"):
        raise HTTPException(400, f"Cannot cancel job with status '{job.status}'")

    # Signal cancellation if running
    cancel_event = _cancel_events.get(job_id)
    if cancel_event:
        cancel_event.set()

    # Mark as cancelled in DB
    job.status = "cancelled"
    from datetime import datetime, timezone, timedelta
    job.finished_at = datetime.now(timezone(timedelta(hours=8)))
    await db.commit()
    await db.refresh(job)
    return _job_to_out(job)


def _job_to_out(job: Job) -> JobOut:
    return JobOut(
        id=job.id,
        type=job.type,
        status=job.status,
        params=job.get_params(),
        log=job.log,
        result_file=job.result_file,
        error=job.error,
        started_at=job.started_at,
        finished_at=job.finished_at,
        created_at=job.created_at,
    )
