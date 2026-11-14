"""Cycle (round-tripping) detection algorithm.
Follows PROJECT_CONTRACT.md Section 6."""
from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from typing import Dict, List, Optional, Tuple

import networkx as nx
import pandas as pd

from app.config import Settings
from app.contracts import PatternHit


def _prune_graph_2core(G: nx.DiGraph) -> nx.DiGraph:
    """Repeatedly drop nodes with in-degree 0 or out-degree 0."""
    H = G.copy()
    changed = True
    while changed:
        changed = False
        to_remove = [n for n in H.nodes() if H.in_degree(n) == 0 or H.out_degree(n) == 0]
        if to_remove:
            H.remove_nodes_from(to_remove)
            changed = True
    return H


def _canonical_cycle(cycle: list[str]) -> Tuple[str, ...]:
    """Rotate cycle so the lexicographically smallest node is first."""
    if not cycle:
        return ()
    min_val = min(cycle)
    min_idx = cycle.index(min_val)
    return tuple(cycle[min_idx:] + cycle[:min_idx])


def detect_cycles(
    df: pd.DataFrame,
    G: nx.MultiDiGraph,
    cfg: Settings,
) -> list[PatternHit]:
    """Detect CYCLE patterns.
    Collapse to simple DiGraph; repeatedly drop nodes with in-degree 0 or out-degree 0;
    run nx.simple_cycles(G, length_bound=CYCLE_MAX_LENGTH) (cap 500 cycles; length >= 3,
    plus length-2 back-and-forth only if amounts differ < 10%).
    Find time-respecting sequence: start from a->b at t0 (try up to 20 starts),
    pick each next hop's earliest tx strictly after previous one, closing hop <= t0 + CYCLE_MAX_SPAN_HOURS.
    Dedupe rotations.
    focal_account = cycle start; accounts = ordered cycle.
    Metrics: cycle_length, span_hours, amount_retention.
    """
    if df.empty or G.number_of_nodes() == 0:
        return []

    # Map directed edge (u, v) -> list of transactions sorted by timestamp
    txs_by_pair: Dict[Tuple[str, str], List[dict]] = defaultdict(list)
    for _, row in df.iterrows():
        u = str(row["sender"])
        v = str(row["receiver"])
        txs_by_pair[(u, v)].append(
            {
                "tx_id": str(row["transaction_id"]),
                "amount": float(row["amount"]),
                "timestamp": row["timestamp"],
            }
        )

    for pair in txs_by_pair:
        txs_by_pair[pair].sort(key=lambda x: x["timestamp"])

    # Collapse to simple DiGraph
    G_simple = nx.DiGraph()
    for (u, v) in txs_by_pair:
        G_simple.add_edge(u, v)

    # 2-core pruning
    H = _prune_graph_2core(G_simple)
    if H.number_of_nodes() == 0:
        return []

    # Find simple cycles up to length_bound, cap 500
    seen_canonical: set[Tuple[str, ...]] = set()
    candidate_cycles: list[list[str]] = []

    cycle_gen = nx.simple_cycles(H, length_bound=cfg.CYCLE_MAX_LENGTH)
    count = 0

    for cyc in cycle_gen:
        count += 1
        if count > 5000:
            break

        k = len(cyc)
        if k < 2:
            continue

        # Canonical dedupe
        can = _canonical_cycle(cyc)
        if can in seen_canonical:
            continue
        seen_canonical.add(can)

        # For length == 2: only if amounts differ < 10%
        if k == 2:
            u, v = cyc[0], cyc[1]
            txs_uv = txs_by_pair.get((u, v), [])
            txs_vu = txs_by_pair.get((v, u), [])
            if not txs_uv or not txs_vu:
                continue
            # Check if any pair of amounts differ < 10%
            has_close_amounts = False
            for t1 in txs_uv[:10]:
                for t2 in txs_vu[:10]:
                    max_amt = max(t1["amount"], t2["amount"])
                    if max_amt > 0 and abs(t1["amount"] - t2["amount"]) / max_amt < 0.10:
                        has_close_amounts = True
                        break
                if has_close_amounts:
                    break
            if not has_close_amounts:
                continue

        candidate_cycles.append(cyc)

    # Evaluate time-respecting sequence for each candidate cycle
    hits: list[PatternHit] = []
    max_span = timedelta(hours=cfg.CYCLE_MAX_SPAN_HOURS)

    for base_cyc in candidate_cycles:
        k = len(base_cyc)
        # simple_cycles may return any rotation of the cycle (e.g. [B, C, A] for A->B->C->A),
        # so try every rotation as the starting account, not just base_cyc[0].
        found = False
        for r in range(k):
            if found:
                break
            cyc = base_cyc[r:] + base_cyc[:r]
            u0, u1 = cyc[0], cyc[1]
            first_hop_txs = txs_by_pair.get((u0, u1), [])
            for start_tx in first_hop_txs[:20]:
                t0 = start_tx["timestamp"]
                chosen_txs = [start_tx]
                prev_ts = t0
                valid = True

                for hop_idx in range(1, k):
                    hop_u = cyc[hop_idx]
                    hop_v = cyc[(hop_idx + 1) % k]
                    candidates = txs_by_pair.get((hop_u, hop_v), [])

                    # Earliest transaction strictly after previous hop
                    next_tx = None
                    for candidate in candidates:
                        if candidate["timestamp"] > prev_ts:
                            next_tx = candidate
                            break

                    if next_tx is None or next_tx["timestamp"] - t0 > max_span:
                        valid = False
                        break

                    chosen_txs.append(next_tx)
                    prev_ts = next_tx["timestamp"]

                if valid and len(chosen_txs) == k:
                    # Found time-respecting cycle sequence
                    tx_ids = [t["tx_id"] for t in chosen_txs]
                    start_time = chosen_txs[0]["timestamp"]
                    end_time = chosen_txs[-1]["timestamp"]
                    span_hours = round(max(0.0, (end_time - start_time).total_seconds() / 3600.0), 2)
                    total_amount = float(sum(t["amount"] for t in chosen_txs))
                    first_amt = chosen_txs[0]["amount"]
                    last_amt = chosen_txs[-1]["amount"]
                    amount_retention = round(last_amt / first_amt, 4) if first_amt > 0 else 0.0

                    hit = PatternHit(
                        pattern_id="",
                        pattern_type="CYCLE",
                        focal_account=cyc[0],
                        accounts=list(cyc),
                        transaction_ids=tx_ids,
                        start_time=start_time,
                        end_time=end_time,
                        total_amount=total_amount,
                        metrics={
                            "cycle_length": float(k),
                            "span_hours": span_hours,
                            "amount_retention": amount_retention,
                        },
                    )
                    hits.append(hit)
                    found = True
                    break  # stop trying starts for this cycle

    return hits
