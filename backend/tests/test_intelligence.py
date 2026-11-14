"""Tests for Member 3's intelligence package (hand-built DetectionOutput, no engine needed)."""
from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace

import networkx as nx
import pandas as pd

from app.config import Settings
from app.contracts import DISCLAIMER, DetectionOutput, PatternHit, RawCluster
from app.intelligence import score_clusters
from app.intelligence.formatting import format_inr, format_minutes
from app.intelligence.risk import (
    _flow_through_factor,
    _structuring_factor,
    _velocity_factor,
    compute_roles,
    median_hop_minutes,
)
from app.intelligence.typology import derive_typologies, primary_typology

T0 = datetime(2026, 11, 9, 14, 2, 0)


# ------------------------------------------------------------------ builders
def make_df(rows, label=None):
    """rows: (transaction_id, sender, receiver, amount, datetime)"""
    df = pd.DataFrame(rows, columns=["transaction_id", "sender", "receiver", "amount", "timestamp"])
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["amount"] = df["amount"].astype(float)
    df["currency"] = "INR"
    df["channel"] = "IMPS"
    df["label"] = label
    df["gt_typology"] = None
    return df


def make_hit(pid, ptype, focal, accounts, df, tx_ids=None):
    ids = tx_ids or list(df["transaction_id"])
    sub = df[df["transaction_id"].isin(ids)]
    return PatternHit(
        pattern_id=pid,
        pattern_type=ptype,
        focal_account=focal,
        accounts=accounts,
        transaction_ids=ids,
        start_time=sub["timestamp"].min().to_pydatetime(),
        end_time=sub["timestamp"].max().to_pydatetime(),
        total_amount=float(sub["amount"].sum()),
    )


def make_detection(df, hits, cluster_id="CL-0001"):
    cluster = RawCluster(
        cluster_id=cluster_id,
        accounts=sorted(set(df["sender"]) | set(df["receiver"])),
        transaction_ids=list(df["transaction_id"]),
        pattern_ids=[h.pattern_id for h in hits],
    )
    return DetectionOutput(
        transactions=df, graph=nx.MultiDiGraph(), patterns=hits, clusters=[cluster], account_features={}
    )


def chain_df(label=None, hops=5, start_amount=990_000.0, ratio=0.98, hop_minutes=38):
    """A fast pass-through chain: ACC0100 -> ACC0101 -> ... with structured amounts."""
    rows, amount, t = [], start_amount, T0
    for i in range(hops):
        rows.append((f"TX{i + 1:06d}", f"ACC{100 + i}", f"ACC{101 + i}", round(amount), t))
        amount *= ratio
        t = t + timedelta(minutes=hop_minutes)
    return make_df(rows, label=label)


def chain_detection(label=None):
    df = chain_df(label=label)
    accounts = [f"ACC{100 + i}" for i in range(6)]
    hit = make_hit("PT-0001", "PASS_THROUGH", accounts[0], accounts, df)
    return make_detection(df, [hit])


def merchant_detection(n=60):
    rows = [
        (f"TX{i + 1:06d}", f"ACC{1000 + i}", "ACC0900", 500 + (i * 37) % 2500, T0 + timedelta(minutes=17 * i))
        for i in range(n)
    ]
    df = make_df(rows)
    accounts = ["ACC0900"] + [f"ACC{1000 + i}" for i in range(n)]
    hit = make_hit("PT-0001", "FAN_IN", "ACC0900", accounts, df)
    return make_detection(df, [hit])


# ------------------------------------------------------------------ formatting
def test_format_inr_indian_grouping():
    assert format_inr(985000) == "₹9,85,000"
    assert format_inr(1234567) == "₹12,34,567"
    assert format_inr(6240000) == "₹62,40,000"
    assert format_inr(100000) == "₹1,00,000"
    assert format_inr(999) == "₹999"
    assert format_inr(0) == "₹0"
    assert format_inr(985000.4) == "₹9,85,000"


def test_format_minutes():
    assert format_minutes(38) == "38 min"
    assert format_minutes(190) == "3 h 10 min"
    assert format_minutes(120) == "2 h"
    assert format_minutes(3000) == "2 d 2 h"
    assert format_minutes(None) == "n/a"


