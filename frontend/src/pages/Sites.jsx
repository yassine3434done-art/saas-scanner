import { useEffect, useState } from "react";
import { apiGet, apiPost } from "../lib/api.js";

export default function Sites() {
  const [items, setItems] = useState(null);
  const [err, setErr] = useState("");
  const [domain, setDomain] = useState("");

  async function load() {
    setErr("");
    try {
      const data = await apiGet("/sites");
      setItems(data);
    } catch (e) {
      setErr(String(e?.message || e));
      setItems(null);
    }
  }

  useEffect(() => { load(); }, []);

  async function onAdd(e) {
    e.preventDefault();
    setErr("");
    try {
      await apiPost("/sites", { url: domain }); // إذا كان الحقل مختلف (domain مثلا) نبدلوه
      setDomain("");
      await load();
    } catch (e2) {
      setErr(String(e2?.message || e2));
    }
  }

  return (
    <div style={card}>
      <h2 style={{ marginTop: 0 }}>Sites</h2>

      <form onSubmit={onAdd} style={{ display: "flex", gap: 8, marginBottom: 12 }}>
        <input
          value={domain}
          onChange={(e) => setDomain(e.target.value)}
          placeholder="https://example.com"
          style={input}
        />
        <button style={btn}>Add</button>
        <button type="button" onClick={load} style={btn2}>Refresh</button>
      </form>

      {err && <div style={errorBox}>{err}</div>}

      <div>
        <b>Response:</b>
        <pre style={pre}>{items ? JSON.stringify(items, null, 2) : "No data yet."}</pre>

        <p style={{ color: "#666", fontSize: 12 }}>
          إذا خرج error هنا، صيفط ليا message ديال error أو screenshot من /docs باش نضبط payload والمسارات.
        </p>
      </div>
    </div>
  );
}

const card = { background: "white", border: "1px solid #eee", borderRadius: 16, padding: 16 };
const input = { flex: 1, padding: 10, borderRadius: 10, border: "1px solid #ddd" };
const btn = { padding: "10px 14px", borderRadius: 10, border: "1px solid #111", background: "#111", color: "white" };
const btn2 = { padding: "10px 14px", borderRadius: 10, border: "1px solid #ddd", background: "white" };
const pre = { background: "#fafafa", border: "1px solid #eee", borderRadius: 12, padding: 10, overflow: "auto" };
const errorBox = { padding: 12, background: "#ffe8e8", border: "1px solid #ffb3b3", borderRadius: 12, marginBottom: 12 };