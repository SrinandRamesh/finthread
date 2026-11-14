# PROJECT_CONTRACT.md — FinThread

**Single source of truth for all three developers. Nobody edits this file except the Integration Lead (Member 2), and only after all three agree.**

FinThread is an Anti-Money Laundering (AML) **investigation-support and risk-prioritisation** platform. It models transactions as a temporal, directed, weighted graph, detects layering patterns (fan-in, fan-out, cycles, rapid pass-through), groups them into suspicious clusters, scores and labels them, explains the money trail in plain language with evidence, and compares itself against a rule-based baseline using precision, recall and F1.

> FinThread never claims a pattern *proves* money laundering. Every alert carries the disclaimer:
> **"This alert highlights a pattern that warrants analyst review. It is not proof of money laundering."**

---

## 1. Architecture

```
Browser (React SPA on Vercel)
   │  HTTPS JSON (fetch)  — base URL from VITE_API_BASE_URL
   ▼
FastAPI backend (Render)
   ├─ routers/core.py   (Member 2)  health, upload, sample, analyze, transactions, graph, patterns, accounts, config
   ├─ routers/intel.py  (Member 3)  overview, clusters, alerts, evaluation
   ├─ pipeline.py       (Member 2)  orchestrates one analysis run
   │     ingestion → graph builder → detection engine         (Member 2)
   │     → risk scoring → typology → explanations → alerts    (Member 3)
   │     → baseline rules → evaluation metrics                (Member 3)
   ├─ state.py          (Member 2)  holds the current AnalysisResult in memory
   └─ SQLite (SQLAlchemy)  datasets, transactions, analysis_runs
```

**Data flow (every stage feeds the next):**
CSV upload → validation & preprocessing → SQLite → temporal directed MultiDiGraph → detection algorithms → pattern hits → clusters → risk score + typology → evidence-backed explanation → alerts → frontend graph & investigation screens → rule-based baseline → precision / recall / F1 / confusion matrix.

**Core rule:** detection and scoring are **deterministic and explainable** (graph algorithms + transparent points). No trained ML model is required. An optional LLM may only re-word an explanation that is already built from real evidence; it is **off by default** (`LLM_ENABLED=false`).

---

## 2. Technology stack (final — do not change)

| Layer | Choice |
|---|---|
| Frontend | React 18 + Vite + TypeScript, Tailwind CSS v4 (`@tailwindcss/vite`), React Router v6, Cytoscape.js + `cytoscape-fcose` (graph), Recharts (charts), Framer Motion (page transitions, reveals, shared-element morphs) + Lenis (smooth scroll on the landing page only), lucide-react (icons), clsx |
| Backend | Python 3.11, FastAPI, Uvicorn, Pandas, NetworkX ≥ 3.2, Pydantic v2, pydantic-settings, SQLAlchemy 2.0, python-multipart |
| Database | SQLite (file `aml.db`). On Render the disk is ephemeral, so the backend re-loads the sample dataset on startup (`LOAD_SAMPLE_ON_STARTUP=true`). |
| Tests | pytest + httpx (backend). Manual + `npm run build` (frontend). |
| Deploy | Vercel (frontend, root `frontend/`), Render free web service (backend, root `backend/`) |
| Repo | One GitHub repo, three feature branches, folder ownership (Section 10) |
| Design helpers | Google Stitch for first screen mockups, Claude / Antigravity for coding |

---

## 3. Folder structure and ownership

```
finthread/
├─ PROJECT_CONTRACT.md                 LEAD ONLY (frozen)
├─ README.md                           LEAD
├─ .gitignore                          LEAD
├─ backend/
│  ├─ requirements.txt                 M2 (M3 asks M2 to add a package)
│  ├─ render.yaml                      M2
│  ├─ app/
│  │  ├─ __init__.py
│  │  ├─ main.py                       M2  (creates app, CORS, includes BOTH routers, startup sample load)
│  │  ├─ config.py                     M2  (Settings, Section 9)
│  │  ├─ contracts.py                  LEAD ONLY (frozen — Appendix A)
│  │  ├─ schemas.py                    LEAD ONLY (frozen — Appendix B)
│  │  ├─ db.py, models.py              M2
│  │  ├─ state.py                      M2  (get_current_result / set_current_result)
│  │  ├─ pipeline.py                   M2  (run_analysis — calls M3 functions, Section 7)
│  │  ├─ ingestion/  loader.py validator.py            M2
│  │  ├─ graph/      builder.py serialize.py           M2  (serialize.py helpers are imported by M3)
│  │  ├─ detection/  fan.py cycles.py pass_through.py timing.py clusters.py engine.py   M2
│  │  ├─ intelligence/ __init__.py risk.py typology.py explain.py alerts.py formatting.py   M3
│  │  ├─ evaluation/ __init__.py baseline.py metrics.py   M3
│  │  └─ routers/   __init__.py core.py (M2)  intel.py (M3)
│  ├─ data/        sample_transactions.csv              M3 (generated, committed)
│  ├─ scripts/     generate_synthetic.py  convert_ibm_aml.py (optional)   M3
│  └─ tests/       test_ingestion.py test_detection.py fixtures/   M2
│                  test_intelligence.py test_evaluation.py           M3
└─ frontend/                            M1 (everything)
   ├─ vercel.json
   ├─ .env.example
   └─ src/
      ├─ types/contract.ts              M1 copies Appendix C VERBATIM, never edits
      ├─ api/client.ts api/endpoints.ts api/mock/*
      ├─ components/ layout/ ui/ graph/ charts/
      └─ pages/ Overview Upload Transactions GraphExplorer Clusters ClusterDetail AccountDetail RiskTypology Evaluation
```

---

## 4. Data contract

### 4.1 Transaction CSV (input)

| Column | Required | Type | Notes |
|---|---|---|---|
| `transaction_id` | yes | string | unique within the file |
| `sender` | yes | string | account id, e.g. `ACC0001` |
| `receiver` | yes | string | account id, must differ from sender |
| `amount` | yes | number | > 0, INR |
| `timestamp` | yes | string | ISO `2026-11-14T10:00:00` or `2026-11-14 10:00:00` (naive, treated as IST) |
| `currency` | no | string | default `INR` |
| `channel` | no | string | `UPI` `IMPS` `NEFT` `RTGS` `CASH` `OTHER` |
| `label` | no | string | ground truth: `suspicious` or `normal` (blank = unknown) |
| `gt_typology` | no | string | ground truth typology code (Section 4.3) or blank |

