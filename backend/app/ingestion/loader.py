"""Database persistence and retrieval for datasets and transactions.
Follows PROJECT_CONTRACT.md Sections 4.2, 5, and 7."""
from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import Literal, Optional

import pandas as pd
from sqlalchemy import select

from app.db import SessionLocal
from app.ingestion.validator import validate_csv_bytes
from app.models import Dataset, Transaction
from app.schemas import DatasetInfo, ValidationReport


def save_dataset(
    name: str,
    source: Literal["upload", "sample"],
    clean_df: pd.DataFrame,
    has_labels: bool,
) -> DatasetInfo:
    """Store accepted rows into SQLite and return DatasetInfo."""
    dataset_id = f"ds_{uuid.uuid4().hex[:8]}"
    now = datetime.now()
    row_count = len(clean_df)

    db = SessionLocal()
    try:
        ds_record = Dataset(
            id=dataset_id,
            name=name,
            source=source,
            uploaded_at=now,
            row_count=row_count,
            has_labels=has_labels,
        )
        db.add(ds_record)

        if row_count > 0:
            tx_records = []
            for _, row in clean_df.iterrows():
                # Ensure timestamp is a python datetime object
                ts = row["timestamp"]
                if hasattr(ts, "to_pydatetime"):
                    ts = ts.to_pydatetime()

                tx_records.append(
                    Transaction(
                        dataset_id=dataset_id,
                        transaction_id=str(row["transaction_id"]),
                        sender=str(row["sender"]),
                        receiver=str(row["receiver"]),
                        amount=float(row["amount"]),
                        timestamp=ts,
                        currency=str(row.get("currency") or "INR"),
                        channel=row.get("channel") if pd.notna(row.get("channel")) else None,
                        label=row.get("label") if pd.notna(row.get("label")) else None,
                        gt_typology=row.get("gt_typology") if pd.notna(row.get("gt_typology")) else None,
                    )
                )
            db.bulk_save_objects(tx_records)

        db.commit()

        return DatasetInfo(
            dataset_id=dataset_id,
            name=name,
            source=source,
            uploaded_at=now,
            row_count=row_count,
            has_labels=has_labels,
        )
    finally:
        db.close()


def load_transactions_df(dataset_id: str) -> pd.DataFrame:
    """Load transactions for a dataset as a pandas DataFrame matching Section 7."""
    db = SessionLocal()
    try:
        stmt = (
            select(
                Transaction.transaction_id,
                Transaction.sender,
                Transaction.receiver,
                Transaction.amount,
                Transaction.timestamp,
                Transaction.currency,
                Transaction.channel,
                Transaction.label,
                Transaction.gt_typology,
            )
            .where(Transaction.dataset_id == dataset_id)
            .order_by(Transaction.timestamp.asc(), Transaction.id.asc())
        )
        rows = db.execute(stmt).all()

        columns = [
            "transaction_id",
            "sender",
            "receiver",
            "amount",
            "timestamp",
            "currency",
            "channel",
            "label",
            "gt_typology",
        ]

        if not rows:
            return pd.DataFrame(columns=columns)

        data = [
            {
                "transaction_id": r.transaction_id,
                "sender": r.sender,
                "receiver": r.receiver,
                "amount": float(r.amount),
                "timestamp": r.timestamp,
                "currency": r.currency,
                "channel": r.channel,
                "label": r.label,
                "gt_typology": r.gt_typology,
            }
            for r in rows
        ]

        df = pd.DataFrame(data, columns=columns)
        df["amount"] = df["amount"].astype(float)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df
    finally:
        db.close()


def ingest_csv_content(
    content: bytes,
    filename: str,
    source: Literal["upload", "sample"] = "upload",
) -> tuple[Optional[DatasetInfo], ValidationReport, pd.DataFrame]:
    """Validate CSV content and, if any rows accepted, persist dataset."""
    clean_df, report = validate_csv_bytes(content)
    if report.accepted_rows == 0:
        return None, report, clean_df

    dataset_info = save_dataset(
        name=filename,
        source=source,
        clean_df=clean_df,
        has_labels=report.has_labels,
    )
    return dataset_info, report, clean_df


def ingest_csv_file(
    file_path: str,
    source: Literal["upload", "sample"] = "sample",
) -> DatasetInfo:
    """Read a CSV file from disk, validate, and persist."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    filename = os.path.basename(file_path)
    with open(file_path, "rb") as f:
        content = f.read()

    dataset_info, report, _ = ingest_csv_content(content, filename, source=source)
    if dataset_info is None:
        raise ValueError(f"No valid rows found in {file_path}: {report.errors}")
    return dataset_info
