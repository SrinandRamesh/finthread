"""Rule-based baseline (Member 3). Contract Section 8.

Per transaction, flag if any rule fires:
    R1_LARGE_AMOUNT   amount >= BASELINE_LARGE_TX
    R2_DAILY_VOLUME   sender's rolling 24 h outgoing total (incl. this tx) >= BASELINE_DAILY_OUT_AMOUNT
    R3_VELOCITY       sender's rolling 24 h outgoing count (incl. this tx) >= BASELINE_DAILY_OUT_COUNT
Ground-truth columns are never read.
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from app.contracts import BaselineOutput
from app.intelligence.risk import cfg_value

_DEFAULTS = {
    "BASELINE_LARGE_TX": 1_000_000,
    "BASELINE_DAILY_OUT_AMOUNT": 2_500_000,
    "BASELINE_DAILY_OUT_COUNT": 10,
}


def run_baseline(transactions: pd.DataFrame, cfg: Any) -> BaselineOutput:
    if transactions is None or transactions.empty:
        return BaselineOutput(flagged_transaction_ids=set(), rules_triggered={})

    large = float(cfg_value(cfg, "BASELINE_LARGE_TX", _DEFAULTS["BASELINE_LARGE_TX"]))
    day_amt = float(cfg_value(cfg, "BASELINE_DAILY_OUT_AMOUNT", _DEFAULTS["BASELINE_DAILY_OUT_AMOUNT"]))
    day_cnt = int(cfg_value(cfg, "BASELINE_DAILY_OUT_COUNT", _DEFAULTS["BASELINE_DAILY_OUT_COUNT"]))

    df = transactions[["transaction_id", "sender", "amount", "timestamp"]].copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["amount"] = df["amount"].astype(float)
    df = df.sort_values(["sender", "timestamp", "transaction_id"], kind="stable").reset_index(drop=True)

    roll_sum = (
        df.groupby("sender", sort=False)
        .rolling("24h", on="timestamp")["amount"]
        .sum()
        .reset_index(level=0, drop=True)
    )
    roll_cnt = (
        df.groupby("sender", sort=False)
        .rolling("24h", on="timestamp")["amount"]
        .count()
        .reset_index(level=0, drop=True)
    )
    df["out_24h_amount"] = roll_sum.values
    df["out_24h_count"] = roll_cnt.values

    rules: dict[str, list[str]] = {}
    for row in df.itertuples(index=False):
        fired = []
        if row.amount >= large:
            fired.append("R1_LARGE_AMOUNT")
        if row.out_24h_amount >= day_amt:
            fired.append("R2_DAILY_VOLUME")
        if row.out_24h_count >= day_cnt:
            fired.append("R3_VELOCITY")
        if fired:
            rules[str(row.transaction_id)] = fired

    return BaselineOutput(flagged_transaction_ids=set(rules), rules_triggered=rules)
