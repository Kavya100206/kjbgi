import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import App from "../App";

function renderApp(initialPath = "/decision") {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[initialPath]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("App routing", () => {
  it("renders decision placeholder on /decision", () => {
    renderApp("/decision");
    expect(screen.getByTestId("decision-placeholder")).toBeInTheDocument();
  });

  it("redirects / to /decision", () => {
    renderApp("/");
    expect(screen.getByTestId("decision-placeholder")).toBeInTheDocument();
  });

  it("renders accuracy placeholder on /accuracy", () => {
    renderApp("/accuracy");
    expect(screen.getByTestId("accuracy-placeholder")).toBeInTheDocument();
  });
});
