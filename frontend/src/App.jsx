import { useEffect, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "";

export default function App() {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    async function run() {
      try {
        setLoading(true);
        setErr("");

        const url = `${API_BASE.replace(/\/$/, "")}/health`;
        const res = await fetch(url);

        const text = await res.text();
        let json = null;
        try {
          json = JSON.parse(text);
        } catch {
          // not json
        }

        if (!res.ok) {
          throw new Error(`HTTP ${res.status}: ${json ? JSON.stringify(json) : text}`);
        }

        setData(json ?? text);
      } catch (e) {
        setErr(String(e?.message || e));
      } finally {
        setLoading(false);
      }
    }
    run();
  }, []);

  return (
    <div style={{ fontFamily: "Arial, sans-serif", padding: 24, maxWidth: 900, margin: "0 auto" }}>
      <h1>SaaS Scanner</h1>

      <p>
        API:{" "}
        <a href={API_BASE} target="_blank" rel="noreferrer">
          {API_BASE}
        </a>{" "}
        |{" "}
        <a href={`${API_BASE.replace(/\/$/, "")}/docs`} target="_blank" rel="noreferrer">
          /docs
        </a>
      </p>

      <hr />

      <h2>Health Check</h2>

      {loading && <p>Loading…</p>}

      {err && (
        <div style={{ padding: 12, background: "#ffe8e8", border: "1px solid #ffb3b3" }}>
          <b>Error:</b> {err}
          <p style={{ marginTop: 8 }}>
            جرّب تفتح{" "}
            <a href={`${API_BASE.replace(/\/$/, "")}/health`} target="_blank" rel="noreferrer">
              /health
            </a>{" "}
            مباشرة وشوف واش كيرجع JSON.
          </p>
        </div>
      )}

      {data && (
        <pre style={{ padding: 12, background: "#f6f6f6", border: "1px solid #ddd", overflow: "auto" }}>
          {typeof data === "string" ? data : JSON.stringify(data, null, 2)}
        </pre>
      )}
    </div>
  );
}