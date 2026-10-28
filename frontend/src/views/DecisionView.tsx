import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { fetchForecastDay, fetchForecastRevisions, fetchRiskBand } from "../api/client";
import { useControlParams } from "../lib/useControlParams";
import {
  formatAgeHours,
  formatDate,
  formatDateTimeUTC,
  formatHour,
  formatMW,
  formatMWDecimal,
} from "../lib/formatters";

export const DecisionView: React.FC = () => {
  const [controls] = useControlParams();
  const [selectedTargetHour, setSelectedTargetHour] = useState<string | null>(null);

  // 1. Fetch 24-hour forecast at decision cutoff
  const {
    data: dayData,
    isLoading: dayLoading,
    error: dayError,
  } = useQuery({
    queryKey: ["forecastDay", controls.deliveryDate, controls.cutoffHour],
    queryFn: () => fetchForecastDay(controls.deliveryDate, controls.cutoffHour),
  });

  // 2. Fetch risk cushion band
  const {
    data: riskData,
    isLoading: riskLoading,
  } = useQuery({
    queryKey: ["riskBand", controls.deliveryDate, controls.cutoffHour, controls.confidence],
    queryFn: () => fetchRiskBand(controls.deliveryDate, controls.cutoffHour, controls.confidence),
  });

  // 3. Fetch vintage revisions for selected target hour (default to 12:00Z if none clicked)
  const activeTarget = selectedTargetHour || `${controls.deliveryDate}T12:00:00Z`;
  const {
    data: revData,
    isLoading: revLoading,
  } = useQuery({
    queryKey: ["revisions", activeTarget, controls.cutoffHour],
    queryFn: () =>
      fetchForecastRevisions({
        target: activeTarget,
        cutoffHour: controls.cutoffHour,
      }),
  });

  // 4. If cutoff !== 9, fetch 09:00 forecast to detect whether vintage changed
  const isCustomCutoff = controls.cutoffHour !== 9;
  const { data: defaultDayData } = useQuery({
    queryKey: ["forecastDay", controls.deliveryDate, 9],
    queryFn: () => fetchForecastDay(controls.deliveryDate, 9),
    enabled: isCustomCutoff,
  });

  if (dayLoading || riskLoading) {
    return (
      <div className="app-container">
        <div className="state-message">
          <h3>Loading day-ahead decision forecast...</h3>
          <p>Evaluating latest vintages published before {formatHour(controls.cutoffHour)} UTC cutoff.</p>
        </div>
      </div>
    );
  }

  if (dayError || !dayData) {
    return (
      <div className="app-container">
        <div className="state-message">
          <h3 style={{ color: "var(--color-risk)" }}>Unable to load decision forecast</h3>
          <p>{dayError instanceof Error ? dayError.message : "Unknown error occurred"}</p>
        </div>
      </div>
    );
  }

  // Merge day forecast rows with risk band hours
  const riskHourMap = new Map(riskData?.hours.map((h) => [h.hour, h]));

  const chartData = dayData.rows.map((row) => {
    const risk = riskHourMap.get(row.hour);
    return {
      hour: row.hour,
      hourLabel: formatHour(row.hour),
      startTime: row.start_time,
      forecast: row.forecast_mw,
      actual: row.actual_mw,
      error: row.error_mw,
      publishTime: row.publish_time,
      forecastAge: row.forecast_age_h,
      bandLo: risk ? risk.band_lo_mw : row.forecast_mw,
      bandHi: risk ? risk.band_hi_mw : row.forecast_mw,
      cushion: risk ? risk.cushion_mw : 0,
      biasUsed: risk ? risk.bias_used_mw : 0,
    };
  });

  // Average cushion for the day
  const avgCushion = riskData?.hours.length
    ? Math.round(riskData.hours.reduce((acc, h) => acc + h.cushion_mw, 0) / riskData.hours.length)
    : 0;

  return (
    <div className="app-container">
      {/* Notice & Context */}
      <div className="callout callout-info" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <strong>Decision Context:</strong> Delivery day <strong>{formatDate(dayData.delivery_date)}</strong>, evaluated at <strong>{formatHour(dayData.cutoff_hour)} UTC on D-1</strong>.
          Selected vintage published at <strong>{formatDateTimeUTC(dayData.selected_vintage_publish_time)}</strong>.
        </div>
        <span className="badge badge-wind">Hourly Pairing Rule (744h Jan Window)</span>
      </div>

      {isCustomCutoff && defaultDayData && defaultDayData.selected_vintage_publish_time === dayData.selected_vintage_publish_time && (
        <div
          className="callout"
          style={{
            marginBottom: "var(--space-4)",
            background: "#fff9eb",
            borderColor: "#f3cc80",
            color: "#7a4b00",
            fontSize: "0.875rem",
          }}
        >
          <strong>Same forecast as 09:00:</strong> latest vintage published before this cutoff is{" "}
          <strong>{formatDateTimeUTC(dayData.selected_vintage_publish_time)}</strong>. No newer National Grid forecast was published between that vintage and {formatHour(dayData.cutoff_hour)} UTC.
        </div>
      )}

      {/* KPI Cards */}
      <section className="kpi-row" aria-label="Day Summary KPIs">
        <div className="kpi-card">
          <div className="kpi-label">Peak Forecast</div>
          <div className="kpi-value">{formatMW(dayData.peak_forecast_mw)}</div>
          <div className="kpi-sub">Maximum day-ahead power</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">Mean Forecast</div>
          <div className="kpi-value">{formatMW(dayData.mean_forecast_mw)}</div>
          <div className="kpi-sub">Day-ahead hourly average</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">Mean Actual (Hindsight)</div>
          <div className="kpi-value" style={{ color: "var(--color-actual)" }}>
            {formatMW(dayData.mean_actual_mw)}
          </div>
          <div className="kpi-sub">Known only after delivery</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">Risk Cushion (Avg)</div>
          <div className="kpi-value" style={{ color: "var(--color-risk)" }}>
            {formatMW(avgCushion)}
          </div>
          <div className="kpi-sub">
            {riskData?.bias_used_mw
              ? `of which ${formatMW(riskData.bias_used_mw)} is systematic bias`
              : "Derived from prior days only"}
          </div>
        </div>
      </section>

      {/* Hero Decision Chart */}
      <section className="card" style={{ marginBottom: "var(--space-6)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", flexWrap: "wrap" }}>
          <div>
            <h2 className="card-title">24-Hour Wind Generation Decision Curve</h2>
            <div className="card-subtitle">
              Forecast at decision cutoff ({formatHour(dayData.cutoff_hour)} UTC), empirical {Math.round(controls.confidence * 100)}% risk band, and post-delivery actual outturn.
            </div>
          </div>
          <div style={{ fontSize: "var(--font-size-xs)", color: "var(--color-ink-muted)" }}>
            Hover for vintage publish time & error · Click hour to inspect revisions
          </div>
        </div>

        <div style={{ width: "100%", height: 420 }}>
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart
              data={chartData}
              onClick={(e) => {
                if (e && e.activePayload && e.activePayload.length > 0) {
                  const targetStart = e.activePayload[0].payload.startTime;
                  setSelectedTargetHour(targetStart);
                }
              }}
              margin={{ top: 20, right: 20, bottom: 20, left: 10 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#e4eaf0" vertical={false} />
              <XAxis dataKey="hourLabel" stroke="#536b82" tick={{ fontSize: 12 }} />
              <YAxis
                stroke="#536b82"
                tick={{ fontSize: 12 }}
                tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
                unit=" MW"
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const d = payload[0].payload;
                    return (
                      <div
                        style={{
                          background: "#ffffff",
                          border: "1px solid #d2dbe2",
                          borderRadius: "6px",
                          padding: "10px 14px",
                          boxShadow: "0 4px 12px rgba(18, 37, 58, 0.12)",
                          fontSize: "0.85rem",
                          lineHeight: 1.5,
                        }}
                      >
                        <div style={{ fontWeight: 700, marginBottom: "4px" }}>
                          Delivery Hour {d.hourLabel} UTC
                        </div>
                        <div style={{ color: "var(--color-wind)" }}>
                          <strong>Forecast at cutoff:</strong> {formatMW(d.forecast)}
                        </div>
                        <div style={{ color: "var(--color-actual)" }}>
                          <strong>Actual outturn:</strong> {formatMW(d.actual)}{" "}
                          <span style={{ fontSize: "0.75rem", fontStyle: "italic" }}>(hindsight)</span>
                        </div>
                        {d.error !== null && (
                          <div style={{ color: d.error > 0 ? "var(--color-risk)" : "var(--color-ink)" }}>
                            <strong>Error (F − A):</strong> {formatMW(d.error, true)}
                          </div>
                        )}
                        <div style={{ color: "var(--color-ink-muted)", fontSize: "0.75rem", marginTop: "6px" }}>
                          Vintage published: {formatDateTimeUTC(d.publishTime)}
                        </div>
                        <div style={{ color: "var(--color-ink-muted)", fontSize: "0.75rem" }}>
                          Forecast age at decision: {formatAgeHours(d.forecastAge)}
                        </div>
                        <div style={{ color: "var(--color-risk)", fontSize: "0.75rem", marginTop: "4px" }}>
                          Empirical cushion: {formatMW(d.cushion)} (bias used: {formatMW(d.biasUsed)})
                        </div>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Legend
                verticalAlign="top"
                align="right"
                wrapperStyle={{ paddingBottom: "12px", fontSize: "0.85rem" }}
              />

              {/* Risk Band: Area between bandLo and bandHi */}
              <Area
                type="monotone"
                dataKey="bandHi"
                name={`Risk Band (${Math.round(controls.confidence * 100)}% empirical)`}
                stroke="transparent"
                fill="var(--color-band)"
                isAnimationActive={false}
              />
              <Area
                type="monotone"
                dataKey="bandLo"
                name="Band Floor"
                legendType="none"
                stroke="transparent"
                fill="#ffffff"
                isAnimationActive={false}
              />

              {/* Forecast at cutoff */}
              <Line
                type="monotone"
                dataKey="forecast"
                name="Forecast at cutoff"
                stroke="var(--color-wind)"
                strokeWidth={2.5}
                dot={{ r: 3, fill: "var(--color-wind)" }}
                activeDot={{ r: 6 }}
              />

              {/* Actuals overlay */}
              <Line
                type="monotone"
                dataKey="actual"
                name="Actual outturn (Known only after delivery)"
                stroke="var(--color-actual)"
                strokeWidth={2}
                strokeDasharray="4 4"
                dot={{ r: 2.5, fill: "var(--color-actual)" }}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </section>

      {/* Revision Drawer / Section */}
      <section className="card" style={{ marginBottom: "var(--space-6)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", flexWrap: "wrap", marginBottom: "var(--space-2)" }}>
          <h3 className="card-title">Forecast Revision Progression</h3>
          <span className="badge badge-muted">
            Target Delivery Hour: {formatDateTimeUTC(activeTarget)}
          </span>
        </div>
        <p className="card-subtitle">
          Shows how National Grid ESO updated the forecast for this delivery hour across successive vintages, from 60+ hours out through delivery.
        </p>

        {revLoading ? (
          <p style={{ color: "var(--color-ink-muted)", fontSize: "0.875rem" }}>Loading vintage revisions...</p>
        ) : revData && revData.vintages.length > 0 ? (
          <div>
            <div style={{ width: "100%", height: 260, marginBottom: "var(--space-4)" }}>
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={revData.vintages} margin={{ top: 10, right: 20, bottom: 20, left: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e4eaf0" vertical={false} />
                  <XAxis
                    dataKey="publish_time"
                    tickFormatter={(v) => formatDateTimeUTC(v).replace(" UTC", "")}
                    stroke="#536b82"
                    tick={{ fontSize: 11 }}
                  />
                  <YAxis stroke="#536b82" tick={{ fontSize: 11 }} unit=" MW" />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (active && payload && payload.length) {
                        const v = payload[0].payload;
                        return (
                          <div style={{ background: "#fff", border: "1px solid #d2dbe2", padding: "8px 12px", borderRadius: "4px", fontSize: "0.8rem" }}>
                            <div><strong>Published:</strong> {formatDateTimeUTC(v.publish_time)}</div>
                            <div style={{ color: "var(--color-wind)" }}><strong>Forecast:</strong> {formatMW(v.forecast_mw)}</div>
                            <div><strong>Lead Time:</strong> {v.horizon_h.toFixed(1)}h</div>
                            <div><strong>Eligible at cutoff:</strong> {v.is_before_cutoff ? "Yes (D-1 09:00)" : "No (Post-cutoff update)"}</div>
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                  <Line
                    type="stepAfter"
                    dataKey="forecast_mw"
                    name="Vintage Forecast"
                    stroke="var(--color-wind)"
                    strokeWidth={2}
                    dot={{ r: 3 }}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>

            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Publish Time (UTC)</th>
                    <th>Forecast MW</th>
                    <th>Lead Time</th>
                    <th>Decision Status</th>
                  </tr>
                </thead>
                <tbody>
                  {revData.vintages.map((v, i) => (
                    <tr key={i}>
                      <td>{formatDateTimeUTC(v.publish_time)}</td>
                      <td>{formatMWDecimal(v.forecast_mw)}</td>
                      <td>{v.horizon_h.toFixed(1)}h ahead</td>
                      <td>
                        {v.is_before_cutoff ? (
                          <span className="badge badge-wind">Eligible (≤ Cutoff)</span>
                        ) : (
                          <span className="badge badge-muted">Post-Cutoff Revision</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <p style={{ color: "var(--color-ink-muted)", fontSize: "0.875rem" }}>No revisions found for this period.</p>
        )}
      </section>

      {/* 24-Period Detailed Table */}
      <section className="card">
        <h3 className="card-title">Hourly Breakdown (24 Target Periods)</h3>
        <p className="card-subtitle">
          Full audit of forecast at decision time, actual outturn, error, and empirical cushion for {formatDate(dayData.delivery_date)}.
        </p>

        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Hour (UTC)</th>
                <th>Forecast (MW)</th>
                <th>Vintage Publish Time</th>
                <th>Forecast Age</th>
                <th>Actual Mean (MW)*</th>
                <th>Error (F − A)</th>
                <th>Empirical Cushion</th>
              </tr>
            </thead>
            <tbody>
              {chartData.map((row) => (
                <tr
                  key={row.hour}
                  style={{ cursor: "pointer", background: selectedTargetHour === row.startTime ? "var(--color-wind-light)" : undefined }}
                  onClick={() => setSelectedTargetHour(row.startTime)}
                  title="Click to view forecast revisions for this delivery hour"
                >
                  <td style={{ fontWeight: 600 }}>{row.hourLabel}</td>
                  <td style={{ color: "var(--color-wind)", fontWeight: 600 }}>{formatMWDecimal(row.forecast)}</td>
                  <td>{formatDateTimeUTC(row.publishTime)}</td>
                  <td>{formatAgeHours(row.forecastAge)}</td>
                  <td style={{ color: "var(--color-actual)" }}>{formatMWDecimal(row.actual)}</td>
                  <td style={{ color: (row.error ?? 0) > 0 ? "var(--color-risk)" : "var(--color-ink)", fontWeight: 600 }}>
                    {formatMW(row.error, true)}
                  </td>
                  <td>{formatMW(row.cushion)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div style={{ marginTop: "var(--space-3)", fontSize: "var(--font-size-xs)", color: "var(--color-ink-faint)" }}>
          * Actuals are hindsight: arithmetic mean of FUELHH :00 and :30 generation periods per the hourly pairing rule.
        </div>
      </section>
    </div>
  );
};
