"""API response/request models. FROZEN: only the Integration Lead edits this file.
Field names must match frontend/src/types/contract.ts exactly."""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

RiskLevel = Literal["high", "medium", "low", "none"]
PatternType = Literal["FAN_IN", "FAN_OUT", "CYCLE", "PASS_THROUGH"]
Typology = Literal["FAN_IN", "FAN_OUT", "CYCLE", "PASS_THROUGH", "SCATTER_GATHER"]


class HealthOut(BaseModel):
    status: str
    version: str
    dataset_loaded: bool
    run_id: Optional[str] = None


class DatasetInfo(BaseModel):
    dataset_id: str
    name: str
    source: Literal["upload", "sample"]
    uploaded_at: datetime
    row_count: int
    has_labels: bool


class RowError(BaseModel):
    row_number: int
    transaction_id: Optional[str] = None
    field: Optional[str] = None
    message: str


class ValidationReport(BaseModel):
    total_rows: int
    accepted_rows: int
    rejected_rows: int
    has_labels: bool
    errors: list[RowError]               # first 100 only


class RunCounts(BaseModel):
    transactions: int
    accounts: int
    patterns: int
    clusters: int
    alerts: int


class RunSummary(BaseModel):
    run_id: str
    dataset_id: str
    status: Literal["completed", "failed"]
    started_at: datetime
    finished_at: datetime
    duration_ms: int
    counts: RunCounts
    error: Optional[str] = None


class UploadResponse(BaseModel):
    dataset: DatasetInfo
    validation: ValidationReport
    run: Optional[RunSummary] = None


class AnalyzeRequest(BaseModel):
    overrides: dict[str, float] = Field(default_factory=dict)


class ConfigOut(BaseModel):
    detection: dict[str, float]
    risk: dict[str, float]
    baseline: dict[str, float]


class GroundTruth(BaseModel):
    label: Optional[Literal["suspicious", "normal"]] = None
    typology: Optional[Typology] = None


class Prediction(BaseModel):
    graph_flagged: bool
    cluster_id: Optional[str] = None
    patterns: list[PatternType]
    baseline_flagged: bool
    baseline_rules: list[str]


class TransactionOut(BaseModel):
    transaction_id: str
    sender: str
    receiver: str
    amount: float
    timestamp: datetime
    currency: str
    channel: Optional[str] = None
    ground_truth: Optional[GroundTruth] = None
    prediction: Prediction


class TransactionPage(BaseModel):
    items: list[TransactionOut]
    page: int
    page_size: int
    total: int


class GraphNode(BaseModel):
    id: str
    label: str
    risk_score: Optional[int] = None
    risk_level: RiskLevel
    total_in: float
    total_out: float
    in_degree: int
    out_degree: int
    patterns: list[PatternType]
    cluster_ids: list[str]
    is_suspicious: bool


class GraphEdge(BaseModel):
    id: str                              # = transaction_id
    source: str
    target: str
    amount: float
    timestamp: datetime
    channel: Optional[str] = None
    patterns: list[PatternType]
    pattern_ids: list[str]
    cluster_id: Optional[str] = None
    is_suspicious: bool


class GraphMeta(BaseModel):
    scope: Literal["suspicious", "full", "cluster", "account"]
    node_count: int
    edge_count: int
    truncated: bool
    time_start: Optional[datetime] = None
    time_end: Optional[datetime] = None


