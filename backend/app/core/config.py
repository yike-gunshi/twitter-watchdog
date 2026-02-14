import os
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent  # twitter-watchdog-repo/
ENGINE_DIR = PROJECT_ROOT / "engine"
CONFIG_DIR = PROJECT_ROOT / "config"

# Config file resolution order:
#   1. WATCHDOG_CONFIG env var
#   2. ~/.claude/skills/twitter-watchdog/config/config.yaml (actual runtime config)
#   3. <repo>/config/config.yaml
#   4. <repo>/config/config.yaml.example
_SKILL_CONFIG = Path.home() / ".claude" / "skills" / "twitter-watchdog" / "config" / "config.yaml"
_REPO_CONFIG = CONFIG_DIR / "config.yaml"
_REPO_EXAMPLE = CONFIG_DIR / "config.yaml.example"

DEFAULT_CONFIG_FILE = Path(
    os.environ.get("WATCHDOG_CONFIG", "")
) if os.environ.get("WATCHDOG_CONFIG") else (
    _SKILL_CONFIG if _SKILL_CONFIG.exists()
    else _REPO_CONFIG if _REPO_CONFIG.exists()
    else _REPO_EXAMPLE
)

# CORS
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
