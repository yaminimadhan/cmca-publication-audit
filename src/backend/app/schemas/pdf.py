from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field

class PdfUploadParams(BaseModel):
    # optional overrides client can send alongside the file
    project_id: int | None = None
    title: str | None = None
    authors: str | None = None
    affiliation: str | None = None
    doi: str | None = None
    publish_date: datetime | None = None  # accept ISO8601; we’ll store as timestamptz

class PdfOut(BaseModel):
    pdf_id: int
    title: str | None
    authors: str | None
    affiliation: str | None
    doi: str | None
    instruments_json: Any | None
    num_pages: int | None
    publish_date: datetime | None
    uploaded_by: int | None
    project_id: int | None
    upload_date: datetime
    cosine_similarity: float | None
    cmca_result: str | None

    class Config:
        from_attributes = True

class PdfUpdate(BaseModel):
    # all optional; only fields provided will be updated
    title: Optional[str] = None
    authors: Optional[str] = None
    affiliation: Optional[str] = None
    doi: Optional[str] = None
    instruments_json: Optional[List[str] | Dict[str, Any]] = None
    publish_date: Optional[datetime | str] = Field(default=None, description="ISO 8601 string or datetime")
    project_id: Optional[int] = None
    cmca_result: Optional[Literal["Yes", "No"]] = None
    cosine_similarity: Optional[float] = None