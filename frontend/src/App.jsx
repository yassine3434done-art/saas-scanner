import { NavLink, Route, Routes, useNavigate } from "react-router-dom";
import Home from "./pages/Home.jsx";
import Sites from "./pages/Sites.jsx";
import Scans from "./pages/Scans.jsx";
import ScanDetails from "./pages/ScanDetails.jsx";
import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";
import { clearToken, getToken } from "./lib/api.js";
import { useMemo, useState } from "react";

export default function App() {
  const nav = useNavigate();
  const [tick, setTick] = useState(0); // باش يرفريش UI من بعد login/logout
  const isAuthed = useMemo(() => !!getToken(), [tick]);

  function onLogout() {
    clearToken();
    setTick((x) => x + 1);
    nav("/login");
  }

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

          <div style={{ marginLeft: "auto", display: "flex", gap: 10, alignItems: "center" }}>
            <div style={{ fontSize: 12, color: "#666" }}>
              API: {import.meta.env.VITE_API_BASE_URL || "(not set)"}
            </div>

            {isAuthed ? (
              <button onClick={onLogout} style={btnSm}>Logout</button>
            ) : (
              <>
                <NavLink to="/login" style={({ isActive }) => linkStyle(isActive)}>Login</NavLink>
                <NavLink to="/register" style={({ isActive }) => linkStyle(isActive)}>Register</NavLink>
              </>
            )}
          </div>
        </div>
      </header>

      <main style={{ maxWidth: 1000, margin: "0 auto", padding: 16 }}>
        <Routes>
          <Route path="/" element={<Home />} />

          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

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

const btnSm = {
  padding: "8px 10px",
  borderRadius: 10,
  border: "1px solid #ddd",
  background: "white",
  cursor: "pointer",
};