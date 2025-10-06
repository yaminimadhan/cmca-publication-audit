from pydantic import BaseModel, Field
from datetime import datetime 
from typing import Literal

UserType = Literal["admin", "general_user"]

class UserBase(BaseModel):
    username: str = Field(min_length=3, max_length=255)
    user_type: UserType

class UserCreate(UserBase):
    password: str = Field(min_length=6)

class UserUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=255)
    user_type: UserType | None = None
    password: str | None = Field(default=None, min_length=6)

class UserOut(BaseModel):
    user_id: int
    username: str
    user_type: UserType
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class LoginIn(BaseModel):
    username: str
    password: str
