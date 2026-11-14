"""Fan-in and Fan-out detection algorithms.
Follows PROJECT_CONTRACT.md Section 6."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import List, Tuple

import networkx as nx
import numpy as np
import pandas as pd

from app.config import Settings
from app.contracts import PatternHit


def _merge_intervals(intervals: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    """Merge overlapping index intervals [start_idx, end_idx]."""
    if not intervals:
        return []

    intervals.sort(key=lambda x: (x[0], x[1]))
    merged = [intervals[0]]

    for current in intervals[1:]:
        prev_start, prev_end = merged[-1]
        cur_start, cur_end = current

        # Overlapping or contiguous intervals
        if cur_start <= prev_end + 1:
            merged[-1] = (prev_start, max(prev_end, cur_end))
        else:
            merged.append(current)

    return merged


def detect_fan_in(
    df: pd.DataFrame,
    G: nx.MultiDiGraph,
    cfg: Settings,
) -> list[PatternHit]:
    """Detect FAN_IN patterns.
    For each account with >= FAN_MIN_COUNTERPARTIES distinct senders overall:
    sort incoming transactions by time; slide a window of FAN_WINDOW_HOURS;
    whenever distinct senders in the window >= FAN_MIN_COUNTERPARTIES, mark the window;
    merge overlapping marked windows of the same account into one hit.
    focal_account = receiver; evidence = incoming transactions in merged window;
    accounts = [focal] + senders.
    Metrics: counterparty_count, window_hours, avg_amount, amount_cv.
    """
    if df.empty:
        return []

    window_delta = timedelta(hours=cfg.FAN_WINDOW_HOURS)
    min_counterparties = cfg.FAN_MIN_COUNTERPARTIES

    # Group incoming transactions by receiver
    # Each item: (tx_id, sender, amount, timestamp)
    incoming_by_receiver = defaultdict(list)
    for _, row in df.iterrows():
        incoming_by_receiver[str(row["receiver"])].append(
            {
                "tx_id": str(row["transaction_id"]),
                "counterparty": str(row["sender"]),
                "amount": float(row["amount"]),
                "timestamp": row["timestamp"],
            }
        )

    hits: list[PatternHit] = []

    for receiver, txs in incoming_by_receiver.items():
        distinct_overall = {t["counterparty"] for t in txs}
        if len(distinct_overall) < min_counterparties:
            continue

        # Sort incoming transactions by time
        txs.sort(key=lambda x: x["timestamp"])
        n = len(txs)

        # Sliding window with two pointers [left, right]
        marked_intervals: List[Tuple[int, int]] = []
        left = 0
        counterparty_counts: dict[str, int] = defaultdict(int)

        for right in range(n):
            counterparty_counts[txs[right]["counterparty"]] += 1

            while txs[right]["timestamp"] - txs[left]["timestamp"] > window_delta:
                cp = txs[left]["counterparty"]
                counterparty_counts[cp] -= 1
                if counterparty_counts[cp] == 0:
                    del counterparty_counts[cp]
                left += 1

            if len(counterparty_counts) >= min_counterparties:
                marked_intervals.append((left, right))

        if not marked_intervals:
            continue

        # Merge overlapping marked windows of the same account into one hit
        merged_intervals = _merge_intervals(marked_intervals)

        for m_start, m_end in merged_intervals:
            evidence_txs = txs[m_start : m_end + 1]
            if not evidence_txs:
                continue

            unique_senders = sorted({t["counterparty"] for t in evidence_txs})
            if len(unique_senders) < min_counterparties:
                continue

            tx_ids = [t["tx_id"] for t in evidence_txs]
            amounts = np.array([t["amount"] for t in evidence_txs], dtype=float)
            start_time = evidence_txs[0]["timestamp"]
            end_time = evidence_txs[-1]["timestamp"]
            total_amount = float(np.sum(amounts))

            # Metrics
            span_seconds = max(0.0, (end_time - start_time).total_seconds())
            window_hours = round(span_seconds / 3600.0, 2)
            avg_amount = float(np.mean(amounts))
            std_amount = float(np.std(amounts))
            amount_cv = round(std_amount / avg_amount, 4) if avg_amount > 0 else 0.0

            hit = PatternHit(
                pattern_id="",  # assigned globally ordered by start_time
                pattern_type="FAN_IN",
                focal_account=receiver,
                accounts=[receiver] + unique_senders,
                transaction_ids=tx_ids,
                start_time=start_time,
                end_time=end_time,
                total_amount=total_amount,
                metrics={
                    "counterparty_count": float(len(unique_senders)),
                    "window_hours": window_hours,
                    "avg_amount": round(avg_amount, 2),
                    "amount_cv": amount_cv,
                },
            )
            hits.append(hit)

    return hits


def detect_fan_out(
    df: pd.DataFrame,
    G: nx.MultiDiGraph,
    cfg: Settings,
) -> list[PatternHit]:
    """Detect FAN_OUT patterns. Mirror of FAN_IN on outgoing transactions.
    focal_account = sender; evidence = outgoing transactions in merged window;
    accounts = [focal] + receivers.
    Metrics: counterparty_count, window_hours, avg_amount, amount_cv.
    """
    if df.empty:
        return []

    window_delta = timedelta(hours=cfg.FAN_WINDOW_HOURS)
    min_counterparties = cfg.FAN_MIN_COUNTERPARTIES

    # Group outgoing transactions by sender
    outgoing_by_sender = defaultdict(list)
    for _, row in df.iterrows():
        outgoing_by_sender[str(row["sender"])].append(
            {
                "tx_id": str(row["transaction_id"]),
                "counterparty": str(row["receiver"]),
                "amount": float(row["amount"]),
                "timestamp": row["timestamp"],
            }
        )

    hits: list[PatternHit] = []

    for sender, txs in outgoing_by_sender.items():
        distinct_overall = {t["counterparty"] for t in txs}
        if len(distinct_overall) < min_counterparties:
            continue

        # Sort outgoing transactions by time
        txs.sort(key=lambda x: x["timestamp"])
        n = len(txs)

        # Sliding window with two pointers [left, right]
        marked_intervals: List[Tuple[int, int]] = []
        left = 0
        counterparty_counts: dict[str, int] = defaultdict(int)

        for right in range(n):
            counterparty_counts[txs[right]["counterparty"]] += 1

            while txs[right]["timestamp"] - txs[left]["timestamp"] > window_delta:
                cp = txs[left]["counterparty"]
                counterparty_counts[cp] -= 1
                if counterparty_counts[cp] == 0:
                    del counterparty_counts[cp]
                left += 1

            if len(counterparty_counts) >= min_counterparties:
                marked_intervals.append((left, right))

        if not marked_intervals:
            continue

        # Merge overlapping marked windows of the same account into one hit
        merged_intervals = _merge_intervals(marked_intervals)

        for m_start, m_end in merged_intervals:
            evidence_txs = txs[m_start : m_end + 1]
            if not evidence_txs:
                continue

            unique_receivers = sorted({t["counterparty"] for t in evidence_txs})
            if len(unique_receivers) < min_counterparties:
                continue

            tx_ids = [t["tx_id"] for t in evidence_txs]
            amounts = np.array([t["amount"] for t in evidence_txs], dtype=float)
            start_time = evidence_txs[0]["timestamp"]
            end_time = evidence_txs[-1]["timestamp"]
            total_amount = float(np.sum(amounts))

            # Metrics
            span_seconds = max(0.0, (end_time - start_time).total_seconds())
            window_hours = round(span_seconds / 3600.0, 2)
            avg_amount = float(np.mean(amounts))
            std_amount = float(np.std(amounts))
            amount_cv = round(std_amount / avg_amount, 4) if avg_amount > 0 else 0.0

            hit = PatternHit(
                pattern_id="",
                pattern_type="FAN_OUT",
                focal_account=sender,
                accounts=[sender] + unique_receivers,
                transaction_ids=tx_ids,
                start_time=start_time,
                end_time=end_time,
                total_amount=total_amount,
                metrics={
                    "counterparty_count": float(len(unique_receivers)),
                    "window_hours": window_hours,
                    "avg_amount": round(avg_amount, 2),
                    "amount_cv": amount_cv,
                },
            )
            hits.append(hit)

    return hits
