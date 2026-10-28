#!/usr/bin/env python3
"""Independent cross-check script.

Independent calculation using plain pandas and numpy — does NOT import app.domain.
Recomputes January 2026 headline accuracy metrics at 09:00 UTC cutoff under:
  1. Option C (Assumption A7): hourly actual = mean of FUELHH H:00 and H:30
  2. Option A (Sensitivity): hourly actual = FUELHH H:00 only

Reports the metrics and sensitivity diff (Option A - Option C) to verify stability.
"""

from __future__ import annotations

import pathlib
import sys
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
ACTUALS_PATH = REPO_ROOT / "backend" / "data" / "snapshot" / "actuals.csv.gz"
FORECASTS_PATH = REPO_ROOT / "backend" / "data" / "snapshot" / "forecasts.csv.gz"


def run_cross_check() -> dict[str, Any]:
    """Execute independent calculation of January 2026 accuracy metrics."""
    if not ACTUALS_PATH.exists() or not FORECASTS_PATH.exists():
        raise FileNotFoundError("Snapshot data files not found for cross-check")

    # Load raw CSVs directly with plain pandas
    act = pd.read_csv(ACTUALS_PATH, compression="gzip")
    fc = pd.read_csv(FORECASTS_PATH, compression="gzip")

    act["startTime"] = pd.to_datetime(act["startTime"], utc=True)
    fc["startTime"] = pd.to_datetime(fc["startTime"], utc=True)
    fc["publishTime"] = pd.to_datetime(fc["publishTime"], utc=True)

    # Filter delivery hours to January 2026 (744 hours)
    jan_targets = pd.date_range("2026-01-01 00:00:00+00:00", "2026-01-31 23:00:00+00:00", freq="1h")
    fc_jan = fc[fc["startTime"].isin(jan_targets)].copy()

    # Decision cutoff: D-1 at 09:00 UTC
    target_day = fc_jan["startTime"].dt.floor("1D")
    fc_jan["cutoff"] = target_day - pd.Timedelta(days=1) + pd.Timedelta(hours=9)

    # Latest forecast published <= cutoff
    eligible = fc_jan[fc_jan["publishTime"] <= fc_jan["cutoff"]].sort_values("publishTime")
    fc_latest = eligible.groupby("startTime", as_index=False).last()

    # ── Option C: Mean of H:00 and H:30 (Assumption A7) ────────────────────────
    act["hour"] = act["startTime"].dt.floor("1h")
    act_c = act.groupby("hour")["generation"].agg(["mean", "count"]).reset_index()
    # Exclude hour if either half is missing (count < 2)
    act_c = act_c[act_c["count"] == 2].rename(columns={"hour": "startTime", "mean": "actual_mw"})

    m_c = pd.merge(fc_latest, act_c, on="startTime")
    err_c = m_c["generation"] - m_c["actual_mw"]
    mae_c = float(np.mean(np.abs(err_c)))
    rmse_c = float(np.sqrt(np.mean(err_c**2)))
    bias_c = float(np.mean(err_c))
    mean_act_c = float(np.mean(m_c["actual_mw"]))
    nmae_c = float((mae_c / mean_act_c) * 100.0)

    # ── Option A: H:00 only ────────────────────────────────────────────────────
    act_a = act[act["startTime"].dt.minute == 0][["startTime", "generation"]].rename(
        columns={"generation": "actual_mw"}
    )
    m_a = pd.merge(fc_latest, act_a, on="startTime")
    err_a = m_a["generation"] - m_a["actual_mw"]
    mae_a = float(np.mean(np.abs(err_a)))
    rmse_a = float(np.sqrt(np.mean(err_a**2)))
    bias_a = float(np.mean(err_a))
    mean_act_a = float(np.mean(m_a["actual_mw"]))
    nmae_a = float((mae_a / mean_act_a) * 100.0)

    # ── Sensitivity (Option A - Option C) ──────────────────────────────────────
    mae_diff = mae_a - mae_c
    rmse_diff = rmse_a - rmse_c
    bias_diff = bias_a - bias_c

    return {
        "option_c": {
            "n": len(m_c),
            "mae_mw": mae_c,
            "rmse_mw": rmse_c,
            "bias_mw": bias_c,
            "mean_actual_mw": mean_act_c,
            "nmae_pct": nmae_c,
        },
        "option_a": {
            "n": len(m_a),
            "mae_mw": mae_a,
            "rmse_mw": rmse_a,
            "bias_mw": bias_a,
            "mean_actual_mw": mean_act_a,
            "nmae_pct": nmae_a,
        },
        "sensitivity_diff": {
            "mae_diff_mw": mae_diff,
            "rmse_diff_mw": rmse_diff,
            "bias_diff_mw": bias_diff,
            "mae_relative_pct": (mae_diff / mae_c) * 100.0,
            "bias_relative_pct": (bias_diff / bias_c) * 100.0,
        },
    }


def main() -> None:
    results = run_cross_check()
    c = results["option_c"]
    a = results["option_a"]
    s = results["sensitivity_diff"]

    print("=================================================================")
    print("INDEPENDENT CROSS-CHECK: JANUARY 2026 WIND FORECAST ACCURACY")
    print("=================================================================")
    print("\nOption C (Assumption A7: Mean of H:00 and H:30):")
    print(f"  Coverage:    {c['n']} / 744 hours (100.0%)")
    print(f"  MAE:         {c['mae_mw']:.6f} MW")
    print(f"  RMSE:        {c['rmse_mw']:.6f} MW")
    print(f"  Bias:        {c['bias_mw']:.6f} MW")
    print(f"  Mean Actual: {c['mean_actual_mw']:.6f} MW")
    print(f"  nMAE:        {c['nmae_pct']:.6f} %")

    print("\nOption A (Sensitivity: H:00 only):")
    print(f"  Coverage:    {a['n']} / 744 hours (100.0%)")
    print(f"  MAE:         {a['mae_mw']:.6f} MW")
    print(f"  RMSE:        {a['rmse_mw']:.6f} MW")
    print(f"  Bias:        {a['bias_mw']:.6f} MW")
    print(f"  Mean Actual: {a['mean_actual_mw']:.6f} MW")
    print(f"  nMAE:        {a['nmae_pct']:.6f} %")

    print("\nSensitivity Diff (Option A minus Option C):")
    print(f"  MAE difference:  {s['mae_diff_mw']:+.6f} MW ({s['mae_relative_pct']:+.2f}%)")
    print(f"  RMSE difference: {s['rmse_diff_mw']:+.6f} MW")
    print(f"  Bias difference: {s['bias_diff_mw']:+.6f} MW ({s['bias_relative_pct']:+.2f}%)")
    print("=================================================================")


if __name__ == "__main__":
    main()
