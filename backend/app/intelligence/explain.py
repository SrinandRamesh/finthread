"""Explanation builder (Member 3). Contract Section 8.

Deterministic templates built only from real evidence: account ids, transaction ids,
amounts and timestamps of the cluster. Nothing is invented and ground-truth columns are
never read.
"""
from __future__ import annotations

from bisect import bisect_right
from datetime import datetime
from typing import Optional

import pandas as pd

from app.contracts import (
    DISCLAIMER,
    TYPOLOGY_LABELS,
    ClusterAccountRole,
    EvidenceItem,
    Explanation,
    PatternHit,
    ScoreFactor,
)
from app.intelligence.formatting import format_dt, format_inr, format_minutes, format_pct

MAX_EVIDENCE = 25


def _ts(value) -> datetime:
    return value.to_pydatetime() if hasattr(value, "to_pydatetime") else value


def _chain(accounts: list[str], limit: int = 6) -> str:
    if len(accounts) <= limit:
        return " → ".join(accounts)
    return " → ".join(accounts[:3] + ["…"] + accounts[-2:])


def _best_hit(hits: list[PatternHit], pattern_type: str) -> Optional[PatternHit]:
    same = [h for h in hits if h.pattern_type == pattern_type]
    if not same:
        return None
    return max(same, key=lambda h: (len(h.transaction_ids), h.total_amount))


def _span(start: datetime, end: datetime) -> str:
    return format_minutes((end - start).total_seconds() / 60)


# ---------------------------------------------------------------- narratives
def _pass_through_story(hit: PatternHit, tx: pd.DataFrame) -> str:
    rows = tx.set_index("transaction_id")
    ids = [t for t in hit.transaction_ids if t in rows.index]
    first = rows.loc[ids[0]] if ids else None
    accounts = hit.accounts
    ratio = hit.metrics.get("flow_through_ratio")
    hop = hit.metrics.get("median_hop_minutes")
    parts = []
    if first is not None:
        parts.append(
            f"{format_inr(first['amount'])} entered {accounts[1] if len(accounts) > 1 else accounts[0]} "
            f"on {format_dt(_ts(first['timestamp']))} and moved through {len(accounts)} accounts "
            f"({_chain(accounts)}) in {_span(hit.start_time, hit.end_time)}."
        )
    detail = []
    if ratio is not None and ratio >= 0.5:
        detail.append(f"{format_pct(ratio)} of the first transfer reached the last account")
    if hop is not None:
        detail.append(f"each hop took a median {format_minutes(hop)}")
    if detail:
        parts.append(" and ".join(detail).capitalize() + ".")
    return " ".join(parts)


def _cycle_story(hit: PatternHit) -> str:
    accounts = hit.accounts
    start = accounts[0]
    middle = accounts[1:]
    retention = hit.metrics.get("amount_retention")
    shaved = f", with {format_pct(1 - retention)} shaved along the way" if retention is not None else ""
    return (
        f"Funds left {start} and returned to it after passing through {', '.join(middle)} "
        f"within {_span(hit.start_time, hit.end_time)} ({len(accounts)}-account cycle{shaved})."
    )


def _fan_in_story(hit: PatternHit) -> str:
    n = int(hit.metrics.get("counterparty_count", len(hit.accounts) - 1))
    return (
        f"{hit.focal_account} received {format_inr(hit.total_amount)} from {n} different accounts "
        f"within {_span(hit.start_time, hit.end_time)} "
        f"({format_dt(hit.start_time)} – {format_dt(hit.end_time)})."
    )


def _fan_out_story(hit: PatternHit) -> str:
    n = int(hit.metrics.get("counterparty_count", len(hit.accounts) - 1))
    return (
        f"{hit.focal_account} sent {format_inr(hit.total_amount)} to {n} different accounts "
        f"within {_span(hit.start_time, hit.end_time)} "
        f"({format_dt(hit.start_time)} – {format_dt(hit.end_time)})."
    )


def _scatter_gather_story(hits: list[PatternHit]) -> str:
    fo = _best_hit(hits, "FAN_OUT")
    fi = _best_hit(hits, "FAN_IN")
    if not fo or not fi:
        return ""
    mules = {a for a in fo.accounts if a != fo.focal_account} & {a for a in fi.accounts if a != fi.focal_account}
    return (
        f"{fo.focal_account} split {format_inr(fo.total_amount)} across "
        f"{len({a for a in fo.accounts if a != fo.focal_account})} accounts, and {len(mules)} of them "
        f"then sent funds on to {fi.focal_account} between {format_dt(fo.start_time)} and "
        f"{format_dt(fi.end_time)}."
    )


