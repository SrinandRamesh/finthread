"""Core routes (Member 2). Follows PROJECT_CONTRACT.md Section 10."""
from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from app import schemas
from app.config import get_settings
from app.ingestion.loader import ingest_csv_content
from app.pipeline import build_run_summary, run_analysis
from app.state import get_current_result

router = APIRouter(tags=["core"])
MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB limit


@router.get("/health", response_model=schemas.HealthOut)
def health() -> schemas.HealthOut:
    """Endpoint 1: liveness check."""
    result = get_current_result()
    return schemas.HealthOut(
        status="ok",
        version="1.0.0",
        dataset_loaded=result is not None,
        run_id=result.run_id if result else None,
    )


@router.post("/upload", response_model=schemas.UploadResponse)
async def upload_csv(
    file: UploadFile = File(...),
    analyze: bool = Query(True),
) -> schemas.UploadResponse:
    """Endpoint 2: upload CSV, validate, store, optionally run analysis."""
    settings = get_settings()

    content = await file.read()
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=400,
            detail="File size exceeds the 10 MB limit",
        )

    filename = file.filename or "uploaded_transactions.csv"

    dataset_info, report, _ = ingest_csv_content(
        content=content,
        filename=filename,
        source="upload",
    )

    if report.total_rows > settings.MAX_UPLOAD_ROWS:
        raise HTTPException(
            status_code=400,
            detail=f"Dataset has {report.total_rows} rows, exceeding limit of {settings.MAX_UPLOAD_ROWS}",
        )

    if dataset_info is None or report.accepted_rows == 0:
        raise HTTPException(
            status_code=400,
            detail="No valid transactions were accepted from the uploaded file",
        )

    run_summary: Optional[schemas.RunSummary] = None
    if analyze:
        result = run_analysis(dataset_info.dataset_id, settings)
        run_summary = build_run_summary(result)

    return schemas.UploadResponse(
        dataset=dataset_info,
        validation=report,
        run=run_summary,
    )


@router.post("/dataset/load-sample", response_model=schemas.UploadResponse)
def load_sample_dataset() -> schemas.UploadResponse:
    """Endpoint 3: load bundled synthetic CSV + run analysis."""
    settings = get_settings()

    if not os.path.exists(settings.SAMPLE_DATA_PATH):
        raise HTTPException(
            status_code=404,
            detail=f"Sample dataset file not found at {settings.SAMPLE_DATA_PATH}",
        )

    filename = os.path.basename(settings.SAMPLE_DATA_PATH)
    with open(settings.SAMPLE_DATA_PATH, "rb") as f:
        content = f.read()

    dataset_info, report, _ = ingest_csv_content(
        content=content,
        filename=filename,
        source="sample",
    )

    if dataset_info is None or report.accepted_rows == 0:
        raise HTTPException(
            status_code=400,
            detail="Sample dataset has no valid rows",
        )

    result = run_analysis(dataset_info.dataset_id, settings)
    run_summary = build_run_summary(result)

    return schemas.UploadResponse(
        dataset=dataset_info,
        validation=report,
        run=run_summary,
    )


@router.get("/dataset/sample")
def download_sample_csv():
    """Endpoint 4: download the sample CSV file."""
    settings = get_settings()

    if not os.path.exists(settings.SAMPLE_DATA_PATH):
        raise HTTPException(
            status_code=404,
            detail=f"Sample dataset file not found at {settings.SAMPLE_DATA_PATH}",
        )

    return FileResponse(
        settings.SAMPLE_DATA_PATH,
        media_type="text/csv",
        filename="finthread_sample_transactions.csv",
    )


@router.get("/config", response_model=schemas.ConfigOut)
def get_active_config() -> schemas.ConfigOut:
    """Endpoint 6: active thresholds grouped by detection, risk, baseline."""
    settings = get_settings()
    return schemas.ConfigOut(**settings.grouped())
