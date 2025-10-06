from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_session
from app.schemas.user import UserCreate, Token, LoginIn
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=Token, status_code=201)
async def register(payload: UserCreate, session: AsyncSession = Depends(get_session)):
    _, token = await AuthService(session).register(payload)
    return {"access_token": token, "token_type": "bearer"}

@router.post("/login", response_model=Token)
async def login(payload: LoginIn, session: AsyncSession = Depends(get_session)):
    _, token = await AuthService(session).login(payload)
    return {"access_token": token, "token_type": "bearer"}