def _summary(primary: str, hits: list[PatternHit], tx: pd.DataFrame, roles: list[ClusterAccountRole],
             total_amount: float, start_time: datetime, end_time: datetime) -> str:
    story = ""
    if primary == "PASS_THROUGH":
        h = _best_hit(hits, "PASS_THROUGH")
        story = _pass_through_story(h, tx) if h else ""
    elif primary == "CYCLE":
        h = _best_hit(hits, "CYCLE")
        story = _cycle_story(h) if h else ""
    elif primary == "SCATTER_GATHER":
        story = _scatter_gather_story(hits)
    elif primary == "FAN_OUT":
        h = _best_hit(hits, "FAN_OUT")
        story = _fan_out_story(h) if h else ""
    elif primary == "FAN_IN":
        h = _best_hit(hits, "FAN_IN")
        story = _fan_in_story(h) if h else ""
    overall = (
        f"In total the cluster moved {format_inr(total_amount)} across {len(roles)} accounts in "
        f"{len(tx)} transactions between {format_dt(start_time)} and {format_dt(end_time)}."
    )
    return f"{story} {overall}".strip()


# ---------------------------------------------------------------- evidence
def _evidence(hits: list[PatternHit], tx: pd.DataFrame) -> list[EvidenceItem]:
    """Up to 25 chronological evidence items with short factual notes."""
    if tx.empty:
        return []
    notes: dict[str, list[str]] = {}

    for h in hits:
        ids = h.transaction_ids
        if h.pattern_type == "CYCLE" and ids:
            notes.setdefault(ids[0], []).append("opening hop of cycle")
            notes.setdefault(ids[-1], []).append(f"closing hop of cycle back to {h.accounts[0]}")
        elif h.pattern_type == "FAN_IN":
            n = len(ids)
            for i, t in enumerate(ids, 1):
                notes.setdefault(t, []).append(f"{i} of {n} inflows to {h.focal_account}")
        elif h.pattern_type == "FAN_OUT":
            n = len(ids)
            for i, t in enumerate(ids, 1):
                notes.setdefault(t, []).append(f"{i} of {n} outflows from {h.focal_account}")

    # forwarding notes: for each transaction into an account, how much of it left again and how fast
    out_by_sender: dict[str, list[tuple]] = {}
    for row in tx.itertuples(index=False):
        out_by_sender.setdefault(row.sender, []).append((row.timestamp, float(row.amount)))
    for lst in out_by_sender.values():
        lst.sort()
    for row in tx.itertuples(index=False):
        outs = out_by_sender.get(row.receiver)
        if not outs:
            continue
        times = [o[0] for o in outs]
        i = bisect_right(times, row.timestamp)
        if i < len(outs):
            nxt_ts, nxt_amt = outs[i]
            minutes = (nxt_ts - row.timestamp).total_seconds() / 60
            if minutes <= 24 * 60 and row.amount > 0:
                notes.setdefault(row.transaction_id, []).append(
                    f"{row.receiver} forwarded {format_pct(min(nxt_amt / float(row.amount), 9.99))} "
                    f"within {format_minutes(minutes)}"
                )

    items: list[EvidenceItem] = []
    flagged = [r for r in tx.itertuples(index=False) if r.transaction_id in notes]
    rest = [r for r in tx.itertuples(index=False) if r.transaction_id not in notes]
    for row in (flagged + rest)[:MAX_EVIDENCE]:
        items.append(
            EvidenceItem(
                transaction_id=str(row.transaction_id),
                sender=str(row.sender),
                receiver=str(row.receiver),
                amount=round(float(row.amount), 2),
                timestamp=_ts(row.timestamp),
                note="; ".join(notes.get(row.transaction_id, [])) or "part of the cluster's money trail",
            )
        )
    items.sort(key=lambda e: (e.timestamp, e.transaction_id))
    return items


# ---------------------------------------------------------------- public
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
    summary = _summary(primary, hits, tx, roles, total_amount, start_time, end_time)
    bullets = [f.reason for f in factors if f.points > 0]
    if len(typologies) > 1:
        others = [TYPOLOGY_LABELS[t] for t in typologies if t != primary]
        bullets.append("Also matches: " + ", ".join(others))
    return Explanation(
        headline=headline,
        summary=summary,
        bullet_points=bullets,
        evidence=_evidence(hits, tx),
        disclaimer=DISCLAIMER,
    )
