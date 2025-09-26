from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import engine, get_session
from app.routers import auth, users
from app.routers import projects

app = FastAPI(title=settings.APP_NAME)

# no Base import, no create_all

@app.get("/health")
async def health():
    return {"ok": True}

@app.get("/health/db")
async def db_health(session: AsyncSession = Depends(get_session)):
    try:
        await session.execute(text("SELECT 1"))
        return {"db": "ok"}
    except Exception:
        raise HTTPException(status_code=500, detail="db not ok")

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(projects.router)