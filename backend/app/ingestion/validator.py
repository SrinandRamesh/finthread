"""CSV validator for transaction datasets. Follows PROJECT_CONTRACT.md Section 4.1."""
from __future__ import annotations

import io
import math
from datetime import datetime
from typing import Optional, Set

import pandas as pd

from app.schemas import RowError, ValidationReport

VALID_TYPOLOGIES: Set[str] = {
    "FAN_IN",
    "FAN_OUT",
    "CYCLE",
    "PASS_THROUGH",
    "SCATTER_GATHER",
}

VALID_LABELS: Set[str] = {"suspicious", "normal"}

REQUIRED_COLUMNS: list[str] = [
    "transaction_id",
    "sender",
    "receiver",
    "amount",
    "timestamp",
]


def _clean_str(val: object) -> Optional[str]:
    if val is None or pd.isna(val):
        return None
    s = str(val).strip()
    return s if s else None


def _parse_timestamp(val_str: str) -> Optional[datetime]:
    try:
        # Fast path for ISO formatted strings with 'T' or space
        dt = datetime.fromisoformat(val_str)
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        return dt
    except Exception:
        try:
            ts = pd.to_datetime(val_str)
            if pd.isna(ts):
                return None
            dt = ts.to_pydatetime()
            if dt.tzinfo is not None:
                dt = dt.replace(tzinfo=None)
            return dt
        except Exception:
            return None


