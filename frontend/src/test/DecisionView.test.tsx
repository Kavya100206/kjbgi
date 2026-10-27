import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { DecisionView } from "../views/DecisionView";
import * as client from "../api/client";

vi.mock("../api/client", () => ({
  fetchForecastDay: vi.fn(),
  fetchForecastRevisions: vi.fn(),
  fetchRiskBand: vi.fn(),
}));

describe("DecisionView with mocked API", () => {
  it("renders forecast points and risk cushion", async () => {
    vi.mocked(client.fetchForecastDay).mockResolvedValue({
      delivery_date: "2026-01-15",
      cutoff_hour: 9,
      selected_vintage_publish_time: "2026-01-14T08:35:00Z",
      peak_forecast_mw: 9500.0,
      mean_forecast_mw: 9500.0,
      min_forecast_mw: 9500.0,
      mean_actual_mw: 8200.0,
      n_missing: 0,
      rows: [
        {
          start_time: "2026-01-15T00:00:00Z",
          hour: 0,
          forecast_mw: 9500.0,
          publish_time: "2026-01-14T08:35:00Z",
          forecast_age_h: 0.4,
          actual_mw: 8200.0,
          error_mw: 1300.0,
        },
      ],
    });

    vi.mocked(client.fetchForecastRevisions).mockResolvedValue({
      target_start_time: "2026-01-15T12:00:00Z",
      delivery_date: "2026-01-15",
      cutoff_hour: 9,
      actual_mw: 8200.0,
      vintages: [],
    });

    vi.mocked(client.fetchRiskBand).mockResolvedValue({
      delivery_date: "2026-01-15",
      cutoff_hour: 9,
      confidence: 0.8,
      history_days_used: 14,
      is_fallback: false,
      bias_used_mw: 1852.4,
      hours: [
        {
          start_time: "2026-01-15T00:00:00Z",
          hour: 0,
          forecast_mw: 9500.0,
          band_lo_mw: 8000.0,
          band_hi_mw: 11000.0,
          cushion_mw: 1500.0,
          bias_used_mw: 1852.4,
        },
      ],
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={["/decision?date=2026-01-15&cutoff=9"]}>
          <DecisionView />
        </MemoryRouter>
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/Decision Context:/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/Known only after delivery/i)).toBeInTheDocument();
    expect(screen.getAllByText("9,500 MW").length).toBeGreaterThan(0);
    expect(screen.getAllByText("1,500 MW").length).toBeGreaterThan(0);
  });
});
