"""Tests for data ingestion, validation rules, persistence, and upload endpoints.
Follows PROJECT_CONTRACT.md Sections 4.1, 4.2, 5, 7, and 10."""
import os
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.db import init_db
from app.ingestion.loader import ingest_csv_content, load_transactions_df, save_dataset
from app.ingestion.validator import validate_csv_bytes
from app.main import app

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "mini.csv"


@pytest.fixture(autouse=True)
def setup_database():
    """Ensure DB schema is initialized for tests."""
    init_db()


def test_valid_rows_accepted_from_fixture():
    """Verify all 40 valid rows from mini.csv are accepted with zero errors."""
    with open(FIXTURE_PATH, "rb") as f:
        content = f.read()

    clean_df, report = validate_csv_bytes(content)

    assert report.total_rows == 40
    assert report.accepted_rows == 40
    assert report.rejected_rows == 0
    assert len(report.errors) == 0
    assert report.has_labels is True

    # Check dataframe schema and types
    assert len(clean_df) == 40
    assert clean_df["amount"].dtype == "float64"
    assert pd.api.types.is_datetime64_any_dtype(clean_df["timestamp"])
    assert "transaction_id" in clean_df.columns
    assert "sender" in clean_df.columns
    assert "receiver" in clean_df.columns

    # Test persistence and reload
    ds_info = save_dataset(
        name="test_mini.csv",
        source="upload",
        clean_df=clean_df,
        has_labels=report.has_labels,
    )
    assert ds_info.row_count == 40
    assert ds_info.dataset_id.startswith("ds_")

    loaded_df = load_transactions_df(ds_info.dataset_id)
    assert len(loaded_df) == 40
    assert pd.api.types.is_datetime64_any_dtype(loaded_df["timestamp"])


def test_rejection_missing_required_fields():
    """Each missing required field should produce a rejection error."""
    csv_missing = (
        "transaction_id,sender,receiver,amount,timestamp\n"
        ",ACC1,ACC2,100,2026-11-01T10:00:00\n"  # missing tx_id
        "TX2,,ACC2,100,2026-11-01T10:00:00\n"   # missing sender
        "TX3,ACC1,,100,2026-11-01T10:00:00\n"   # missing receiver
        "TX4,ACC1,ACC2,,2026-11-01T10:00:00\n"  # missing amount
        "TX5,ACC1,ACC2,100,\n"                  # missing timestamp
    ).encode("utf-8")

    clean_df, report = validate_csv_bytes(csv_missing)
    assert report.total_rows == 5
    assert report.accepted_rows == 0
    assert report.rejected_rows == 5
    assert len(report.errors) == 5

    fields_with_errors = [e.field for e in report.errors]
    assert "transaction_id" in fields_with_errors
    assert "sender" in fields_with_errors
    assert "receiver" in fields_with_errors
    assert "amount" in fields_with_errors
    assert "timestamp" in fields_with_errors


def test_rejection_sender_equals_receiver():
    """Sender identical to receiver must be rejected."""
    csv_data = (
        "transaction_id,sender,receiver,amount,timestamp\n"
        "TX1,ACC001,ACC001,500,2026-11-01T10:00:00\n"
    ).encode("utf-8")

    clean_df, report = validate_csv_bytes(csv_data)
    assert report.accepted_rows == 0
    assert report.rejected_rows == 1
    assert "different accounts" in report.errors[0].message


def test_rejection_invalid_amount():
    """Negative, zero, and non-numeric amounts must be rejected."""
    csv_data = (
        "transaction_id,sender,receiver,amount,timestamp\n"
        "TX1,ACC1,ACC2,0,2026-11-01T10:00:00\n"
        "TX2,ACC1,ACC2,-150.50,2026-11-01T10:00:00\n"
        "TX3,ACC1,ACC2,abc,2026-11-01T10:00:00\n"
    ).encode("utf-8")

    clean_df, report = validate_csv_bytes(csv_data)
    assert report.accepted_rows == 0
    assert report.rejected_rows == 3
    for err in report.errors:
        assert err.field == "amount"
        assert "positive number" in err.message


def test_rejection_unparseable_timestamp():
    """Invalid datetime format must be rejected."""
    csv_data = (
        "transaction_id,sender,receiver,amount,timestamp\n"
        "TX1,ACC1,ACC2,100,not-a-valid-date\n"
    ).encode("utf-8")

    clean_df, report = validate_csv_bytes(csv_data)
    assert report.accepted_rows == 0
    assert report.rejected_rows == 1
    assert report.errors[0].field == "timestamp"
    assert "Unparseable timestamp" in report.errors[0].message


