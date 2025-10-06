from __future__ import annotations
import os
from typing import Annotated
from datetime import datetime
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import FileResponse
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_session
from app.schemas.pdf import PdfUploadParams, PdfOut, PdfUpdate
from app.services.pdf_service import PdfService

router = APIRouter(prefix="/pdfs", tags=["pdfs"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_actor_claims(token: str = Depends(oauth2_scheme)) -> dict:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return {
            "user_id": int(payload.get("sub")),
            "username": payload.get("username"),
            "user_type": payload.get("user_type"),
        }
    except (JWTError, ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

@router.post("/upload", response_model=PdfOut, status_code=201)
async def upload_pdf(
    file: UploadFile = File(...),  # <-- PDF file (bytes) passed to extractor
    project_id: int | None = Form(default=None),   # <-- From API input
    title: str | None = Form(default=None),        # <-- Optional overrides (beats extractor)
    authors: str | None = Form(default=None),
    affiliation: str | None = Form(default=None),
    doi: str | None = Form(default=None),
    publish_date: str | None = Form(default=None), # ISO string; extractor can also supply
    session: AsyncSession = Depends(get_session),
    actor=Depends(get_actor_claims),
):
    content = await file.read()
    overrides = {
        "title": title,
        "authors": authors,
        "affiliation": affiliation,
        "doi": doi,
        "publish_date": publish_date,
    }
    svc = PdfService(session)
    doc = await svc.ingest(
        file_bytes=content,
        uploaded_by=actor["user_id"],   # <-- From API context (JWT)
        project_id=project_id,          # <-- From API form field
        overrides=overrides             # <-- Optional client overrides
    )
    return doc

@router.get("", response_model=list[PdfOut])
async def list_pdfs(
    project_id: int | None = Query(default=None),
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    session: AsyncSession = Depends(get_session),
    actor=Depends(get_actor_claims),
):
    from app.repositories.pdf_repo import PdfRepo
    repo = PdfRepo(session)
    return await repo.list(project_id=project_id, limit=limit, offset=offset)

@router.get("/{pdf_id}", response_model=PdfOut)
async def get_pdf(
    pdf_id: int,
    session: AsyncSession = Depends(get_session),
    actor=Depends(get_actor_claims),
):
    from app.repositories.pdf_repo import PdfRepo
    repo = PdfRepo(session)
    doc = await repo.get(pdf_id)
    if not doc:
        raise HTTPException(status_code=404, detail="PDF not found")
    return doc

@router.get("/{pdf_id}/file")
async def download_pdf(
    pdf_id: int,
    session: AsyncSession = Depends(get_session),
    actor=Depends(get_actor_claims),  # keeps it protected
):
    from app.repositories.pdf_repo import PdfRepo
    repo = PdfRepo(session)
    doc = await repo.get(pdf_id)
    if not doc:
        raise HTTPException(status_code=404, detail="PDF not found")
    if not doc.storage_path or not os.path.exists(doc.storage_path):
        raise HTTPException(status_code=404, detail="File not found on server")
    return FileResponse(
        doc.storage_path,
        media_type="application/pdf",
        filename=f"{(doc.title or 'document')}.pdf",
    )

def _parse_publish_date(value: Any):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None

@router.patch("/{pdf_id}", response_model=PdfOut)
async def edit_pdf(
    pdf_id: int,
    payload: PdfUpdate,
    session: AsyncSession = Depends(get_session),
    actor=Depends(get_actor_claims),
):
    from app.repositories.pdf_repo import PdfRepo
    repo = PdfRepo(session)
    doc = await repo.get(pdf_id)
    if not doc:
        raise HTTPException(status_code=404, detail="PDF not found")

    # Optional auth rules (you said no special privileges; leaving open)
    # if actor["user_type"] != "admin" and actor["user_id"] != doc.uploaded_by: ...

    fields = payload.model_dump(exclude_unset=True)

    # handle publish_date flexibility (str/datetime)
    if "publish_date" in fields:
        pd = fields.get("publish_date")
        parsed = _parse_publish_date(pd)
        # if your column is TEXT, store original string; if it's datetime, store parsed
        fields["publish_date"] = parsed or pd  # harmless either way

    try:
        updated = await repo.update(doc, **fields)
    except Exception as e:
        # handle uniqueness errors etc.
        raise HTTPException(status_code=400, detail=f"Update failed: {e}")

    return updated

@router.delete("/{pdf_id}", status_code=204)
async def delete_pdf(
    pdf_id: int,
    session: AsyncSession = Depends(get_session),
    actor=Depends(get_actor_claims),
):
    from app.repositories.pdf_repo import PdfRepo
    repo = PdfRepo(session)
    doc = await repo.get(pdf_id)
    if not doc:
        raise HTTPException(status_code=404, detail="PDF not found")

    # Optional auth check
    # if actor["user_type"] != "admin" and actor["user_id"] != doc.uploaded_by: ...

    # Best-effort file removal
    try:
        if getattr(doc, "storage_path", None) and os.path.exists(doc.storage_path):
            os.remove(doc.storage_path)
    except Exception:
        pass

    await repo.delete(doc)
    return