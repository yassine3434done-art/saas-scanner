// frontend/src/pages/Register.jsx
import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { apiPost, setToken } from "../lib/api.js";

export default function Register() {
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  async function onSubmit(e) {
    e.preventDefault();
    setErr("");
    setLoading(true);
    try {
      const res = await apiPost("/auth/register", { email, password });
      const token = res?.access_token;
      if (!token) throw new Error("No access_token returned from API");
      setToken(token);
      nav("/sites");
    } catch (e2) {
      setErr(String(e2?.message || e2));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={card}>
      <h2 style={{ marginTop: 0 }}>Register</h2>

      <form onSubmit={onSubmit} style={{ display: "grid", gap: 10 }}>
        <input style={input} value={email} onChange={(e) => setEmail(e.target.value)} placeholder="email" />
        <input style={input} value={password} onChange={(e) => setPassword(e.target.value)} placeholder="password" type="password" />
        <button style={btn} disabled={loading}>{loading ? "Loading..." : "Create account"}</button>
      </form>

      {err && <div style={errorBox}>{err}</div>}

      <p style={{ fontSize: 12, color: "#666" }}>
        عندك حساب؟ <Link to="/login">Login</Link>
      </p>
    </div>
  );
}

const card = { background: "white", border: "1px solid #eee", borderRadius: 16, padding: 16, maxWidth: 420 };
const input = { padding: 10, borderRadius: 10, border: "1px solid #ddd" };
const btn = { padding: "10px 14px", borderRadius: 10, border: "1px solid #111", background: "#111", color: "white" };
const errorBox = { marginTop: 12, padding: 12, background: "#ffe8e8", border: "1px solid #ffb3b3", borderRadius: 12 };