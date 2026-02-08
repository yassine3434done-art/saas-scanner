// frontend/src/lib/api.js

const API_BASE = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");
const MVP_TOKEN = (import.meta.env.VITE_MVP_TOKEN || "").trim();

function authHeaders(extra = {}) {
  // إذا ماكاينش token نخليها تخدم بحال قبل
  if (!MVP_TOKEN) return extra;
  return { ...extra, Authorization: `Bearer ${MVP_TOKEN}` };
}

export async function apiGet(path) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: authHeaders(),
  });

  const text = await res.text();
  let json = null;
  try { json = JSON.parse(text); } catch {}

  if (!res.ok) throw new Error(`HTTP ${res.status}: ${json ? JSON.stringify(json) : text}`);
  return json ?? text;
}

export async function apiPost(path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(body ?? {}),
  });

  const text = await res.text();
  let json = null;
  try { json = JSON.parse(text); } catch {}

  if (!res.ok) throw new Error(`HTTP ${res.status}: ${json ? JSON.stringify(json) : text}`);
  return json ?? text;
}