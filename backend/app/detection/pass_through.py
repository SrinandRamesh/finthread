"""Pass-through (mule chain) detection algorithm.
Follows PROJECT_CONTRACT.md Section 6."""
from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import timedelta
from typing import Dict, List, Set

import networkx as nx
import pandas as pd

from app.config import Settings
from app.contracts import PatternHit


def detect_pass_through(
    df: pd.DataFrame,
    G: nx.MultiDiGraph,
    cfg: Settings,
) -> list[PatternHit]:
    """Detect PASS_THROUGH patterns.
    (1) Forwarding link: for incoming u->v (amount A, time t), take v's outgoing txs after t
    and within PASS_THROUGH_MAX_HOURS in time order, summing until sum >= PASS_THROUGH_MIN_RATIO * A.
    Link incoming to each contributing outgoing tx.
    (2) Chains: treat txs as nodes and forwarding links as edges. DFS (depth cap 12) from
    txs with no incoming link to find maximal paths. Keep paths >= PASS_THROUGH_MIN_HOPS.
    Drop paths that are sub-paths of another.
    focal_account = first sender; accounts = ordered chain.
    Metrics: hop_count, median_hop_minutes, flow_through_ratio, span_hours.
    """
    if df.empty:
        return []

    # Map transaction_id -> dict with details
    tx_dict: Dict[str, dict] = {}
    incoming_by_acc: Dict[str, List[dict]] = defaultdict(list)
    outgoing_by_acc: Dict[str, List[dict]] = defaultdict(list)

    for _, row in df.iterrows():
        tx_id = str(row["transaction_id"])
        sender = str(row["sender"])
        receiver = str(row["receiver"])
        amount = float(row["amount"])
        timestamp = row["timestamp"]

        item = {
            "tx_id": tx_id,
            "sender": sender,
            "receiver": receiver,
            "amount": amount,
            "timestamp": timestamp,
        }
        tx_dict[tx_id] = item
        incoming_by_acc[receiver].append(item)
        outgoing_by_acc[sender].append(item)

    for acc in outgoing_by_acc:
        outgoing_by_acc[acc].sort(key=lambda x: x["timestamp"])

    max_delta = timedelta(hours=cfg.PASS_THROUGH_MAX_HOURS)
    min_ratio = cfg.PASS_THROUGH_MIN_RATIO

    # 1. Forwarding links
    forwarding_graph: Dict[str, List[str]] = defaultdict(list)
    in_degrees: Dict[str, int] = defaultdict(int)
    all_link_nodes: Set[str] = set()

    for intermediary, in_txs in incoming_by_acc.items():
        out_txs = outgoing_by_acc.get(intermediary, [])
        if not out_txs:
            continue

        for in_tx in in_txs:
            t_in = in_tx["timestamp"]
            amt_in = in_tx["amount"]
            target_amount = min_ratio * amt_in

            cum_sum = 0.0
            contributing: list[str] = []

            for out_tx in out_txs:
                t_out = out_tx["timestamp"]
                if t_out < t_in:
                    continue
                if t_out - t_in > max_delta:
                    break  # out_txs is sorted by timestamp

                cum_sum += out_tx["amount"]
                contributing.append(out_tx["tx_id"])

                if cum_sum >= target_amount:
                    # Target ratio reached! Link in_tx to each of the contributing out_txs
                    for out_id in contributing:
                        forwarding_graph[in_tx["tx_id"]].append(out_id)
                        in_degrees[out_id] += 1
                        all_link_nodes.add(in_tx["tx_id"])
                        all_link_nodes.add(out_id)
                    break

    if not forwarding_graph:
        return []

    # 2. Chains: DFS from transactions with no incoming link
    roots = [node for node in all_link_nodes if in_degrees[node] == 0 and forwarding_graph.get(node)]

    # If all nodes are in cycles (no in_degree == 0), take all nodes with outgoing edges
    if not roots:
        roots = [node for node in all_link_nodes if forwarding_graph.get(node)]

    all_paths: list[list[str]] = []

    def dfs(current_path: list[str], visited: set[str]) -> None:
        if len(current_path) >= 12:
            if len(current_path) >= cfg.PASS_THROUGH_MIN_HOPS:
                all_paths.append(list(current_path))
            return

        curr = current_path[-1]
        next_nodes = [nxt for nxt in forwarding_graph.get(curr, []) if nxt not in visited]

        if not next_nodes:
            if len(current_path) >= cfg.PASS_THROUGH_MIN_HOPS:
                all_paths.append(list(current_path))
            return

        for nxt in next_nodes:
            dfs(current_path + [nxt], visited | {nxt})

    for root in roots:
        dfs([root], {root})

    if not all_paths:
        return []

    # 3. Drop paths that are sub-paths of another
    # Sort paths by length descending
    all_paths.sort(key=lambda p: len(p), reverse=True)
    maximal_paths: list[list[str]] = []

    for path in all_paths:
        is_sub = False
        p_len = len(path)
        for existing in maximal_paths:
            e_len = len(existing)
            if p_len >= e_len:
                continue
            for i in range(e_len - p_len + 1):
                if existing[i : i + p_len] == path:
                    is_sub = True
                    break
            if is_sub:
                break

        if not is_sub:
            # Also prevent exact duplicates
            if path not in maximal_paths:
                maximal_paths.append(path)

    # 4. Build PatternHits
    hits: list[PatternHit] = []

    for path in maximal_paths:
        tx_objs = [tx_dict[tid] for tid in path]
        first_sender = tx_objs[0]["sender"]

        # Ordered chain of accounts: first sender + each hop's receiver
        accounts = [first_sender] + [t["receiver"] for t in tx_objs]

        start_time = tx_objs[0]["timestamp"]
        end_time = tx_objs[-1]["timestamp"]
        total_amount = float(sum(t["amount"] for t in tx_objs))

        # Metrics
        hop_count = float(len(tx_objs))
        hop_minutes = [
            (tx_objs[i + 1]["timestamp"] - tx_objs[i]["timestamp"]).total_seconds() / 60.0
            for i in range(len(tx_objs) - 1)
        ]
        median_hop = round(float(statistics.median(hop_minutes)), 2) if hop_minutes else 0.0
        first_amt = tx_objs[0]["amount"]
        last_amt = tx_objs[-1]["amount"]
        flow_through_ratio = round(last_amt / first_amt, 4) if first_amt > 0 else 0.0
        span_hours = round(max(0.0, (end_time - start_time).total_seconds() / 3600.0), 2)

        hit = PatternHit(
            pattern_id="",
            pattern_type="PASS_THROUGH",
            focal_account=first_sender,
            accounts=accounts,
            transaction_ids=path,
            start_time=start_time,
            end_time=end_time,
            total_amount=total_amount,
            metrics={
                "hop_count": hop_count,
                "median_hop_minutes": median_hop,
                "flow_through_ratio": flow_through_ratio,
                "span_hours": span_hours,
            },
        )
        hits.append(hit)

    return hits