**Ground truth (`label`, `gt_typology`) is never used by detection, scoring or the baseline.** It is used only by evaluation, and the API always returns it in a separate `ground_truth` object, never mixed into `prediction`.

**Validation rules (row is rejected and reported):** missing required field; non-numeric or ≤ 0 amount; unparseable timestamp; sender == receiver; duplicate `transaction_id` (first kept); `label` not in {suspicious, normal, blank}; `gt_typology` not a valid code. Whitespace is trimmed, column names are case-insensitive. Limits: 10 MB, 50,000 rows. If zero rows are accepted the upload fails with HTTP 400.

### 4.2 Ids and formats
- `dataset_id`: `ds_` + 8 hex chars. `run_id`: `run_` + 8 hex chars.
- `cluster_id`: `CL-0001`… ordered by cluster `start_time` ascending.
- `pattern_id`: `PT-0001`… ordered by `start_time` ascending.
- `alert_id`: `AL-0001`… ordered by `risk_score` descending.
- Datetimes in JSON: ISO 8601 without timezone, `2026-11-14T10:00:00`.
- Amounts: JSON numbers (float), INR. The frontend formats them with Indian grouping (₹9,85,000).
- Errors: FastAPI default `{"detail": "message"}`. **HTTP 409** with `{"detail":"No analysis run yet. Upload a dataset or load the sample."}` whenever an endpoint needs a run and none exists. The frontend shows an empty state with a **Load sample dataset** button.

### 4.3 Pattern types and typology codes

Pattern types (produced by detection, Member 2): `FAN_IN`, `FAN_OUT`, `CYCLE`, `PASS_THROUGH`.

Typology codes (produced by Member 3; also valid `gt_typology` values):

| Code | Display label |
|---|---|
| `FAN_IN` | Fan-in (funnel collection) |
| `FAN_OUT` | Fan-out (dispersion) |
| `CYCLE` | Round-tripping (cycle) |
| `PASS_THROUGH` | Rapid pass-through (mule chain) |
| `SCATTER_GATHER` | Scatter-gather layering |

Risk levels: `high` (score ≥ 70), `medium` (40–69), `low` (< 40), `none` (account in no cluster).

---

## 5. Database schema (SQLite, SQLAlchemy, Member 2)

```
datasets       id TEXT PK, name TEXT, source TEXT('upload'|'sample'), uploaded_at DATETIME,
               row_count INT, has_labels BOOL
transactions   id INTEGER PK AUTOINCREMENT, dataset_id TEXT FK, transaction_id TEXT, sender TEXT,
               receiver TEXT, amount REAL, timestamp DATETIME, currency TEXT, channel TEXT NULL,
               label TEXT NULL, gt_typology TEXT NULL
               UNIQUE(dataset_id, transaction_id); INDEX(sender), INDEX(receiver), INDEX(timestamp)
analysis_runs  id TEXT PK, dataset_id TEXT FK, started_at DATETIME, finished_at DATETIME,
               status TEXT('completed'|'failed'), config_json TEXT, summary_json TEXT, error TEXT NULL
```

Only one dataset is "active": the most recently loaded. The full `AnalysisResult` lives in memory (`state.py`); `analysis_runs` keeps the run summary for traceability. On startup, if `LOAD_SAMPLE_ON_STARTUP=true` and no dataset exists, the backend loads `backend/data/sample_transactions.csv` and runs analysis.

---

## 6. Detection engine (Member 2) — exact semantics

The graph is a `networkx.MultiDiGraph`: node = account id; edge key = `transaction_id`, edge attrs `amount` (float), `timestamp` (datetime), `channel`. Parallel transactions are kept.

**FAN_IN** — for each account with ≥ `FAN_MIN_COUNTERPARTIES` distinct senders overall: sort incoming transactions by time; slide a window of `FAN_WINDOW_HOURS`; whenever distinct senders in the window ≥ `FAN_MIN_COUNTERPARTIES`, mark the window; merge overlapping marked windows of the same account into one hit. `focal_account` = the receiver; evidence = incoming transactions in the merged window; `accounts` = [focal] + senders. Metrics: `counterparty_count`, `window_hours`, `avg_amount`, `amount_cv` (std/mean).

**FAN_OUT** — mirror of FAN_IN on outgoing transactions. `focal_account` = the sender.

**CYCLE** — collapse to a simple DiGraph; repeatedly drop nodes with in-degree 0 or out-degree 0; run `nx.simple_cycles(G, length_bound=CYCLE_MAX_LENGTH)` (cap 500 cycles; length ≥ 3, plus length-2 back-and-forth only if amounts differ < 10%). For each cycle `[a,b,c,…]` find a **time-respecting** sequence: start from an `a→b` transaction at t0 (try up to 20 starts, earliest first), pick each next hop's earliest transaction strictly after the previous one, and the closing hop back to `a` must be ≤ t0 + `CYCLE_MAX_SPAN_HOURS`. Dedupe rotations. `focal_account` = the cycle start; `accounts` = ordered cycle. Metrics: `cycle_length`, `span_hours`, `amount_retention` (last hop amount / first hop amount).

**PASS_THROUGH** — (1) *Forwarding link*: for an incoming transaction `u→v` (amount A, time t), take `v`'s outgoing transactions after t and within `PASS_THROUGH_MAX_HOURS` in time order, summing until the sum ≥ `PASS_THROUGH_MIN_RATIO × A`; if reached, link the incoming transaction to each of those outgoing transactions. (2) *Chains*: treat transactions as nodes and forwarding links as edges; DFS (depth cap 12) from transactions with no incoming link to find maximal paths; keep paths with ≥ `PASS_THROUGH_MIN_HOPS` transactions; drop paths that are sub-paths of another. `focal_account` = first sender; `accounts` = ordered chain. Metrics: `hop_count`, `median_hop_minutes`, `flow_through_ratio` (last amount / first amount), `span_hours`.

**Timing analysis (per account)** — `median_dwell_minutes`: for each incoming transaction, minutes until the account's next outgoing transaction (none → skipped); `retention_ratio` = 1 − total_out / total_in (null if total_in = 0); `max_out_24h_amount` and `max_out_24h_count` over rolling 24-hour windows.

**Clusters** — union of the evidence transactions of all hits → undirected account graph → connected components. Each component is a `RawCluster` holding its accounts, the evidence transactions inside it, and the ids of the hits whose accounts fall in it. Sort by earliest evidence time; assign `CL-0001…`. Each `PatternHit.cluster_id` is filled in.

