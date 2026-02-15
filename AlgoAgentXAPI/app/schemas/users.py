from pydantic import BaseModel, EmailStr
from datetime import datetime
from uuid import UUID

class UserBase(BaseModel):
    email: EmailStr
    role: str = "user"

class UserCreate(UserBase):
    password: str
    fullname: str | None = None
    mobile: str | None = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(UserBase):
    id: UUID
    created_at: datetime
    fullname: str | None = None
    mobile: str | None = None

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    full_name: str | None = None

    class Config:
        from_attributes = True

class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    role: str
    full_name: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True