# ------------------------------------------------------------------ typology
def test_derive_typologies_distinct_and_severity_ordered():
    df = chain_df()
    a = make_hit("PT-1", "FAN_IN", "ACC1", ["ACC1", "ACC2"], df)
    b = make_hit("PT-2", "PASS_THROUGH", "ACC2", ["ACC2", "ACC3"], df)
    c = make_hit("PT-3", "FAN_IN", "ACC4", ["ACC4", "ACC5"], df)
    assert derive_typologies([a, b, c]) == ["PASS_THROUGH", "FAN_IN"]


def test_primary_typology_follows_severity_order():
    assert primary_typology(["FAN_IN", "FAN_OUT"]) == "FAN_OUT"
    assert primary_typology(["FAN_OUT", "SCATTER_GATHER"]) == "SCATTER_GATHER"
    assert primary_typology(["SCATTER_GATHER", "PASS_THROUGH"]) == "PASS_THROUGH"
    assert primary_typology(["PASS_THROUGH", "CYCLE", "FAN_IN"]) == "CYCLE"


def _fan_hits(overlap_receivers, total_receivers=6):
    df = chain_df()
    receivers = [f"M{i}" for i in range(total_receivers)]
    fan_out = make_hit("PT-1", "FAN_OUT", "SRC", ["SRC"] + receivers, df)
    senders = receivers[:overlap_receivers] + [f"X{i}" for i in range(total_receivers - overlap_receivers)]
    fan_in = make_hit("PT-2", "FAN_IN", "COL", ["COL"] + senders, df)
    return fan_out, fan_in


def test_scatter_gather_derived_when_half_or_more_overlap():
    fo, fi = _fan_hits(overlap_receivers=6)
    typ = derive_typologies([fo, fi])
    assert "SCATTER_GATHER" in typ and "FAN_OUT" in typ and "FAN_IN" in typ
    assert primary_typology(typ) == "SCATTER_GATHER"
    fo, fi = _fan_hits(overlap_receivers=3)          # exactly 50%
    assert "SCATTER_GATHER" in derive_typologies([fo, fi])


def test_scatter_gather_not_derived_below_half_overlap():
    fo, fi = _fan_hits(overlap_receivers=2)          # 33%
    assert "SCATTER_GATHER" not in derive_typologies([fo, fi])


def test_fan_out_alone_or_fan_in_alone_is_not_scatter_gather():
    fo, fi = _fan_hits(overlap_receivers=6)
    assert "SCATTER_GATHER" not in derive_typologies([fo])
    assert "SCATTER_GATHER" not in derive_typologies([fi])


# ------------------------------------------------------------------ roles / hops
def test_roles_and_in_cluster_totals():
    df = chain_df()
    roles = {r.account_id: r for r in compute_roles(df, [f"ACC{100 + i}" for i in range(6)])}
    assert roles["ACC100"].role == "source"
    assert roles["ACC105"].role == "collector"
    assert all(roles[f"ACC{101 + i}"].role == "intermediary" for i in range(4))
    assert roles["ACC100"].total_in == 0 and roles["ACC100"].total_out == 990000
    assert roles["ACC105"].total_out == 0
    assert roles["ACC101"].total_in == 990000


def test_account_without_cluster_transactions_is_member():
    df = chain_df()
    roles = {r.account_id: r for r in compute_roles(df, ["ACC100", "ACC999"])}
    assert roles["ACC999"].role == "member"


def test_median_hop_minutes_for_chain_is_38():
    df = chain_df(hop_minutes=38)
    roles = compute_roles(df, [])
    assert median_hop_minutes(df, roles) == 38.0


def test_median_hop_none_without_intermediaries():
    det = merchant_detection(10)
    roles = compute_roles(det.transactions, det.clusters[0].accounts)
    assert median_hop_minutes(det.transactions, roles) is None


