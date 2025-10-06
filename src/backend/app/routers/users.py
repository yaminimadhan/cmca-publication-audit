# app/routers/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.db.session import get_session
from app.schemas.user import UserOut, UserUpdate
from app.services.auth_service import AuthService
from app.repositories.user_repo import UserRepo

router = APIRouter(prefix="/users", tags=["users"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_actor_claims(token: str = Depends(oauth2_scheme)) -> dict:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        # token was created with sub=user_id and extra {username, user_type}
        return {
            "user_id": int(payload.get("sub")),
            "username": payload.get("username"),
            "user_type": payload.get("user_type"),
        }
    except (JWTError, ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    actor=Depends(get_actor_claims),
):
    repo = UserRepo(session)
    user = await repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Authorization: admin can view anyone; others can only view themselves
    if actor["user_type"] != "admin" and actor["user_id"] != user.user_id:
        raise HTTPException(status_code=403, detail="Not allowed to view this user")
    return user

@router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    session: AsyncSession = Depends(get_session),
    actor=Depends(get_actor_claims),
):
    service = AuthService(session)
    user = await service.edit_user(actor["user_id"], user_id, payload)
    return user