Performance target: sample dataset (~5k rows) analysed in < 5 s; 50k rows in < 30 s on a laptop.

---

## 7. Member 2 ↔ Member 3 integration (Python)

Dataclasses live in `backend/app/contracts.py` (Appendix A). **Member 3 implements exactly these functions; Member 2's `pipeline.py` calls them in this order:**

```python
# backend/app/intelligence/__init__.py  (Member 3)
def score_clusters(detection: DetectionOutput, cfg: Settings) -> list[ScoredCluster]: ...
def build_alerts(clusters: list[ScoredCluster], cfg: Settings) -> list[AlertRecord]: ...
def compute_account_risk(clusters: list[ScoredCluster]) -> dict[str, AccountRisk]: ...

# backend/app/evaluation/__init__.py  (Member 3)
def run_baseline(transactions: pd.DataFrame, cfg: Settings) -> BaselineOutput: ...
def evaluate(transactions: pd.DataFrame, clusters: list[ScoredCluster],
             baseline: BaselineOutput, cfg: Settings) -> EvaluationResult: ...
```

```python
# backend/app/pipeline.py  (Member 2)
def run_analysis(dataset_id: str, cfg: Settings) -> AnalysisResult:
    df = load_transactions_df(dataset_id)            # M2
    G = build_graph(df)                              # M2
    detection = run_detection(df, G, cfg)            # M2 -> DetectionOutput
    clusters = score_clusters(detection, cfg)        # M3
    alerts = build_alerts(clusters, cfg)             # M3
    account_risk = compute_account_risk(clusters)    # M3
    baseline = run_baseline(df, cfg)                 # M3
    evaluation = evaluate(df, clusters, baseline, cfg)  # M3
    result = AnalysisResult(...)                     # M2
    set_current_result(result)                       # M2 state.py
    return result
```

The transactions DataFrame passed to Member 3 has columns: `transaction_id, sender, receiver, amount (float), timestamp (pandas datetime64), currency, channel, label, gt_typology` (last two may be None).

Member 3's router (`routers/intel.py`) reads data with `from app.state import get_current_result` and raises HTTP 409 if it returns None. Member 2's router uses the same function. **Until the real engine is ready, Member 3 tests against a hand-built `DetectionOutput` in `tests/`; Member 2 uses temporary stub versions of the five functions that return empty results.** At the first integration checkpoint, M2 deletes the stubs and imports M3's real functions.

---

## 8. Risk scoring, typology, explanations, baseline, evaluation (Member 3) — exact semantics

**Typologies of a cluster** = the distinct pattern types of its hits, plus `SCATTER_GATHER` if the cluster has a FAN_OUT hit and a FAN_IN hit where ≥ 50% of the fan-out receivers are also fan-in senders. `primary_typology` = highest severity in this order: CYCLE > PASS_THROUGH > SCATTER_GATHER > FAN_OUT > FAN_IN.

**Risk score (0–100, integer, capped at 100)** — every factor is recorded in `score_breakdown` with points, max points and a one-line reason:

| Factor | Points |
|---|---|
| `pattern_severity` (max over typologies) | CYCLE 35 · PASS_THROUGH 30 · SCATTER_GATHER 30 · FAN_OUT 20 · FAN_IN 20 |
| `multiple_typologies` | +10 per extra distinct typology, max 20 |
| `velocity` (cluster `median_hop_minutes`) | ≤ 360 → 20 · ≤ 1440 → 12 · ≤ 4320 → 5 · else / null → 0 |
| `structuring` (share of cluster txs with amount in [`STRUCTURING_LOWER_RATIO`×`REPORTING_THRESHOLD`, `REPORTING_THRESHOLD`)) | ≥ 50% → 15 · ≥ 20% → 8 · else 0 |
| `flow_through` (Σout / Σin over intermediary accounts, inside the cluster) | ≥ 0.9 → 10 · ≥ 0.75 → 5 · else 0 |

`median_hop_minutes` of a cluster: for each intermediary account, minutes from an incoming cluster transaction to its next outgoing cluster transaction; median of all such values (null if none).
Account roles inside a cluster: `source` (no incoming cluster txs), `collector` (no outgoing cluster txs), `intermediary` (both), `member` (fallback).
A cluster is **alerted** when `risk_score ≥ ALERT_THRESHOLD` (40). Account risk = max score over the account's clusters.

*Design intent:* a single legitimate pattern (a merchant receiving from many customers, or a payroll fan-out) scores ~20 → low, not alerted. Real layering combines patterns, speed, structuring and flow-through, and crosses 40.

**Explanations** — deterministic templates built only from real evidence (account ids, transaction ids, amounts, timestamps). Each `Explanation` has `headline` (e.g. "Rapid pass-through (mule chain) across 6 accounts · ₹48,20,000"), `summary` (2–3 sentences telling the money trail in order), `bullet_points` (one per score factor that scored > 0), `evidence` (up to 25 `EvidenceItem`s, chronological, each with a short `note` such as "forwarded 97% within 42 min"), and the fixed `disclaimer` text above.

**Baseline (rule-based, per transaction)** — flag a transaction if any rule fires:
`R1_LARGE_AMOUNT`: amount ≥ `BASELINE_LARGE_TX`.
`R2_DAILY_VOLUME`: sender's rolling 24-hour outgoing total including this transaction ≥ `BASELINE_DAILY_OUT_AMOUNT`.
`R3_VELOCITY`: sender's rolling 24-hour outgoing count including this transaction ≥ `BASELINE_DAILY_OUT_COUNT`.

**Evaluation (transaction level)** — rows with blank `label` are excluded. Positive = `label == "suspicious"`. Graph prediction = transaction belongs to an alerted cluster. Baseline prediction = baseline flag. For each model: TP, FP, FN, TN, precision = TP/(TP+FP), recall = TP/(TP+FN), F1 = 2PR/(P+R), accuracy (any zero denominator → 0.0), rounded to 4 decimals. Per-typology recall uses `gt_typology` where present. If no labelled rows: `available = false` with a reason. **Metrics are computed live on every run; nothing is ever hardcoded.**

---

## 9. Configuration and environment variables

Backend (`app/config.py`, pydantic-settings, all overridable by env):

