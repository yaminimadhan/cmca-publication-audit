from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.project import Project

class ProjectRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, project_id: int) -> Project | None:
        res = await self.session.execute(select(Project).where(Project.project_id == project_id))
        return res.scalars().first()

    async def get_by_name(self, name: str) -> Project | None:
        res = await self.session.execute(select(Project).where(Project.project_name == name))
        return res.scalars().first()

    async def create(self, *, name: str, created_by: int) -> Project:
        proj = Project(project_name=name, created_by=created_by)
        self.session.add(proj)
        await self.session.commit()
        await self.session.refresh(proj)
        return proj

    async def rename(self, *, project_id: int, new_name: str) -> Project | None:
        await self.session.execute(
            update(Project)
            .where(Project.project_id == project_id)
            .values(project_name=new_name)
        )
        await self.session.commit()
        return await self.get_by_id(project_id)

    async def delete(self, project_id: int) -> None:
        await self.session.execute(delete(Project).where(Project.project_id == project_id))
        await self.session.commit()

    async def list_all(self, *, limit: int = 50, offset: int = 0) -> list[Project]:
        stmt = (
            select(Project)
            .order_by(Project.created_at.desc(), Project.project_id.desc())
            .limit(limit)
            .offset(offset)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def list_by_creator(self, *, user_id: int, limit: int = 50, offset: int = 0) -> list[Project]:
        stmt = (
            select(Project)
            .where(Project.created_by == user_id)
            .order_by(Project.created_at.desc(), Project.project_id.desc())
            .limit(limit)
            .offset(offset)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())
