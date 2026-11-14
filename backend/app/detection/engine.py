"""Detection engine orchestration. Follows PROJECT_CONTRACT.md Section 6."""
from __future__ import annotations

import networkx as nx
import pandas as pd

from app.config import Settings
from app.contracts import DetectionOutput
from app.detection.clusters import form_clusters
from app.detection.cycles import detect_cycles
from app.detection.fan import detect_fan_in, detect_fan_out
from app.detection.pass_through import detect_pass_through
from app.detection.timing import compute_account_features


def run_detection(
    df: pd.DataFrame,
    G: nx.MultiDiGraph,
    cfg: Settings,
) -> DetectionOutput:
    """Run all graph detection algorithms:
    1. FAN_IN & FAN_OUT sliding window detection
    2. Pruned simple cycles with time-respecting verification
    3. Multi-hop pass-through mule chain detection
    4. Pattern ID assignment sorted chronologically (PT-0001...)
    5. Connected-component clustering (CL-0001...)
    6. Account features and timing metrics
    """
    if df.empty or G.number_of_nodes() == 0:
        return DetectionOutput(
            transactions=df,
            graph=G,
            patterns=[],
            clusters=[],
            account_features={},
        )

    # 1. Run detectors
    fan_in_hits = detect_fan_in(df, G, cfg)
    fan_out_hits = detect_fan_out(df, G, cfg)
    cycle_hits = detect_cycles(df, G, cfg)
    pass_through_hits = detect_pass_through(df, G, cfg)

    # 2. Combine and sort patterns chronologically
    all_patterns = fan_in_hits + fan_out_hits + cycle_hits + pass_through_hits
    all_patterns.sort(key=lambda h: (h.start_time, h.end_time, h.pattern_type))

    # 3. Assign sequential pattern IDs
    for idx, hit in enumerate(all_patterns, 1):
        hit.pattern_id = f"PT-{idx:04d}"

    # 4. Form clusters and assign cluster IDs
    clusters = form_clusters(all_patterns, df)

    # 5. Compute account topological and temporal features
    account_features = compute_account_features(df, G)
    for hit in all_patterns:
        for acc in hit.accounts:
            if acc in account_features:
                if hit.pattern_id not in account_features[acc].pattern_ids:
                    account_features[acc].pattern_ids.append(hit.pattern_id)

    return DetectionOutput(
        transactions=df,
        graph=G,
        patterns=all_patterns,
        clusters=clusters,
        account_features=account_features,
    )
