"""Tests for alerts, account risk, explanations, baseline and evaluation (Member 3)."""
from datetime import datetime

import pandas as pd
import pytest

from app.config import get_settings
from app.contracts import (
    DISCLAIMER, BaselineOutput, ClusterAccountRole, Explanation, ScoredCluster,
)
from app.evaluation import evaluate, run_baseline
from app.evaluation.metrics import confusion, scores
from app.intelligence import build_alerts, compute_account_risk


def _tx(rows):
    df = pd.DataFrame(rows, columns=["transaction_id", "sender", "receiver", "amount", "timestamp", "label", "gt_typology"])
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["currency"] = "INR"
    df["channel"] = None
    return df


def _cluster(cid, score, level, alerted, accounts, tx_ids, typ=("PASS_THROUGH",), amount=100.0):
    return ScoredCluster(
        cluster_id=cid,
        accounts=[ClusterAccountRole(a, "member", 0.0, 0.0) for a in accounts],
        transaction_ids=list(tx_ids), pattern_ids=[], typologies=list(typ), primary_typology=typ[0],
        risk_score=score, risk_level=level, alerted=alerted, score_breakdown=[],
        explanation=Explanation(f"headline {cid}", "s", [], [], DISCLAIMER),
        total_amount=amount, start_time=datetime(2026, 11, 1), end_time=datetime(2026, 11, 2),
        median_hop_minutes=None,
    )


def test_metrics_from_hand_made_confusion_matrix():
    m = scores({"tp": 8, "fp": 2, "fn": 4, "tn": 86})
    assert m["precision"] == 0.8 and m["recall"] == 0.6667 and m["f1"] == 0.7273 and m["accuracy"] == 0.94


def test_zero_division_is_zero():
    assert scores({"tp": 0, "fp": 0, "fn": 0, "tn": 5}) == {"precision": 0.0, "recall": 0.0, "f1": 0.0, "accuracy": 1.0}
    assert confusion([True, False], [False, True]) == {"tp": 0, "fp": 1, "fn": 1, "tn": 0}


def test_baseline_rules_fire():
    cfg = get_settings()
    rows = [("T1", "A", "B", 1_200_000, "2026-11-01 10:00", "normal", None)]          # R1
    rows += [(f"V{i}", "C", f"X{i}", 1000, f"2026-11-01 {10+i%10}:0{i//10}", "normal", None) for i in range(10)]  # R3
    rows += [("D1", "D", "Y", 900_000, "2026-11-01 09:00", "normal", None),
             ("D2", "D", "Y", 900_000, "2026-11-01 12:00", "normal", None),
             ("D3", "D", "Y", 900_000, "2026-11-01 15:00", "normal", None)]               # R2 on D3
    rows += [("N1", "E", "F", 500, "2026-11-01 10:00", "normal", None)]
    out = run_baseline(_tx(rows), cfg)
    assert out.rules_triggered["T1"] == ["R1_LARGE_AMOUNT"]
    assert "R3_VELOCITY" in out.rules_triggered[sorted(t for t in out.rules_triggered if t.startswith("V"))[-1]]
    assert out.rules_triggered["D3"] == ["R2_DAILY_VOLUME"] and "D1" not in out.rules_triggered
    assert "N1" not in out.flagged_transaction_ids


def test_evaluate_uses_alerted_clusters_and_labels():
    cfg = get_settings()
    df = _tx([("S1", "A", "B", 10, "2026-11-01", "suspicious", "PASS_THROUGH"),
              ("S2", "B", "C", 10, "2026-11-01", "suspicious", "PASS_THROUGH"),
              ("N1", "D", "E", 10, "2026-11-01", "normal", None),
              ("U1", "F", "G", 10, "2026-11-01", None, None)])
    clusters = [_cluster("CL-0001", 80, "high", True, ["A", "B", "C"], ["S1", "S2"]),
                _cluster("CL-0002", 20, "low", False, ["D", "E"], ["N1"])]
    ev = evaluate(df, clusters, BaselineOutput({"N1"}, {"N1": ["R1_LARGE_AMOUNT"]}), cfg)
    assert ev["available"] and ev["total"] == 3 and ev["positives"] == 2
    graph, base = ev["models"]
    assert graph["confusion_matrix"] == {"tp": 2, "fp": 0, "fn": 0, "tn": 1}
    assert base["confusion_matrix"] == {"tp": 0, "fp": 1, "fn": 2, "tn": 0}
    assert ev["per_typology"][0]["typology"] == "PASS_THROUGH" and ev["per_typology"][0]["graph_recall"] == 1.0


def test_evaluate_unavailable_without_labels():
    df = _tx([("A1", "A", "B", 10, "2026-11-01", None, None)])
    ev = evaluate(df, [], BaselineOutput(set(), {}), get_settings())
    assert ev["available"] is False and ev["reason"]


def test_alerts_only_for_alerted_clusters_ordered_by_risk():
    cs = [_cluster("CL-0001", 50, "medium", True, ["A"], ["T1"]),
          _cluster("CL-0002", 90, "high", True, ["B"], ["T2"]),
          _cluster("CL-0003", 20, "low", False, ["C"], ["T3"])]
    alerts = build_alerts(cs, get_settings())
    assert [a.cluster_id for a in alerts] == ["CL-0002", "CL-0001"]
    assert [a.alert_id for a in alerts] == ["AL-0001", "AL-0002"]


def test_account_risk_is_max_over_clusters():
    cs = [_cluster("CL-0001", 50, "medium", True, ["A", "B"], ["T1"], typ=("FAN_IN",)),
          _cluster("CL-0002", 90, "high", True, ["B"], ["T2"], typ=("CYCLE",))]
    risk = compute_account_risk(cs)
    assert risk["A"].risk_score == 50
    assert risk["B"].risk_score == 90 and risk["B"].risk_level == "high"
    assert risk["B"].typologies == ["CYCLE", "FAN_IN"] and risk["B"].cluster_ids == ["CL-0001", "CL-0002"]


def test_full_sample_end_to_end_api():
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        assert c.post("/api/dataset/load-sample").status_code == 200
        ov = c.get("/api/overview").json()
        assert ov["stats"]["alerts"] > 0 and ov["headline_metrics"] is not None
        cl = c.get("/api/clusters").json()["items"]
        assert any(x["alerted"] for x in cl) and any(not x["alerted"] for x in cl)
        d = c.get(f"/api/clusters/{cl[0]['cluster_id']}").json()
        ev_ids = {e["transaction_id"] for e in d["explanation"]["evidence"]}
        assert ev_ids and ev_ids <= {t["transaction_id"] for t in d["transactions"]}
        assert d["explanation"]["disclaimer"] == DISCLAIMER and d["subgraph"]["edges"]
        ev = c.get("/api/evaluation").json()
        assert ev["available"] and ev["label_source"] == "synthetic" and len(ev["models"]) == 2
        for m in ev["models"]:
            assert sum(m["confusion_matrix"].values()) == ev["total"]
        assert c.get("/api/clusters/CL-9999").status_code == 404
        assert c.get("/api/alerts?level=high").status_code == 200
