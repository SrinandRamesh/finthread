#!/usr/bin/env python3
"""FinThread - synthetic labelled transaction dataset generator (Member 3).

Writes backend/data/sample_transactions.csv (seed 42). The data is SYNTHETIC.

Run (from the backend folder):
    python scripts/generate_synthetic.py

Never used by detection/scoring/baseline: the `label` and `gt_typology` columns
exist only for evaluation.

Layout of the account space
    ACC0001-ACC0180  payers   (ACC0001-0040 = payroll employees,
                               ACC0041-0110 = customers of merchant 1,
                               ACC0111-0180 = customers of merchant 2)
    ACC0181-ACC0260  payees   (receive ordinary payments, never forward them)
    ACC0261-ACC0262  big merchants (60+ customers each, hold the money)
    ACC0263          payroll account (40 employees, two pay days)
    ACC0264          corporate (genuine transfers >= Rs 10 lakh) -> vendors ACC0265-0269
    ACC0270+         accounts used by injected laundering patterns (each used once)

Ordinary traffic is deliberately "payer -> payee" only and every payee has at most
4 distinct senders. That keeps accidental fan-in / fan-out / pass-through hits among
ordinary accounts out of the data, so the ONLY legitimate-looking patterns are the
labelled false-positive traps (merchants, payroll, corporate). This is a limitation
of synthetic data and is stated in the evaluation notes.
"""
from __future__ import annotations

import itertools
import math
import random
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

START = datetime(2026, 11, 1, 0, 0, 0)
END = datetime(2026, 11, 14, 23, 59, 59)
TARGET_ROWS = 5000
OUT_PATH = Path(__file__).resolve().parents[1] / "data" / "sample_transactions.csv"

HOUR_W = np.array([1, 1, 1, 1, 1, 2, 3, 5, 7, 8, 8, 8, 9, 8, 7, 7, 8, 9, 10, 10, 8, 5, 3, 2], dtype=float)
HOUR_W = HOUR_W / HOUR_W.sum()


def acc(n: int) -> str:
    return f"ACC{n:04d}"


PAYERS = [acc(i) for i in range(1, 181)]
EMPLOYEES = PAYERS[0:40]
M1_CUSTOMERS = PAYERS[40:110]
M2_CUSTOMERS = PAYERS[110:180]
PAYEES = [acc(i) for i in range(181, 261)]
MERCHANTS = [acc(261), acc(262)]
PAYROLL = acc(263)
CORPORATE = acc(264)
VENDORS = [acc(i) for i in range(265, 270)]
_inj_ids = itertools.count(270)


def new() -> str:
    """Fresh account for an injected pattern."""
    return acc(next(_inj_ids))


rows: list[dict] = []


def channel_for(amount: float) -> str:
    if amount >= 500_000:
        return random.choices(["RTGS", "NEFT"], [60, 40])[0]
    if amount >= 200_000:
        return random.choices(["RTGS", "NEFT", "IMPS"], [40, 40, 20])[0]
    if amount > 100_000:
        return random.choice(["IMPS", "NEFT"])
    return random.choices(["UPI", "IMPS", "NEFT", "OTHER"], [55, 25, 15, 5])[0]


def ordinary_channel(amount: float) -> str:
    if amount > 100_000:
        return random.choice(["IMPS", "NEFT"])
    if amount <= 30_000:
        return random.choices(["UPI", "IMPS", "NEFT", "CASH", "OTHER"], [58, 15, 10, 10, 7])[0]
    return random.choices(["UPI", "IMPS", "NEFT", "OTHER"], [50, 25, 20, 5])[0]


def add(ts, sender, receiver, amount, label="normal", gt="", pid=None, channel=None) -> dict:
    amount = round(float(amount), 2)
    row = {
        "ts": ts.replace(microsecond=0),
        "sender": sender,
        "receiver": receiver,
        "amount": amount,
        "channel": channel or channel_for(amount),
        "label": label,
        "gt": gt,
        "pid": pid,
    }
    rows.append(row)
    return row


def structured() -> float:
    """Amount just under the Rs 10,00,000 reporting threshold."""
    return float(round(random.uniform(900_000, 999_000), -2))


def minutes(x: float) -> timedelta:
    return timedelta(minutes=x)


def hours(x: float) -> timedelta:
    return timedelta(hours=x)


def pattern_start() -> datetime:
    return START + hours(random.uniform(24, 24 * 9))


SPECS: list[dict] = []   # data for the self-checks at the end


