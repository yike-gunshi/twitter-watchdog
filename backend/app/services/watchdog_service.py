"""Service layer that wraps the engine's TwitterWatchdog class.

Provides a thin adapter so the API/task layer can call engine methods
without knowing CLI details. All engine stdout is captured as log text.
"""

import sys
import types
import threading
from pathlib import Path

from app.core.config import ENGINE_DIR, DEFAULT_CONFIG_FILE

# Add engine directory to sys.path so we can import it
if str(ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_DIR))

from twitter_watchdog import TwitterWatchdog  # noqa: E402


def _make_args(**kwargs):
    """Build a simple namespace that looks like argparse output."""
    return types.SimpleNamespace(**kwargs)


class LogCapture:
    """Thread-safe stdout capture that allows concurrent reading."""

    def __init__(self):
        self._lock = threading.Lock()
        self._chunks: list[str] = []

    def write(self, s: str):
        if s:
            with self._lock:
                self._chunks.append(s)

    def flush(self):
        pass

    def getvalue(self) -> str:
        with self._lock:
            return "".join(self._chunks)


class WatchdogService:
    """Stateless helper that creates a fresh TwitterWatchdog per invocation."""

    def __init__(self, config_file: str | None = None):
        self.config_file = config_file or str(DEFAULT_CONFIG_FILE)

    def _new_engine(self, report_only: bool = False, config_overrides: dict | None = None, **cli_overrides) -> TwitterWatchdog:
        args = _make_args(**cli_overrides) if cli_overrides else None
        engine = TwitterWatchdog(
            config_file=self.config_file,
            cli_args=args,
            report_only=report_only,
        )
        # Apply runtime config overrides (style, custom_prompt, etc.)
        if config_overrides:
            if "style" in config_overrides:
                engine.config.setdefault("ai_summary", {})["style"] = config_overrides["style"]
            if "custom_prompt" in config_overrides:
                engine.config.setdefault("ai_summary", {})["custom_prompt"] = config_overrides["custom_prompt"]
            if "min_views" in config_overrides:
                engine.config.setdefault("trending_search", {})["min_views"] = config_overrides["min_views"]
            if "max_tweets" in config_overrides:
                engine.config.setdefault("trending_search", {})["max_tweets"] = config_overrides["max_tweets"]
        return engine

    # ── Capture stdout into a LogCapture while running ──

    @staticmethod
    def _capture(func, log_buf: LogCapture | None = None, *args, **kwargs):
        """Run *func* while capturing stdout. Returns (result, log_text).
        If log_buf is provided, uses it (allows external polling).
        """
        buf = log_buf or LogCapture()
        old_stdout = sys.stdout
        sys.stdout = buf
        try:
            result = func(*args, **kwargs)
        finally:
            sys.stdout = old_stdout
        return result, buf.getvalue()

    # ── Public methods ──

    def _build_config_overrides(self, params: dict) -> dict:
        """Extract config overrides from params dict."""
        cfg = {}
        if params.get("style"):
            cfg["style"] = params["style"]
        if params.get("custom_prompt"):
            cfg["custom_prompt"] = params["custom_prompt"]
        if params.get("max_tweets") is not None:
            cfg["max_tweets"] = params["max_tweets"]
        if params.get("min_views") is not None:
            cfg["min_views"] = params["min_views"]
        return cfg

    def run_scrape(
        self,
        hours_ago: int | None = None,
        log_buf: LogCapture | None = None,
        **extra_params,
    ) -> tuple[str | None, str]:
        """Run Layer 1 scrape. Returns (result_file_path, log_text)."""
        overrides = {}
        if hours_ago is not None:
            overrides["hours_ago"] = hours_ago
        cfg = self._build_config_overrides(extra_params)
        engine = self._new_engine(config_overrides=cfg, **overrides)
        return self._capture(engine.run_scrape, log_buf)

    def run_analyze(
        self,
        source: str | None = None,
        hours_ago: int | None = None,
        log_buf: LogCapture | None = None,
        **extra_params,
    ) -> tuple[str | None, str]:
        """Run Layer 2 analysis. Returns (result_file_path, log_text)."""
        overrides = {}
        if hours_ago is not None:
            overrides["hours_ago"] = hours_ago
        cfg = self._build_config_overrides(extra_params)
        engine = self._new_engine(config_overrides=cfg, **overrides)
        return self._capture(engine.run_analyze, log_buf, source=source)

    def run_report(
        self,
        source: str | None = None,
        daily: str | None = None,
        weekly: str | None = None,
        monthly: str | None = None,
        log_buf: LogCapture | None = None,
        **extra_params,
    ) -> tuple[str | None, str]:
        """Run Layer 3 report generation. Returns (result_file_path, log_text)."""
        cfg = self._build_config_overrides(extra_params)
        engine = self._new_engine(report_only=True, config_overrides=cfg)
        return self._capture(
            engine.run_report,
            log_buf,
            source=source,
            daily=daily,
            weekly=weekly,
            monthly=monthly,
        )

    def run_pipeline(
        self,
        hours_ago: int | None = None,
        log_buf: LogCapture | None = None,
        **extra_params,
    ) -> tuple[None, str]:
        """Run full pipeline (scrape -> analyze -> report). Returns (None, log_text)."""
        overrides = {}
        if hours_ago is not None:
            overrides["hours_ago"] = hours_ago
        cfg = self._build_config_overrides(extra_params)
        engine = self._new_engine(config_overrides=cfg, **overrides)
        return self._capture(engine.run_pipeline, log_buf)
