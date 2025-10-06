# src/backend/app/services/auth_service.py
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.user_repo import UserRepo
from app.schemas.user import UserCreate, UserUpdate, LoginIn, UserOut
from app.core.security import hash_password, verify_password, create_access_token

class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = UserRepo(session)

    async def register(self, payload: UserCreate):
        # username must be unique
        existing = await self.repo.get_by_username(payload.username)
        if existing:
            raise HTTPException(status_code=409, detail="Username already exists")

        pwd_hash = hash_password(payload.password)
        user = await self.repo.create(
            username=payload.username,
            password_hash=pwd_hash,
            user_type=payload.user_type,
        )
        token = create_access_token(
            subject=user.user_id,
            extra={"username": user.username, "user_type": user.user_type},
        )
        return user, token

    async def login(self, payload: LoginIn):
        user = await self.repo.get_by_username(payload.username)
        if not user or not verify_password(payload.password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
        token = create_access_token(
            subject=user.user_id,
            extra={"username": user.username, "user_type": user.user_type},
        )
        return user, token

    async def edit_user(self, actor_id: int, target_user_id: int, payload: UserUpdate):
        # Authorization: admin can edit anyone; general_user can only edit themself & cannot change role
        target = await self.repo.get_by_id(target_user_id)
        if not target:
            raise HTTPException(status_code=404, detail="User not found")

        # get actor (caller)
        actor = await self.repo.get_by_id(actor_id)
        if not actor:
            raise HTTPException(status_code=401, detail="Unauthorized")

        # general_user cannot edit others
        if actor.user_type != "admin" and actor.user_id != target.user_id:
            raise HTTPException(status_code=403, detail="Not allowed")

        # general_user cannot escalate privileges
        next_user_type = payload.user_type if payload.user_type is not None else target.user_type
        if actor.user_type != "admin" and payload.user_type is not None and payload.user_type != target.user_type:
            raise HTTPException(status_code=403, detail="Not allowed to change role")

        next_username = payload.username if payload.username is not None else target.username
        next_pwd_hash = target.password_hash
        if payload.password:
            next_pwd_hash = hash_password(payload.password)

        updated = await self.repo.update(
            target,
            username=next_username,
            user_type=next_user_type,
            password_hash=next_pwd_hash,
        )
        return updated