def test_rejection_duplicate_transaction_id():
    """First transaction_id is accepted; subsequent duplicates are rejected."""
    csv_data = (
        "transaction_id,sender,receiver,amount,timestamp\n"
        "TX_DUP,ACC1,ACC2,100,2026-11-01T10:00:00\n"
        "TX_DUP,ACC3,ACC4,200,2026-11-01T11:00:00\n"
    ).encode("utf-8")

    clean_df, report = validate_csv_bytes(csv_data)
    assert report.total_rows == 2
    assert report.accepted_rows == 1
    assert report.rejected_rows == 1
    assert report.errors[0].transaction_id == "TX_DUP"
    assert "Duplicate transaction_id" in report.errors[0].message
    assert clean_df.iloc[0]["sender"] == "ACC1"


def test_rejection_invalid_label_and_typology():
    """Labels must be in {suspicious, normal, blank} and typology must be recognized."""
    csv_data = (
        "transaction_id,sender,receiver,amount,timestamp,label,gt_typology\n"
        "TX1,ACC1,ACC2,100,2026-11-01T10:00:00,fraud,FAN_IN\n"
        "TX2,ACC1,ACC3,100,2026-11-01T10:00:00,suspicious,UNKNOWN_CODE\n"
    ).encode("utf-8")

    clean_df, report = validate_csv_bytes(csv_data)
    assert report.accepted_rows == 0
    assert report.rejected_rows == 2
    assert report.errors[0].field == "label"
    assert report.errors[1].field == "gt_typology"


def test_label_columns_detected():
    """has_labels should be True only when labels exist in data."""
    csv_no_labels = (
        "transaction_id,sender,receiver,amount,timestamp\n"
        "TX1,ACC1,ACC2,100,2026-11-01T10:00:00\n"
    ).encode("utf-8")

    clean_df, report = validate_csv_bytes(csv_no_labels)
    assert report.accepted_rows == 1
    assert report.has_labels is False

    csv_with_labels = (
        "transaction_id,sender,receiver,amount,timestamp,label\n"
        "TX1,ACC1,ACC2,100,2026-11-01T10:00:00,suspicious\n"
    ).encode("utf-8")

    clean_df2, report2 = validate_csv_bytes(csv_with_labels)
    assert report2.accepted_rows == 1
    assert report2.has_labels is True


def test_row_numbers_counted_from_two():
    """First data row has row_number=2, second has row_number=3."""
    csv_data = (
        "transaction_id,sender,receiver,amount,timestamp\n"
        "TX1,ACC1,ACC2,invalid_amount,2026-11-01T10:00:00\n"
        "TX2,ACC1,ACC2,200,invalid_date\n"
    ).encode("utf-8")

    _, report = validate_csv_bytes(csv_data)
    assert report.errors[0].row_number == 2
    assert report.errors[1].row_number == 3


def test_api_upload_and_analyze():
    """Test POST /api/upload endpoint with valid CSV and analyze=True."""
    client = TestClient(app)

    with open(FIXTURE_PATH, "rb") as f:
        response = client.post(
            "/api/upload",
            files={"file": ("mini.csv", f, "text/csv")},
            params={"analyze": "true"},
        )

    assert response.status_code == 200
    data = response.json()

    assert data["dataset"]["name"] == "mini.csv"
    assert data["dataset"]["row_count"] == 40
    assert data["validation"]["accepted_rows"] == 40
    assert data["validation"]["rejected_rows"] == 0
    assert data["run"] is not None
    assert data["run"]["status"] == "completed"
    assert data["run"]["counts"]["transactions"] == 40

    # Check health now reflects loaded dataset
    health_resp = client.get("/api/health")
    assert health_resp.status_code == 200
    health_data = health_resp.json()
    assert health_data["dataset_loaded"] is True
    assert health_data["run_id"] == data["run"]["run_id"]


def test_api_upload_zero_rows_rejected():
    """Upload with zero accepted rows must return HTTP 400."""
    client = TestClient(app)

    bad_csv = b"transaction_id,sender,receiver,amount,timestamp\nTX1,ACC1,ACC1,100,2026-11-01T10:00:00\n"
    response = client.post(
        "/api/upload",
        files={"file": ("bad.csv", bad_csv, "text/csv")},
    )

    assert response.status_code == 400
    assert "No valid transactions" in response.json()["detail"]


def test_api_config():
    """GET /api/config returns grouped configuration."""
    client = TestClient(app)
    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    assert "detection" in data
    assert "risk" in data
    assert "baseline" in data
    assert data["detection"]["FAN_MIN_COUNTERPARTIES"] == 5
    assert data["risk"]["ALERT_THRESHOLD"] == 40
