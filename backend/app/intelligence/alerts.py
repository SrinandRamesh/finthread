"""Alerts and account risk (Member 3). Contract Section 8."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from app.contracts import AccountRisk, AlertRecord, ScoredCluster
from app.intelligence.typology import SEVERITY_ORDER


def build_alerts(clusters: list[ScoredCluster], cfg: Any) -> list[AlertRecord]:
    """One alert per alerted cluster, ids AL-0001… by risk score (desc), then amount (desc)."""
    alerted = [c for c in clusters if c.alerted]
    alerted.sort(key=lambda c: (-c.risk_score, -c.total_amount, c.cluster_id))
    now = datetime.now().replace(microsecond=0)
    return [
        AlertRecord(
            alert_id=f"AL-{i:04d}",
            cluster_id=c.cluster_id,
            risk_score=c.risk_score,
            risk_level=c.risk_level,
            primary_typology=c.primary_typology,
            typologies=list(c.typologies),
            headline=c.explanation.headline,
            created_at=now,
            account_count=len(c.accounts),
            transaction_count=len(c.transaction_ids),
            total_amount=c.total_amount,
        )
        for i, c in enumerate(alerted, 1)
    ]


def compute_account_risk(clusters: list[ScoredCluster]) -> dict[str, AccountRisk]:
    """Max cluster score per account, its level, union of typologies and cluster ids."""
    out: dict[str, AccountRisk] = {}
    for c in clusters:
        for role in c.accounts:
            a = role.account_id
            cur = out.get(a)
            if cur is None:
                out[a] = AccountRisk(
                    risk_score=c.risk_score,
                    risk_level=c.risk_level,
                    typologies=list(c.typologies),
                    cluster_ids=[c.cluster_id],
                )
                continue
            if c.risk_score > (cur.risk_score or 0):
                cur.risk_score = c.risk_score
                cur.risk_level = c.risk_level
            for t in c.typologies:
                if t not in cur.typologies:
                    cur.typologies.append(t)
            cur.typologies.sort(key=SEVERITY_ORDER.index)
            if c.cluster_id not in cur.cluster_ids:
                cur.cluster_ids.append(c.cluster_id)
    return out
