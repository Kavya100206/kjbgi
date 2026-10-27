import React from "react";
import { Link, useLocation } from "react-router-dom";

export const Header: React.FC = () => {
  const location = useLocation();
  const currentPath = location.pathname;

  const search = location.search;

  return (
    <header className="site-header" role="banner">
      <div className="app-container header-inner">
        <div className="brand-block">
          <Link to={`/${search}`} style={{ textDecoration: "none", color: "inherit" }}>
            <span className="brand-title">Vane</span>
          </Link>
          <span className="brand-subtitle">UK Wind Decision Portal · Elexon BMRS</span>
        </div>

        <nav className="nav-tabs" aria-label="Main navigation">
          <Link
            to={`/${search}`}
            className={`nav-tab ${currentPath === "/" || currentPath === "/decision" ? "active" : ""}`}
            aria-current={currentPath === "/" || currentPath === "/decision" ? "page" : undefined}
          >
            Decision
          </Link>
          <Link
            to={`/accuracy${search}`}
            className={`nav-tab ${currentPath === "/accuracy" ? "active" : ""}`}
            aria-current={currentPath === "/accuracy" ? "page" : undefined}
          >
            Accuracy
          </Link>
          <Link
            to={`/method${search}`}
            className={`nav-tab ${currentPath === "/method" ? "active" : ""}`}
            aria-current={currentPath === "/method" ? "page" : undefined}
          >
            Method & Assumptions
          </Link>
        </nav>
      </div>
    </header>
  );
};
