import { NavLink } from "react-router-dom";

export default function NavBar() {
  const apiBase = import.meta.env.VITE_API_BASE_URL || "";

  return (
    <header style={{ background: "white", borderBottom: "1px solid #eee" }}>
      <div
        style={{
          maxWidth: 1000,
          margin: "0 auto",
          padding: 16,
          display: "flex",
          gap: 16,
          alignItems: "center",
        }}
      >
        <div style={{ fontWeight: 800 }}>SaaS Scanner</div>

        <nav style={{ display: "flex", gap: 12 }}>
          <NavLink to="/" style={({ isActive }) => linkStyle(isActive)}>
            Home
          </NavLink>
          <NavLink to="/sites" style={({ isActive }) => linkStyle(isActive)}>
            Sites
          </NavLink>
          <NavLink to="/scans" style={({ isActive }) => linkStyle(isActive)}>
            Scans
          </NavLink>
        </nav>

        <div style={{ marginLeft: "auto", fontSize: 12, color: "#666" }}>
          API:{" "}
          {apiBase ? (
            <a
              href={apiBase}
              target="_blank"
              rel="noreferrer"
              style={{ color: "#666", textDecoration: "underline" }}
            >
              {apiBase}
            </a>
          ) : (
            "(not set)"
          )}
        </div>
      </div>
    </header>
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