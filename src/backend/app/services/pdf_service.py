#src/backend/app/services/pdf_service.py

import json
import os
from uuid import uuid4
from pathlib import Path
from datetime import datetime
from typing import Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.pdf_repo import PdfRepo
from app.services.extraction_service import extract_api


# --- plug your existing services here ---
# EXPECTED CONTRACTS:
# 1) Extractor: takes PDF bytes, returns JSON with keys:
#    { "title": str|None, "authors": str|None, "affiliation": str|None,
#      "doi": str|None, "instruments": list|dict|None, "num_pages": int|None,
#      "publish_date": str|None (ISO8601) }
#
# 2) LLM: takes the *extractor JSON* (or text) and returns:
#    { "cosine_similarity": float|None, "cmca_result": "Yes"|"No" }
#
# Replace the two stubs `_run_extractor` and `_run_llm` with your real calls.

async def _run_extractor(file_bytes: bytes) -> Dict[str, Any]:
    return extract_api(file_bytes)  # sync call is fine here
   

# async def _run_llm(extractor_json: Dict[str, Any]) -> Dict[str, Any]:
#     # TODO: CALL YOUR LLM HERE using extractor_json as input
#     # e.g., resp = await llm_client.classify(extractor_json); return resp
#     raise NotImplementedError("wire your LLM client here")

def _parse_publish_date(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        # Pydantic can parse on the router too, but this ensures robustness
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None

class PdfService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = PdfRepo(session)

    async def ingest(
        self,
        *,
        file_bytes: bytes,
        uploaded_by: int | None,
        project_id: int | None,
        overrides: Dict[str, Any] | None = None
    ):
        # ---- Save file to disk (local storage) ----
        base_dir = os.getenv("UPLOAD_DIR", "storage/pdfs")
        Path(base_dir).mkdir(parents=True, exist_ok=True)
        filename = f"{uuid4().hex}.pdf"
        storage_path = str((Path(base_dir) / filename).resolve())
        with open(storage_path, "wb") as f:
            f.write(file_bytes)

        # === 1) EXTRACTOR CALL ===
        extractor_json = await _run_extractor(file_bytes)  # <-- CALL YOUR EXTRACTOR HERE

        # pull expected fields from extractor JSON
        title = (overrides or {}).get("title") or extractor_json.get("title")
        authors = (overrides or {}).get("authors") or extractor_json.get("authors")
        affiliation = (overrides or {}).get("affiliation") or extractor_json.get("affiliation")
        doi = (overrides or {}).get("doi") or extractor_json.get("doi")
        instruments = extractor_json.get("instruments")  # list or dict
        num_pages = extractor_json.get("num_pages")
        publish_date = (overrides or {}).get("publish_date") or extractor_json.get("publish_date")
        publish_dt = _parse_publish_date(publish_date)

        # # === 2) LLM CALL ===
        # llm_json = await _run_llm(extractor_json)         # <-- CALL YOUR LLM HERE
        # cosine = llm_json.get("cosine_similarity")
        # cmca = llm_json.get("cmca_result")

        # === 3) PERSIST ===
        doc = await self.repo.create(
            title=title,
            authors=authors,
            affiliation=affiliation,
            doi=doi,
            instruments_json=instruments,
            num_pages=num_pages,
            publish_date=publish_dt,
            uploaded_by=uploaded_by,
            project_id=project_id,
            # cosine_similarity=cosine,
            # cmca_result=cmca,
            storage_path=storage_path,
        )
        return doc