```
DATABASE_URL=sqlite:///./aml.db
CORS_ORIGINS=http://localhost:5173            # comma-separated; add the Vercel URL in production
LOAD_SAMPLE_ON_STARTUP=true
SAMPLE_DATA_PATH=data/sample_transactions.csv
MAX_UPLOAD_ROWS=50000
MAX_GRAPH_EDGES=1500
FAN_WINDOW_HOURS=48
FAN_MIN_COUNTERPARTIES=5
CYCLE_MAX_LENGTH=6
CYCLE_MAX_SPAN_HOURS=168
PASS_THROUGH_MAX_HOURS=24
PASS_THROUGH_MIN_RATIO=0.8
PASS_THROUGH_MIN_HOPS=3
REPORTING_THRESHOLD=1000000
STRUCTURING_LOWER_RATIO=0.9
ALERT_THRESHOLD=40
HIGH_RISK_THRESHOLD=70
BASELINE_LARGE_TX=1000000
BASELINE_DAILY_OUT_AMOUNT=2500000
BASELINE_DAILY_OUT_COUNT=10
LLM_ENABLED=false
```

`GET /api/config` groups them as `detection` (FAN_*, CYCLE_*, PASS_THROUGH_*), `risk` (REPORTING_THRESHOLD, STRUCTURING_LOWER_RATIO, ALERT_THRESHOLD, HIGH_RISK_THRESHOLD), `baseline` (BASELINE_*).

Frontend (`frontend/.env`, `.env.example` committed):

```
VITE_API_BASE_URL=http://localhost:8000
VITE_USE_MOCK=false
```

---

## 10. API contract

All routes are prefixed with `/api`. Response models are in Appendix B (Python) and Appendix C (TypeScript), with identical field names.

| # | Method & route | Owner | Purpose | Params / body | Response | Used by screen |
|---|---|---|---|---|---|---|
| 1 | `GET /api/health` | M2 | liveness | – | `HealthOut` | app shell (status dot) |
| 2 | `POST /api/upload` | M2 | upload CSV, validate, store, run analysis | multipart `file`; query `analyze` (bool, default true) | `UploadResponse` | Upload |
| 3 | `POST /api/dataset/load-sample` | M2 | load bundled synthetic CSV + run | – | `UploadResponse` | Upload, empty states |
| 4 | `GET /api/dataset/sample` | M2 | download the sample CSV | – | `text/csv` file | Upload |
| 5 | `POST /api/analyze` | M2 | re-run analysis on active dataset | body `AnalyzeRequest` (optional `overrides`) | `RunSummary` | Upload, Evaluation ("Re-run") |
| 6 | `GET /api/config` | M2 | active thresholds | – | `ConfigOut` | Risk & Typology, Evaluation |
| 7 | `GET /api/transactions` | M2 | paginated explorer | `page`=1, `page_size`=50 (max 200), `account`, `min_amount`, `max_amount`, `start`, `end`, `flagged_only` (bool), `pattern` (PatternType), `sort` (`timestamp`\|`-timestamp`\|`amount`\|`-amount`, default `-timestamp`) | `TransactionPage` | Transactions |
| 8 | `GET /api/graph` | M2 | nodes/edges for Cytoscape | `scope` = `suspicious` (default: cluster accounts + 1-hop neighbours) \| `full` \| `cluster` \| `account`; `cluster_id`; `account_id`; `min_amount`; `start`; `end`. Capped at `MAX_GRAPH_EDGES` (largest amounts kept, `truncated=true`) | `GraphOut` | Graph Explorer |
| 9 | `GET /api/patterns` | M2 | raw pattern hits | `type` (PatternType, optional) | `PatternList` | Graph Explorer (pattern highlight), Risk & Typology |
| 10 | `GET /api/accounts/{account_id}` | M2 | account profile, timing, risk, counterparties, ego graph | – (404 if unknown) | `AccountDetail` | Account page |
| 11 | `GET /api/overview` | M3 | dashboard aggregates | – | `OverviewOut` | Overview |
| 12 | `GET /api/clusters` | M3 | cluster list | `min_risk` (int), `typology`, `alerted_only` (bool), `sort` (`-risk_score` default \| `-total_amount` \| `start_time`) | `ClusterList` | Clusters, Risk & Typology |
| 13 | `GET /api/clusters/{cluster_id}` | M3 | full investigation | – (404 if unknown) | `ClusterDetail` | Cluster investigation page |
| 14 | `GET /api/alerts` | M3 | alert queue | `level` (`high`\|`medium`, optional) | `AlertList` | Overview, Clusters |
| 15 | `GET /api/evaluation` | M3 | graph vs baseline metrics | – | `EvaluationOut` | Evaluation |

Dependencies: 7–15 need a completed run (else 409). 2/3/5 create runs. M2's `/accounts` takes risk fields from `AnalysisResult.account_risk` (M3 output). M2's `/transactions` and `/graph` fill `prediction.baseline_flagged/baseline_rules` and `is_suspicious` from M3's baseline and alerted clusters. M3's `/clusters/{id}` builds `subgraph`, `patterns` and `transactions` using M2's helpers in `app/graph/serialize.py` (M2 owns; M3 imports).

> **Helper contract (M2 owns `app/graph/serialize.py`, M3 may import):**
> `to_transaction_out(row: dict, result: AnalysisResult) -> schemas.TransactionOut`
> `build_graph_out(result: AnalysisResult, account_ids: set[str] | None, transaction_ids: set[str] | None, scope: str) -> schemas.GraphOut`
> `to_pattern_out(hit: PatternHit) -> schemas.PatternOut`

### Example responses

`GET /api/alerts`
```json
{"items":[{"alert_id":"AL-0001","cluster_id":"CL-0007","risk_score":88,"risk_level":"high",
 "primary_typology":"PASS_THROUGH","typologies":["PASS_THROUGH","FAN_IN"],
 "headline":"Rapid pass-through (mule chain) across 7 accounts · ₹62,40,000",
 "created_at":"2026-11-14T12:41:09","account_count":7,"transaction_count":14,
 "total_amount":6240000.0,"status":"open"}],"total":1}
```

`GET /api/graph` (shape)
```json
{"nodes":[{"id":"ACC0042","label":"ACC0042","risk_score":88,"risk_level":"high","total_in":985000.0,
  "total_out":962000.0,"in_degree":1,"out_degree":1,"patterns":["PASS_THROUGH"],
  "cluster_ids":["CL-0007"],"is_suspicious":true}],
 "edges":[{"id":"TX004512","source":"ACC0042","target":"ACC0087","amount":962000.0,
  "timestamp":"2026-11-09T14:22:00","channel":"IMPS","patterns":["PASS_THROUGH"],
  "pattern_ids":["PT-0031"],"cluster_id":"CL-0007","is_suspicious":true}],
 "meta":{"scope":"suspicious","node_count":214,"edge_count":633,"truncated":false,
  "time_start":"2026-11-01T00:04:00","time_end":"2026-11-14T23:51:00"}}
```