# ------------------------------------------------------------------ injected patterns
def gen_fan_in(pid: str, n: int) -> None:
    mules = [new() for _ in range(n)]
    k, b, c = new(), new(), new()
    t0 = pattern_start()
    span = random.uniform(6, 16)
    times = sorted(t0 + minutes(random.uniform(0, span * 60)) for _ in mules)
    ins = []
    for m, t in zip(mules, times):
        amt = structured() if random.random() < 0.6 else float(random.randint(60_000, 600_000))
        ins.append(add(t, m, k, amt, "suspicious", "FAN_IN", pid))
    total = sum(r["amount"] for r in ins)
    t1 = times[-1] + minutes(random.uniform(20, 150))
    out1 = add(t1, k, b, round(total * random.uniform(0.92, 0.98), -2), "suspicious", "FAN_IN", pid)
    t2 = t1 + minutes(random.uniform(20, 150))
    out2 = add(t2, b, c, round(out1["amount"] * random.uniform(0.95, 0.99), -2), "suspicious", "FAN_IN", pid)
    SPECS.append({"type": "FAN_IN", "pid": pid, "ins": ins, "out1": out1, "out2": out2})


def gen_fan_out(pid: str, k: int) -> None:
    o, s = new(), new()
    mules = [new() for _ in range(k)]
    t0 = pattern_start()
    ring_structured = random.random() < 0.6
    splits = [structured() if ring_structured else float(random.randint(150_000, 700_000)) for _ in range(k)]
    inflow = add(t0, o, s, round(sum(splits) / random.uniform(0.96, 0.99), -2), "suspicious", "FAN_OUT", pid)
    first = t0 + minutes(random.uniform(15, 60))
    times = sorted(first + minutes(random.uniform(0, random.uniform(6, 18) * 60)) for _ in mules)
    split_rows = [add(t, s, m, a, "suspicious", "FAN_OUT", pid) for m, t, a in zip(mules, times, splits)]
    n_fwd = max(3, round(0.6 * k))
    fwd_idx = sorted(random.sample(range(k), n_fwd))
    fwds = []
    for i in fwd_idx:
        sr = split_rows[i]
        fr = add(sr["ts"] + minutes(random.uniform(15, 175)), sr["receiver"], new(),
                 round(sr["amount"] * random.uniform(0.92, 0.99), -2), "suspicious", "FAN_OUT", pid)
        fwds.append((sr, fr))
    SPECS.append({"type": "FAN_OUT", "pid": pid, "inflow": inflow, "splits": split_rows, "fwds": fwds})


def gen_cycle(pid: str, length: int) -> None:
    accs = [new() for _ in range(length)]
    t = pattern_start()
    amt = structured() if random.random() < 0.6 else float(random.randint(300_000, 800_000))
    cyc = []
    for i in range(length):
        cyc.append(add(t, accs[i], accs[(i + 1) % length], amt, "suspicious", "CYCLE", pid))
        amt = round(amt * (1 - random.uniform(0.01, 0.03)), -2)
        t = t + hours(random.uniform(2, 12))
    SPECS.append({"type": "CYCLE", "pid": pid, "rows": cyc})


def gen_pass_through(pid: str, n_accounts: int) -> None:
    accs = [new() for _ in range(n_accounts)]
    t = pattern_start()
    amt = structured() if random.random() < 0.7 else float(random.randint(150_000, 800_000))
    chain = []
    for i in range(n_accounts - 1):
        chain.append(add(t, accs[i], accs[i + 1], amt, "suspicious", "PASS_THROUGH", pid))
        t = t + minutes(random.uniform(10, 180))
        amt = round(amt * random.uniform(0.92, 0.99), -2)
    SPECS.append({"type": "PASS_THROUGH", "pid": pid, "rows": chain})


def gen_scatter_gather(pid: str, m: int) -> None:
    o, s, c = new(), new(), new()
    mules = [new() for _ in range(m)]
    t0 = pattern_start()
    splits = [float(random.randint(300_000, 950_000)) for _ in mules]
    inflow = add(t0, o, s, round(sum(splits) / random.uniform(0.96, 0.99), -2), "suspicious", "SCATTER_GATHER", pid)
    times = sorted(t0 + minutes(random.uniform(20, random.uniform(5, 12) * 60)) for _ in mules)
    split_rows = [add(t, s, mu, a, "suspicious", "SCATTER_GATHER", pid) for mu, t, a in zip(mules, times, splits)]
    fwds = []
    for sr in split_rows:
        fr = add(sr["ts"] + minutes(random.uniform(30, 175)), sr["receiver"], c,
                 round(sr["amount"] * random.uniform(0.92, 0.99), -2), "suspicious", "SCATTER_GATHER", pid)
        fwds.append((sr, fr))
    SPECS.append({"type": "SCATTER_GATHER", "pid": pid, "inflow": inflow, "splits": split_rows, "fwds": fwds})


