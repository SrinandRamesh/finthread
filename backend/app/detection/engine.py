"""Detection engine orchestration. Follows PROJECT_CONTRACT.md Section 6."""
from __future__ import annotations

import networkx as nx
import pandas as pd

from app.config import Settings
from app.contracts import DetectionOutput


def run_detection(
    df: pd.DataFrame,
    G: nx.MultiDiGraph,
    cfg: Settings,
) -> DetectionOutput:
    """Run detection algorithms on the graph and transactions.
    Full algorithm implementations are added in detection modules (fan, cycles, pass_through, timing, clusters).
    """
    # Baseline/initial return structure for Step 2; expanded in subsequent steps
    return DetectionOutput(
        transactions=df,
        graph=G,
        patterns=[],
        clusters=[],
        account_features={},
    )
