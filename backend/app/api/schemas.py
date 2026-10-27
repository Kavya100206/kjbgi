"""Pydantic request and response schemas for Vane API."""

from __future__ import annotations

from pydantic import BaseModel

# ── Metadata ──────────────────────────────────────────────────────────────────


class WindowInfo(BaseModel):
    start: str
    end: str
    default_cutoff_hour: int


class MetaResponse(BaseModel):
    status: str = "ready"
    ingested_at: str
    window: WindowInfo
    default_cutoff_hour: int = 9
    available_delivery_dates: list[str]
    actuals_rows: int
    forecasts_rows: int
    total_compressed_size_kb: float


# ── Forecast Day & Revisions ──────────────────────────────────────────────────


class ForecastHourItem(BaseModel):
    start_time: str
    hour: int
    forecast_mw: float
    publish_time: str
    forecast_age_h: float
    actual_mw: float | None = None
    error_mw: float | None = None


class ForecastDayResponse(BaseModel):
    delivery_date: str
    cutoff_hour: int
    selected_vintage_publish_time: str
    peak_forecast_mw: float
    mean_forecast_mw: float
    min_forecast_mw: float
    mean_actual_mw: float | None = None
    n_missing: int
    rows: list[ForecastHourItem]


class RevisionVintageItem(BaseModel):
    publish_time: str
    forecast_mw: float
    horizon_h: float
    forecast_age_h: float | None = None
    is_before_cutoff: bool | None = None


class ForecastRevisionsResponse(BaseModel):
    target_start_time: str
    delivery_date: str
    cutoff_hour: int
    actual_mw: float | None = None
    vintages: list[RevisionVintageItem]


# ── Accuracy Metrics ──────────────────────────────────────────────────────────


class AccuracySummaryResponse(BaseModel):
    from_date: str
    to_date: str
    cutoff_hour: int
    n: int
    denominator: int
    coverage_pct: float
    mae_mw: float | None = None
    rmse_mw: float | None = None
    bias_mw: float | None = None
    error_std_mw: float | None = None
    nmae_pct: float | None = None
    mean_actual_mw: float | None = None
    mean_forecast_mw: float | None = None
    forecast_to_actual_ratio: float | None = None
    bias_share_of_mse: float | None = None
    p50_abs_error_mw: float | None = None
    p90_abs_error_mw: float | None = None
    p95_abs_error_mw: float | None = None
    p90_over_forecast_mw: float | None = None
    worst_over_forecast_mw: float | None = None


class HorizonBucketItem(BaseModel):
    bucket: str
    n: int
    mean_forecast_mw: float | None = None
    mean_actual_mw: float | None = None
    bias_mw: float | None = None
    mae_mw: float | None = None
    rmse_mw: float | None = None


class AccuracyByHorizonResponse(BaseModel):
    from_date: str
    to_date: str
    total_vintages_evaluated: int
    excluded_backcasts_count: int
    buckets: list[HorizonBucketItem]


class HourMetricItem(BaseModel):
    hour: int
    mean_forecast_mw: float | None = None
    mean_actual_mw: float | None = None
    bias_mw: float | None = None
    mae_mw: float | None = None
    rmse_mw: float | None = None
    n: int
    coverage_pct: float


class AccuracyByHourResponse(BaseModel):
    from_date: str
    to_date: str
    cutoff_hour: int
    lead_time_confounding_note: str
    hours: list[HourMetricItem]


class DailyMetricItem(BaseModel):
    date: str
    mean_forecast_mw: float | None = None
    mean_actual_mw: float | None = None
    bias_mw: float | None = None
    mae_mw: float | None = None
    rmse_mw: float | None = None
    n: int
    coverage_pct: float


class AccuracyDailyResponse(BaseModel):
    from_date: str
    to_date: str
    cutoff_hour: int
    days: list[DailyMetricItem]


class DistributionBinItem(BaseModel):
    bin_start: float
    bin_end: float
    bin_mid: float
    count: int
    pct: float


class AccuracyDistributionResponse(BaseModel):
    from_date: str
    to_date: str
    cutoff_hour: int
    num_samples: int
    bins: list[DistributionBinItem]
    quantiles: dict[str, float]
    plain_english_reading: str


# ── Risk Buffer ───────────────────────────────────────────────────────────────


class RiskBandHourItem(BaseModel):
    start_time: str
    hour: int
    forecast_mw: float
    band_lo_mw: float
    band_hi_mw: float
    cushion_mw: float
    bias_used_mw: float


class RiskBandResponse(BaseModel):
    delivery_date: str
    cutoff_hour: int
    confidence: float
    history_days_used: int
    is_fallback: bool
    bias_used_mw: float
    hours: list[RiskBandHourItem]