`GET /api/evaluation` (shape — numbers are produced live, these are placeholders)
```json
{"available":true,"reason":null,"granularity":"transaction","label_source":"synthetic",
 "total":5120,"positives":412,"negatives":4708,
 "thresholds":{"ALERT_THRESHOLD":40,"BASELINE_LARGE_TX":1000000,"BASELINE_DAILY_OUT_AMOUNT":2500000,"BASELINE_DAILY_OUT_COUNT":10},
 "models":[{"model":"graph","display_name":"Graph-based detection","precision":0.0,"recall":0.0,"f1":0.0,"accuracy":0.0,"flagged_count":0,"confusion_matrix":{"tp":0,"fp":0,"fn":0,"tn":0}},
           {"model":"baseline","display_name":"Rule-based baseline","precision":0.0,"recall":0.0,"f1":0.0,"accuracy":0.0,"flagged_count":0,"confusion_matrix":{"tp":0,"fp":0,"fn":0,"tn":0}}],
 "per_typology":[{"typology":"CYCLE","label":"Round-tripping (cycle)","positives":0,"graph_recall":0.0,"baseline_recall":0.0}],
 "notes":["Labels come from a synthetic dataset generated by backend/scripts/generate_synthetic.py (seed 42)."]}
```

---

## 11. Synthetic labelled dataset (Member 3 builds, everyone uses)

`backend/scripts/generate_synthetic.py` (seed 42) writes `backend/data/sample_transactions.csv`, **clearly synthetic**, ~400 accounts (`ACC0001`…), 2026-11-01 → 2026-11-14, ~5,000 rows, all CSV columns filled:
- **Ordinary**: ~4,000 P2P/merchant transfers, log-normal amounts ₹200–₹2,00,000, random times. `label=normal`.
- **Legitimate high volume (false-positive traps)**: 2 merchants each receiving from 60+ customers and holding the money; 1 payroll account paying 40 employees on two pay days; 1 corporate making several genuine transfers ≥ ₹10,00,000. `label=normal`.
- **Injected laundering** (`label=suspicious`, `gt_typology` set): 4 fan-in rings (6–10 mules → collector, then collector forwards within hours); 4 fan-out dispersions (large inflow then split to 6–10 accounts within 24 h); 4 cycles (3–5 accounts, time-ordered hops within 3 days, 1–3% shaved per hop); 4 pass-through chains (4–7 accounts, 10–180 min per hop, 92–99% forwarded); 2 scatter-gather (fan-out to mules → mules fan-in to one collector). Many injected amounts sit just below ₹10,00,000 (structuring).

Optional, after the review: `scripts/convert_ibm_aml.py` converts a slice of the public IBM "Transactions for Anti Money Laundering" Kaggle dataset into this CSV format for an independent evaluation.

---

## 12. Frontend screens → endpoints

| Screen (route) | Endpoints |
|---|---|
| Landing `/` (frontend only) | `/overview` (live numbers, optional), `/health` |
| Overview `/dashboard` | `/overview`, `/alerts`, `/health` |
| Upload `/upload` | `/upload`, `/dataset/load-sample`, `/dataset/sample`, `/analyze` |
| Transactions `/transactions` | `/transactions` |
| Graph Explorer `/graph` | `/graph`, `/patterns`, `/clusters` |
| Clusters `/clusters` | `/clusters`, `/alerts` |
| Cluster investigation `/clusters/:clusterId` | `/clusters/{id}` |
| Account `/accounts/:accountId` | `/accounts/{id}` |
| Risk & Typology `/risk` | `/clusters`, `/patterns`, `/config`, `/overview` |
| Evaluation `/evaluation` | `/evaluation`, `/config`, `/analyze` |

---

## 13. Integration and Git rules

1. One repo `finthread`. Branches: `feat/frontend` (M1), `feat/backend` (M2, Integration Lead), `feat/intel` (M3). `main` is only updated by the lead through GitHub Pull Requests.
2. Work only in your own folders (Section 3). Never edit, reformat or delete another member's files.
3. `contracts.py`, `schemas.py`, `contract.ts` and this file are frozen. If something is missing, message the lead; the lead changes all copies together and everyone pulls.
4. Commit small, push to your branch every 30–45 minutes.
5. At each checkpoint the lead merges PRs into `main`; everyone then runs `git pull origin main` on their own branch.
6. Mock data must match these schemas exactly, so switching `VITE_USE_MOCK=false` just works.
7. Ask before any architecture-level change.

---

## Appendix A — `backend/app/contracts.py` (frozen, copy verbatim)

