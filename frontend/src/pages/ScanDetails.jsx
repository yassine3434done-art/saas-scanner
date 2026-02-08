import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { apiGet } from "../lib/api.js";

export default function ScanDetails() {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (!id) return;
    apiGet(`/scans/${id}`)
      .then(setData)
      .catch((e) => setErr(String(e?.message || e)));
  }, [id]);

  return (
    <div style={card}>
      <h2 style={{ marginTop: 0 }}>Scan Details</h2>
      <p><b>ID:</b> {id}</p>

      {err && <div style={errorBox}>{err}</div>}
      <pre style={pre}>{data ? JSON.stringify(data, null, 2) : "Loading…"}</pre>
    </div>
  );
}

const card = { background: "white", border: "1px solid #eee", borderRadius: 16, padding: 16 };
const pre = { background: "#fafafa", border: "1px solid #eee", borderRadius: 12, padding: 10, overflow: "auto" };
const errorBox = { padding: 12, background: "#ffe8e8", border: "1px solid #ffb3b3", borderRadius: 12, marginBottom: 12 };