def test_median_hop_uses_next_outgoing_after_inflow():
    rows = [
        ("TX1", "A", "B", 100000, T0),
        ("TX2", "B", "C", 98000, T0 + timedelta(minutes=30)),
        ("TX3", "A", "B", 100000, T0 + timedelta(minutes=40)),
        ("TX4", "B", "C", 98000, T0 + timedelta(minutes=100)),
    ]
    df = make_df(rows)
    roles = compute_roles(df, [])
    # B: inflow t=0 -> next out t=30 (30 min); inflow t=40 -> next out t=100 (60 min); median 45
    assert median_hop_minutes(df, roles) == 45.0


# ------------------------------------------------------------------ factor bands
def test_velocity_bands():
    assert _velocity_factor(38).points == 20
    assert _velocity_factor(360).points == 20
    assert _velocity_factor(361).points == 12
    assert _velocity_factor(1440).points == 12
    assert _velocity_factor(1441).points == 5
    assert _velocity_factor(4320).points == 5
    assert _velocity_factor(4321).points == 0
    assert _velocity_factor(None).points == 0
    assert "38 min" in _velocity_factor(38).reason


def test_structuring_bands_and_boundaries():
    amounts = [900_000, 950_000, 999_999, 1_000_000, 500_000]       # 3 of 5 in [9L, 10L)
    df = make_df([(f"T{i}", "A", "B", a, T0) for i, a in enumerate(amounts)])
    f = _structuring_factor(df, 1_000_000, 0.9)
    assert f.points == 15 and "3 of 5" in f.reason
    df = make_df([(f"T{i}", "A", "B", a, T0) for i, a in enumerate([950_000, 1, 2, 3, 4])])   # 20%
    assert _structuring_factor(df, 1_000_000, 0.9).points == 8
    df = make_df([(f"T{i}", "A", "B", a, T0) for i, a in enumerate([950_000, 1, 2, 3, 4, 5])])  # 16.7%
    assert _structuring_factor(df, 1_000_000, 0.9).points == 0


def test_flow_through_bands():
    df = chain_df()
    roles = compute_roles(df, [])
    assert _flow_through_factor(roles).points == 10
    assert _flow_through_factor([]).points == 0


# ------------------------------------------------------------------ scoring end to end
def test_fast_five_hop_chain_with_structured_amounts_is_high_risk():
    sc = score_clusters(chain_detection(), Settings())[0]
    pts = {f.factor: f.points for f in sc.score_breakdown}
    assert pts == {
        "pattern_severity": 30, "multiple_typologies": 0, "velocity": 20,
        "structuring": 15, "flow_through": 10,
    }
    assert sc.risk_score == 75 and sc.risk_score >= 70
    assert sc.risk_level == "high" and sc.alerted
    assert sc.primary_typology == "PASS_THROUGH" and sc.typologies == ["PASS_THROUGH"]
    assert sc.median_hop_minutes == 38.0
    assert sc.cluster_id == "CL-0001"


def test_breakdown_lists_all_five_factors_with_numeric_reasons():
    sc = score_clusters(chain_detection(), Settings())[0]
    assert [f.factor for f in sc.score_breakdown] == [
        "pattern_severity", "multiple_typologies", "velocity", "structuring", "flow_through",
    ]
    for f in sc.score_breakdown:
        assert 0 <= f.points <= f.max_points and f.reason
    assert "38 min" in sc.score_breakdown[2].reason
    assert "₹9,00,000" in sc.score_breakdown[3].reason


def test_merchant_style_fan_in_alone_is_low_and_not_alerted():
    sc = score_clusters(merchant_detection(60), Settings())[0]
    assert sc.risk_score == 20
    assert sc.risk_level == "low" and not sc.alerted
    assert sc.primary_typology == "FAN_IN"
    assert sc.median_hop_minutes is None


