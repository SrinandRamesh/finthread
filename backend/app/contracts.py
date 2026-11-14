"""Shared internal contracts between the detection engine (M2) and intelligence/evaluation (M3).
FROZEN: only the Integration Lead edits this file."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal, Optional

import networkx as nx
import pandas as pd

PatternType = Literal["FAN_IN", "FAN_OUT", "CYCLE", "PASS_THROUGH"]
Typology = Literal["FAN_IN", "FAN_OUT", "CYCLE", "PASS_THROUGH", "SCATTER_GATHER"]
RiskLevel = Literal["high", "medium", "low", "none"]

TYPOLOGY_LABELS: dict[str, str] = {
    "FAN_IN": "Fan-in (funnel collection)",
    "FAN_OUT": "Fan-out (dispersion)",
    "CYCLE": "Round-tripping (cycle)",
    "PASS_THROUGH": "Rapid pass-through (mule chain)",
    "SCATTER_GATHER": "Scatter-gather layering",
}
DISCLAIMER = "This alert highlights a pattern that warrants analyst review. It is not proof of money laundering."


# ---------- produced by Member 2 (detection) ----------
@dataclass
class PatternHit:
    pattern_id: str
    pattern_type: PatternType
    focal_account: Optional[str]
    accounts: list[str]                 # ordered for CYCLE / PASS_THROUGH
    transaction_ids: list[str]          # evidence, chronological
    start_time: datetime
    end_time: datetime
    total_amount: float
    metrics: dict[str, float] = field(default_factory=dict)
    cluster_id: Optional[str] = None


@dataclass
class AccountFeatures:
    account_id: str
    in_degree: int
    out_degree: int
    in_tx_count: int
    out_tx_count: int
    total_in: float
    total_out: float
    first_seen: datetime
    last_seen: datetime
    median_dwell_minutes: Optional[float]
    retention_ratio: Optional[float]
    max_out_24h_amount: float
    max_out_24h_count: int
    pattern_ids: list[str] = field(default_factory=list)


@dataclass
class RawCluster:
    cluster_id: str
    accounts: list[str]
    transaction_ids: list[str]
    pattern_ids: list[str]


@dataclass
class DetectionOutput:
    transactions: pd.DataFrame          # columns per contract Section 7
    graph: nx.MultiDiGraph
    patterns: list[PatternHit]
    clusters: list[RawCluster]
    account_features: dict[str, AccountFeatures]


# ---------- produced by Member 3 (intelligence + evaluation) ----------
@dataclass
class ScoreFactor:
    factor: str                         # pattern_severity | multiple_typologies | velocity | structuring | flow_through
    points: int
    max_points: int
    reason: str


@dataclass
class EvidenceItem:
    transaction_id: str
    sender: str
    receiver: str
    amount: float
    timestamp: datetime
    note: str


@dataclass
class Explanation:
    headline: str
    summary: str
    bullet_points: list[str]
    evidence: list[EvidenceItem]
    disclaimer: str = DISCLAIMER


@dataclass
class ClusterAccountRole:
    account_id: str
    role: Literal["source", "intermediary", "collector", "member"]
    total_in: float                     # inside the cluster
    total_out: float                    # inside the cluster


@dataclass
class ScoredCluster:
    cluster_id: str
    accounts: list[ClusterAccountRole]
    transaction_ids: list[str]
    pattern_ids: list[str]
    typologies: list[Typology]
    primary_typology: Typology
    risk_score: int
    risk_level: RiskLevel
    alerted: bool
    score_breakdown: list[ScoreFactor]
    explanation: Explanation
    total_amount: float
    start_time: datetime
    end_time: datetime
    median_hop_minutes: Optional[float]


@dataclass
class AlertRecord:
    alert_id: str
    cluster_id: str
    risk_score: int
    risk_level: RiskLevel
    primary_typology: Typology
    typologies: list[Typology]
    headline: str
    created_at: datetime
    account_count: int
    transaction_count: int
    total_amount: float
    status: Literal["open"] = "open"


@dataclass
class AccountRisk:
    risk_score: Optional[int]
    risk_level: RiskLevel
    typologies: list[Typology]
    cluster_ids: list[str]


@dataclass
class BaselineOutput:
    flagged_transaction_ids: set[str]
    rules_triggered: dict[str, list[str]]   # transaction_id -> ["R1_LARGE_AMOUNT", ...]


# EvaluationResult is a plain dict shaped exactly like schemas.EvaluationOut
EvaluationResult = dict[str, Any]


# ---------- assembled by Member 2 (pipeline) ----------
@dataclass
class DatasetMeta:
    dataset_id: str
    name: str
    source: Literal["upload", "sample"]
    uploaded_at: datetime
    row_count: int
    has_labels: bool


@dataclass
class AnalysisResult:
    run_id: str
    dataset: DatasetMeta
    started_at: datetime
    finished_at: datetime
    detection: DetectionOutput
    clusters: list[ScoredCluster]
    alerts: list[AlertRecord]
    account_risk: dict[str, AccountRisk]
    baseline: BaselineOutput
    evaluation: EvaluationResult
