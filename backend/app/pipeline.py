"""Pipeline orchestrator for FinThread analysis.
Follows PROJECT_CONTRACT.md Section 7 and 10."""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime

from sqlalchemy import select

from app.config import Settings
from app.contracts import AnalysisResult, DatasetMeta
from app.db import SessionLocal
from app.detection.engine import run_detection
from app.evaluation import evaluate, run_baseline
from app.graph.builder import build_graph
from app.ingestion.loader import load_transactions_df
from app.intelligence import build_alerts, compute_account_risk, score_clusters
from app.models import AnalysisRun, Dataset
from app.schemas import RunCounts, RunSummary
from app.state import set_current_result

logger = logging.getLogger("finthread")


def build_run_summary(result: AnalysisResult) -> RunSummary:
    """Helper to convert AnalysisResult into RunSummary schema."""
    duration_ms = max(
        0,
        int((result.finished_at - result.started_at).total_seconds() * 1000),
    )
    counts = RunCounts(
        transactions=len(result.detection.transactions),
        accounts=result.detection.graph.number_of_nodes(),
        patterns=len(result.detection.patterns),
        clusters=len(result.clusters),
        alerts=len(result.alerts),
    )
    return RunSummary(
        run_id=result.run_id,
        dataset_id=result.dataset.dataset_id,
        status="completed",
        started_at=result.started_at,
        finished_at=result.finished_at,
        duration_ms=duration_ms,
        counts=counts,
        error=None,
    )


def run_analysis(dataset_id: str, cfg: Settings) -> AnalysisResult:
    """Execute complete analysis pipeline on dataset_id, write run record, set state."""
    run_id = f"run_{uuid.uuid4().hex[:8]}"
    started_at = datetime.now()

    # Query dataset metadata from SQLite
    db = SessionLocal()
    try:
        ds_row = db.execute(
            select(Dataset).where(Dataset.id == dataset_id)
        ).scalar_one_or_none()
        if ds_row is None:
            raise ValueError(f"Dataset {dataset_id} not found")

        dataset_meta = DatasetMeta(
            dataset_id=ds_row.id,
            name=ds_row.name,
            source=ds_row.source,  # type: ignore
            uploaded_at=ds_row.uploaded_at,
            row_count=ds_row.row_count,
            has_labels=ds_row.has_labels,
        )
    finally:
        db.close()

    try:
        # 1. Load transactions DataFrame (M2)
        df = load_transactions_df(dataset_id)

        # 2. Build temporal graph (M2)
        G = build_graph(df)

        # 3. Detection engine (M2)
        detection = run_detection(df, G, cfg)

        # 4. Intelligence modules (M3)
        clusters = score_clusters(detection, cfg)
        alerts = build_alerts(clusters, cfg)
        account_risk = compute_account_risk(clusters)

        # 5. Evaluation modules (M3)
        baseline = run_baseline(df, cfg)
        evaluation = evaluate(df, clusters, baseline, cfg)

        finished_at = datetime.now()

        result = AnalysisResult(
            run_id=run_id,
            dataset=dataset_meta,
            started_at=started_at,
            finished_at=finished_at,
            detection=detection,
            clusters=clusters,
            alerts=alerts,
            account_risk=account_risk,
            baseline=baseline,
            evaluation=evaluation,
        )

        # Save to global in-memory state
        set_current_result(result)

        # Record completed run in SQLite
        summary = build_run_summary(result)
        db = SessionLocal()
        try:
            run_record = AnalysisRun(
                id=run_id,
                dataset_id=dataset_id,
                started_at=started_at,
                finished_at=finished_at,
                status="completed",
                config_json=json.dumps(cfg.grouped()),
                summary_json=summary.model_dump_json(),
                error=None,
            )
            db.add(run_record)
            db.commit()
        finally:
            db.close()

        return result

    except Exception as e:
        finished_at = datetime.now()
        logger.error(f"Analysis run {run_id} failed: {e}", exc_info=True)
        db = SessionLocal()
        try:
            run_record = AnalysisRun(
                id=run_id,
                dataset_id=dataset_id,
                started_at=started_at,
                finished_at=finished_at,
                status="failed",
                config_json=json.dumps(cfg.grouped()),
                summary_json=None,
                error=str(e),
            )
            db.add(run_record)
            db.commit()
        finally:
            db.close()
        raise
