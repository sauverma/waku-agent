"""Debug helpers controlled by WAKU_DEBUG."""

from __future__ import annotations

import os


def debug_enabled() -> bool:
    return os.getenv("WAKU_DEBUG", "").lower() in ("1", "true", "yes", "on")
