// frontend/src/lib/api.js

const API_BASE = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

// token كنخزنوه فالـbrowser
const TOKEN_KEY = "saas_scanner_token";

export function getToken() {
  return (localStorage.getItem(TOKEN_KEY) || "").trim();
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, (token || "").trim());
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

function authHeaders(extra = {}) {
  const token = getToken();
  if (!token) return extra;
  return { ...extra, Authorization: `Bearer ${token}` };
}

async function parseResponse(res) {
  const text = await res.text();
  let json = null;
  try { json = JSON.parse(text); } catch {}
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${json ? JSON.stringify(json) : text}`);
  return json ?? text;
}

export async function apiGet(path) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: authHeaders(),
  });
  return parseResponse(res);
}

export async function apiPost(path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(body ?? {}),
  });
  return parseResponse(res);
}

// مهم: login/register ما خاصهمش Authorization
export async function apiPostNoAuth(path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body ?? {}),
  });
  return parseResponse(res);
}