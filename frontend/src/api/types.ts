/**
 * API response types mirrored from backend Pydantic schemas.
 */

export interface MetaResponse {
  status: string;
  ingested_at: string;
  window: {
    start: string;
    end: string;
    default_cutoff_hour: number;
  };
  default_cutoff_hour: number;
  available_delivery_dates: string[];
  actuals_rows: number;
  forecasts_rows: number;
  total_compressed_size_kb: number;
}

export interface ForecastHourItem {
  start_time: string;
  hour: number;
  forecast_mw: number;
  publish_time: string;
  forecast_age_h: number;
  actual_mw: number | null;
  error_mw: number | null;
}

export interface ForecastDayResponse {
  delivery_date: string;
  cutoff_hour: number;
  selected_vintage_publish_time: string;
  peak_forecast_mw: number;
  mean_forecast_mw: number;
  min_forecast_mw: number;
  mean_actual_mw: number | null;
  n_missing: number;
  rows: ForecastHourItem[];
}

export interface RevisionVintageItem {
  publish_time: string;
  forecast_mw: number;
  horizon_h: number;
  forecast_age_h: number | null;
  is_before_cutoff: boolean | null;
}

export interface ForecastRevisionsResponse {
  target_start_time: string;
  delivery_date: string;
  cutoff_hour: number;
  actual_mw: number | null;
  vintages: RevisionVintageItem[];
}

export interface AccuracySummaryResponse {
  from_date: string;
  to_date: string;
  cutoff_hour: number;
  n: number;
  denominator: number;
  coverage_pct: number;
  mae_mw: number | null;
  rmse_mw: number | null;
  bias_mw: number | null;
  error_std_mw: number | null;
  nmae_pct: number | null;
  mean_actual_mw: number | null;
  mean_forecast_mw: number | null;
  forecast_to_actual_ratio: number | null;
  bias_share_of_mse: number | null;
  p50_abs_error_mw: number | null;
  p90_abs_error_mw: number | null;
  p95_abs_error_mw: number | null;
  p90_over_forecast_mw: number | null;
  worst_over_forecast_mw: number | null;
}

export interface HorizonBucketItem {
  bucket: string;
  n: number;
  mean_forecast_mw: number | null;
  mean_actual_mw: number | null;
  bias_mw: number | null;
  mae_mw: number | null;
  rmse_mw: number | null;
}

export interface AccuracyByHorizonResponse {
  from_date: string;
  to_date: string;
  total_vintages_evaluated: number;
  excluded_backcasts_count: number;
  buckets: HorizonBucketItem[];
}

export interface HourMetricItem {
  hour: number;
  mean_forecast_mw: number | null;
  mean_actual_mw: number | null;
  bias_mw: number | null;
  mae_mw: number | null;
  rmse_mw: number | null;
  n: number;
  coverage_pct: number;
}

export interface AccuracyByHourResponse {
  from_date: string;
  to_date: string;
  cutoff_hour: number;
  lead_time_confounding_note: string;
  hours: HourMetricItem[];
}

export interface DailyMetricItem {
  date: string;
  mean_forecast_mw: number | null;
  mean_actual_mw: number | null;
  bias_mw: number | null;
  mae_mw: number | null;
  rmse_mw: number | null;
  n: number;
  coverage_pct: number;
}

export interface AccuracyDailyResponse {
  from_date: string;
  to_date: string;
  cutoff_hour: number;
  days: DailyMetricItem[];
}

export interface DistributionBinItem {
  bin_start: number;
  bin_end: number;
  bin_mid: number;
  count: number;
  pct: number;
}

export interface AccuracyDistributionResponse {
  from_date: string;
  to_date: string;
  cutoff_hour: number;
  num_samples: number;
  bins: DistributionBinItem[];
  quantiles: Record<string, number>;
  plain_english_reading: string;
}

export interface RiskBandHourItem {
  start_time: string;
  hour: number;
  forecast_mw: number;
  band_lo_mw: number;
  band_hi_mw: number;
  cushion_mw: number;
  bias_used_mw: number;
}

export interface RiskBandResponse {
  delivery_date: string;
  cutoff_hour: number;
  confidence: number;
  history_days_used: number;
  is_fallback: boolean;
  bias_used_mw: number;
  hours: RiskBandHourItem[];
}
