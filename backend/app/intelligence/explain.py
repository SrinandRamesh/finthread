"""Explanation builder (Member 3).

STEP 2 PLACEHOLDER: headline, a factual one-line summary, bullets per scored factor and the
disclaimer are real; the per-typology narrative and the evidence list arrive in Step 3,
which replaces this file completely. The function signature is final.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

import pandas as pd

from app.contracts import (
    DISCLAIMER,
    TYPOLOGY_LABELS,
    ClusterAccountRole,
    Explanation,
    PatternHit,
    ScoreFactor,
)
from app.intelligence.formatting import format_dt, format_inr


def build_explanation(
    *,
    primary: str,
    typologies: list[str],
    hits: list[PatternHit],
    tx: pd.DataFrame,
    roles: list[ClusterAccountRole],
    factors: list[ScoreFactor],
    total_amount: float,
    start_time: datetime,
    end_time: datetime,
    median_hop_minutes: Optional[float],
) -> Explanation:
    headline = f"{TYPOLOGY_LABELS[primary]} across {len(roles)} accounts · {format_inr(total_amount)}"
    summary = (
        f"{format_inr(total_amount)} moved across {len(roles)} accounts in {len(tx)} transactions "
        f"between {format_dt(start_time)} and {format_dt(end_time)}."
    )
    bullets = [f.reason for f in factors if f.points > 0]
    return Explanation(
        headline=headline,
        summary=summary,
        bullet_points=bullets,
        evidence=[],
        disclaimer=DISCLAIMER,
    )
