"""Serialization helpers for graph, transactions, and patterns.
Shared between Member 2 (core routes) and Member 3 (intelligence routes).
Follows PROJECT_CONTRACT.md Section 10."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, Set

import pandas as pd

from app import schemas
from app.contracts import AnalysisResult, PatternHit


def to_pattern_out(hit: PatternHit) -> schemas.PatternOut:
    """Convert an internal PatternHit to API schema PatternOut."""
    return schemas.PatternOut(
        pattern_id=hit.pattern_id,
        pattern_type=hit.pattern_type,
        focal_account=hit.focal_account,
        accounts=hit.accounts,
        transaction_ids=hit.transaction_ids,
        start_time=hit.start_time,
        end_time=hit.end_time,
        total_amount=round(hit.total_amount, 2),
        metrics=hit.metrics,
        cluster_id=hit.cluster_id,
    )


def to_transaction_out(
    row: dict | pd.Series,
    result: AnalysisResult,
) -> schemas.TransactionOut:
    """Convert transaction row/dict to API schema TransactionOut.
    Fills prediction from clusters, pattern hits, and baseline.
    """
    tx_id = str(row["transaction_id"])
    sender = str(row["sender"])
    receiver = str(row["receiver"])
    amount = float(row["amount"])
    timestamp = row["timestamp"]
    if hasattr(timestamp, "to_pydatetime"):
        timestamp = timestamp.to_pydatetime()

    currency = str(row.get("currency") or "INR")
    channel = row.get("channel") if pd.notna(row.get("channel")) else None

    # Ground truth (null when both label and gt_typology are blank)
    raw_label = row.get("label") if pd.notna(row.get("label")) else None
    raw_gt = row.get("gt_typology") if pd.notna(row.get("gt_typology")) else None

    ground_truth: Optional[schemas.GroundTruth] = None
    if raw_label or raw_gt:
        ground_truth = schemas.GroundTruth(
            label=str(raw_label).lower() if raw_label else None,  # type: ignore
            typology=str(raw_gt).upper() if raw_gt else None,  # type: ignore
        )

    # Prediction
    # 1. Alerted clusters set
    alerted_clusters = {c.cluster_id for c in result.clusters if getattr(c, "alerted", False)}
    # If no clusters are scored yet or none alerted, fallback to any cluster containing it
    all_cluster_txs: Dict[str, str] = {}
    for c in result.clusters:
        for tid in c.transaction_ids:
            all_cluster_txs[tid] = c.cluster_id
    if not all_cluster_txs:
        # Fallback to raw clusters from detection
        for rc in result.detection.clusters:
            for tid in rc.transaction_ids:
                all_cluster_txs[tid] = rc.cluster_id

    assigned_cluster = all_cluster_txs.get(tx_id)
    graph_flagged = bool(assigned_cluster and (assigned_cluster in alerted_clusters or not alerted_clusters))

    # 2. Patterns containing this transaction
    patterns_for_tx: list[schemas.PatternType] = []
    for hit in result.detection.patterns:
        if tx_id in hit.transaction_ids:
            if hit.pattern_type not in patterns_for_tx:
                patterns_for_tx.append(hit.pattern_type)

    # 3. Baseline output
    baseline_flagged = tx_id in result.baseline.flagged_transaction_ids
    baseline_rules = result.baseline.rules_triggered.get(tx_id, [])

    prediction = schemas.Prediction(
        graph_flagged=graph_flagged,
        cluster_id=assigned_cluster,
        patterns=patterns_for_tx,
        baseline_flagged=baseline_flagged,
        baseline_rules=baseline_rules,
    )

    return schemas.TransactionOut(
        transaction_id=tx_id,
        sender=sender,
        receiver=receiver,
        amount=amount,
        timestamp=timestamp,
        currency=currency,
        channel=channel,
        ground_truth=ground_truth,
        prediction=prediction,
    )


def build_graph_out(
    result: AnalysisResult,
    account_ids: Optional[Set[str]] = None,
    transaction_ids: Optional[Set[str]] = None,
    scope: str = "suspicious",
    min_amount: Optional[float] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    max_edges: int = 1500,
) -> schemas.GraphOut:
    """Build Cytoscape-compatible GraphOut according to scope and filters."""
    df = result.detection.transactions
    G = result.detection.graph

    # Identify alerted clusters and transactions
    alerted_clusters = {c.cluster_id for c in result.clusters if getattr(c, "alerted", False)}
    cluster_tx_map: Dict[str, str] = {}
    cluster_accounts_all: Set[str] = set()

    for c in result.clusters:
        for tid in c.transaction_ids:
            cluster_tx_map[tid] = c.cluster_id
        cluster_accounts_all.update([a.account_id for a in c.accounts] if hasattr(c.accounts[0], "account_id") else c.accounts)  # type: ignore

    if not cluster_tx_map:
        for rc in result.detection.clusters:
            for tid in rc.transaction_ids:
                cluster_tx_map[tid] = rc.cluster_id
            cluster_accounts_all.update(rc.accounts)

    # Pattern maps for edges
    tx_to_patterns: Dict[str, List[schemas.PatternType]] = {}
    tx_to_pattern_ids: Dict[str, List[str]] = {}
    for hit in result.detection.patterns:
        for tid in hit.transaction_ids:
            tx_to_patterns.setdefault(tid, [])
            if hit.pattern_type not in tx_to_patterns[tid]:
                tx_to_patterns[tid].append(hit.pattern_type)
            tx_to_pattern_ids.setdefault(tid, []).append(hit.pattern_id)

    # Determine allowed accounts based on scope
    filtered_accounts = set(account_ids) if account_ids is not None else None

    if scope == "suspicious" and filtered_accounts is None:
        # Accounts in any cluster + their 1-hop neighbours
        filtered_accounts = set()
        for acc in cluster_accounts_all:
            filtered_accounts.add(acc)
            if G.has_node(acc):
                filtered_accounts.update(G.predecessors(acc))
                filtered_accounts.update(G.successors(acc))

    # Collect candidate edges
    candidate_edges: list[schemas.GraphEdge] = []

    for _, row in df.iterrows():
        tx_id = str(row["transaction_id"])
        u = str(row["sender"])
        v = str(row["receiver"])
        amt = float(row["amount"])
        ts = row["timestamp"]
        if hasattr(ts, "to_pydatetime"):
            ts = ts.to_pydatetime()

        # Filter by transaction_ids if given
        if transaction_ids is not None and tx_id not in transaction_ids:
            continue

        # Filter by accounts
        if filtered_accounts is not None:
            if u not in filtered_accounts or v not in filtered_accounts:
                continue

        # Filters: min_amount, start_time, end_time
        if min_amount is not None and amt < min_amount:
            continue
        if start_time is not None and ts < start_time:
            continue
        if end_time is not None and ts > end_time:
            continue

        c_id = cluster_tx_map.get(tx_id)
        is_suspicious = bool(c_id and (c_id in alerted_clusters or not alerted_clusters))

        edge = schemas.GraphEdge(
            id=tx_id,
            source=u,
            target=v,
            amount=amt,
            timestamp=ts,
            channel=row.get("channel") if pd.notna(row.get("channel")) else None,
            patterns=tx_to_patterns.get(tx_id, []),
            pattern_ids=tx_to_pattern_ids.get(tx_id, []),
            cluster_id=c_id,
            is_suspicious=is_suspicious,
        )
        candidate_edges.append(edge)

    # Truncate edges if > max_edges: always keep suspicious edges, then largest amounts
    truncated = False
    if len(candidate_edges) > max_edges:
        truncated = True
        suspicious_edges = [e for e in candidate_edges if e.is_suspicious]
        normal_edges = [e for e in candidate_edges if not e.is_suspicious]

        # Sort normal edges by amount descending
        normal_edges.sort(key=lambda e: e.amount, reverse=True)
        remaining_slots = max(0, max_edges - len(suspicious_edges))
        final_edges = suspicious_edges + normal_edges[:remaining_slots]
    else:
        final_edges = candidate_edges

    # Nodes that touch the final edges (or focal account in ego network)
    node_ids: Set[str] = set()
    for e in final_edges:
        node_ids.add(e.source)
        node_ids.add(e.target)

    if scope == "account" and filtered_accounts:
        node_ids.update(filtered_accounts)

    nodes: list[schemas.GraphNode] = []
    features_map = result.detection.account_features

    for acc_id in sorted(node_ids):
        feat = features_map.get(acc_id)
        risk = result.account_risk.get(acc_id)

        risk_score = risk.risk_score if risk else None
        risk_level = risk.risk_level if risk else "none"

        # Node patterns and clusters
        acc_patterns: list[schemas.PatternType] = []
        acc_clusters: set[str] = set()
        for hit in result.detection.patterns:
            if acc_id in hit.accounts:
                if hit.pattern_type not in acc_patterns:
                    acc_patterns.append(hit.pattern_type)
                if hit.cluster_id:
                    acc_clusters.add(hit.cluster_id)

        is_node_suspicious = bool(
            (acc_clusters and any(cid in alerted_clusters for cid in acc_clusters))
            or risk_level in ("high", "medium")
            or (not alerted_clusters and acc_clusters)
        )

        node = schemas.GraphNode(
            id=acc_id,
            label=acc_id,
            risk_score=risk_score,
            risk_level=risk_level,  # type: ignore
            total_in=feat.total_in if feat else 0.0,
            total_out=feat.total_out if feat else 0.0,
            in_degree=feat.in_degree if feat else 0,
            out_degree=feat.out_degree if feat else 0,
            patterns=acc_patterns,
            cluster_ids=sorted(list(acc_clusters)),
            is_suspicious=is_node_suspicious,
        )
        nodes.append(node)

    # Edge timestamps for time_start / time_end
    edge_times = [e.timestamp for e in final_edges]
    time_start = min(edge_times) if edge_times else None
    time_end = max(edge_times) if edge_times else None

    meta = schemas.GraphMeta(
        scope=scope,  # type: ignore
        node_count=len(nodes),
        edge_count=len(final_edges),
        truncated=truncated,
        time_start=time_start,
        time_end=time_end,
    )

    return schemas.GraphOut(nodes=nodes, edges=final_edges, meta=meta)
