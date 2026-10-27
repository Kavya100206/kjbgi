import React from "react";
import { useControlParams } from "../lib/useControlParams";

export const ControlStrip: React.FC = () => {
  const [controls, updateControls] = useControlParams();

  // 31 January 2026 dates
  const dates = Array.from({ length: 31 }, (_, i) => {
    const d = (i + 1).toString().padStart(2, "0");
    return `2026-01-${d}`;
  });

  return (
    <section className="control-strip" aria-label="Portal controls">
      <div className="app-container control-strip-inner">
        <div className="control-group">
          <label htmlFor="delivery-date-select" className="control-label">
            Delivery Day
          </label>
          <select
            id="delivery-date-select"
            className="control-input"
            value={controls.deliveryDate}
            onChange={(e) => updateControls({ deliveryDate: e.target.value })}
          >
            {dates.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </div>

        <div className="control-group">
          <label htmlFor="cutoff-hour-select" className="control-label">
            Decision Cutoff (D-1)
          </label>
          <select
            id="cutoff-hour-select"
            className="control-input"
            value={controls.cutoffHour}
            onChange={(e) => updateControls({ cutoffHour: parseInt(e.target.value, 10) })}
          >
            {Array.from({ length: 24 }, (_, i) => (
              <option key={i} value={i}>
                {i.toString().padStart(2, "0")}:00 UTC
              </option>
            ))}
          </select>
        </div>

        <div className="control-group">
          <label htmlFor="range-from-select" className="control-label">
            Evaluation Window
          </label>
          <div style={{ display: "flex", gap: "0.25rem", alignItems: "center" }}>
            <select
              id="range-from-select"
              className="control-input"
              value={controls.fromDate}
              onChange={(e) => updateControls({ fromDate: e.target.value })}
              aria-label="Evaluation window start date"
            >
              {dates.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
            <span style={{ color: "var(--color-ink-muted)", fontSize: "0.75rem" }}>to</span>
            <select
              id="range-to-select"
              className="control-input"
              value={controls.toDate}
              onChange={(e) => updateControls({ toDate: e.target.value })}
              aria-label="Evaluation window end date"
            >
              {dates.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="control-group">
          <label htmlFor="confidence-select" className="control-label">
            Risk Confidence
          </label>
          <select
            id="confidence-select"
            className="control-input"
            value={controls.confidence}
            onChange={(e) => updateControls({ confidence: parseFloat(e.target.value) })}
          >
            <option value={0.8}>80% (P10–P90)</option>
            <option value={0.9}>90% (P05–P95)</option>
            <option value={0.95}>95% (P2.5–P97.5)</option>
          </select>
        </div>
      </div>
    </section>
  );
};
