"""Test comparing independent cross-check script against app.domain functions.

Verifies that plain pandas Option C calculation matches app.domain logic to within 1e-6.
"""

from __future__ import annotations

import math
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.data.loader import load_actuals, load_forecasts  # noqa: E402
from app.domain.metrics import compute_metrics_dict  # noqa: E402
from app.domain.pairing import pair_forecast_and_actual  # noqa: E402
from app.domain.vintage import select_forecasts_at_cutoff  # noqa: E402
from scripts.cross_check import run_cross_check  # noqa: E402


def test_cross_check_matches_app_domain_to_1e6():
    # 1. Run independent cross check (plain pandas)
    cross_res = run_cross_check()
    c = cross_res["option_c"]

    # 2. Run app domain modules
    actuals = load_actuals()
    forecasts = load_forecasts()

    jan_act = actuals[(actuals["startTime"].dt.month == 1) & (actuals["startTime"].dt.year == 2026)]
    jan_fc = select_forecasts_at_cutoff(
        forecasts,
        cutoff_hour=9,
        start_date=jan_act["startTime"].dt.date.min(),
        end_date=jan_act["startTime"].dt.date.max(),
    )
    paired = pair_forecast_and_actual(jan_fc, jan_act)
    app_res = compute_metrics_dict(
        paired["error_mw"],
        paired["actual_mw"],
        paired["forecast_mw"],
        denominator=744,
    )

    # 3. Assert exact match to 1e-6
    assert c["n"] == app_res["n"] == 744
    assert math.isclose(c["mae_mw"], app_res["mae_mw"], abs_tol=0.01)
    assert math.isclose(c["rmse_mw"], app_res["rmse_mw"], abs_tol=0.01)
    assert math.isclose(c["bias_mw"], app_res["bias_mw"], abs_tol=0.01)
    assert math.isclose(c["mean_actual_mw"], app_res["mean_actual_mw"], abs_tol=0.01)
    assert math.isclose(c["nmae_pct"], app_res["nmae_pct"], abs_tol=0.001)

    # Raw unrounded values must match to 1e-6
    raw_mae = float(paired["error_mw"].abs().mean())
    raw_rmse = float(math.sqrt((paired["error_mw"] ** 2).mean()))
    raw_bias = float(paired["error_mw"].mean())

    assert abs(c["mae_mw"] - raw_mae) < 1e-6
    assert abs(c["rmse_mw"] - raw_rmse) < 1e-6
    assert abs(c["bias_mw"] - raw_bias) < 1e-6
