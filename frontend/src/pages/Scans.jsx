import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiGet } from "../lib/api.js";

export default function Scans() {
  const [items, setItems] = useState(null);
  const [err, setErr] = useState("");

  async function load() {
    setErr("");
    try {
      const data = await apiGet("/scans");
      setItems(data);
    } catch (e) {
      setErr(String(e?.message || e));
      setItems(null);
    }
  }

  useEffect(() => { load(); }, []);

  return (
    <div style={card}>
      <h2 style={{ marginTop: 0 }}>Scans</h2>
      <button onClick={load} style={btn2}>Refresh</button>

      {err && <div style={errorBox}>{err}</div>}

      <pre style={pre}>{items ? JSON.stringify(items, null, 2) : "No data yet."}</pre>

      {/* إذا كانت scans عبارة عن array فيها id, نعرضها بروابط */}
      {Array.isArray(items) && (
        <div style={{ marginTop: 12 }}>
          <b>Open scan:</b>
          <ul>
            {items.slice(0, 20).map((s, i) => (
              <li key={s?.id ?? i}>
                <Link to={`/scans/${s?.id ?? ""}`}>{s?.id ?? `scan-${i}`}</Link>
              </li>
            ))}
          </ul>
        </div>
      )}

      <p style={{ color: "#666", fontSize: 12 }}>
        إذا /scans كيرجع object مختلف، صيفط ليا شكل الresponse من /docs ونبدلو UI.
      </p>
    </div>
  );
}

const card = { background: "white", border: "1px solid #eee", borderRadius: 16, padding: 16 };
const btn2 = { padding: "10px 14px", borderRadius: 10, border: "1px solid #ddd", background: "white", marginBottom: 12 };
const pre = { background: "#fafafa", border: "1px solid #eee", borderRadius: 12, padding: 10, overflow: "auto" };
const errorBox = { padding: 12, background: "#ffe8e8", border: "1px solid #ffb3b3", borderRadius: 12, marginBottom: 12 };