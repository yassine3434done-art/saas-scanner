from __future__ import annotations

import os
from typing import Any, Dict
from pathlib import Path

import requests
from dotenv import load_dotenv


# ------------------------------------------------------------------
# 🔐 Ensure ENV is loaded (safe for prod & local)
# ------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[2]  # backend/
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=False)
# override=False: ما يطيحش ENV ديال Render فالإنتاج


RESEND_API_URL = "https://api.resend.com/emails"


class EmailSendError(RuntimeError):
    pass


def _get_from_email() -> str:
    """
    Priority:
      1) RESEND_FROM_EMAIL="My Site <support@esms44.shop>"
      2) RESEND_DOMAIN="esm44.shop" => "My Site <onboarding@esms44.shop>"
    """
    from_email = (os.getenv("RESEND_FROM_EMAIL") or "").strip()
    if from_email:
        return from_email

    domain = (os.getenv("RESEND_DOMAIN") or "").strip().lstrip("@")
    if domain:
        return f"My Site <onboarding@{domain}>"

    # last fallback (will likely be blocked by Resend for non-owner recipients)
    return "My Site <onboarding@resend.dev>"


def send_email(to_email: str, subject: str, html: str) -> Dict[str, Any]:
    """
    Send transactional email via Resend HTTP API (NO SMTP).
    Reads API key from env: RESEND_API_KEY
    From email:
      - RESEND_FROM_EMAIL (recommended) OR
      - RESEND_DOMAIN
    """

    api_key = (os.getenv("RESEND_API_KEY") or "").strip()
    if not api_key:
        raise EmailSendError(
            "RESEND_API_KEY is missing. Ensure it exists in environment variables or backend/.env"
        )

    to_email = (to_email or "").strip()
    if not to_email:
        raise EmailSendError("to_email is empty")

    subject = (subject or "").strip()
    if not subject:
        raise EmailSendError("subject is empty")

    html = (html or "").strip()
    if not html:
        raise EmailSendError("html is empty")

    from_email = _get_from_email()

    payload = {
        "from": from_email,
        "to": [to_email],
        "subject": subject,
        "html": html,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "saas-scanner/1.0",
    }

    # ⏱ Prevent hanging (important on Render & Windows)
    timeout = (5, 10)  # connect, read

    try:
        resp = requests.post(RESEND_API_URL, json=payload, headers=headers, timeout=timeout)
    except requests.RequestException as e:
        raise EmailSendError(f"Resend request failed: {e}") from e

    if not (200 <= resp.status_code < 300):
        body = (resp.text or "")[:900]

        if resp.status_code == 403:
            raise EmailSendError(
                "Resend API 403. غالباً السبب واحد من هادشي:\n"
                "- حسابك مازال Testing mode (كتقدر تصيفط غير لمالك الحساب)\n"
                "- أو 'from' ماشي من domain verified ديالك\n\n"
                "الحل:\n"
                "1) تأكد domain verified فـ Resend.\n"
                "2) حط FROM من نفس الدومين، مثلاً: RESEND_FROM_EMAIL='My Site <support@esm44.shop>'\n"
                "3) جرّب تصيفط لأي email.\n\n"
                f"Details: {body}"
            )

        raise EmailSendError(f"Resend API error {resp.status_code}: {body}")

    try:
        return resp.json()
    except ValueError as e:
        raise EmailSendError("Resend returned non-JSON response") from e