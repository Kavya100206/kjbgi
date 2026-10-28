import React from "react";
import { useQuery } from "@tanstack/react-query";

import { fetchMeta } from "../api/client";
import { formatDateTimeUTC } from "../lib/formatters";

export const MethodView: React.FC = () => {
  const { data: meta } = useQuery({
    queryKey: ["meta"],
    queryFn: fetchMeta,
  });

  return (
    <div className="app-container" style={{ maxWidth: 960 }}>
      <div style={{ marginBottom: "var(--space-6)" }}>
        <h1 className="brand-title" style={{ fontSize: "2.2rem", marginBottom: "var(--space-2)" }}>
          Methodology, Assumptions & Data Provenance
        </h1>
        <p style={{ color: "var(--color-ink-muted)", fontSize: "1.05rem" }}>
          Full documentation of analytical conventions, mathematical formulations, operational constraints, and empirical diagnostic findings.
        </p>
      </div>

      {/* Snapshot Provenance Card */}
      <section className="card" style={{ marginBottom: "var(--space-6)" }}>
        <h2 className="card-title">Data Snapshot & Provenance</h2>
        <p className="card-subtitle">
          To eliminate rate-limiting and external API outage risks during operational review, Vane serves a verified, committed snapshot of Elexon BMRS data.
        </p>

        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Dataset</th>
                <th>BMRS Feed</th>
                <th>Resolution</th>
                <th>Snapshot Rows</th>
                <th>Filtering & Scope</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><strong>Wind Actuals</strong></td>
                <td><code>FUELHH</code></td>
                <td>30-minute settlement period</td>
                <td>{meta?.actuals_rows ? meta.actuals_rows.toLocaleString() : "1,536"} rows</td>
                <td><code>fuelType == "WIND"</code>, 2026-01-01 to 2026-02-01</td>
              </tr>
              <tr>
                <td><strong>Wind Forecasts</strong></td>
                <td><code>WINDFOR</code></td>
                <td>Hourly target delivery</td>
                <td>{meta?.forecasts_rows ? meta.forecasts_rows.toLocaleString() : "19,856"} rows</td>
                <td>272 unique vintages, published 2025-12-29 to 2026-01-31</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div style={{ marginTop: "var(--space-3)", fontSize: "0.8rem", color: "var(--color-ink-muted)" }}>
          Snapshot Ingested: <strong>{meta?.ingested_at ? formatDateTimeUTC(meta.ingested_at) : "2026-10-27T09:08:24Z"}</strong> · Compressed Payload: <strong>{meta?.total_compressed_size_kb ? meta.total_compressed_size_kb.toFixed(1) : "113.7"} KB</strong>
        </div>
      </section>

      {/* Bias Diagnostics Finding */}
      <section className="card" style={{ marginBottom: "var(--space-6)", borderColor: "var(--color-actual)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", flexWrap: "wrap" }}>
          <h2 className="card-title" style={{ color: "var(--color-ink)" }}>
            January 2026 Systematic Bias Finding (+1,852 MW)
          </h2>
          <span className="badge badge-risk">Empirical Diagnostic</span>
        </div>
        <p className="card-subtitle">
          Empirical diagnostics confirmed that day-ahead WINDFOR forecasts at the 09:00 UTC cutoff ran systematically <strong>+1,851.90 MW (~16.0%) above</strong> actual generation across January 2026.
        </p>

        <div className="callout callout-warning">
          <strong>Key Empirical Facts:</strong>
          <ul style={{ paddingLeft: "1.25rem", marginTop: "0.5rem" }}>
            <li><strong>Consistency:</strong> Over-forecast occurred on <strong>27 of 31 days (87.1%)</strong> and across all 24 hours of the day (ranging from +1,365 MW to +2,463 MW).</li>
            <li><strong>Scale:</strong> Mean forecast was 13,433 MW vs mean actual 11,581 MW. Regression yields <code>actual = 0.7951 × forecast + 900.28 MW</code> (R² = 0.8604).</li>
            <li><strong>Error Variance Breakdown:</strong> Systematic bias accounts for <strong>50.3% of Mean Squared Error</strong> (<code>Bias² / MSE</code>), with the remaining 49.7% being random weather variance.</li>
            <li><strong>Meteorological Skill:</strong> Despite the offset, the forecast captures weather swings with <strong>r = 0.9255</strong> correlation, achieving a <strong>51.3% lower MAE</strong> than honest 48h persistence.</li>
          </ul>
        </div>

        <div style={{ marginTop: "var(--space-4)" }}>
          <h3 style={{ fontSize: "1rem", fontWeight: 700, marginBottom: "0.5rem" }}>
            Plausible Hypothesis: Fleet Scope Discrepancy (Unverified)
          </h3>
          <p style={{ fontSize: "0.875rem", lineHeight: 1.6, color: "var(--color-ink)" }}>
            A plausible industry cause is that National Grid ESO’s <strong>WINDFOR</strong> model forecasts total Great Britain wind generation (including distribution-connected embedded wind farms), whereas Elexon BMRS <strong>FUELHH</strong> records metered generation from Transmission-System connected Balancing Mechanism Units (BMUs) only. Another possible contributor is commercial wind curtailment.
          </p>
          <p style={{ fontSize: "0.875rem", lineHeight: 1.6, color: "var(--color-ink)", marginTop: "0.5rem" }}>
            <strong>Portal Policy:</strong> Because Elexon BMRS does not supply embedded wind metering or dispatch bid-offer acceptances, <em>any physical fleet attribution remains an unverified hypothesis</em>. <strong>Vane does NOT apply artificial bias adjustments or synthetic scaling to the data.</strong> Instead, we report empirical bias and error standard deviation transparently so trading desks can price in the cushion cleanly.
          </p>
        </div>
      </section>

      {/* Assumptions A1–A7 */}
      <section className="card" style={{ marginBottom: "var(--space-6)" }}>
        <h2 className="card-title">Core Modelling Assumptions (A1–A7)</h2>
        <p className="card-subtitle">
          Every assumption is explicit, configurable, and transparent to the trading desk.
        </p>

        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
          <div style={{ borderLeft: "3px solid var(--color-wind)", paddingLeft: "var(--space-3)" }}>
            <h3 style={{ fontSize: "0.95rem", fontWeight: 700 }}>A1. Delivery Window</h3>
            <p style={{ fontSize: "0.85rem", color: "var(--color-ink-muted)" }}>
              Target periods with <code>startTime</code> in 2026-01-01 00:00Z to 2026-01-31 23:00Z (744 hourly periods). Snapshot includes forecasts published from 2025-12-29 to ensure full day-ahead coverage for January 1.
            </p>
          </div>

          <div style={{ borderLeft: "3px solid var(--color-wind)", paddingLeft: "var(--space-3)" }}>
            <h3 style={{ fontSize: "0.95rem", fontWeight: 700 }}>A2. Decision Cutoff & Vintage Selection</h3>
            <p style={{ fontSize: "0.85rem", color: "var(--color-ink-muted)" }}>
              The buyer decides on day D-1 at a user-selectable cutoff hour (default <strong>09:00 UTC</strong>). For target delivery hour <code>t</code> on day D, the decision forecast is the latest vintage with <code>publishTime &le; (D-1 at cutoff_hour:00 UTC)</code>. Look-ahead is prevented by construction and covered by tests.
            </p>
          </div>

          <div style={{ borderLeft: "3px solid var(--color-risk)", paddingLeft: "var(--space-3)" }}>
            <h3 style={{ fontSize: "0.95rem", fontWeight: 700 }}>A3. Error Sign Convention</h3>
            <p style={{ fontSize: "0.85rem", color: "var(--color-ink-muted)" }}>
              <code>error = forecast &minus; actual</code>. A positive error indicates an <strong>over-forecast</strong> (the forecast predicted more power than materialized), representing shortfall risk where the utility under-procures.
            </p>
          </div>

          <div style={{ borderLeft: "3px solid var(--color-wind)", paddingLeft: "var(--space-3)" }}>
            <h3 style={{ fontSize: "0.95rem", fontWeight: 700 }}>A4. Missing Data & Coverage</h3>
            <p style={{ fontSize: "0.85rem", color: "var(--color-ink-muted)" }}>
              If no vintage exists prior to cutoff or an actual half-hour is missing, that target hour is excluded from metrics and reflected in coverage (<code>n / 744</code>). No synthetic forward-fill.
            </p>
          </div>

          <div style={{ borderLeft: "3px solid var(--color-wind)", paddingLeft: "var(--space-3)" }}>
            <h3 style={{ fontSize: "0.95rem", fontWeight: 700 }}>A5. No Demand Data</h3>
            <p style={{ fontSize: "0.85rem", color: "var(--color-ink-muted)" }}>
              We do not fabricate consumer demand or pricing. We quantify national wind volumetric uncertainty (MW) which buyers apply to their proprietary demand books.
            </p>
          </div>

          <div style={{ borderLeft: "3px solid var(--color-wind)", paddingLeft: "var(--space-3)" }}>
            <h3 style={{ fontSize: "0.95rem", fontWeight: 700 }}>A6. Exact Deduplication</h3>
            <p style={{ fontSize: "0.85rem", color: "var(--color-ink-muted)" }}>
              FUELHH carries observed <code>publishTime</code>; exact duplicates per <code>(startTime, fuelType)</code> are dropped. WINDFOR preserves all distinct vintages.
            </p>
          </div>

          <div style={{ borderLeft: "3px solid var(--color-actual)", paddingLeft: "var(--space-3)" }}>
            <h3 style={{ fontSize: "0.95rem", fontWeight: 700 }}>A7. Hourly Actual Pairing Rule & Sensitivity Analysis</h3>
            <p style={{ fontSize: "0.85rem", color: "var(--color-ink-muted)" }}>
              WINDFOR is published at hourly resolution; FUELHH is reported half-hourly (:00 and :30). Under Assumption A7, <code>actual_hourly(H) = mean(FUELHH[H:00], FUELHH[H:30])</code>. Both half-hours must exist.
            </p>
            <p style={{ fontSize: "0.85rem", color: "var(--color-ink-muted)", marginTop: "4px" }}>
              <strong>Sensitivity Check (Option A vs Option C):</strong> In sensitivity analysis, comparing Option C (mean of H:00 and H:30) against Option A (H:00 only) across all 744 January hours showed a MAE difference of only <strong>&minus;14.64 MW (&minus;0.68%)</strong> and bias difference of <strong>&minus;0.38 MW (&minus;0.02%)</strong>. The choice of pairing rule does not materially alter accuracy conclusions.
            </p>
          </div>
        </div>
      </section>

      {/* Operational Caveats */}
      <section className="card">
        <h2 className="card-title">Operational Caveats to Surface</h2>
        <ul style={{ paddingLeft: "1.25rem", fontSize: "0.875rem", lineHeight: 1.6, color: "var(--color-ink)" }}>
          <li>
            <strong>Actuals are Hindsight:</strong> On the Decision view, the actuals overlay is strictly post-delivery outturn. Actual generation was unknown at decision time.
          </li>
          <li>
            <strong>Lead-Time Confounding:</strong> For a fixed 09:00 UTC morning cutoff on D-1, forecast lead time naturally increases from ~16.5 hours for delivery hour 00 to ~39.5 hours for delivery hour 23. Variations by hour-of-day reflect both diurnal meteorological patterns and forecast horizon decay.
          </li>
          <li>
            <strong>Retrospective Backcasts:</strong> 20.6% of WINDFOR rows in Elexon's feed have <code>horizon &lt; 0</code> (published after delivery). These backcasts are filtered out of all forward horizon evaluations.
          </li>
          <li>
            <strong>Empirical Risk Bands:</strong> The risk buffer is computed strictly from delivery days prior to day D (<code>D_prior &lt; D</code>). When fewer than 3 days of history exist (e.g. Jan 1–2), a fallback indicator is displayed.
          </li>
        </ul>
      </section>
    </div>
  );
};
