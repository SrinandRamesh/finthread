"""TEMPORARY STUB created by the Integration Lead at kickoff.
Member 3 owns this package and replaces this file on feat/intel.
Signatures are fixed by PROJECT_CONTRACT.md Section 7."""
from app.config import Settings
from app.contracts import AccountRisk, AlertRecord, DetectionOutput, ScoredCluster


def score_clusters(detection: DetectionOutput, cfg: Settings) -> list[ScoredCluster]:
    return []


def build_alerts(clusters: list[ScoredCluster], cfg: Settings) -> list[AlertRecord]:
    return []


def compute_account_risk(clusters: list[ScoredCluster]) -> dict[str, AccountRisk]:
    return {}
