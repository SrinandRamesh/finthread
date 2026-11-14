"""Core routes (Member 2). Follows PROJECT_CONTRACT.md Section 10."""
from __future__ import annotations

import os
from collections import defaultdict
from datetime import datetime
from typing import Literal, Optional

import pandas as pd
from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from app import schemas
from app.config import get_settings
from app.graph.serialize import build_graph_out, to_pattern_out, to_transaction_out
from app.ingestion.loader import ingest_csv_content
from app.pipeline import build_run_summary, run_analysis
from app.state import get_current_result

router = APIRouter(tags=["core"])
MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB limit


def _require_run():
    """Helper to check if analysis run exists; raises HTTP 409 if not."""
    result = get_current_result()
    if result is None:
        raise HTTPException(
            status_code=409,
            detail="No analysis run yet. Upload a dataset or load the sample.",
        )
    return result


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


@router.post("/analyze", response_model=schemas.RunSummary)
def analyze(req: schemas.AnalyzeRequest) -> schemas.RunSummary:
    """Endpoint 5: re-run analysis on active dataset with optional parameter overrides."""
    result = _require_run()
    cfg = get_settings()

    if req.overrides:
        cfg = cfg.model_copy(update=req.overrides)

    new_result = run_analysis(result.dataset.dataset_id, cfg)
    return build_run_summary(new_result)


@router.get("/config", response_model=schemas.ConfigOut)
def get_active_config() -> schemas.ConfigOut:
    """Endpoint 6: active thresholds grouped by detection, risk, baseline."""
    settings = get_settings()
    return schemas.ConfigOut(**settings.grouped())


