import json
import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy import select, func, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.db import Report
from app.models.schemas import ReportOut, ReportListOut, PaginatedReports
from app.api.data import _get_output_dir

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("", response_model=PaginatedReports)
async def list_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    type: str | None = Query(None, description="Filter by report type"),
    db: AsyncSession = Depends(get_db),
):
    query = select(Report)
    count_query = select(func.count(Report.id))

    if type:
        query = query.where(Report.type == type)
        count_query = count_query.where(Report.type == type)

    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(Report.id.desc()).offset(offset).limit(page_size)
    )
    reports = result.scalars().all()

    return PaginatedReports(
        items=[
            ReportListOut(
                id=r.id,
                type=r.type,
                summary=r.summary,
                tweet_count=r.tweet_count,
                created_at=r.created_at,
            )
            for r in reports
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{report_id}", response_model=ReportOut)
async def get_report(report_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if report is None:
        raise HTTPException(404, "Report not found")
    return ReportOut(
        id=report.id,
        type=report.type,
        file_path=report.file_path,
        summary=report.summary,
        tweet_count=report.tweet_count,
        created_at=report.created_at,
    )


@router.get("/{report_id}/html", response_class=HTMLResponse)
async def get_report_html(report_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if report is None:
        raise HTTPException(404, "Report not found")

    file_path = Path(report.file_path)
    # Try the stored path directly, and also try .html sibling
    html_path = None
    if file_path.suffix == ".html" and file_path.exists():
        html_path = file_path
    else:
        candidate = file_path.with_suffix(".html")
        if candidate.exists():
            html_path = candidate

    if html_path is None or not html_path.exists():
        raise HTTPException(404, "HTML report file not found on disk")

    content = html_path.read_text(encoding="utf-8")

    # Rewrite relative image paths to use the static assets endpoint
    # images/20260214_102125/xxx.jpg -> /api/report-assets/images/20260214_102125/xxx.jpg
    content = content.replace('src="images/', 'src="/api/report-assets/images/')

    return HTMLResponse(content=content)


@router.delete("/{report_id}", status_code=204)
async def delete_report(
    report_id: int,
    delete_files: bool = Query(False, description="Also delete report files on disk"),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if report is None:
        raise HTTPException(404, "Report not found")

    # Optionally delete associated files
    if delete_files and report.file_path:
        file_path = Path(report.file_path)
        for ext in [".html", ".md"]:
            candidate = file_path.with_suffix(ext)
            if candidate.exists():
                candidate.unlink(missing_ok=True)
        if file_path.exists():
            file_path.unlink(missing_ok=True)

    await db.execute(sa_delete(Report).where(Report.id == report_id))
    await db.commit()


@router.get("/{report_id}/context")
async def get_report_context(report_id: int, db: AsyncSession = Depends(get_db)):
    """Find the analysis and raw files associated with a report via timestamp matching."""
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if report is None:
        raise HTTPException(404, "Report not found")

    # Extract timestamp from report file_path (e.g., 20260214_102355.html)
    match = re.search(r"(\d{8}_\d{6})", report.file_path or "")
    if not match:
        raise HTTPException(404, "Cannot determine report timestamp")

    report_ts = match.group(1)

    output_dir = _get_output_dir()
    analysis_dir = output_dir / "analysis"
    raw_dir = output_dir / "raw"

    # Find closest analysis file by timestamp
    analysis_file = None
    analysis_metadata = {}
    if analysis_dir.exists():
        analysis_files = sorted(analysis_dir.glob("*.json"), reverse=True)
        # Find the closest analysis file by timestamp prefix (same date ideally)
        report_date = report_ts[:8]  # YYYYMMDD
        for af in analysis_files:
            if af.stem.startswith(report_date) or af.stem <= report_ts:
                analysis_file = af.name
                try:
                    with open(af, "r", encoding="utf-8") as f:
                        adata = json.load(f)
                    analysis_metadata = adata.get("metadata", {})
                except Exception:
                    pass
                break

    # Find raw file from analysis metadata or by timestamp
    raw_file = None
    raw_metadata = {}
    source_files = analysis_metadata.get("source_files", [])
    if source_files and raw_dir.exists():
        raw_path = raw_dir / source_files[0]
        if raw_path.exists():
            raw_file = source_files[0]
            try:
                with open(raw_path, "r", encoding="utf-8") as f:
                    rdata = json.load(f)
                raw_metadata = rdata.get("metadata", {})
            except Exception:
                pass
    elif raw_dir.exists():
        # Fallback: find closest raw file
        raw_files = sorted(raw_dir.glob("*.json"), reverse=True)
        for rf in raw_files:
            if rf.stem <= report_ts:
                raw_file = rf.name
                try:
                    with open(rf, "r", encoding="utf-8") as f:
                        rdata = json.load(f)
                    raw_metadata = rdata.get("metadata", {})
                except Exception:
                    pass
                break

    return {
        "analysis_file": analysis_file,
        "raw_file": raw_file,
        "analysis_metadata": {
            "analyzed_at": analysis_metadata.get("analyzed_at", ""),
            "total_tweets": analysis_metadata.get("total_tweets", 0),
            "filtered_count": analysis_metadata.get("filtered_count", 0),
            "model": analysis_metadata.get("model", ""),
        },
        "raw_metadata": {
            "scraped_at": raw_metadata.get("scraped_at", ""),
            "followings_count": raw_metadata.get("followings_count", 0),
            "total_tweets": raw_metadata.get("total_tweets", 0),
            "api_calls": raw_metadata.get("api_calls", 0),
        },
    }
