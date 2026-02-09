import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { apiPostNoAuth, setToken } from "../lib/api.js";

export default function Register() {
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(e) {
    e.preventDefault();
    setErr("");
    setLoading(true);
    try {
      const res = await apiPostNoAuth("/auth/register", { email, password });
      if (!res?.access_token) throw new Error("No access_token returned");
      setToken(res.access_token);
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

      <form onSubmit={onSubmit} style={{ display: "grid", gap: 10, maxWidth: 420 }}>
        <input
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="email"
          type="email"
          required
          style={input}
        />
        <input
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="password (min 8)"
          type="password"
          required
          style={input}
        />

        {err && <div style={errorBox}>{err}</div>}

        <button disabled={loading} style={btn}>
          {loading ? "..." : "Create account"}
        </button>

        <div style={{ fontSize: 13, color: "#666" }}>
          عندك حساب؟ <Link to="/login">Login</Link>
        </div>
      </form>
    </div>
  );
}

const card = { background: "white", border: "1px solid #eee", borderRadius: 16, padding: 16 };
const input = { padding: 10, borderRadius: 10, border: "1px solid #ddd" };
const btn = { padding: "10px 14px", borderRadius: 10, border: "1px solid #111", background: "#111", color: "white" };
const errorBox = { padding: 12, background: "#ffe8e8", border: "1px solid #ffb3b3", borderRadius: 12 };