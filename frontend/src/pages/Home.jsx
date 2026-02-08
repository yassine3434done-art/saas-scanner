import { useEffect, useState } from "react";
import { apiGet } from "../lib/api.js";

export default function Home() {
  const [health, setHealth] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    apiGet("/health")
      .then(setHealth)
      .catch((e) => setErr(String(e?.message || e)));
  }, []);

  return (
    <div style={card}>
      <h1 style={{ marginTop: 0 }}>Welcome 👋</h1>
      <p>هاد المنصة كتعاونك تفحص مواقع SaaS (sites) وتدير scans وتراجع النتائج.</p>

      <div style={{ display: "grid", gap: 12, gridTemplateColumns: "1fr 1fr" }}>
        <div style={miniCard}>
          <b>Backend status</b>
          <div style={{ marginTop: 8 }}>
            {err && <span style={{ color: "crimson" }}>{err}</span>}
            {health && <pre style={pre}>{JSON.stringify(health, null, 2)}</pre>}
            {!err && !health && <span>Loading…</span>}
          </div>
        </div>

        <div style={miniCard}>
          <b>Next steps</b>
          <ul style={{ marginTop: 8 }}>
            <li>مشي لـ Sites وزيد دومين</li>
            <li>دير Scan وشوف النتائج فـ Scans</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

const card = { background: "white", border: "1px solid #eee", borderRadius: 16, padding: 16 };
const miniCard = { background: "#fafafa", border: "1px solid #eee", borderRadius: 14, padding: 12 };
const pre = { background: "white", border: "1px solid #eee", borderRadius: 12, padding: 10, overflow: "auto" };