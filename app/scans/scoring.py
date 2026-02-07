# backend/app/scans/scoring.py

from __future__ import annotations

from typing import Any

SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"]
SEVERITY_RANK = {s: i for i, s in enumerate(SEVERITY_ORDER)}

# points deducted per finding
SEVERITY_POINTS = {
    "critical": 25,
    "high": 15,
    "medium": 7,
    "low": 3,
    "info": 1,
}

def normalize_severity(sev: str | None) -> str:
    s = (sev or "").strip().lower()
    if s in SEVERITY_RANK:
        return s
    return "info"

def sort_findings(findings: list[dict]) -> list[dict]:
    def key(f: dict):
        sev = normalize_severity(f.get("severity"))
        return (SEVERITY_RANK.get(sev, 999), str(f.get("id") or ""), str(f.get("title") or ""))
    return sorted(findings or [], key=key)

def summarize_findings(findings: list[dict]) -> dict[str, int]:
    out = {s: 0 for s in SEVERITY_ORDER}
    for f in findings or []:
        out[normalize_severity(f.get("severity"))] += 1
    return out

def compute_score(findings: list[dict]) -> tuple[int, dict[str, int], int]:
    """
    score = 100 - sum(points(severity))
    returns: (score 0..100, breakdown counts, deducted_points)
    """
    breakdown = summarize_findings(findings)
    deducted = 0
    for sev, cnt in breakdown.items():
        deducted += (SEVERITY_POINTS.get(sev, 0) * cnt)

    score = 100 - deducted
    if score < 0:
        score = 0
    if score > 100:
        score = 100
    return score, breakdown, deducted

def risk_level(score: int) -> str:
    # simple, readable thresholds
    if score >= 90:
        return "low"
    if score >= 75:
        return "medium"
    if score >= 55:
        return "high"
    return "critical"

def enrich_summary(summary: dict[str, Any]) -> dict[str, Any]:
    """
    Adds:
      summary["risk"] = {"score": int, "level": str, "breakdown": {...}, "deducted": int}
      summary["findings"] sorted by severity
    """
    summary = summary or {}
    findings = summary.get("findings") or []
    findings_sorted = sort_findings(findings)

    score, breakdown, deducted = compute_score(findings_sorted)
    summary["findings"] = findings_sorted
    summary["risk"] = {
        "score": score,
        "level": risk_level(score),
        "breakdown": breakdown,
        "deducted": deducted,
    }
    return summary