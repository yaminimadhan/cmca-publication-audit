from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_session
from app.schemas.pdf import PdfUploadParams, PdfOut
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
