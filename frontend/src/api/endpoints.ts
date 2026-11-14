import { apiFetch } from './client';
import type {
  HealthOut, UploadResponse, RunSummary, ConfigOut,
  TransactionPage, GraphOut, PatternList, AccountDetail,
  OverviewOut, ClusterList, ClusterDetail, AlertList, EvaluationOut,
} from '../types/contract';

export const getHealth = () => apiFetch<HealthOut>('/api/health');
export const loadSample = () => apiFetch<UploadResponse>('/api/dataset/load-sample', { method: 'POST' });
export const analyze = () => apiFetch<RunSummary>('/api/analyze', { method: 'POST', body: JSON.stringify({}) });
export const getConfig = () => apiFetch<ConfigOut>('/api/config');
export const getOverview = () => apiFetch<OverviewOut>('/api/overview');
export const getAlerts = () => apiFetch<AlertList>('/api/alerts');
export const getClusters = (params?: string) => apiFetch<ClusterList>(`/api/clusters${params ? '?' + params : ''}`);
export const getCluster = (id: string) => apiFetch<ClusterDetail>(`/api/clusters/${id}`);
export const getGraph = (params?: string) => apiFetch<GraphOut>(`/api/graph${params ? '?' + params : ''}`);
export const getPatterns = (params?: string) => apiFetch<PatternList>(`/api/patterns${params ? '?' + params : ''}`);
export const getTransactions = (params?: string) => apiFetch<TransactionPage>(`/api/transactions${params ? '?' + params : ''}`);
export const getAccount = (id: string) => apiFetch<AccountDetail>(`/api/accounts/${id}`);
export const getEvaluation = () => apiFetch<EvaluationOut>('/api/evaluation');

export async function uploadCsv(file: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append('file', file);
  const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
  const res = await fetch(`${BASE_URL}/api/upload`, { method: 'POST', body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? res.statusText);
  }
  return res.json();
}