```python
"""Shared internal contracts between the detection engine (M2) and intelligence/evaluation (M3).
FROZEN: only the Integration Lead edits this file."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal, Optional

import networkx as nx
import pandas as pd

PatternType = Literal["FAN_IN", "FAN_OUT", "CYCLE", "PASS_THROUGH"]
Typology = Literal["FAN_IN", "FAN_OUT", "CYCLE", "PASS_THROUGH", "SCATTER_GATHER"]
RiskLevel = Literal["high", "medium", "low", "none"]

TYPOLOGY_LABELS: dict[str, str] = {
    "FAN_IN": "Fan-in (funnel collection)",
    "FAN_OUT": "Fan-out (dispersion)",
    "CYCLE": "Round-tripping (cycle)",
    "PASS_THROUGH": "Rapid pass-through (mule chain)",
    "SCATTER_GATHER": "Scatter-gather layering",
}
DISCLAIMER = "This alert highlights a pattern that warrants analyst review. It is not proof of money laundering."


# ---------- produced by Member 2 (detection) ----------
@dataclass
class PatternHit:
    pattern_id: str
    pattern_type: PatternType
    focal_account: Optional[str]
    accounts: list[str]                 # ordered for CYCLE / PASS_THROUGH
    transaction_ids: list[str]          # evidence, chronological
    start_time: datetime
    end_time: datetime
    total_amount: float
    metrics: dict[str, float] = field(default_factory=dict)
    cluster_id: Optional[str] = None


@dataclass
class AccountFeatures:
    account_id: str
    in_degree: int
    out_degree: int
    in_tx_count: int
    out_tx_count: int
    total_in: float
    total_out: float
    first_seen: datetime
    last_seen: datetime
    median_dwell_minutes: Optional[float]
    retention_ratio: Optional[float]
    max_out_24h_amount: float
    max_out_24h_count: int
    pattern_ids: list[str] = field(default_factory=list)


@dataclass
class RawCluster:
    cluster_id: str
    accounts: list[str]
    transaction_ids: list[str]
    pattern_ids: list[str]


@dataclass
class DetectionOutput:
    transactions: pd.DataFrame          # columns per contract Section 7
    graph: nx.MultiDiGraph
    patterns: list[PatternHit]
    clusters: list[RawCluster]
    account_features: dict[str, AccountFeatures]


# ---------- produced by Member 3 (intelligence + evaluation) ----------
@dataclass
class ScoreFactor:
    factor: str                         # pattern_severity | multiple_typologies | velocity | structuring | flow_through
    points: int
    max_points: int
    reason: str


@dataclass
class EvidenceItem:
    transaction_id: str
    sender: str
    receiver: str
    amount: float
    timestamp: datetime
    note: str


@dataclass
class Explanation:
    headline: str
    summary: str
    bullet_points: list[str]
    evidence: list[EvidenceItem]
    disclaimer: str = DISCLAIMER


@dataclass
class ClusterAccountRole:
    account_id: str
    role: Literal["source", "intermediary", "collector", "member"]
    total_in: float                     # inside the cluster
    total_out: float                    # inside the cluster


@dataclass
class ScoredCluster:
    cluster_id: str
    accounts: list[ClusterAccountRole]
    transaction_ids: list[str]
    pattern_ids: list[str]
    typologies: list[Typology]
    primary_typology: Typology
    risk_score: int
    risk_level: RiskLevel
    alerted: bool
    score_breakdown: list[ScoreFactor]
    explanation: Explanation
    total_amount: float
    start_time: datetime
    end_time: datetime
    median_hop_minutes: Optional[float]


@dataclass
class AlertRecord:
    alert_id: str
    cluster_id: str
    risk_score: int
    risk_level: RiskLevel
    primary_typology: Typology
    typologies: list[Typology]
    headline: str
    created_at: datetime
    account_count: int
    transaction_count: int
    total_amount: float
    status: Literal["open"] = "open"


@dataclass
class AccountRisk:
    risk_score: Optional[int]
    risk_level: RiskLevel
    typologies: list[Typology]
    cluster_ids: list[str]


@dataclass
class BaselineOutput:
    flagged_transaction_ids: set[str]
    rules_triggered: dict[str, list[str]]   # transaction_id -> ["R1_LARGE_AMOUNT", ...]


# EvaluationResult is a plain dict shaped exactly like schemas.EvaluationOut
EvaluationResult = dict[str, Any]


# ---------- assembled by Member 2 (pipeline) ----------
@dataclass
class DatasetMeta:
    dataset_id: str
    name: str
    source: Literal["upload", "sample"]
    uploaded_at: datetime
    row_count: int
    has_labels: bool


@dataclass
class AnalysisResult:
    run_id: str
    dataset: DatasetMeta
    started_at: datetime
    finished_at: datetime
    detection: DetectionOutput
    clusters: list[ScoredCluster]
    alerts: list[AlertRecord]
    account_risk: dict[str, AccountRisk]
    baseline: BaselineOutput
    evaluation: EvaluationResult
```

---

## Appendix B — `backend/app/schemas.py` (frozen, copy verbatim)

