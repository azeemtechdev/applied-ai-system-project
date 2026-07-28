"""Central configuration for PawPal+.

Loads settings from a local ``.env`` file (if present) and the process
environment. Nothing here ever prints or logs the API key.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

try:
    # python-dotenv is optional at import time so the app still runs if it
    # is not installed yet; a missing .env simply means "no key configured".
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover - exercised only without the dependency
    pass


def _int_env(name: str, default: int) -> int:
    """Read an integer env var, falling back to a default on missing/invalid."""
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    """Immutable snapshot of PawPal+ runtime configuration."""

    gemini_api_key: str
    model: str
    max_iterations: int
    max_tasks: int

    @property
    def has_api_key(self) -> bool:
        """True when a non-empty Gemini API key is configured."""
        return bool(self.gemini_api_key.strip())


def get_settings() -> Settings:
    """Build a Settings snapshot from the environment (and .env if present)."""
    return Settings(
        gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
        model=os.getenv("PAWPAL_MODEL", "gemini-2.5-flash"),
        max_iterations=_int_env("PAWPAL_MAX_ITERATIONS", 3),
        max_tasks=_int_env("PAWPAL_MAX_TASKS", 20),
    )
