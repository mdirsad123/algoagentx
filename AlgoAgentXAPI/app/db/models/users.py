from sqlalchemy import Column, String, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import func
from ..base import Base
import uuid


class User(Base):
    __tablename__ = "users"

    # Use proper UUID column type for PostgreSQL
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="user")
    fullname = Column(String, nullable=True)
    mobile = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