@router.get("/transactions", response_model=schemas.TransactionPage)
def get_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    account: Optional[str] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    flagged_only: bool = False,
    pattern: Optional[schemas.PatternType] = None,
    sort: str = Query("-timestamp", pattern=r"^(-?timestamp|-?amount)$"),
) -> schemas.TransactionPage:
    """Endpoint 7: paginated transaction explorer with search, filtering, and sorting."""
    result = _require_run()
    df = result.detection.transactions.copy()

    # Filter by account (sender or receiver)
    if account:
        df = df[(df["sender"] == account) | (df["receiver"] == account)]

    # Filter by amount range
    if min_amount is not None:
        df = df[df["amount"] >= min_amount]
    if max_amount is not None:
        df = df[df["amount"] <= max_amount]

    # Filter by timestamp range
    if start is not None:
        df = df[df["timestamp"] >= start]
    if end is not None:
        df = df[df["timestamp"] <= end]

    # Filter by pattern type
    if pattern:
        matching_txs: set[str] = set()
        for hit in result.detection.patterns:
            if hit.pattern_type == pattern:
                matching_txs.update(hit.transaction_ids)
        df = df[df["transaction_id"].isin(matching_txs)]

    # Filter by flagged_only
    if flagged_only:
        alerted_cluster_ids = {c.cluster_id for c in result.clusters if getattr(c, "alerted", False)}
        flagged_txs: set[str] = set()
        for c in result.clusters:
            if c.cluster_id in alerted_cluster_ids or not alerted_cluster_ids:
                flagged_txs.update(c.transaction_ids)
        if not flagged_txs:
            for rc in result.detection.clusters:
                flagged_txs.update(rc.transaction_ids)
        df = df[df["transaction_id"].isin(flagged_txs)]

    # Sorting
    ascending = not sort.startswith("-")
    sort_col = sort.lstrip("-")
    df = df.sort_values(by=sort_col, ascending=ascending)

    total = len(df)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    page_df = df.iloc[start_idx:end_idx]

    items = [to_transaction_out(row, result) for _, row in page_df.iterrows()]

    return schemas.TransactionPage(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/graph", response_model=schemas.GraphOut)
def get_graph(
    scope: Literal["suspicious", "full", "cluster", "account"] = "suspicious",
    cluster_id: Optional[str] = None,
    account_id: Optional[str] = None,
    min_amount: Optional[float] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> schemas.GraphOut:
    """Endpoint 8: nodes and edges for Cytoscape graph visualization."""
    result = _require_run()
    settings = get_settings()

    target_accounts: Optional[set[str]] = None
    target_txs: Optional[set[str]] = None

    if scope == "cluster":
        if not cluster_id:
            raise HTTPException(status_code=400, detail="cluster_id is required when scope='cluster'")
        matching_c = next((c for c in result.clusters if c.cluster_id == cluster_id), None)
        if not matching_c:
            matching_c = next((rc for rc in result.detection.clusters if rc.cluster_id == cluster_id), None)
        if not matching_c:
            raise HTTPException(status_code=404, detail=f"Cluster {cluster_id} not found")

        accs = getattr(matching_c, "accounts", [])
        if accs and hasattr(accs[0], "account_id"):
            target_accounts = {a.account_id for a in accs}
        else:
            target_accounts = set(accs)
        target_txs = set(matching_c.transaction_ids)

    elif scope == "account":
        if not account_id:
            raise HTTPException(status_code=400, detail="account_id is required when scope='account'")
        G = result.detection.graph
        if not G.has_node(account_id):
            raise HTTPException(status_code=404, detail=f"Account {account_id} not found")
        target_accounts = {account_id}
        target_accounts.update(G.predecessors(account_id))
        target_accounts.update(G.successors(account_id))

    return build_graph_out(
        result=result,
        account_ids=target_accounts,
        transaction_ids=target_txs,
        scope=scope,
        min_amount=min_amount,
        start_time=start,
        end_time=end,
        max_edges=settings.MAX_GRAPH_EDGES,
    )


@router.get("/patterns", response_model=schemas.PatternList)
def get_patterns(
    type: Optional[schemas.PatternType] = None,
) -> schemas.PatternList:
    """Endpoint 9: raw pattern hits list."""
    result = _require_run()
    patterns = result.detection.patterns
    if type:
        patterns = [p for p in patterns if p.pattern_type == type]
    return schemas.PatternList(items=[to_pattern_out(p) for p in patterns])


@router.get("/accounts/{account_id}", response_model=schemas.AccountDetail)
def get_account_detail(account_id: str) -> schemas.AccountDetail:
    """Endpoint 10: account profile, risk, counterparties, transactions, and ego graph."""
    result = _require_run()
    features = result.detection.account_features.get(account_id)
    if not features:
        raise HTTPException(status_code=404, detail=f"Account {account_id} not found")

    # 1. Profile
    profile = schemas.AccountProfile(
        account_id=features.account_id,
        in_degree=features.in_degree,
        out_degree=features.out_degree,
        in_tx_count=features.in_tx_count,
        out_tx_count=features.out_tx_count,
        total_in=features.total_in,
        total_out=features.total_out,
        first_seen=features.first_seen,
        last_seen=features.last_seen,
        median_dwell_minutes=features.median_dwell_minutes,
        retention_ratio=features.retention_ratio,
        max_out_24h_amount=features.max_out_24h_amount,
        max_out_24h_count=features.max_out_24h_count,
    )

    # 2. Risk
    risk_rec = result.account_risk.get(account_id)
    risk = schemas.AccountRiskOut(
        risk_score=risk_rec.risk_score if risk_rec else None,
        risk_level=risk_rec.risk_level if risk_rec else "none",
        typologies=risk_rec.typologies if risk_rec else [],
        cluster_ids=risk_rec.cluster_ids if risk_rec else [],
    )

    # 3. Patterns
    patterns = [
        to_pattern_out(h)
        for h in result.detection.patterns
        if account_id in h.accounts
    ]

    # 4. Counterparties (top 20 by total amount)
    df = result.detection.transactions
    cp_amounts: dict[tuple[str, str], float] = defaultdict(float)
    cp_counts: dict[tuple[str, str], int] = defaultdict(int)

    acc_in = df[df["receiver"] == account_id]
    for _, r in acc_in.iterrows():
        key = (str(r["sender"]), "in")
        cp_amounts[key] += float(r["amount"])
        cp_counts[key] += 1

    acc_out = df[df["sender"] == account_id]
    for _, r in acc_out.iterrows():
        key = (str(r["receiver"]), "out")
        cp_amounts[key] += float(r["amount"])
        cp_counts[key] += 1

    counterparties: list[schemas.Counterparty] = []
    sorted_cps = sorted(cp_amounts.items(), key=lambda x: x[1], reverse=True)
    for (cp_id, direction), total_amt in sorted_cps[:20]:
        counterparties.append(
            schemas.Counterparty(
                account_id=cp_id,
                direction=direction,  # type: ignore
                tx_count=cp_counts[(cp_id, direction)],
                total_amount=round(total_amt, 2),
            )
        )

    # 5. Latest 200 transactions
    acc_all = df[(df["sender"] == account_id) | (df["receiver"] == account_id)]
    acc_sorted = acc_all.sort_values(by="timestamp", ascending=False).head(200)
    transactions = [to_transaction_out(row, result) for _, row in acc_sorted.iterrows()]

    # 6. Ego subgraph (1-hop)
    G = result.detection.graph
    ego_accounts = {account_id}
    if G.has_node(account_id):
        ego_accounts.update(G.predecessors(account_id))
        ego_accounts.update(G.successors(account_id))

    subgraph = build_graph_out(
        result=result,
        account_ids=ego_accounts,
        scope="account",
    )

    return schemas.AccountDetail(
        account=profile,
        risk=risk,
        patterns=patterns,
        counterparties=counterparties,
        transactions=transactions,
        subgraph=subgraph,
    )
