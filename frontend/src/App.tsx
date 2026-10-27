import { Routes, Route, Navigate } from "react-router-dom";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/decision" replace />} />
      <Route
        path="/decision"
        element={<div data-testid="decision-placeholder">Decision view — coming in T4.2</div>}
      />
      <Route
        path="/accuracy"
        element={<div data-testid="accuracy-placeholder">Accuracy view — coming in T4.4</div>}
      />
      <Route
        path="/method"
        element={<div data-testid="method-placeholder">Method view — coming in T4.5</div>}
      />
    </Routes>
  );
}