def validate_dataframe(df_raw: pd.DataFrame) -> tuple[pd.DataFrame, ValidationReport]:
    """Validate raw DataFrame (already read with dtype=str).
    Returns (clean_df, ValidationReport).
    clean_df has exact columns with parsed types.
    """
    total_rows = len(df_raw)
    errors: list[RowError] = []
    accepted_records: list[dict] = []
    seen_tx_ids: set[str] = set()
    has_labels = False

    # Normalise column names (case-insensitive, trimmed)
    col_map = {str(col).strip().lower(): col for col in df_raw.columns}

    # Check for missing required columns in the header
    missing_required = [col for col in REQUIRED_COLUMNS if col not in col_map]
    if missing_required:
        for idx in range(total_rows):
            row_num = idx + 2
            for col in missing_required:
                errors.append(
                    RowError(
                        row_number=row_num,
                        transaction_id=None,
                        field=col,
                        message=f"Missing required column in CSV header: '{col}'",
                    )
                )
        return (
            pd.DataFrame(
                columns=[
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
            ),
            ValidationReport(
                total_rows=total_rows,
                accepted_rows=0,
                rejected_rows=total_rows,
                has_labels=False,
                errors=errors[:100],
            ),
        )

    # Process each row (row numbers start at 2 for the first data row)
    for idx, row in df_raw.iterrows():
        row_number = int(idx) + 2
        row_failed = False

        # 1. transaction_id
        raw_tx_id = _clean_str(row.get(col_map["transaction_id"]))
        if not raw_tx_id:
            errors.append(
                RowError(
                    row_number=row_number,
                    transaction_id=None,
                    field="transaction_id",
                    message="Missing required field: transaction_id",
                )
            )
            continue

        if raw_tx_id in seen_tx_ids:
            errors.append(
                RowError(
                    row_number=row_number,
                    transaction_id=raw_tx_id,
                    field="transaction_id",
                    message=f"Duplicate transaction_id: {raw_tx_id} (first occurrence kept)",
                )
            )
            continue

        # 2. sender
        sender = _clean_str(row.get(col_map["sender"]))
        if not sender:
            errors.append(
                RowError(
                    row_number=row_number,
                    transaction_id=raw_tx_id,
                    field="sender",
                    message="Missing required field: sender",
                )
            )
            row_failed = True

        # 3. receiver
        receiver = _clean_str(row.get(col_map["receiver"]))
        if not receiver:
            errors.append(
                RowError(
                    row_number=row_number,
                    transaction_id=raw_tx_id,
                    field="receiver",
                    message="Missing required field: receiver",
                )
            )
            row_failed = True

        # Sender must differ from receiver
        if sender and receiver and sender == receiver:
            errors.append(
                RowError(
                    row_number=row_number,
                    transaction_id=raw_tx_id,
                    field="receiver",
                    message="Sender and receiver must be different accounts",
                )
            )
            row_failed = True

        # 4. amount
        raw_amount = _clean_str(row.get(col_map["amount"]))
        amount: Optional[float] = None
        if not raw_amount:
            errors.append(
                RowError(
                    row_number=row_number,
                    transaction_id=raw_tx_id,
                    field="amount",
                    message="Missing required field: amount",
                )
            )
            row_failed = True
        else:
            try:
                # Remove commas if any, e.g. "1,000.50"
                cleaned_amount = raw_amount.replace(",", "")
                amount = float(cleaned_amount)
                if amount <= 0 or not math.isfinite(amount):
                    errors.append(
                        RowError(
                            row_number=row_number,
                            transaction_id=raw_tx_id,
                            field="amount",
                            message="Amount must be a positive number",
                        )
                    )
                    row_failed = True
            except (ValueError, TypeError):
                errors.append(
                    RowError(
                        row_number=row_number,
                        transaction_id=raw_tx_id,
                        field="amount",
                        message="Amount must be a positive number",
                    )
                )
                row_failed = True

        # 5. timestamp
        raw_ts = _clean_str(row.get(col_map["timestamp"]))
        dt: Optional[datetime] = None
        if not raw_ts:
            errors.append(
                RowError(
                    row_number=row_number,
                    transaction_id=raw_tx_id,
                    field="timestamp",
                    message="Missing required field: timestamp",
                )
            )
            row_failed = True
        else:
            dt = _parse_timestamp(raw_ts)
            if dt is None:
                errors.append(
                    RowError(
                        row_number=row_number,
                        transaction_id=raw_tx_id,
                        field="timestamp",
                        message=f"Unparseable timestamp: {raw_ts}",
                    )
                )
                row_failed = True

        # 6. Optional: currency (default INR)
        currency = "INR"
        if "currency" in col_map:
            c = _clean_str(row.get(col_map["currency"]))
            if c:
                currency = c

        # 7. Optional: channel
        channel: Optional[str] = None
        if "channel" in col_map:
            ch = _clean_str(row.get(col_map["channel"]))
            if ch:
                channel = ch.upper()

        # 8. Optional: label
        label: Optional[str] = None
        if "label" in col_map:
            lbl = _clean_str(row.get(col_map["label"]))
            if lbl:
                lbl_lower = lbl.lower()
                if lbl_lower not in VALID_LABELS:
                    errors.append(
                        RowError(
                            row_number=row_number,
                            transaction_id=raw_tx_id,
                            field="label",
                            message=f"Invalid label: {lbl}. Must be 'suspicious', 'normal', or blank.",
                        )
                    )
                    row_failed = True
                else:
                    label = lbl_lower
                    has_labels = True

        # 9. Optional: gt_typology
        gt_typology: Optional[str] = None
        if "gt_typology" in col_map:
            gt = _clean_str(row.get(col_map["gt_typology"]))
            if gt:
                gt_upper = gt.upper()
                if gt_upper not in VALID_TYPOLOGIES:
                    errors.append(
                        RowError(
                            row_number=row_number,
                            transaction_id=raw_tx_id,
                            field="gt_typology",
                            message=f"Invalid gt_typology: {gt}. Must be one of {sorted(VALID_TYPOLOGIES)} or blank.",
                        )
                    )
                    row_failed = True
                else:
                    gt_typology = gt_upper

        if not row_failed and amount is not None and dt is not None and sender and receiver:
            seen_tx_ids.add(raw_tx_id)
            accepted_records.append(
                {
                    "transaction_id": raw_tx_id,
                    "sender": sender,
                    "receiver": receiver,
                    "amount": amount,
                    "timestamp": dt,
                    "currency": currency,
                    "channel": channel,
                    "label": label,
                    "gt_typology": gt_typology,
                }
            )

    accepted_rows = len(accepted_records)
    rejected_rows = total_rows - accepted_rows

    if accepted_records:
        clean_df = pd.DataFrame(accepted_records)
        clean_df["amount"] = clean_df["amount"].astype(float)
        clean_df["timestamp"] = pd.to_datetime(clean_df["timestamp"])
    else:
        clean_df = pd.DataFrame(
            columns=[
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
        )

    report = ValidationReport(
        total_rows=total_rows,
        accepted_rows=accepted_rows,
        rejected_rows=rejected_rows,
        has_labels=has_labels,
        errors=errors[:100],
    )

    return clean_df, report


def validate_csv_bytes(content: bytes) -> tuple[pd.DataFrame, ValidationReport]:
    """Parse raw bytes as CSV using dtype=str first, then validate."""
    stream = io.BytesIO(content)
    df_raw = pd.read_csv(stream, dtype=str, keep_default_na=False)
    return validate_dataframe(df_raw)
