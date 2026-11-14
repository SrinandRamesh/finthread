"""Cluster formation from pattern hits.
Follows PROJECT_CONTRACT.md Section 6."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Set

import networkx as nx
import pandas as pd

from app.contracts import PatternHit, RawCluster


def form_clusters(
    patterns: list[PatternHit],
    df: pd.DataFrame,
) -> list[RawCluster]:
    """Union of evidence transactions of all hits -> undirected account graph -> connected components.
    Each component is a RawCluster holding its accounts, the evidence transactions inside it,
    and the ids of the hits whose accounts fall in it.
    Sort by earliest evidence time; assign CL-0001...
    Each PatternHit.cluster_id is filled in.
    """
    if not patterns or df.empty:
        return []

    # Map transaction_id -> timestamp & sender/receiver
    tx_meta: Dict[str, dict] = {}
    for _, row in df.iterrows():
        tx_meta[str(row["transaction_id"])] = {
            "sender": str(row["sender"]),
            "receiver": str(row["receiver"]),
            "timestamp": row["timestamp"],
        }

    # Collect all evidence transaction IDs
    all_evidence_ids: Set[str] = set()
    for hit in patterns:
        all_evidence_ids.update(hit.transaction_ids)

    # Build undirected account graph over evidence transactions
    G_acc = nx.Graph()
    for tx_id in all_evidence_ids:
        meta = tx_meta.get(tx_id)
        if meta:
            G_acc.add_edge(meta["sender"], meta["receiver"])

    # Also add any standalone accounts mentioned in hits
    for hit in patterns:
        for acc in hit.accounts:
            if not G_acc.has_node(acc):
                G_acc.add_node(acc)

    components = list(nx.connected_components(G_acc))
    if not components:
        return []

    # For each component, associate hits and compute earliest evidence timestamp
    cluster_candidates: list[dict] = []

    for comp_accounts in components:
        comp_hits = [
            h for h in patterns if any(acc in comp_accounts for acc in h.accounts)
        ]
        if not comp_hits:
            continue

        comp_tx_ids: Set[str] = set()
        for h in comp_hits:
            comp_tx_ids.update(h.transaction_ids)

        # Chronological timestamps
        timestamps = [
            tx_meta[tid]["timestamp"]
            for tid in comp_tx_ids
            if tid in tx_meta
        ]
        earliest_ts = min(timestamps) if timestamps else datetime.max

        cluster_candidates.append(
            {
                "accounts": comp_accounts,
                "hits": comp_hits,
                "tx_ids": comp_tx_ids,
                "earliest_ts": earliest_ts,
            }
        )

    # Sort clusters by earliest evidence time ascending
    cluster_candidates.sort(key=lambda c: c["earliest_ts"])

    raw_clusters: list[RawCluster] = []

    for idx, c in enumerate(cluster_candidates, 1):
        cluster_id = f"CL-{idx:04d}"

        # Sort transactions chronologically
        sorted_txs = sorted(
            list(c["tx_ids"]),
            key=lambda tid: tx_meta[tid]["timestamp"] if tid in tx_meta else datetime.min,
        )

        pattern_ids = sorted({h.pattern_id for h in c["hits"] if h.pattern_id})

        # Update each PatternHit's cluster_id
        for hit in c["hits"]:
            hit.cluster_id = cluster_id

        raw_cluster = RawCluster(
            cluster_id=cluster_id,
            accounts=sorted(list(c["accounts"])),
            transaction_ids=sorted_txs,
            pattern_ids=pattern_ids,
        )
        raw_clusters.append(raw_cluster)

    return raw_clusters