```python
"""API response/request models. FROZEN: only the Integration Lead edits this file.
Field names must match frontend/src/types/contract.ts exactly."""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

RiskLevel = Literal["high", "medium", "low", "none"]
PatternType = Literal["FAN_IN", "FAN_OUT", "CYCLE", "PASS_THROUGH"]
Typology = Literal["FAN_IN", "FAN_OUT", "CYCLE", "PASS_THROUGH", "SCATTER_GATHER"]


class HealthOut(BaseModel):
    status: str
    version: str
    dataset_loaded: bool
    run_id: Optional[str] = None


class DatasetInfo(BaseModel):
    dataset_id: str
    name: str
    source: Literal["upload", "sample"]
    uploaded_at: datetime
    row_count: int
    has_labels: bool


class RowError(BaseModel):
    row_number: int
    transaction_id: Optional[str] = None
    field: Optional[str] = None
    message: str


class ValidationReport(BaseModel):
    total_rows: int
    accepted_rows: int
    rejected_rows: int
    has_labels: bool
    errors: list[RowError]               # first 100 only


class RunCounts(BaseModel):
    transactions: int
    accounts: int
    patterns: int
    clusters: int
    alerts: int


class RunSummary(BaseModel):
    run_id: str
    dataset_id: str
    status: Literal["completed", "failed"]
    started_at: datetime
    finished_at: datetime
    duration_ms: int
    counts: RunCounts
    error: Optional[str] = None


class UploadResponse(BaseModel):
    dataset: DatasetInfo
    validation: ValidationReport
    run: Optional[RunSummary] = None


class AnalyzeRequest(BaseModel):
    overrides: dict[str, float] = Field(default_factory=dict)


class ConfigOut(BaseModel):
    detection: dict[str, float]
    risk: dict[str, float]
    baseline: dict[str, float]


class GroundTruth(BaseModel):
    label: Optional[Literal["suspicious", "normal"]] = None
    typology: Optional[Typology] = None


class Prediction(BaseModel):
    graph_flagged: bool
    cluster_id: Optional[str] = None
    patterns: list[PatternType]
    baseline_flagged: bool
    baseline_rules: list[str]


class TransactionOut(BaseModel):
    transaction_id: str
    sender: str
    receiver: str
    amount: float
    timestamp: datetime
    currency: str
    channel: Optional[str] = None
    ground_truth: Optional[GroundTruth] = None
    prediction: Prediction


class TransactionPage(BaseModel):
    items: list[TransactionOut]
    page: int
    page_size: int
    total: int


class GraphNode(BaseModel):
    id: str
    label: str
    risk_score: Optional[int] = None
    risk_level: RiskLevel
    total_in: float
    total_out: float
    in_degree: int
    out_degree: int
    patterns: list[PatternType]
    cluster_ids: list[str]
    is_suspicious: bool


class GraphEdge(BaseModel):
    id: str                              # = transaction_id
    source: str
    target: str
    amount: float
    timestamp: datetime
    channel: Optional[str] = None
    patterns: list[PatternType]
    pattern_ids: list[str]
    cluster_id: Optional[str] = None
    is_suspicious: bool


class GraphMeta(BaseModel):
    scope: Literal["suspicious", "full", "cluster", "account"]
    node_count: int
    edge_count: int
    truncated: bool
    time_start: Optional[datetime] = None
    time_end: Optional[datetime] = None


class GraphOut(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    meta: GraphMeta


class PatternOut(BaseModel):
    pattern_id: str
    pattern_type: PatternType
    focal_account: Optional[str] = None
    accounts: list[str]
    transaction_ids: list[str]
    start_time: datetime
    end_time: datetime
    total_amount: float
    metrics: dict[str, float]
    cluster_id: Optional[str] = None


class PatternList(BaseModel):
    items: list[PatternOut]


class ScoreFactorOut(BaseModel):
    factor: str
    points: int
    max_points: int
    reason: str


class EvidenceOut(BaseModel):
    transaction_id: str
    sender: str
    receiver: str
    amount: float
    timestamp: datetime
    note: str


class ExplanationOut(BaseModel):
    headline: str
    summary: str
    bullet_points: list[str]
    evidence: list[EvidenceOut]
    disclaimer: str


class ClusterSummary(BaseModel):
    cluster_id: str
    risk_score: int
    risk_level: RiskLevel
    primary_typology: Typology
    typologies: list[Typology]
    account_count: int
    transaction_count: int
    total_amount: float
    start_time: datetime
    end_time: datetime
    median_hop_minutes: Optional[float] = None
    alerted: bool
    headline: str


class ClusterAccount(BaseModel):
    account_id: str
    role: Literal["source", "intermediary", "collector", "member"]
    total_in: float
    total_out: float


class ClusterDetail(ClusterSummary):
    accounts: list[ClusterAccount]
    patterns: list[PatternOut]
    score_breakdown: list[ScoreFactorOut]
    explanation: ExplanationOut
    transactions: list[TransactionOut]
    subgraph: GraphOut


class ClusterList(BaseModel):
    items: list[ClusterSummary]
    total: int


class AlertOut(BaseModel):
    alert_id: str
    cluster_id: str
    risk_score: int
    risk_level: RiskLevel
    primary_typology: Typology
    typologies: list[Typology]
    headline: str
    created_at: datetime
    account_count: int
    transaction_count: int
    total_amount: float
    status: Literal["open"]


class AlertList(BaseModel):
    items: list[AlertOut]
    total: int


class AccountProfile(BaseModel):
    account_id: str
    in_degree: int
    out_degree: int
    in_tx_count: int
    out_tx_count: int
    total_in: float
    total_out: float
    first_seen: datetime
    last_seen: datetime
    median_dwell_minutes: Optional[float] = None
    retention_ratio: Optional[float] = None
    max_out_24h_amount: float
    max_out_24h_count: int


class AccountRiskOut(BaseModel):
    risk_score: Optional[int] = None
    risk_level: RiskLevel
    typologies: list[Typology]
    cluster_ids: list[str]


class Counterparty(BaseModel):
    account_id: str
    direction: Literal["in", "out"]
    tx_count: int
    total_amount: float


class AccountDetail(BaseModel):
    account: AccountProfile
    risk: AccountRiskOut
    patterns: list[PatternOut]
    counterparties: list[Counterparty]   # top 20 by total_amount
    transactions: list[TransactionOut]   # latest 200, in and out
    subgraph: GraphOut                   # 1-hop ego network


class TypologyCount(BaseModel):
    typology: Typology
    label: str
    count: int                           # clusters having this typology


class LevelCount(BaseModel):
    level: RiskLevel
    count: int                           # clusters at this level


class DailyVolume(BaseModel):
    date: str                            # YYYY-MM-DD
    tx_count: int
    total_amount: float
    flagged_amount: float                # amount in graph-flagged transactions


class OverviewStats(BaseModel):
    total_transactions: int
    total_accounts: int
    total_amount: float
    flagged_transactions: int
    clusters: int
    alerts: int
    high_risk_alerts: int
    medium_risk_alerts: int


class HeadlineMetrics(BaseModel):
    graph_f1: float
    baseline_f1: float
    graph_recall: float
    baseline_recall: float


class OverviewOut(BaseModel):
    dataset: DatasetInfo
    run: RunSummary
    stats: OverviewStats
    typology_counts: list[TypologyCount]
    risk_distribution: list[LevelCount]
    top_alerts: list[AlertOut]           # top 5
    daily_volume: list[DailyVolume]
    headline_metrics: Optional[HeadlineMetrics] = None


class ConfusionMatrix(BaseModel):
    tp: int
    fp: int
    fn: int
    tn: int


class ModelMetrics(BaseModel):
    model: Literal["graph", "baseline"]
    display_name: str
    precision: float
    recall: float
    f1: float
    accuracy: float
    flagged_count: int
    confusion_matrix: ConfusionMatrix


class TypologyRecall(BaseModel):
    typology: Typology
    label: str
    positives: int
    graph_recall: Optional[float] = None
    baseline_recall: Optional[float] = None


class EvaluationOut(BaseModel):
    available: bool
    reason: Optional[str] = None
    granularity: Literal["transaction"] = "transaction"
    label_source: Optional[Literal["synthetic", "uploaded"]] = None
    total: int = 0
    positives: int = 0
    negatives: int = 0
    thresholds: dict[str, float] = Field(default_factory=dict)
    models: list[ModelMetrics] = Field(default_factory=list)
    per_typology: list[TypologyRecall] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
```

---

## Appendix C — `frontend/src/types/contract.ts` (frozen, copy verbatim)

