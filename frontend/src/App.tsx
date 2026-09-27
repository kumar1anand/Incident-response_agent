import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import { useEffect, useState } from "react";
import { api, type Health } from "./api";
import Investigate from "./screens/Investigate";
import Memory from "./screens/Memory";
import Learning from "./screens/Learning";
import History from "./screens/History";

const NAV = [
  { to: "/investigate", label: "Investigate", icon: "🚨" },
  { to: "/memory", label: "Memory", icon: "🧠" },
  { to: "/learning", label: "Learning", icon: "📈" },
  { to: "/history", label: "History", icon: "📋" },
];

export default function App() {
  const [health, setHealth] = useState<Health | null>(null);

  useEffect(() => {
    api
      .health()
      .then(setHealth)
      .catch(() => setHealth({ status: "offline", hindsight: false, bank_id: "" }));
  }, []);

  const healthy = health?.status === "healthy";

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-logo">🚨</span>
          <span className="brand-name">IncidentIQ</span>
          <span className="brand-sub">Incident Command Center</span>
        </div>
        <div className={`status-pill ${healthy ? "ok" : "bad"}`}>
          <span className="dot" />
          {health
            ? healthy
              ? "Production: Healthy"
              : `System: ${health.status}`
            : "Connecting…"}
        </div>
      </header>

      <nav className="sidebar">
        {NAV.map((n) => (
          <NavLink
            key={n.to}
            to={n.to}
            className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}
          >
            <span className="nav-icon">{n.icon}</span>
            <span>{n.label}</span>
          </NavLink>
        ))}
        <div className="sidebar-foot">
          {health?.bank_id && (
            <span>
              bank: <code>{health.bank_id}</code>
            </span>
          )}
        </div>
      </nav>

      <main className="content">
        <Routes>
          <Route path="/" element={<Navigate to="/investigate" replace />} />
          <Route path="/investigate" element={<Investigate />} />
          <Route path="/memory" element={<Memory />} />
          <Route path="/learning" element={<Learning />} />
          <Route path="/history" element={<History />} />
        </Routes>
      </main>
    </div>
  );
}
