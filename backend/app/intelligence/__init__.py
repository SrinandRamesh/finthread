"""Risk intelligence package (Member 3).

Public API called by Member 2's pipeline.py:
    score_clusters(detection, cfg)   -> list[ScoredCluster]
    build_alerts(clusters, cfg)      -> list[AlertRecord]
    compute_account_risk(clusters)   -> dict[str, AccountRisk]
"""
from __future__ import annotations

from app.intelligence.alerts import build_alerts, compute_account_risk
from app.intelligence.risk import score_clusters

__all__ = ["score_clusters", "build_alerts", "compute_account_risk"]
