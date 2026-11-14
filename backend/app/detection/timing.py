"""Timing analysis and account features computation.
Follows PROJECT_CONTRACT.md Section 6."""
from __future__ import annotations

import bisect
import statistics
from collections import defaultdict
from datetime import timedelta
from typing import Dict, List, Optional

import networkx as nx
import pandas as pd

from app.contracts import AccountFeatures


def compute_account_features(
    df: pd.DataFrame,
    G: nx.MultiDiGraph,
) -> dict[str, AccountFeatures]:
    """Compute per-account topological and temporal features:
    - in_degree / out_degree: distinct counterparties (predecessors/successors)
    - in_tx_count / out_tx_count: transaction counts
    - total_in / total_out: volume in/out
    - first_seen / last_seen: activity timespan
    - median_dwell_minutes: for each in-tx, minutes until next out-tx
    - retention_ratio: 1 - total_out / total_in (None if total_in == 0)
    - max_out_24h_amount / max_out_24h_count: over rolling 24-hour windows
    """
    if df.empty:
        return {}

    # Group transactions by account
    in_txs_map: Dict[str, List[dict]] = defaultdict(list)
    out_txs_map: Dict[str, List[dict]] = defaultdict(list)

    all_accounts: set[str] = set()

    for _, row in df.iterrows():
        sender = str(row["sender"])
        receiver = str(row["receiver"])
        amount = float(row["amount"])
        ts = row["timestamp"]

        all_accounts.add(sender)
        all_accounts.add(receiver)

        out_txs_map[sender].append({"amount": amount, "timestamp": ts})
        in_txs_map[receiver].append({"amount": amount, "timestamp": ts})

    features_map: dict[str, AccountFeatures] = {}
    twenty_four_hours = timedelta(hours=24)

    for account in all_accounts:
        in_list = in_txs_map.get(account, [])
        out_list = out_txs_map.get(account, [])

        in_list.sort(key=lambda x: x["timestamp"])
        out_list.sort(key=lambda x: x["timestamp"])

        in_tx_count = len(in_list)
        out_tx_count = len(out_list)

        total_in = float(sum(t["amount"] for t in in_list))
        total_out = float(sum(t["amount"] for t in out_list))

        # Distinct neighbor degrees
        in_degree = len(list(G.predecessors(account))) if G.has_node(account) else 0
        out_degree = len(list(G.successors(account))) if G.has_node(account) else 0

        # Activity timestamps
        all_timestamps = [t["timestamp"] for t in in_list] + [t["timestamp"] for t in out_list]
        first_seen = min(all_timestamps)
        last_seen = max(all_timestamps)

        # Median dwell minutes
        # For each incoming transaction, minutes until the account's next outgoing transaction
        out_timestamps = [t["timestamp"] for t in out_list]
        dwell_minutes_list: list[float] = []

        for in_tx in in_list:
            t_in = in_tx["timestamp"]
            # Find earliest out_tx with timestamp >= t_in
            idx = bisect.bisect_left(out_timestamps, t_in)
            if idx < len(out_timestamps):
                t_out = out_timestamps[idx]
                dwell = max(0.0, (t_out - t_in).total_seconds() / 60.0)
                dwell_minutes_list.append(dwell)

        median_dwell: Optional[float] = None
        if dwell_minutes_list:
            median_dwell = round(float(statistics.median(dwell_minutes_list)), 2)

        # Retention ratio = 1 - total_out / total_in (null if total_in = 0)
        retention_ratio: Optional[float] = None
        if total_in > 0:
            retention_ratio = round(1.0 - (total_out / total_in), 4)

        # max_out_24h_amount and max_out_24h_count over rolling 24-hour windows
        max_out_amount = 0.0
        max_out_count = 0

        if out_list:
            left = 0
            cur_amount = 0.0
            n_out = len(out_list)

            for right in range(n_out):
                cur_amount += out_list[right]["amount"]

                while out_list[right]["timestamp"] - out_list[left]["timestamp"] > twenty_four_hours:
                    cur_amount -= out_list[left]["amount"]
                    left += 1

                window_count = right - left + 1
                if cur_amount > max_out_amount:
                    max_out_amount = cur_amount
                if window_count > max_out_count:
                    max_out_count = window_count

        features_map[account] = AccountFeatures(
            account_id=account,
            in_degree=in_degree,
            out_degree=out_degree,
            in_tx_count=in_tx_count,
            out_tx_count=out_tx_count,
            total_in=round(total_in, 2),
            total_out=round(total_out, 2),
            first_seen=first_seen,
            last_seen=last_seen,
            median_dwell_minutes=median_dwell,
            retention_ratio=retention_ratio,
            max_out_24h_amount=round(max_out_amount, 2),
            max_out_24h_count=max_out_count,
            pattern_ids=[],
        )

    return features_map
