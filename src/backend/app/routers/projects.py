from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from app.core.config import settings
from app.db.session import get_session
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectOut
from app.repositories.project_repo import ProjectRepo
from app.repositories.user_repo import UserRepo

router = APIRouter(prefix="/projects", tags=["projects"])
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

@router.post("", response_model=ProjectOut, status_code=201)
async def create_project(
    payload: ProjectCreate,
    session: AsyncSession = Depends(get_session),
    actor=Depends(get_actor_claims),
):
    repo = ProjectRepo(session)
    # enforce unique name
    if await repo.get_by_name(payload.project_name):
        raise HTTPException(status_code=409, detail="Project name already exists")
    proj = await repo.create(name=payload.project_name, created_by=actor["user_id"])
    return proj

@router.patch("/{project_id}", response_model=ProjectOut)
async def edit_project(
    project_id: int,
    payload: ProjectUpdate,
    session: AsyncSession = Depends(get_session),
    actor=Depends(get_actor_claims),
):
    repo = ProjectRepo(session)
    proj = await repo.get_by_id(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    # Only creator or admin can edit
    if actor["user_type"] != "admin" and actor["user_id"] != proj.created_by:
        raise HTTPException(status_code=403, detail="Not allowed")

    if payload.project_name:
        # check uniqueness
        clash = await repo.get_by_name(payload.project_name)
        if clash and clash.project_id != project_id:
            raise HTTPException(status_code=409, detail="Project name already exists")
        proj = await repo.rename(project_id=project_id, new_name=payload.project_name)

    return proj

@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: int,
    session: AsyncSession = Depends(get_session),
    actor=Depends(get_actor_claims),
):
    repo = ProjectRepo(session)
    proj = await repo.get_by_id(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    # Only creator or admin can delete
    if actor["user_type"] != "admin" and actor["user_id"] != proj.created_by:
        raise HTTPException(status_code=403, detail="Not allowed")

    try:
        await repo.delete(project_id)
    except Exception:
        # e.g., FK constraints from future tables
        raise HTTPException(status_code=409, detail="Cannot delete: project in use")
    
# list projects
@router.get("", response_model=list[ProjectOut])
async def list_projects(
    mine: bool = Query(False, description="Only projects created by me"),
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    session: AsyncSession = Depends(get_session),
    actor=Depends(get_actor_claims),
):
    repo = ProjectRepo(session)
    if mine:
        return await repo.list_by_creator(user_id=actor["user_id"], limit=limit, offset=offset)
    return await repo.list_all(limit=limit, offset=offset)
