"""Tests for all detection algorithms: FAN_IN, FAN_OUT, CYCLE, PASS_THROUGH,
clusters, timing features, and engine orchestration.
Follows PROJECT_CONTRACT.md Section 6."""
from pathlib import Path

import pandas as pd
import pytest

from app.config import get_settings
from app.detection.clusters import form_clusters
from app.detection.cycles import detect_cycles
from app.detection.engine import run_detection
from app.detection.fan import detect_fan_in, detect_fan_out
from app.detection.pass_through import detect_pass_through
from app.detection.timing import compute_account_features
from app.graph.builder import build_graph
from app.ingestion.validator import validate_csv_bytes

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "mini.csv"


@pytest.fixture
def mini_dataset():
    """Load and parse mini.csv fixture."""
    with open(FIXTURE_PATH, "rb") as f:
        clean_df, report = validate_csv_bytes(f.read())
    G = build_graph(clean_df)
    cfg = get_settings()
    return clean_df, G, cfg


def test_fan_in_detection(mini_dataset):
    """Test FAN_IN detects both criminal collector and merchant funnel."""
    df, G, cfg = mini_dataset
    hits = detect_fan_in(df, G, cfg)

    focal_accounts = {h.focal_account for h in hits}
    assert "ACC_COLL_01" in focal_accounts
    assert "ACC_MERCHANT" in focal_accounts

    coll_hit = next(h for h in hits if h.focal_account == "ACC_COLL_01")
    assert coll_hit.pattern_type == "FAN_IN"
    assert coll_hit.metrics["counterparty_count"] == 6.0
    assert len(coll_hit.transaction_ids) == 6
    assert coll_hit.total_amount == 537000.0
    assert coll_hit.metrics["avg_amount"] > 0
    assert coll_hit.metrics["amount_cv"] >= 0
    assert coll_hit.metrics["window_hours"] <= cfg.FAN_WINDOW_HOURS

    senders = [a for a in coll_hit.accounts if a != "ACC_COLL_01"]
    assert len(senders) == 6
    assert "ACC_MULE_01" in senders


def test_fan_out_detection(mini_dataset):
    """Test FAN_OUT detects dispersion from ACC_DISP_01 to 6 receivers."""
    df, G, cfg = mini_dataset
    hits = detect_fan_out(df, G, cfg)

    focal_accounts = {h.focal_account for h in hits}
    assert "ACC_DISP_01" in focal_accounts

    disp_hit = next(h for h in hits if h.focal_account == "ACC_DISP_01")
    assert disp_hit.pattern_type == "FAN_OUT"
    assert disp_hit.metrics["counterparty_count"] == 6.0
    assert len(disp_hit.transaction_ids) == 6
    assert disp_hit.total_amount == 470000.0
    assert disp_hit.metrics["window_hours"] <= cfg.FAN_WINDOW_HOURS

    receivers = [a for a in disp_hit.accounts if a != "ACC_DISP_01"]
    assert len(receivers) == 6
    assert "ACC_RECV_01" in receivers


def test_cycle_detection(mini_dataset):
    """Test 3-node cycle detection on mini.csv (ACC_CYC_A -> B -> C -> A)."""
    df, G, cfg = mini_dataset
    hits = detect_cycles(df, G, cfg)

    assert len(hits) >= 1
    cyc_hit = hits[0]
    assert cyc_hit.pattern_type == "CYCLE"
    assert set(cyc_hit.accounts) == {"ACC_CYC_A", "ACC_CYC_B", "ACC_CYC_C"}
    assert cyc_hit.metrics["cycle_length"] == 3.0
    assert len(cyc_hit.transaction_ids) == 3
    assert cyc_hit.total_amount == 735000.0  # 250k + 245k + 240k
    assert cyc_hit.metrics["span_hours"] == 5.0  # 10:00 to 15:00
    assert cyc_hit.metrics["amount_retention"] == pytest.approx(0.96, abs=0.01)  # 240k / 250k


