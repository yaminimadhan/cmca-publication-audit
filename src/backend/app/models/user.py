# src/backend/app/models/user.py
from datetime import datetime
from sqlalchemy import String, CheckConstraint, text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("user_type IN ('admin','general_user')", name="ck_user_type"),
    )

    user_id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    user_type: Mapped[str] = mapped_column(String(16), nullable=False)  # admin|general_user
    created_at: Mapped[datetime] = mapped_column(
        # DB column is TIMESTAMPTZ with DEFAULT now()
        nullable=False,
        server_default=text("now()"),
    )
