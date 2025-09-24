from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User

class UserRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_username(self, username: str) -> User | None:
        res = await self.session.execute(select(User).where(User.username == username))
        return res.scalars().first()

    async def get_by_id(self, user_id: int) -> User | None:
        res = await self.session.execute(select(User).where(User.user_id == user_id))
        return res.scalars().first()

    async def create(self, *, username: str, password_hash: str, user_type: str) -> User:
        user = User(username=username, password_hash=password_hash, user_type=user_type)
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def update(
        self,
        user: User,
        *,
        username: str | None = None,
        user_type: str | None = None,
        password_hash: str | None = None
    ) -> User:
        if username is not None:
            user.username = username
        if user_type is not None:
            user.user_type = user_type
        if password_hash is not None:
            user.password_hash = password_hash
        await self.session.commit()
        await self.session.refresh(user)
        return user
