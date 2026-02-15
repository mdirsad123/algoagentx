from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Optional
from uuid import UUID

from ..db.models.users import User as UserModel
from ..schemas.users import UserUpdate


class UserService:
    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: str) -> Optional[UserModel]:
        """
        Get user by ID
        """
        try:
            result = await db.execute(
                select(UserModel).where(UserModel.id == UUID(user_id))
            )
            user = result.scalar_one_or_none()
            return user
        except Exception as e:
            raise e

    @staticmethod
    async def update_user(db: AsyncSession, user_id: str, full_name: str) -> Optional[UserModel]:
        """
        Update user full_name
        """
        try:
            # Get user by ID
            result = await db.execute(
                select(UserModel).where(UserModel.id == UUID(user_id))
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return None
            
            # Update full_name
            user.fullname = full_name
            
            # Commit changes
            await db.commit()
            await db.refresh(user)
            
            return user
            
        except Exception as e:
            await db.rollback()
            raise e

    @staticmethod
    async def update_user_profile(db: AsyncSession, user_id: str, user_update: UserUpdate) -> Optional[UserModel]:
        """
        Update user profile information
        """
        try:
            # Get user by ID
            result = await db.execute(
                select(UserModel).where(UserModel.id == UUID(user_id))
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return None
            
            # Update fields if provided
            if user_update.fullname is not None:
                user.fullname = user_update.fullname
            if user_update.mobile is not None:
                user.mobile = user_update.mobile
            
            # Commit changes
            await db.commit()
            await db.refresh(user)
            
            return user
            
        except Exception as e:
            await db.rollback()
            raise e
