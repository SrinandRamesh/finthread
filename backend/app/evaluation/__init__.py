"""Baseline + evaluation package (Member 3).

Public API called by Member 2's pipeline.py:
    run_baseline(transactions, cfg)                     -> BaselineOutput
    evaluate(transactions, clusters, baseline, cfg)     -> EvaluationResult (dict shaped like EvaluationOut)
"""
from __future__ import annotations

from app.evaluation.baseline import run_baseline
from app.evaluation.metrics import evaluate

__all__ = ["run_baseline", "evaluate"]
