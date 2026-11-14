"""Risk intelligence package (Member 3).

Public API called by Member 2's pipeline.py:
    score_clusters(detection, cfg)   -> list[ScoredCluster]
    build_alerts(clusters, cfg)      -> list[AlertRecord]
    compute_account_risk(clusters)   -> dict[str, AccountRisk]

STEP 2: score_clusters is real. build_alerts and compute_account_risk below are temporary
placeholders that return empty results; Step 3 replaces them with the real implementations
(alerts.py) and this import block changes accordingly.
"""
from __future__ import annotations

from typing import Any

from app.contracts import AccountRisk, AlertRecord, ScoredCluster
from app.intelligence.risk import score_clusters

__all__ = ["score_clusters", "build_alerts", "compute_account_risk"]


def build_alerts(clusters: list[ScoredCluster], cfg: Any) -> list[AlertRecord]:  # replaced in Step 3
    return []


def compute_account_risk(clusters: list[ScoredCluster]) -> dict[str, AccountRisk]:  # replaced in Step 3
    return {}