# ------------------------------------------------------------------ false-positive traps
def gen_merchants() -> None:
    for merchant, customers in zip(MERCHANTS, (M1_CUSTOMERS, M2_CUSTOMERS)):
        payers = list(customers) + random.choices(customers, k=random.randint(10, 15))
        for p in payers:
            amt = float(int(min(max(np.random.lognormal(math.log(900), 0.9), 150), 15_000)))
            day = random.randint(0, 13)
            hr = int(np.random.choice(24, p=HOUR_W))
            ts = START + timedelta(days=day, hours=hr, minutes=random.randint(0, 59), seconds=random.randint(0, 59))
            add(ts, p, merchant, amt, channel=ordinary_channel(amt))


def gen_payroll() -> None:
    salaries = {e: float(round(random.uniform(35_000, 95_000), -2)) for e in EMPLOYEES}
    for payday in (datetime(2026, 11, 1, 9, 0, 0), datetime(2026, 11, 14, 9, 0, 0)):
        for e in EMPLOYEES:
            ts = payday + timedelta(seconds=random.randint(0, 45 * 60))
            add(ts, PAYROLL, e, salaries[e], channel=random.choices(["NEFT", "IMPS"], [60, 40])[0])


def gen_corporate() -> None:
    base = datetime(2026, 11, 2, 10, 0, 0)
    for i in range(8):
        ts = base + hours(38 * i) + minutes(random.uniform(-60, 60))
        amt = float(round(random.uniform(1_050_000, 4_800_000), -3))
        add(ts, CORPORATE, random.choice(VENDORS), amt, channel=random.choices(["RTGS", "NEFT"], [70, 30])[0])


# ------------------------------------------------------------------ ordinary traffic
def gen_ordinary(n: int) -> None:
    cap = {q: 4 for q in PAYEES}
    contacts: dict[str, list[str]] = {}
    order = PAYERS[:]
    random.shuffle(order)
    for p in order:
        avail = [q for q in PAYEES if cap[q] > 0]
        k = min(random.choice([1, 2]), len(avail))
        chosen = random.sample(avail, k)
        for q in chosen:
            cap[q] -= 1
        contacts[p] = chosen
    w = np.random.lognormal(0.0, 0.35, size=len(PAYERS))
    w = w / w.sum()
    senders = np.random.choice(len(PAYERS), size=n, p=w)
    amounts = np.clip(np.random.lognormal(math.log(2500), 1.2, size=n), 200, 200_000)
    days = np.random.randint(0, 14, size=n)
    hrs = np.random.choice(24, size=n, p=HOUR_W)
    mins = np.random.randint(0, 60, size=n)
    secs = np.random.randint(0, 60, size=n)
    for i in range(n):
        p = PAYERS[senders[i]]
        amt = float(round(amounts[i], -2)) if amounts[i] > 1500 and random.random() < 0.5 else float(round(amounts[i]))
        amt = max(amt, 200.0)
        ts = START + timedelta(days=int(days[i]), hours=int(hrs[i]), minutes=int(mins[i]), seconds=int(secs[i]))
        add(ts, p, random.choice(contacts[p]), amt, channel=ordinary_channel(amt))


# ------------------------------------------------------------------ self-checks
def _mins(a, b) -> float:
    return (b["ts"] - a["ts"]).total_seconds() / 60


