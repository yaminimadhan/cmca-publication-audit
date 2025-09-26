import json
from datetime import datetime
from typing import Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.pdf_repo import PdfRepo

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
    # TODO: CALL YOUR EXTRACTOR HERE (HTTP client or local function)
    # e.g., resp = await http.post(EXTRACTOR_URL, files={"file": file_bytes}); return resp.json()
    raise NotImplementedError("wire your extractor client here")

async def _run_llm(extractor_json: Dict[str, Any]) -> Dict[str, Any]:
    # TODO: CALL YOUR LLM HERE using extractor_json as input
    # e.g., resp = await llm_client.classify(extractor_json); return resp
    raise NotImplementedError("wire your LLM client here")

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

        # === 2) LLM CALL ===
        llm_json = await _run_llm(extractor_json)         # <-- CALL YOUR LLM HERE
        cosine = llm_json.get("cosine_similarity")
        cmca = llm_json.get("cmca_result")

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
            cosine_similarity=cosine,
            cmca_result=cmca,
        )
        return doc
