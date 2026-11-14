"""TEMPORARY STUB created by the Integration Lead at kickoff.
Member 3 owns this package and replaces this file on feat/intel.
Signatures are fixed by PROJECT_CONTRACT.md Section 7."""
import pandas as pd

from app.config import Settings
from app.contracts import BaselineOutput, EvaluationResult, ScoredCluster


def run_baseline(transactions: pd.DataFrame, cfg: Settings) -> BaselineOutput:
    return BaselineOutput(flagged_transaction_ids=set(), rules_triggered={})


def evaluate(transactions: pd.DataFrame, clusters: list[ScoredCluster],
             baseline: BaselineOutput, cfg: Settings) -> EvaluationResult:
    return {"available": False, "reason": "Evaluation not implemented yet"}
