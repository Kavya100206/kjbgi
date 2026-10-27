import { describe, it, expect } from "vitest";
import {
  formatMW,
  formatMWDecimal,
  formatPct,
  formatRatio,
  formatHour,
  formatHourUTC,
  formatDate,
  formatDateTimeUTC,
  formatAgeHours,
} from "../lib/formatters";

describe("formatters", () => {
  it("formats power in MW with rounding and sign handling", () => {
    expect(formatMW(1852.4)).toBe("1,852 MW");
    expect(formatMW(1852.4, true)).toBe("+1,852 MW");
    expect(formatMW(-500.2, true)).toBe("-500 MW");
    expect(formatMW(0, true)).toBe("0 MW");
    expect(formatMW(null)).toBe("—");
    expect(formatMW(undefined)).toBe("—");
  });

  it("formats decimal MW", () => {
    expect(formatMWDecimal(1234.56, 1)).toBe("1,234.6 MW");
    expect(formatMWDecimal(null)).toBe("—");
  });

  it("formats percentages", () => {
    expect(formatPct(15.99)).toBe("16.0%");
    expect(formatPct(15.99, 2)).toBe("15.99%");
    expect(formatPct(null)).toBe("—");
  });

  it("formats ratios", () => {
    expect(formatRatio(1.1599)).toBe("1.16×");
    expect(formatRatio(null)).toBe("—");
  });

  it("formats hours and UTC hours", () => {
    expect(formatHour(9)).toBe("09:00");
    expect(formatHourUTC(9)).toBe("09:00 UTC");
  });

  it("formats dates and timestamps in UTC", () => {
    expect(formatDate("2026-01-15")).toBe("15 Jan 2026");
    expect(formatDateTimeUTC("2026-01-15T12:00:00Z")).toBe("15 Jan 12:00 UTC");
    expect(formatDateTimeUTC("")).toBe("—");
  });

  it("formats forecast vintage age in hours", () => {
    expect(formatAgeHours(3.5)).toBe("3.5h");
    expect(formatAgeHours(null)).toBe("—");
  });
});
