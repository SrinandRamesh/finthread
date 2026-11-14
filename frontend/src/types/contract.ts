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