def test_cycle_plus_pass_through_scores_high_and_never_exceeds_100():
    rows, amount, t = [], 990_000.0, T0
    accs = ["C1", "C2", "C3", "C4"]
    for i in range(4):
        rows.append((f"TX{i + 1}", accs[i], accs[(i + 1) % 4], round(amount), t))
        amount *= 0.98
        t += timedelta(hours=3)
    df = make_df(rows)
    cyc = make_hit("PT-1", "CYCLE", "C1", accs, df)
    pt = make_hit("PT-2", "PASS_THROUGH", "C1", accs, df)
    sc = score_clusters(make_detection(df, [cyc, pt]), Settings())[0]
    assert sc.primary_typology == "CYCLE"
    assert sc.typologies == ["CYCLE", "PASS_THROUGH"]
    assert sc.risk_level == "high" and 70 <= sc.risk_score <= 100


def test_scatter_gather_cluster_is_scored_as_scatter_gather():
    t = T0
    rows = []
    for i in range(6):
        rows.append((f"TX{i}", "SRC", f"M{i}", 800_000, t + timedelta(minutes=5 * i)))
    for i in range(6):
        rows.append((f"TY{i}", f"M{i}", "COL", 780_000, t + timedelta(minutes=120 + 5 * i)))
    df = make_df(rows)
    fo = make_hit("PT-1", "FAN_OUT", "SRC", ["SRC"] + [f"M{i}" for i in range(6)], df,
                  [f"TX{i}" for i in range(6)])
    fi = make_hit("PT-2", "FAN_IN", "COL", ["COL"] + [f"M{i}" for i in range(6)], df,
                  [f"TY{i}" for i in range(6)])
    sc = score_clusters(make_detection(df, [fo, fi]), Settings())[0]
    assert "SCATTER_GATHER" in sc.typologies and sc.primary_typology == "SCATTER_GATHER"
    assert sc.risk_score >= 70       # 30 + 20 (3 typologies) + 20 velocity + ... ; alerted
    assert sc.alerted


def test_labels_never_influence_the_score():
    a = score_clusters(chain_detection(label=None), Settings())[0]
    b = score_clusters(chain_detection(label="suspicious"), Settings())[0]
    c = score_clusters(chain_detection(label="normal"), Settings())[0]
    assert a.risk_score == b.risk_score == c.risk_score
    assert [f.points for f in a.score_breakdown] == [f.points for f in c.score_breakdown]


def test_disclaimer_present_and_headline_uses_real_numbers():
    sc = score_clusters(chain_detection(), Settings())[0]
    assert sc.explanation.disclaimer == DISCLAIMER
    assert sc.explanation.headline.startswith("Rapid pass-through (mule chain) across 6 accounts")
    assert "₹" in sc.explanation.headline
    assert len(sc.explanation.bullet_points) == sum(1 for f in sc.score_breakdown if f.points > 0)


def test_cluster_totals_and_times():
    det = chain_detection()
    sc = score_clusters(det, Settings())[0]
    df = det.transactions
    assert sc.total_amount == float(df["amount"].sum())
    assert sc.start_time == T0
    assert sc.end_time == T0 + timedelta(minutes=38 * 4)
    assert sc.transaction_ids == list(df["transaction_id"])


def test_thresholds_come_from_settings():
    cfg = Settings()
    cfg.ALERT_THRESHOLD = 80
    cfg.HIGH_RISK_THRESHOLD = 90
    sc = score_clusters(chain_detection(), cfg)[0]          # score 75
    assert sc.risk_level == "low" and not sc.alerted
    cfg.ALERT_THRESHOLD = 40
    cfg.HIGH_RISK_THRESHOLD = 75
    sc = score_clusters(chain_detection(), cfg)[0]
    assert sc.risk_level == "high" and sc.alerted


def test_settings_with_lowercase_attribute_names_also_work():
    cfg = SimpleNamespace(
        reporting_threshold=1_000_000, structuring_lower_ratio=0.9,
        alert_threshold=40, high_risk_threshold=70,
    )
    sc = score_clusters(chain_detection(), cfg)[0]
    assert sc.risk_score == 75 and sc.alerted


def test_cluster_without_hits_or_transactions_is_skipped():
    det = chain_detection()
    det.clusters.append(RawCluster("CL-0002", ["Z1"], ["NOPE"], ["PT-9999"]))
    out = score_clusters(det, Settings())
    assert [c.cluster_id for c in out] == ["CL-0001"]
