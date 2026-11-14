"""In-memory holder for the current AnalysisResult.
Thread-safe via a threading.Lock."""
from __future__ import annotations

import threading
from typing import Optional

from app.contracts import AnalysisResult

_lock = threading.Lock()
_current_result: Optional[AnalysisResult] = None


def get_current_result() -> Optional[AnalysisResult]:
    with _lock:
        return _current_result


def set_current_result(result: AnalysisResult) -> None:
    global _current_result
    with _lock:
        _current_result = result
