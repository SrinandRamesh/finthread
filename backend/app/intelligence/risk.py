"""Cluster risk scoring (Member 3). Contract Section 8.

Score (0-100, int, capped):
    pattern_severity      CYCLE 35 | PASS_THROUGH 30 | SCATTER_GATHER 30 | FAN_OUT 20 | FAN_IN 20
    multiple_typologies   +10 per extra distinct typology, max 20
    velocity              median hop <= 6 h: 20 | <= 24 h: 12 | <= 72 h: 5 | else/none: 0
    structuring           share of txs in [LOWER_RATIO x THRESHOLD, THRESHOLD): >=50%: 15 | >=20%: 8
    flow_through          sum(out)/sum(in) over intermediaries: >=0.9: 10 | >=0.75: 5

Only transaction ids, amounts, timestamps and pattern hits are read.
`label` and `gt_typology` are never touched here.
"""
from __future__ import annotations

from bisect import bisect_right
from datetime import datetime
from statistics import median
from typing import Any, Optional

import pandas as pd

from app.contracts import (
    TYPOLOGY_LABELS,
    ClusterAccountRole,
    DetectionOutput,
    PatternHit,
    ScoreFactor,
    ScoredCluster,
)
from app.intelligence.explain import build_explanation
from app.intelligence.formatting import format_inr, format_minutes, format_pct
from app.intelligence.typology import derive_typologies, primary_typology

SEVERITY_POINTS: dict[str, int] = {
    "CYCLE": 35,
    "PASS_THROUGH": 30,
    "SCATTER_GATHER": 30,
    "FAN_OUT": 20,
    "FAN_IN": 20,
}
MAX_POINTS = {
    "pattern_severity": 35,
    "multiple_typologies": 20,
    "velocity": 20,
    "structuring": 15,
    "flow_through": 10,
}

_DEFAULTS = {
    "REPORTING_THRESHOLD": 1_000_000,
    "STRUCTURING_LOWER_RATIO": 0.9,
    "ALERT_THRESHOLD": 40,
    "HIGH_RISK_THRESHOLD": 70,
}


def cfg_value(cfg: Any, name: str, default: Any = None) -> Any:
    """Read a setting whether Settings exposes it as ALERT_THRESHOLD or alert_threshold."""
    for key in (name, name.lower()):
        if hasattr(cfg, key):
            return getattr(cfg, key)
    if default is not None:
        return default
    return _DEFAULTS.get(name)


# ---------------------------------------------------------------- cluster building blocks
def cluster_frame(transactions: pd.DataFrame, transaction_ids: list[str]) -> pd.DataFrame:
    """The cluster's transactions in chronological order."""
    ids = set(transaction_ids)
    sub = transactions[transactions["transaction_id"].isin(ids)]
    return sub.sort_values(["timestamp", "transaction_id"], kind="stable").reset_index(drop=True)


def compute_roles(sub: pd.DataFrame, account_ids: list[str]) -> list[ClusterAccountRole]:
    """source / collector / intermediary / member with in-cluster totals.

    Accounts are listed in the order they first appear in the cluster's money trail.
    """
    in_tot: dict[str, float] = {}
    out_tot: dict[str, float] = {}
    in_cnt: dict[str, int] = {}
    out_cnt: dict[str, int] = {}
    order: list[str] = []
    seen: set[str] = set()
    for row in sub.itertuples(index=False):
        s, r, amt = row.sender, row.receiver, float(row.amount)
        out_tot[s] = out_tot.get(s, 0.0) + amt
        out_cnt[s] = out_cnt.get(s, 0) + 1
        in_tot[r] = in_tot.get(r, 0.0) + amt
        in_cnt[r] = in_cnt.get(r, 0) + 1
        for a in (s, r):
            if a not in seen:
                seen.add(a)
                order.append(a)
    for a in account_ids:           # accounts of the cluster with no in-cluster tx
        if a not in seen:
            seen.add(a)
            order.append(a)

    roles: list[ClusterAccountRole] = []
    for a in order:
        has_in, has_out = in_cnt.get(a, 0) > 0, out_cnt.get(a, 0) > 0
        if has_in and has_out:
            role = "intermediary"
        elif has_out:
            role = "source"
        elif has_in:
            role = "collector"
        else:
            role = "member"
        roles.append(
            ClusterAccountRole(
                account_id=a,
                role=role,
                total_in=round(in_tot.get(a, 0.0), 2),
                total_out=round(out_tot.get(a, 0.0), 2),
            )
        )
    return roles


