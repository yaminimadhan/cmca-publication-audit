# core/api.py
from __future__ import annotations
import os, typing as t, requests
import streamlit as st

BASE_URL = st.secrets.get("API_BASE_URL") or os.getenv("API_BASE_URL") or "http://localhost:8000"
TIMEOUT = 30

def _headers(token: str | None = None, extra: dict[str, str] | None = None) -> dict[str, str]:
    h = {"Accept": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    if extra:
        h.update(extra)
    return h

def get(path: str, token: str | None = None, params: dict | None = None):
    r = requests.get(f"{BASE_URL}{path}", headers=_headers(token), params=params, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

def post_json(path: str, payload: dict, token: str | None = None):
    r = requests.post(
        f"{BASE_URL}{path}",
        headers=_headers(token, {"Content-Type": "application/json"}),
        json=payload,
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return r.json()

def post_form(path: str, data: dict[str, t.Any], files: dict[str, t.IO[bytes]] | None = None, token: str | None = None):
    r = requests.post(f"{BASE_URL}{path}", headers=_headers(token), data=data, files=files, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

# --- NEW: multipart upload (for PDFs) ---
def post_multipart(
    path: str,
    files: dict[str, tuple[str, t.Union[bytes, t.IO[bytes]], str]] | None = None,
    data: dict[str, t.Any] | None = None,
    token: str | None = None,
    timeout: int | None = None,
):
    """
    Send multipart/form-data.
    files example:
      {"file": ("paper.pdf", pdf_bytes_or_file, "application/pdf")}
    data example:
      {"project_id": "1", "title": "optional override", ...}
    """
    r = requests.post(
        f"{BASE_URL}{path}",
        headers=_headers(token),
        files=files,
        data=data or {},
        timeout=timeout or max(TIMEOUT, 600),  # allow large uploads
    )
    r.raise_for_status()
    return r.json()

def delete(path: str, token: str | None = None):
    r = requests.delete(f"{BASE_URL}{path}", headers=_headers(token), timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()