class GraphOut(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    meta: GraphMeta


class PatternOut(BaseModel):
    pattern_id: str
    pattern_type: PatternType
    focal_account: Optional[str] = None
    accounts: list[str]
    transaction_ids: list[str]
    start_time: datetime
    end_time: datetime
    total_amount: float
    metrics: dict[str, float]
    cluster_id: Optional[str] = None


class PatternList(BaseModel):
    items: list[PatternOut]


class ScoreFactorOut(BaseModel):
    factor: str
    points: int
    max_points: int
    reason: str


class EvidenceOut(BaseModel):
    transaction_id: str
    sender: str
    receiver: str
    amount: float
    timestamp: datetime
    note: str


class ExplanationOut(BaseModel):
    headline: str
    summary: str
    bullet_points: list[str]
    evidence: list[EvidenceOut]
    disclaimer: str


class ClusterSummary(BaseModel):
    cluster_id: str
    risk_score: int
    risk_level: RiskLevel
    primary_typology: Typology
    typologies: list[Typology]
    account_count: int
    transaction_count: int
    total_amount: float
    start_time: datetime
    end_time: datetime
    median_hop_minutes: Optional[float] = None
    alerted: bool
    headline: str


class ClusterAccount(BaseModel):
    account_id: str
    role: Literal["source", "intermediary", "collector", "member"]
    total_in: float
    total_out: float


class ClusterDetail(ClusterSummary):
    accounts: list[ClusterAccount]
    patterns: list[PatternOut]
    score_breakdown: list[ScoreFactorOut]
    explanation: ExplanationOut
    transactions: list[TransactionOut]
    subgraph: GraphOut


class ClusterList(BaseModel):
    items: list[ClusterSummary]
    total: int


class AlertOut(BaseModel):
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
    status: Literal["open"]


class AlertList(BaseModel):
    items: list[AlertOut]
    total: int


class AccountProfile(BaseModel):
    account_id: str
    in_degree: int
    out_degree: int
    in_tx_count: int
    out_tx_count: int
    total_in: float
    total_out: float
    first_seen: datetime
    last_seen: datetime
    median_dwell_minutes: Optional[float] = None
    retention_ratio: Optional[float] = None
    max_out_24h_amount: float
    max_out_24h_count: int


class AccountRiskOut(BaseModel):
    risk_score: Optional[int] = None
    risk_level: RiskLevel
    typologies: list[Typology]
    cluster_ids: list[str]


class Counterparty(BaseModel):
    account_id: str
    direction: Literal["in", "out"]
    tx_count: int
    total_amount: float


class AccountDetail(BaseModel):
    account: AccountProfile
    risk: AccountRiskOut
    patterns: list[PatternOut]
    counterparties: list[Counterparty]   # top 20 by total_amount
    transactions: list[TransactionOut]   # latest 200, in and out
    subgraph: GraphOut                   # 1-hop ego network


class TypologyCount(BaseModel):
    typology: Typology
    label: str
    count: int                           # clusters having this typology


class LevelCount(BaseModel):
    level: RiskLevel
    count: int                           # clusters at this level


class DailyVolume(BaseModel):
    date: str                            # YYYY-MM-DD
    tx_count: int
    total_amount: float
    flagged_amount: float                # amount in graph-flagged transactions


class OverviewStats(BaseModel):
    total_transactions: int
    total_accounts: int
    total_amount: float
    flagged_transactions: int
    clusters: int
    alerts: int
    high_risk_alerts: int
    medium_risk_alerts: int


class HeadlineMetrics(BaseModel):
    graph_f1: float
    baseline_f1: float
    graph_recall: float
    baseline_recall: float


class OverviewOut(BaseModel):
    dataset: DatasetInfo
    run: RunSummary
    stats: OverviewStats
    typology_counts: list[TypologyCount]
    risk_distribution: list[LevelCount]
    top_alerts: list[AlertOut]           # top 5
    daily_volume: list[DailyVolume]
    headline_metrics: Optional[HeadlineMetrics] = None


class ConfusionMatrix(BaseModel):
    tp: int
    fp: int
    fn: int
    tn: int


class ModelMetrics(BaseModel):
    model: Literal["graph", "baseline"]
    display_name: str
    precision: float
    recall: float
    f1: float
    accuracy: float
    flagged_count: int
    confusion_matrix: ConfusionMatrix


class TypologyRecall(BaseModel):
    typology: Typology
    label: str
    positives: int
    graph_recall: Optional[float] = None
    baseline_recall: Optional[float] = None


class EvaluationOut(BaseModel):
    available: bool
    reason: Optional[str] = None
    granularity: Literal["transaction"] = "transaction"
    label_source: Optional[Literal["synthetic", "uploaded"]] = None
    total: int = 0
    positives: int = 0
    negatives: int = 0
    thresholds: dict[str, float] = Field(default_factory=dict)
    models: list[ModelMetrics] = Field(default_factory=list)
    per_typology: list[TypologyRecall] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
