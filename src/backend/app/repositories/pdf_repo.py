from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.pdf import Pdf

class PdfRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, **values) -> Pdf:
        doc = Pdf(**values)
        self.session.add(doc)
        await self.session.commit()
        await self.session.refresh(doc)
        return doc

    async def get(self, pdf_id: int) -> Pdf | None:
        res = await self.session.execute(select(Pdf).where(Pdf.pdf_id == pdf_id))
        return res.scalars().first()

    async def list(self, *, project_id: int | None = None, limit: int = 50, offset: int = 0) -> list[Pdf]:
        stmt = select(Pdf).order_by(Pdf.pdf_id.desc()).limit(limit).offset(offset)
        if project_id is not None:
            stmt = select(Pdf).where(Pdf.project_id == project_id).order_by(Pdf.pdf_id.desc()).limit(limit).offset(offset)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def update(self, pdf: Pdf, **fields) -> Pdf:
        # assign only provided (not None) fields
        for k, v in list(fields.items()):
            if v is not None and hasattr(pdf, k):
                setattr(pdf, k, v)
        await self.session.commit()
        await self.session.refresh(pdf)
        return pdf

    async def delete(self, pdf: Pdf) -> None:
        await self.session.delete(pdf)
        await self.session.commit()