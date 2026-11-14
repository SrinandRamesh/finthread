"""Tests for core API routes (Endpoints 1-10 in PROJECT_CONTRACT.md Section 10)."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db import init_db
from app.main import app
from app.state import set_current_result

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "mini.csv"


@pytest.fixture(autouse=True)
def setup_clean_db():
    init_db()


def test_409_before_any_run():
    """Endpoints 7-10 must return HTTP 409 before any dataset is loaded."""
    set_current_result(None)  # reset state
    client = TestClient(app)

    r_tx = client.get("/api/transactions")
    assert r_tx.status_code == 409
    assert "No analysis run yet" in r_tx.json()["detail"]

    r_gr = client.get("/api/graph")
    assert r_gr.status_code == 409

    r_pt = client.get("/api/patterns")
    assert r_pt.status_code == 409

    r_ac = client.get("/api/accounts/ACC0001")
    assert r_ac.status_code == 409

    r_an = client.post("/api/analyze", json={})
    assert r_an.status_code == 409


def test_core_endpoints_complete_flow():
    """Upload mini.csv and test all core endpoints 1-10 validate against schemas."""
    client = TestClient(app)

    # 1. Health
    r_health = client.get("/api/health")
    assert r_health.status_code == 200

    # 2. Upload and analyze
    with open(FIXTURE_PATH, "rb") as f:
        r_upload = client.post(
            "/api/upload",
            files={"file": ("mini.csv", f, "text/csv")},
            params={"analyze": "true"},
        )
    assert r_upload.status_code == 200
    upload_data = r_upload.json()
    assert upload_data["run"]["status"] == "completed"

    # Health now shows dataset_loaded = True
    r_health2 = client.get("/api/health")
    assert r_health2.json()["dataset_loaded"] is True

    # 3. Config
    r_cfg = client.get("/api/config")
    assert r_cfg.status_code == 200
    assert "detection" in r_cfg.json()

    # 4. Analyze endpoint (re-run with override)
    r_analyze = client.post(
        "/api/analyze",
        json={"overrides": {"FAN_MIN_COUNTERPARTIES": 6}},
    )
    assert r_analyze.status_code == 200
    assert r_analyze.json()["status"] == "completed"

    # 5. Transactions endpoint
    r_txs = client.get("/api/transactions", params={"page": 1, "page_size": 20})
    assert r_txs.status_code == 200
    txs_data = r_txs.json()
    assert txs_data["total"] == 40
    assert len(txs_data["items"]) == 20
    assert "prediction" in txs_data["items"][0]

    # Filter transactions by account
    r_txs_acc = client.get("/api/transactions", params={"account": "ACC_COLL_01"})
    assert r_txs_acc.status_code == 200
    assert r_txs_acc.json()["total"] == 6

    # 6. Graph endpoint (scope=suspicious)
    r_graph = client.get("/api/graph", params={"scope": "suspicious"})
    assert r_graph.status_code == 200
    graph_data = r_graph.json()
    assert "nodes" in graph_data
    assert "edges" in graph_data
    assert graph_data["meta"]["scope"] == "suspicious"

    # Graph endpoint (scope=full)
    r_graph_full = client.get("/api/graph", params={"scope": "full"})
    assert r_graph_full.status_code == 200
    assert len(r_graph_full.json()["edges"]) == 40

    # 7. Patterns endpoint
    r_pat = client.get("/api/patterns")
    assert r_pat.status_code == 200
    pat_data = r_pat.json()
    assert len(pat_data["items"]) >= 4

    # Filter pattern by type
    r_pat_fi = client.get("/api/patterns", params={"type": "FAN_IN"})
    assert r_pat_fi.status_code == 200
    for p in r_pat_fi.json()["items"]:
        assert p["pattern_type"] == "FAN_IN"

    # 8. Account detail endpoint
    r_acc = client.get("/api/accounts/ACC_COLL_01")
    assert r_acc.status_code == 200
    acc_data = r_acc.json()
    assert acc_data["account"]["account_id"] == "ACC_COLL_01"
    assert acc_data["account"]["in_degree"] == 6
    assert len(acc_data["counterparties"]) == 6
    assert len(acc_data["transactions"]) == 6
    assert "subgraph" in acc_data

    # Unknown account -> 404
    r_unknown = client.get("/api/accounts/UNKNOWN_ACCOUNT")
    assert r_unknown.status_code == 404