def median_hop_minutes(sub: pd.DataFrame, roles: list[ClusterAccountRole]) -> Optional[float]:
    """Median minutes from an incoming cluster tx to the account's next outgoing cluster tx,
    over all intermediary accounts. None when no such pair exists."""
    intermediaries = {r.account_id for r in roles if r.role == "intermediary"}
    if not intermediaries:
        return None
    out_times: dict[str, list[pd.Timestamp]] = {a: [] for a in intermediaries}
    for row in sub.itertuples(index=False):
        if row.sender in out_times:
            out_times[row.sender].append(row.timestamp)
    for times in out_times.values():
        times.sort()
    gaps: list[float] = []
    for row in sub.itertuples(index=False):
        a = row.receiver
        if a not in out_times:
            continue
        times = out_times[a]
        i = bisect_right(times, row.timestamp)      # next outgoing strictly after the inflow
        if i < len(times):
            gaps.append((times[i] - row.timestamp).total_seconds() / 60)
    if not gaps:
        return None
    return round(float(median(gaps)), 1)


# ---------------------------------------------------------------- the five factors
def _severity_factor(primary: str) -> ScoreFactor:
    pts = SEVERITY_POINTS[primary]
    return ScoreFactor(
        "pattern_severity", pts, MAX_POINTS["pattern_severity"],
        f"Most severe pattern is {TYPOLOGY_LABELS[primary]} ({pts} of 35 points)",
    )


def _multiple_factor(typologies: list[str]) -> ScoreFactor:
    extra = len(typologies) - 1
    pts = min(MAX_POINTS["multiple_typologies"], 10 * extra)
    if extra <= 0:
        reason = "Only one typology detected, no combined-pattern uplift"
    else:
        names = ", ".join(typologies)
        reason = f"{len(typologies)} typologies combined ({names}): +10 for each of {extra} extra"
        if pts < 10 * extra:
            reason += " (capped at 20)"
    return ScoreFactor("multiple_typologies", pts, MAX_POINTS["multiple_typologies"], reason)


def _velocity_factor(hop: Optional[float]) -> ScoreFactor:
    if hop is None:
        pts, reason = 0, "No intermediary hop to time (funds were not forwarded inside the cluster)"
    elif hop <= 360:
        pts, reason = 20, f"Median hop time {format_minutes(hop)} (≤ 6 h)"
    elif hop <= 1440:
        pts, reason = 12, f"Median hop time {format_minutes(hop)} (≤ 24 h)"
    elif hop <= 4320:
        pts, reason = 5, f"Median hop time {format_minutes(hop)} (≤ 72 h)"
    else:
        pts, reason = 0, f"Median hop time {format_minutes(hop)} (slower than 72 h)"
    return ScoreFactor("velocity", pts, MAX_POINTS["velocity"], reason)


def _structuring_factor(sub: pd.DataFrame, threshold: float, lower_ratio: float) -> ScoreFactor:
    lower = lower_ratio * threshold
    n = len(sub)
    hits = int(((sub["amount"] >= lower) & (sub["amount"] < threshold)).sum()) if n else 0
    share = hits / n if n else 0.0
    if share >= 0.5:
        pts = 15
    elif share >= 0.2:
        pts = 8
    else:
        pts = 0
    reason = (
        f"{format_pct(share)} of cluster transactions ({hits} of {n}) fall between "
        f"{format_inr(lower)} and {format_inr(threshold)}, just under the reporting threshold"
    )
    return ScoreFactor("structuring", pts, MAX_POINTS["structuring"], reason)


