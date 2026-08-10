"""Debug helpers controlled by WAKU_DEBUG.

Use debug_break() instead of raw pdb.set_trace() so checked-in breakpoints stay
silent until the user explicitly starts Waku in debug mode.
"""

from __future__ import annotations

import os


def debug_enabled() -> bool:
    return os.getenv("WAKU_DEBUG", "").lower() in ("1", "true", "yes", "on")


def debug_break() -> None:
    if not debug_enabled():
        return
    import pdb

    pdb.set_trace()
