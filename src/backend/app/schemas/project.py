from datetime import datetime
from pydantic import BaseModel, Field

class ProjectCreate(BaseModel):
    project_name: str = Field(min_length=3, max_length=255)

class ProjectUpdate(BaseModel):
    project_name: str | None = Field(default=None, min_length=3, max_length=255)

class ProjectOut(BaseModel):
    project_id: int
    project_name: str
    created_by: int
    created_at: datetime

    class Config:
        from_attributes = True