def _flow_through_factor(roles: list[ClusterAccountRole]) -> ScoreFactor:
    inter = [r for r in roles if r.role == "intermediary"]
    total_in = sum(r.total_in for r in inter)
    total_out = sum(r.total_out for r in inter)
    if not inter or total_in <= 0:
        return ScoreFactor("flow_through", 0, MAX_POINTS["flow_through"],
                           "No intermediary accounts that received and forwarded funds")
    ratio = total_out / total_in
    if ratio >= 0.9:
        pts, band = 10, "(≥ 90%)"
    elif ratio >= 0.75:
        pts, band = 5, "(≥ 75%)"
    else:
        pts, band = 0, "(below 75%)"
    reason = (
        f"Intermediary accounts passed on {format_pct(ratio)} of the {format_inr(total_in)} "
        f"they received {band}"
    )
    return ScoreFactor("flow_through", pts, MAX_POINTS["flow_through"], reason)


def risk_level_for(score: int, cfg: Any) -> str:
    if score >= cfg_value(cfg, "HIGH_RISK_THRESHOLD"):
        return "high"
    if score >= cfg_value(cfg, "ALERT_THRESHOLD"):
        return "medium"
    return "low"


# ---------------------------------------------------------------- public entry point
def score_clusters(detection: DetectionOutput, cfg: Any) -> list[ScoredCluster]:
    """Score every RawCluster. cluster_ids are kept exactly as Member 2 assigned them."""
    threshold = float(cfg_value(cfg, "REPORTING_THRESHOLD"))
    lower_ratio = float(cfg_value(cfg, "STRUCTURING_LOWER_RATIO"))
    alert_threshold = cfg_value(cfg, "ALERT_THRESHOLD")

    hits_by_id: dict[str, PatternHit] = {h.pattern_id: h for h in detection.patterns}
    out: list[ScoredCluster] = []

    for raw in detection.clusters:
        hits = [hits_by_id[p] for p in raw.pattern_ids if p in hits_by_id]
        sub = cluster_frame(detection.transactions, raw.transaction_ids)
        if not hits or sub.empty:
            continue

        typologies = derive_typologies(hits)
        primary = primary_typology(typologies)
        roles = compute_roles(sub, raw.accounts)
        hop = median_hop_minutes(sub, roles)

        factors = [
            _severity_factor(primary),
            _multiple_factor(typologies),
            _velocity_factor(hop),
            _structuring_factor(sub, threshold, lower_ratio),
            _flow_through_factor(roles),
        ]
        score = min(100, sum(f.points for f in factors))
        total_amount = round(float(sub["amount"].sum()), 2)
        start_time: datetime = sub["timestamp"].min().to_pydatetime()
        end_time: datetime = sub["timestamp"].max().to_pydatetime()

        explanation = build_explanation(
            primary=primary,
            typologies=typologies,
            hits=hits,
            tx=sub,
            roles=roles,
            factors=factors,
            total_amount=total_amount,
            start_time=start_time,
            end_time=end_time,
            median_hop_minutes=hop,
        )
        out.append(
            ScoredCluster(
                cluster_id=raw.cluster_id,
                accounts=roles,
                transaction_ids=list(sub["transaction_id"]),
                pattern_ids=[h.pattern_id for h in hits],
                typologies=typologies,            # type: ignore[arg-type]
                primary_typology=primary,         # type: ignore[arg-type]
                risk_score=int(score),
                risk_level=risk_level_for(score, cfg),   # type: ignore[arg-type]
                alerted=score >= alert_threshold,
                score_breakdown=factors,
                explanation=explanation,
                total_amount=total_amount,
                start_time=start_time,
                end_time=end_time,
                median_hop_minutes=hop,
            )
        )
    return out