```ts
// FROZEN: mirrors backend/app/schemas.py. Datetimes arrive as ISO strings.
export type RiskLevel = "high" | "medium" | "low" | "none";
export type PatternType = "FAN_IN" | "FAN_OUT" | "CYCLE" | "PASS_THROUGH";
export type Typology = PatternType | "SCATTER_GATHER";
export type ISODate = string;

export const TYPOLOGY_LABELS: Record<Typology, string> = {
  FAN_IN: "Fan-in (funnel collection)",
  FAN_OUT: "Fan-out (dispersion)",
  CYCLE: "Round-tripping (cycle)",
  PASS_THROUGH: "Rapid pass-through (mule chain)",
  SCATTER_GATHER: "Scatter-gather layering",
};

export interface HealthOut { status: string; version: string; dataset_loaded: boolean; run_id: string | null; }
export interface DatasetInfo { dataset_id: string; name: string; source: "upload" | "sample"; uploaded_at: ISODate; row_count: number; has_labels: boolean; }
export interface RowError { row_number: number; transaction_id: string | null; field: string | null; message: string; }
export interface ValidationReport { total_rows: number; accepted_rows: number; rejected_rows: number; has_labels: boolean; errors: RowError[]; }
export interface RunCounts { transactions: number; accounts: number; patterns: number; clusters: number; alerts: number; }
export interface RunSummary { run_id: string; dataset_id: string; status: "completed" | "failed"; started_at: ISODate; finished_at: ISODate; duration_ms: number; counts: RunCounts; error: string | null; }
export interface UploadResponse { dataset: DatasetInfo; validation: ValidationReport; run: RunSummary | null; }
export interface AnalyzeRequest { overrides?: Record<string, number>; }
export interface ConfigOut { detection: Record<string, number>; risk: Record<string, number>; baseline: Record<string, number>; }

export interface GroundTruth { label: "suspicious" | "normal" | null; typology: Typology | null; }
export interface Prediction { graph_flagged: boolean; cluster_id: string | null; patterns: PatternType[]; baseline_flagged: boolean; baseline_rules: string[]; }
export interface TransactionOut { transaction_id: string; sender: string; receiver: string; amount: number; timestamp: ISODate; currency: string; channel: string | null; ground_truth: GroundTruth | null; prediction: Prediction; }
export interface TransactionPage { items: TransactionOut[]; page: number; page_size: number; total: number; }

export interface GraphNode { id: string; label: string; risk_score: number | null; risk_level: RiskLevel; total_in: number; total_out: number; in_degree: number; out_degree: number; patterns: PatternType[]; cluster_ids: string[]; is_suspicious: boolean; }
export interface GraphEdge { id: string; source: string; target: string; amount: number; timestamp: ISODate; channel: string | null; patterns: PatternType[]; pattern_ids: string[]; cluster_id: string | null; is_suspicious: boolean; }
export interface GraphMeta { scope: "suspicious" | "full" | "cluster" | "account"; node_count: number; edge_count: number; truncated: boolean; time_start: ISODate | null; time_end: ISODate | null; }
export interface GraphOut { nodes: GraphNode[]; edges: GraphEdge[]; meta: GraphMeta; }

export interface PatternOut { pattern_id: string; pattern_type: PatternType; focal_account: string | null; accounts: string[]; transaction_ids: string[]; start_time: ISODate; end_time: ISODate; total_amount: number; metrics: Record<string, number>; cluster_id: string | null; }
export interface PatternList { items: PatternOut[]; }

export interface ScoreFactorOut { factor: string; points: number; max_points: number; reason: string; }
export interface EvidenceOut { transaction_id: string; sender: string; receiver: string; amount: number; timestamp: ISODate; note: string; }
export interface ExplanationOut { headline: string; summary: string; bullet_points: string[]; evidence: EvidenceOut[]; disclaimer: string; }
export interface ClusterSummary { cluster_id: string; risk_score: number; risk_level: RiskLevel; primary_typology: Typology; typologies: Typology[]; account_count: number; transaction_count: number; total_amount: number; start_time: ISODate; end_time: ISODate; median_hop_minutes: number | null; alerted: boolean; headline: string; }
export interface ClusterAccount { account_id: string; role: "source" | "intermediary" | "collector" | "member"; total_in: number; total_out: number; }
export interface ClusterDetail extends ClusterSummary { accounts: ClusterAccount[]; patterns: PatternOut[]; score_breakdown: ScoreFactorOut[]; explanation: ExplanationOut; transactions: TransactionOut[]; subgraph: GraphOut; }
export interface ClusterList { items: ClusterSummary[]; total: number; }

export interface AlertOut { alert_id: string; cluster_id: string; risk_score: number; risk_level: RiskLevel; primary_typology: Typology; typologies: Typology[]; headline: string; created_at: ISODate; account_count: number; transaction_count: number; total_amount: number; status: "open"; }
export interface AlertList { items: AlertOut[]; total: number; }

export interface AccountProfile { account_id: string; in_degree: number; out_degree: number; in_tx_count: number; out_tx_count: number; total_in: number; total_out: number; first_seen: ISODate; last_seen: ISODate; median_dwell_minutes: number | null; retention_ratio: number | null; max_out_24h_amount: number; max_out_24h_count: number; }
export interface AccountRiskOut { risk_score: number | null; risk_level: RiskLevel; typologies: Typology[]; cluster_ids: string[]; }
export interface Counterparty { account_id: string; direction: "in" | "out"; tx_count: number; total_amount: number; }
export interface AccountDetail { account: AccountProfile; risk: AccountRiskOut; patterns: PatternOut[]; counterparties: Counterparty[]; transactions: TransactionOut[]; subgraph: GraphOut; }

export interface TypologyCount { typology: Typology; label: string; count: number; }
export interface LevelCount { level: RiskLevel; count: number; }
export interface DailyVolume { date: string; tx_count: number; total_amount: number; flagged_amount: number; }
export interface OverviewStats { total_transactions: number; total_accounts: number; total_amount: number; flagged_transactions: number; clusters: number; alerts: number; high_risk_alerts: number; medium_risk_alerts: number; }
export interface HeadlineMetrics { graph_f1: number; baseline_f1: number; graph_recall: number; baseline_recall: number; }
export interface OverviewOut { dataset: DatasetInfo; run: RunSummary; stats: OverviewStats; typology_counts: TypologyCount[]; risk_distribution: LevelCount[]; top_alerts: AlertOut[]; daily_volume: DailyVolume[]; headline_metrics: HeadlineMetrics | null; }

export interface ConfusionMatrix { tp: number; fp: number; fn: number; tn: number; }
export interface ModelMetrics { model: "graph" | "baseline"; display_name: string; precision: number; recall: number; f1: number; accuracy: number; flagged_count: number; confusion_matrix: ConfusionMatrix; }
export interface TypologyRecall { typology: Typology; label: string; positives: number; graph_recall: number | null; baseline_recall: number | null; }
export interface EvaluationOut { available: boolean; reason: string | null; granularity: "transaction"; label_source: "synthetic" | "uploaded" | null; total: number; positives: number; negatives: number; thresholds: Record<string, number>; models: ModelMetrics[]; per_typology: TypologyRecall[]; notes: string[]; }
```
