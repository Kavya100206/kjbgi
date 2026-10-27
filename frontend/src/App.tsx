import { Navigate, Route, Routes } from "react-router-dom";

import { ControlStrip } from "./components/ControlStrip";
import { Header } from "./components/Header";
import { AccuracyView } from "./views/AccuracyView";
import { DecisionView } from "./views/DecisionView";
import { MethodView } from "./views/MethodView";

export default function App() {
  return (
    <>
      <Header />
      <ControlStrip />
      <main className="main-content" role="main">
        <Routes>
          <Route path="/" element={<DecisionView />} />
          <Route path="/decision" element={<DecisionView />} />
          <Route path="/accuracy" element={<AccuracyView />} />
          <Route path="/method" element={<MethodView />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </>
  );
}
