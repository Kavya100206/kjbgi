import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router-dom";
import { ControlStrip } from "../components/ControlStrip";

function LocationDisplay() {
  const location = useLocation();
  return <div data-testid="location-search">{location.search}</div>;
}

describe("ControlStrip", () => {
  it("renders with default values and allows changing delivery date", () => {
    render(
      <MemoryRouter initialEntries={["/decision?date=2026-01-15&cutoff=9"]}>
        <ControlStrip />
        <LocationDisplay />
      </MemoryRouter>
    );

    const select = screen.getByLabelText(/Delivery Day/i) as HTMLSelectElement;
    expect(select.value).toBe("2026-01-15");

    fireEvent.change(select, { target: { value: "2026-01-20" } });
    expect(screen.getByTestId("location-search").textContent).toContain("date=2026-01-20");
  });

  it("allows changing decision cutoff hour", () => {
    render(
      <MemoryRouter initialEntries={["/decision?date=2026-01-15&cutoff=9"]}>
        <ControlStrip />
        <LocationDisplay />
      </MemoryRouter>
    );

    const cutoffSelect = screen.getByLabelText(/Decision Cutoff/i) as HTMLSelectElement;
    expect(cutoffSelect.value).toBe("9");

    fireEvent.change(cutoffSelect, { target: { value: "11" } });
    expect(screen.getByTestId("location-search").textContent).toContain("cutoff=11");
  });
});