def test_cycle_wrong_timestamp_order_not_detected():
    """A geometric cycle where transactions occur in the wrong order must NOT be detected."""
    # A -> B at 12:00, B -> C at 10:00, C -> A at 15:00 (B->C occurred BEFORE A->B)
    csv_data = (
        "transaction_id,sender,receiver,amount,timestamp\n"
        "TX1,A,B,1000,2026-11-01T12:00:00\n"
        "TX2,B,C,1000,2026-11-01T10:00:00\n"
        "TX3,C,A,1000,2026-11-01T15:00:00\n"
    ).encode("utf-8")

    clean_df, _ = validate_csv_bytes(csv_data)
    G = build_graph(clean_df)
    cfg = get_settings()

    hits = detect_cycles(clean_df, G, cfg)
    assert len(hits) == 0


def test_pass_through_detection(mini_dataset):
    """Test 4-hop pass-through chain detection (ACC_PASS_1 -> 2 -> 3 -> 4 -> 5)."""
    df, G, cfg = mini_dataset
    hits = detect_pass_through(df, G, cfg)

    assert len(hits) >= 1
    pt_hit = next(h for h in hits if "ACC_PASS_1" in h.accounts)
    assert pt_hit.pattern_type == "PASS_THROUGH"
    assert pt_hit.focal_account == "ACC_PASS_1"
    assert pt_hit.metrics["hop_count"] == 4.0
    assert len(pt_hit.transaction_ids) == 4
    assert pt_hit.accounts == ["ACC_PASS_1", "ACC_PASS_2", "ACC_PASS_3", "ACC_PASS_4", "ACC_PASS_5"]
    assert pt_hit.metrics["flow_through_ratio"] == pytest.approx(0.90, abs=0.01)  # 450k / 500k
    assert pt_hit.metrics["median_hop_minutes"] == 90.0  # 90m, 90m, 120m -> median 90


def test_timing_account_features(mini_dataset):
    """Test topological and timing features (degrees, dwell time, retention, 24h volume)."""
    df, G, cfg = mini_dataset
    features = compute_account_features(df, G)

    coll = features["ACC_COLL_01"]
    assert coll.in_degree == 6
    assert coll.out_degree == 0
    assert coll.in_tx_count == 6
    assert coll.out_tx_count == 0
    assert coll.total_in == 537000.0
    assert coll.total_out == 0.0
    assert coll.median_dwell_minutes is None
    assert coll.retention_ratio == 1.0

    mule2 = features["ACC_PASS_2"]
    assert mule2.in_degree == 1
    assert mule2.out_degree == 1
    assert mule2.total_in == 500000.0
    assert mule2.total_out == 480000.0
    assert mule2.median_dwell_minutes == 90.0
    assert mule2.retention_ratio == pytest.approx(0.04, abs=0.001)


def test_run_detection_engine_complete(mini_dataset):
    """Test end-to-end detection engine: all patterns, clustering, and ID ordering."""
    df, G, cfg = mini_dataset
    detection = run_detection(df, G, cfg)

    # 1. Pattern hits found
    types = {h.pattern_type for h in detection.patterns}
    assert "FAN_IN" in types
    assert "FAN_OUT" in types
    assert "CYCLE" in types
    assert "PASS_THROUGH" in types

    # 2. Sequential IDs sorted by start_time
    for idx, hit in enumerate(detection.patterns, 1):
        assert hit.pattern_id == f"PT-{idx:04d}"
        assert hit.cluster_id is not None
        assert hit.cluster_id.startswith("CL-")

    # 3. Clusters properly formed
    assert len(detection.clusters) >= 4  # fan-in, fan-out, cycle, pass-through, plus merchant
    for idx, cluster in enumerate(detection.clusters, 1):
        assert cluster.cluster_id == f"CL-{idx:04d}"
        assert len(cluster.accounts) >= 2
        assert len(cluster.transaction_ids) >= 1
        assert len(cluster.pattern_ids) >= 1

    # 4. Account features have patterns linked
    coll = detection.account_features["ACC_COLL_01"]
    assert len(coll.pattern_ids) >= 1
    assert any(pid.startswith("PT-") for pid in coll.pattern_ids)
