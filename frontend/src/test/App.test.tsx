import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import App from "../App";

function renderApp(initialPath = "/decision") {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter
        initialEntries={[initialPath]}
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("App routing", () => {
  it("renders header branding and navigation on /decision", () => {
    renderApp("/decision");
    expect(screen.getByText("Vane")).toBeInTheDocument();
    expect(screen.getByText("Decision")).toBeInTheDocument();
    expect(screen.getByText("Accuracy")).toBeInTheDocument();
    expect(screen.getByText(/Method & Assumptions/i)).toBeInTheDocument();
  });

  it("renders method page on /method", () => {
    renderApp("/method");
    expect(screen.getByText(/Methodology, Assumptions & Data Provenance/i)).toBeInTheDocument();
  });
});

