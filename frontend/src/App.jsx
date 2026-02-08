import { NavLink, Route, Routes } from "react-router-dom";
import Home from "./pages/Home.jsx";
import Sites from "./pages/Sites.jsx";
import Scans from "./pages/Scans.jsx";
import ScanDetails from "./pages/ScanDetails.jsx";

export default function App() {
  return (
    <div style={{ fontFamily: "Arial, sans-serif", minHeight: "100vh", background: "#fafafa" }}>
      <header style={{ background: "white", borderBottom: "1px solid #eee" }}>
        <div style={{ maxWidth: 1000, margin: "0 auto", padding: 16, display: "flex", gap: 16, alignItems: "center" }}>
          <div style={{ fontWeight: 800 }}>SaaS Scanner</div>

          <nav style={{ display: "flex", gap: 12 }}>
            <NavLink to="/" style={({ isActive }) => linkStyle(isActive)}>Home</NavLink>
            <NavLink to="/sites" style={({ isActive }) => linkStyle(isActive)}>Sites</NavLink>
            <NavLink to="/scans" style={({ isActive }) => linkStyle(isActive)}>Scans</NavLink>
          </nav>

          <div style={{ marginLeft: "auto", fontSize: 12, color: "#666" }}>
            API: {import.meta.env.VITE_API_BASE_URL || "(not set)"}
          </div>
        </div>
      </header>

      <main style={{ maxWidth: 1000, margin: "0 auto", padding: 16 }}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/sites" element={<Sites />} />
          <Route path="/scans" element={<Scans />} />
          <Route path="/scans/:id" element={<ScanDetails />} />
        </Routes>
      </main>
    </div>
  );
}

function linkStyle(active) {
  return {
    padding: "6px 10px",
    borderRadius: 8,
    textDecoration: "none",
    color: active ? "white" : "#333",
    background: active ? "#111" : "transparent",
  };
}