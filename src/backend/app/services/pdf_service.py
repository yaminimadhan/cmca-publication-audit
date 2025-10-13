# src/backend/app/services/pdf_service.py
import json
import os
from uuid import uuid4
from pathlib import Path
from datetime import datetime
from typing import Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.pdf_repo import PdfRepo
from app.services.extraction_service import extract_api
from app.services.llm_service import run_llm_verification_from_json
from app.services.highlight_service import highlight_answer_yes_sentences_from_bytes  # ✅ NEW IMPORT


async def _run_llm(extractor_json: dict, file_bytes: bytes) -> dict:
    return await run_llm_verification_from_json(extractor_json)


async def _run_extractor(file_bytes: bytes) -> Dict[str, Any]:
    return extract_api(file_bytes)


def _parse_publish_date(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
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
        # === 1) EXTRACT ===
        extractor_json = await _run_extractor(file_bytes)

        title = (overrides or {}).get("title") or extractor_json.get("title")
        authors = (overrides or {}).get("authors") or extractor_json.get("authors")
        affiliation = (overrides or {}).get("affiliation") or extractor_json.get("affiliation")
        doi = (overrides or {}).get("doi") or extractor_json.get("doi")
        instruments = extractor_json.get("instruments")
        num_pages = extractor_json.get("num_pages")
        publish_date = (overrides or {}).get("publish_date") or extractor_json.get("publish_date")
        publish_dt = _parse_publish_date(publish_date)

        # === 2) LLM ===
        llm_json = await _run_llm(extractor_json, file_bytes)
        cosine = llm_json.get("cosine_similarity")
        cmca = llm_json.get("cmca_result")
        sentence_results = llm_json.get("Sentence_verifications", [])
        print(sentence_results)

        # === 3) HIGHLIGHT === 
        try:
            highlighted_bytes = highlight_answer_yes_sentences_from_bytes(
                pdf_bytes=file_bytes,
                sentences=extractor_json["sentences"],
                llm_outputs=sentence_results,
            )
        except Exception as e:
            print(f"[warn] Highlighting failed: {e}")
            highlighted_bytes = file_bytes

        # === 4) SAVE FILE ===
        base_dir = os.getenv("UPLOAD_DIR", "storage/pdfs")
        Path(base_dir).mkdir(parents=True, exist_ok=True)
        filename = f"{uuid4().hex}.pdf"
        storage_path = str((Path(base_dir) / filename).resolve())

        with open(storage_path, "wb") as f:
            f.write(highlighted_bytes)

        # === 5) PERSIST METADATA ===
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
            storage_path=storage_path,
        )
        return doc
