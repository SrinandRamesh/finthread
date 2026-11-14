"""Temporal MultiDiGraph builder. Follows PROJECT_CONTRACT.md Section 6."""
from __future__ import annotations

import networkx as nx
import pandas as pd


def build_graph(df: pd.DataFrame) -> nx.MultiDiGraph:
    """Build a MultiDiGraph from a transactions DataFrame.
    Node = account id.
    Edge key = transaction_id.
    Edge attrs = amount (float), timestamp (datetime), channel (str | None).
    Parallel transactions are kept.
    """
    G = nx.MultiDiGraph()

    if df.empty:
        return G

    for _, row in df.iterrows():
        sender = str(row["sender"])
        receiver = str(row["receiver"])
        tx_id = str(row["transaction_id"])
        amount = float(row["amount"])
        timestamp = row["timestamp"]
        channel = row["channel"] if pd.notna(row["channel"]) else None

        # Ensure nodes exist
        if not G.has_node(sender):
            G.add_node(sender)
        if not G.has_node(receiver):
            G.add_node(receiver)

        G.add_edge(
            sender,
            receiver,
            key=tx_id,
            amount=amount,
            timestamp=timestamp,
            channel=channel,
        )

    return G
