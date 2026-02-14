from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import CORS_ORIGINS, DEFAULT_CONFIG_FILE
from app.core.database import init_db
from app.api.config import router as config_router
from app.api.jobs import router as jobs_router
from app.api.reports import router as reports_router
from app.api.data import router as data_router
from app.api.tweets import router as tweets_router, author_router as authors_router


def _resolve_reports_dir() -> Path | None:
    """Resolve the reports output directory from config."""
    import yaml
    try:
        with open(DEFAULT_CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        output_dir = Path(cfg.get("output", {}).get(
            "directory",
            str(Path.home() / ".claude" / "skills" / "twitter-watchdog" / "output"),
        ))
        reports_dir = output_dir / "reports"
        if reports_dir.exists():
            return reports_dir
    except Exception:
        pass
    # Fallback
    fallback = Path.home() / ".claude" / "skills" / "twitter-watchdog" / "output" / "reports"
    if fallback.exists():
        return fallback
    return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables
    await init_db()
    yield
    # Shutdown: nothing to clean up


app = FastAPI(
    title="Twitter Watchdog API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all routes under /api
app.include_router(config_router, prefix="/api")
app.include_router(jobs_router, prefix="/api")
app.include_router(reports_router, prefix="/api")
app.include_router(data_router, prefix="/api")
app.include_router(tweets_router)
app.include_router(authors_router)

# Mount report assets (images) as static files
_reports_dir = _resolve_reports_dir()
if _reports_dir:
    app.mount(
        "/api/report-assets",
        StaticFiles(directory=str(_reports_dir)),
        name="report-assets",
    )


@app.get("/api/health")
async def health():
    return {"status": "ok"}
