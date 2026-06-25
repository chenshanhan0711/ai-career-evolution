from __future__ import annotations

import os
import platform
from pathlib import Path
from typing import Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_NAME = "ai_career.db"
LINUX_SYSTEM_DATA_DIR = Path("/var/lib/ai-career-viz")


def resolve_database_path(
    system_name: str | None = None,
    environ: Mapping[str, str] | None = None,
    project_root: Path | None = None,
) -> Path:
    """Resolve the SQLite path without touching the filesystem."""
    env = os.environ if environ is None else environ
    explicit_path = env.get("APP_DB_PATH")
    if explicit_path:
        return Path(explicit_path).expanduser().resolve()

    current_system = system_name or platform.system()
    root = project_root or PROJECT_ROOT

    if current_system in {"Darwin", "Windows"}:
        return (root / DATABASE_NAME).resolve()

    if current_system == "Linux":
        data_home = env.get("XDG_DATA_HOME")
        if data_home:
            return (Path(data_home).expanduser() / "ai-career-viz" / DATABASE_NAME).resolve()
        return LINUX_SYSTEM_DATA_DIR / DATABASE_NAME

    return (root / DATABASE_NAME).resolve()


def get_database_path() -> Path:
    """
    Return a writable database path.

    Linux deployments target /var/lib by default. If the service account cannot
    create that directory, a user-level XDG-compatible data directory is used.
    """
    selected = resolve_database_path()
    try:
        selected.parent.mkdir(parents=True, exist_ok=True)
        target = selected if selected.exists() else selected.parent
        if os.access(target, os.W_OK):
            return selected
    except OSError:
        pass

    fallback = Path.home() / ".local" / "share" / "ai-career-viz" / DATABASE_NAME
    fallback.parent.mkdir(parents=True, exist_ok=True)
    return fallback


def describe_runtime() -> str:
    system_name = platform.system()
    mode = "本地模式" if system_name in {"Darwin", "Windows"} else "服务器模式"
    return f"{mode} · {system_name} · {get_database_path()}"
