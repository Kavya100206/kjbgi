/**
 * Typed API client for Vane backend endpoints.
 */

import type {
  AccuracyByHorizonResponse,
  AccuracyByHourResponse,
  AccuracyDailyResponse,
  AccuracyDistributionResponse,
  AccuracySummaryResponse,
  ForecastDayResponse,
  ForecastRevisionsResponse,
  MetaResponse,
  RiskBandResponse,
} from "./types";

const BASE_URL = "";

async function fetchJson<T>(url: string): Promise<T> {
  const resp = await fetch(url);
  if (!resp.ok) {
    let errorDetail = `Request failed: ${resp.status} ${resp.statusText}`;
    try {
      const errBody = await resp.json();
      if (errBody && errBody.detail) {
        errorDetail = typeof errBody.detail === "string" ? errBody.detail : JSON.stringify(errBody.detail);
      }
    } catch {
      // ignore json parse failure on error body
    }
    throw new Error(errorDetail);
  }
  return resp.json();
}

export async function fetchMeta(): Promise<MetaResponse> {
  return fetchJson<MetaResponse>(`${BASE_URL}/api/meta`);
}

export async function fetchForecastDay(date: string, cutoffHour: number): Promise<ForecastDayResponse> {
  const params = new URLSearchParams({
    date,
    cutoff_hour: cutoffHour.toString(),
  });
  return fetchJson<ForecastDayResponse>(`${BASE_URL}/api/forecast/day?${params}`);
}

export async function fetchForecastRevisions(targetOrDate: {
  target?: string;
  date?: string;
  cutoffHour: number;
}): Promise<ForecastRevisionsResponse> {
  const params = new URLSearchParams({
    cutoff_hour: targetOrDate.cutoffHour.toString(),
  });
  if (targetOrDate.target) {
    params.set("target", targetOrDate.target);
  } else if (targetOrDate.date) {
    params.set("date", targetOrDate.date);
  }
  return fetchJson<ForecastRevisionsResponse>(`${BASE_URL}/api/forecast/revisions?${params}`);
}

export async function fetchAccuracySummary(
  fromDate: string,
  toDate: string,
  cutoffHour: number
): Promise<AccuracySummaryResponse> {
  const params = new URLSearchParams({
    from_date: fromDate,
    to_date: toDate,
    cutoff_hour: cutoffHour.toString(),
  });
  return fetchJson<AccuracySummaryResponse>(`${BASE_URL}/api/accuracy/summary?${params}`);
}

export async function fetchAccuracyByHorizon(
  fromDate: string,
  toDate: string
): Promise<AccuracyByHorizonResponse> {
  const params = new URLSearchParams({
    from_date: fromDate,
    to_date: toDate,
  });
  return fetchJson<AccuracyByHorizonResponse>(`${BASE_URL}/api/accuracy/by-horizon?${params}`);
}

export async function fetchAccuracyByHour(
  fromDate: string,
  toDate: string,
  cutoffHour: number
): Promise<AccuracyByHourResponse> {
  const params = new URLSearchParams({
    from_date: fromDate,
    to_date: toDate,
    cutoff_hour: cutoffHour.toString(),
  });
  return fetchJson<AccuracyByHourResponse>(`${BASE_URL}/api/accuracy/by-hour?${params}`);
}

export async function fetchAccuracyDaily(
  fromDate: string,
  toDate: string,
  cutoffHour: number
): Promise<AccuracyDailyResponse> {
  const params = new URLSearchParams({
    from_date: fromDate,
    to_date: toDate,
    cutoff_hour: cutoffHour.toString(),
  });
  return fetchJson<AccuracyDailyResponse>(`${BASE_URL}/api/accuracy/daily?${params}`);
}

export async function fetchAccuracyDistribution(
  fromDate: string,
  toDate: string,
  cutoffHour: number,
  bins: number = 20
): Promise<AccuracyDistributionResponse> {
  const params = new URLSearchParams({
    from_date: fromDate,
    to_date: toDate,
    cutoff_hour: cutoffHour.toString(),
    bins: bins.toString(),
  });
  return fetchJson<AccuracyDistributionResponse>(`${BASE_URL}/api/accuracy/distribution?${params}`);
}

export async function fetchRiskBand(
  date: string,
  cutoffHour: number,
  confidence: number = 0.8
): Promise<RiskBandResponse> {
  const params = new URLSearchParams({
    date,
    cutoff_hour: cutoffHour.toString(),
    confidence: confidence.toString(),
  });
  return fetchJson<RiskBandResponse>(`${BASE_URL}/api/risk/band?${params}`);
}