def verify() -> None:
    """Assert the injected patterns really satisfy the default detection thresholds."""
    for sp in SPECS:
        t = sp["type"]
        if t == "FAN_IN":
            ins, o1, o2 = sp["ins"], sp["out1"], sp["out2"]
            assert len({r["sender"] for r in ins}) >= 6
            assert _mins(ins[0], ins[-1]) <= 48 * 60
            assert 0.915 <= o1["amount"] / sum(r["amount"] for r in ins) <= 0.985
            assert _mins(ins[-1], o1) <= 180 and _mins(o1, o2) <= 180
            assert 0.945 <= o2["amount"] / o1["amount"] <= 0.995
            assert _mins(ins[0], o1) <= 24 * 60
        elif t in ("FAN_OUT", "SCATTER_GATHER"):
            inflow, splits, fwds = sp["inflow"], sp["splits"], sp["fwds"]
            assert len({r["receiver"] for r in splits}) >= 6
            assert all(_mins(inflow, r) <= 24 * 60 for r in splits)
            assert _mins(splits[0], splits[-1]) <= 48 * 60
            assert sum(r["amount"] for r in splits) >= 0.8 * inflow["amount"]
            for sr, fr in fwds:
                assert 0 < _mins(sr, fr) <= 180
                assert 0.915 <= fr["amount"] / sr["amount"] <= 0.995
            if t == "SCATTER_GATHER":
                assert len({fr["sender"] for _, fr in fwds}) >= 6
                assert _mins(fwds[0][1], fwds[-1][1]) <= 48 * 60
        elif t == "CYCLE":
            r = sp["rows"]
            assert r[-1]["receiver"] == r[0]["sender"]
            assert all(r[i]["ts"] < r[i + 1]["ts"] for i in range(len(r) - 1))
            assert _mins(r[0], r[-1]) <= 72 * 60
            for i in range(len(r) - 1):
                assert 0.965 <= r[i + 1]["amount"] / r[i]["amount"] <= 0.995
        elif t == "PASS_THROUGH":
            r = sp["rows"]
            assert len(r) >= 3
            for i in range(len(r) - 1):
                assert r[i]["receiver"] == r[i + 1]["sender"]
                assert 0 < _mins(r[i], r[i + 1]) <= 180
                assert 0.915 <= r[i + 1]["amount"] / r[i]["amount"] <= 0.995
    assert all(START <= r["ts"] <= END for r in rows), "timestamp out of range"
    assert all(r["sender"] != r["receiver"] for r in rows)


# ------------------------------------------------------------------ main
def main() -> None:
    # injected laundering
    for i, n in enumerate([6, 7, 8, 10], 1):
        gen_fan_in(f"FI{i}", n)
    for i, k in enumerate([6, 8, 9, 10], 1):
        gen_fan_out(f"FO{i}", k)
    for i, length in enumerate([3, 4, 5, 4], 1):
        gen_cycle(f"CY{i}", length)
    for i, n in enumerate([4, 5, 6, 7], 1):
        gen_pass_through(f"PT{i}", n)
    for i, m in enumerate([6, 8], 1):
        gen_scatter_gather(f"SG{i}", m)
    n_susp = len(rows)

    # false-positive traps (label normal)
    gen_merchants()
    gen_payroll()
    gen_corporate()
    n_traps = len(rows) - n_susp

    # ordinary traffic fills up to the target
    gen_ordinary(max(0, TARGET_ROWS - len(rows)))

    verify()

    df = pd.DataFrame(rows).sort_values("ts", kind="stable").reset_index(drop=True)
    df["transaction_id"] = [f"TX{i:06d}" for i in range(1, len(df) + 1)]
    df["timestamp"] = df["ts"].dt.strftime("%Y-%m-%dT%H:%M:%S")
    df["currency"] = "INR"
    df["amount"] = df["amount"].map(lambda x: f"{x:.2f}")
    out = df.rename(columns={"gt": "gt_typology"})[
        ["transaction_id", "sender", "receiver", "amount", "timestamp", "currency", "channel", "label", "gt_typology"]
    ]
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_PATH, index=False)

    amounts = df["amount"].astype(float)
    susp = df[df["label"] == "suspicious"]
    s_amt = susp["amount"].astype(float)
    accounts = set(df["sender"]) | set(df["receiver"])
    print(f"Wrote {OUT_PATH}")
    print(f"rows: {len(df)}   accounts: {len(accounts)}   window: {df['timestamp'].min()} -> {df['timestamp'].max()}")
    print(f"normal: {(df['label'] == 'normal').sum()}   suspicious: {len(susp)}   "
          f"(traps among normal: {n_traps} rows from merchants/payroll/corporate)")
    print("suspicious by typology:")
    for typ, cnt in susp["gt"].value_counts().items():
        print(f"  {typ:<15} {cnt}")
    structured_n = int(((s_amt >= 900_000) & (s_amt < 1_000_000)).sum())
    print(f"structured suspicious txs (Rs 9,00,000-9,99,999): {structured_n} of {len(susp)}")
    print(f"normal txs >= Rs 10,00,000: {int(((amounts >= 1_000_000) & (df['label'] == 'normal')).sum())}")
    print(f"suspicious txs >= Rs 10,00,000: {int((s_amt >= 1_000_000).sum())}")
    print("self-checks passed: all injected patterns satisfy the default detection thresholds")


if __name__ == "__main__":
    main()
