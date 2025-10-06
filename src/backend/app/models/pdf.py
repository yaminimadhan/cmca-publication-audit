from datetime import datetime
from sqlalchemy import String, ForeignKey, text, Integer, Float
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Pdf(Base):
    __tablename__ = "pdfs"

    pdf_id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # From extractor JSON
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    authors: Mapped[str | None] = mapped_column(String, nullable=True)
    affiliation: Mapped[str | None] = mapped_column(String, nullable=True)
    doi: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    instruments_json: Mapped[dict | list | None] = mapped_column(JSONB, nullable=True)
    num_pages: Mapped[int | None] = mapped_column(Integer, nullable=True)
    publish_date: Mapped[datetime | None] = mapped_column(nullable=True)

    # From API / context
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.user_id", ondelete="SET NULL"))
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.project_id", ondelete="SET NULL"))
    upload_date: Mapped[datetime] = mapped_column(nullable=False, server_default=text("now()"))

    # From LLM
    cosine_similarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    cmca_result: Mapped[str | None] = mapped_column(String, nullable=True)  # 'Yes' | 'No'
