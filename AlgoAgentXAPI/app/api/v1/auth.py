from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional
import uuid
import bcrypt

from ...db.session import async_session
from ...db.models import User
from ...core.security import verify_token, get_current_user
from ...core.config import settings
from ...schemas import UserCreate, UserLogin

router = APIRouter()

@router.post("/login")
async def login(login_data: UserLogin):
    """
    Authenticate user and return JWT token
    """
    try:
        async with async_session() as db:
            # Find user by email
            stmt = select(User).where(User.email == login_data.email)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials"
                )

            # DEBUG: Log the stored hash for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"[AUTH DEBUG] User found: {user.email}")
            logger.info(f"[AUTH DEBUG] Stored hash type: {type(user.password_hash)}")
            logger.info(f"[AUTH DEBUG] Stored hash length: {len(user.password_hash)}")
            logger.info(f"[AUTH DEBUG] Stored hash preview: {user.password_hash[:20]}..." if len(user.password_hash) > 20 else f"[AUTH DEBUG] Stored hash: {user.password_hash}")

            # Verify password with robust handling
            password_bytes = login_data.password.encode('utf-8')
            stored_hash = user.password_hash.strip()

            # Handle both bytes and string stored hashes
            if isinstance(stored_hash, str):
                stored_hash_bytes = stored_hash.encode('utf-8')
            else:
                stored_hash_bytes = stored_hash

            logger.info(f"[AUTH DEBUG] Password bytes length: {len(password_bytes)}")
            
            try:
                password_valid = bcrypt.checkpw(password_bytes, stored_hash_bytes)
                logger.info(f"[AUTH DEBUG] bcrypt.checkpw result: {password_valid}")
            except Exception as e:
                logger.error(f"[AUTH DEBUG] bcrypt error: {e}")
                # Try alternative approach - maybe the hash is already a string that bcrypt can check
                try:
                    password_valid = bcrypt.checkpw(password_bytes, stored_hash.encode('utf-8'))
                    logger.info(f"[AUTH DEBUG] bcrypt.checkpw (alt) result: {password_valid}")
                except Exception as e2:
                    logger.error(f"[AUTH DEBUG] bcrypt alt error: {e2}")
                    password_valid = False

            if not password_valid:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials"
                )

            # Generate JWT token
            from jose import jwt
            from datetime import datetime, timedelta

            payload = {
                "sub": str(user.id),
                "email": user.email,
                "role": user.role,
                "exp": datetime.utcnow() + timedelta(days=1)
            }

            token = jwt.encode(
                payload,
                settings.jwt_secret_key,
                algorithm=settings.jwt_algorithm
            )

            return {
                "access_token": token,
                "token_type": "bearer",
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "role": user.role,
                    "fullname": user.fullname
                }
            }
            
    except SQLAlchemyError as e:
        # Database connection or SQL-related errors
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"[AUTH] Database error during login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable"
        )
    except Exception as e:
        # Check if it's a connection error (asyncpg, psycopg2, etc.)
        error_str = str(e).lower()
        if any(keyword in error_str for keyword in ["connection", "connect", "database", "server"]):
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"[AUTH] Database connection error during login: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database unavailable"
            )
        # For other exceptions, re-raise to let middleware handle
        raise

@router.post("/signup")
async def signup(user_data: UserCreate):
    """
    Create new user account
    """
    try:
        async with async_session() as db:
            # Check if user already exists by email
            stmt = select(User).where(User.email == user_data.email)
            result = await db.execute(stmt)
            existing_user = result.scalar_one_or_none()

            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User with this email already exists"
                )

            # Check if mobile number already exists (if provided)
            if user_data.mobile:
                stmt = select(User).where(User.mobile == user_data.mobile)
                result = await db.execute(stmt)
                existing_mobile = result.scalar_one_or_none()

                if existing_mobile:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="User with this mobile number already exists"
                    )

            # Hash password
            hashed_password = bcrypt.hashpw(
                user_data.password.encode('utf-8'),
                bcrypt.gensalt()
            ).decode('utf-8')

            # Create new user (id will be auto-generated by the model default)
            new_user = User(
                email=user_data.email,
                password_hash=hashed_password,
                role="user",
                fullname=user_data.fullname,
                mobile=user_data.mobile
            )

            db.add(new_user)
            await db.commit()
            await db.refresh(new_user)

            return {
                "message": "User created successfully",
                "user": {
                    "id": str(new_user.id),
                    "email": new_user.email,
                    "role": new_user.role,
                    "fullname": new_user.fullname
                }
            }
            
    except SQLAlchemyError as e:
        # Database connection or SQL-related errors
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"[AUTH] Database error during signup: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable"
        )
    except Exception as e:
        # Check if it's a connection error (asyncpg, psycopg2, etc.)
        error_str = str(e).lower()
        if any(keyword in error_str for keyword in ["connection", "connect", "database", "server"]):
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"[AUTH] Database connection error during signup: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database unavailable"
            )
        # For other exceptions, re-raise to let middleware handle
        raise

@router.get("/verify")
async def verify_token(current_user: dict = Depends(get_current_user)):
    """
    Verify JWT token and return user info
    """
    return {
        "valid": True,
        "user": current_user
    }

@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    """
    Get current user information
    """
    return {"user": current_user}

@router.post("/forgot-password")
async def forgot_password(body: dict):
    """
    Request password reset - sends reset instructions
    In production, this would send an email with reset link
    For development, it returns a temporary reset token
    """
    import logging
    logger = logging.getLogger(__name__)
    
    email = body.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is required"
        )
    
    async with async_session() as db:
        # Find user by email
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            # For security, don't reveal if email exists or not
            return {
                "message": "If the email exists in our system, you will receive password reset instructions shortly."
            }
        
        logger.info(f"[AUTH] Password reset requested for: {email}")
        
        # In production, you would:
        # 1. Generate a secure reset token
        # 2. Store it in database with expiration time
        # 3. Send email with reset link
        
        # For development, return success message
        return {
            "message": "If the email exists in our system, you will receive password reset instructions shortly.",
            "dev_note": "In development mode - password reset functionality would send email in production"
        }

@router.post("/reset-password")
async def reset_password(body: dict):
    """
    Reset password with token (production would use secure token)
    For development, this allows direct password reset by email
    """
    import logging
    logger = logging.getLogger(__name__)
    
    email = body.get("email") 
    new_password = body.get("new_password")
    reset_token = body.get("reset_token", "dev-token")  # In prod, this would be required
    
    if not email or not new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and new password are required"
        )
    
    if len(new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters"
        )
    
    async with async_session() as db:
        # Find user by email
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Hash new password
        new_hash = bcrypt.hashpw(
            new_password.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')
        
        # Update user password
        user.password_hash = new_hash
        await db.commit()
        
        logger.info(f"[AUTH] Password reset successful for: {email}")
        
        return {
            "message": "Password reset successful. You can now log in with your new password."
        }


# ============= DEV-ONLY DEBUG ENDPOINTS =============

@router.get("/debug/db")
async def debug_database():
    """
    DEBUG ENDPOINT - Development only!
    Returns database diagnostic information.
    
    Returns 404 in production environment.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Check environment
    if settings.is_production:
        logger.warning(f"[SECURITY] Someone tried to access debug endpoint from production")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endpoint not found"
        )
    
    logger.info(f"[DEBUG] DB debug endpoint accessed from {settings.env} environment")
    
    async with async_session() as db:
        try:
            # Get current database
            result = await db.execute(text("SELECT current_database()"))
            current_db = result.scalar_one_or_none()
            
            # Get user count
            result = await db.execute(text("SELECT COUNT(*) FROM users"))
            user_count = result.scalar_one_or_none()
            
            # Get first 3 emails
            result = await db.execute(text("SELECT id, email, password_hash FROM users LIMIT 3"))
            users = result.fetchall()
            
            # Get schema info for users table
            result = await db.execute(text("""
                SELECT column_name, data_type, is_nullable 
                FROM information_schema.columns 
                WHERE table_name='users' 
                ORDER BY ordinal_position
            """))
            schema_info = result.fetchall()
            
            return {
                "environment": settings.env,
                "database": {
                    "name": current_db,
                    "host": settings.database_host,
                    "port": settings.database_port,
                    "url": settings.masked_database_url
                },
                "users_table": {
                    "total_count": user_count,
                    "schema": [
                        {"column": row[0], "type": row[1], "nullable": row[2]}
                        for row in schema_info
                    ],
                    "sample_users": [
                        {
                            "id": str(u[0]),
                            "email": u[1],
                            "password_hash_preview": u[2][:20] + "..." if u[2] and len(u[2]) > 20 else u[2]
                        }
                        for u in users
                    ]
                }
            }
        except Exception as e:
            logger.error(f"[DEBUG] DB debug error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error: {str(e)}"
            )


@router.post("/debug/reset-password")
async def debug_reset_password(body: dict):
    """
    DEBUG ENDPOINT - Development only!
    Reset password for a user (bcrypt hash the new password).
    
    Returns 404 in production environment.
    
    Body: { "email": "...", "new_password": "..." }
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Check environment
    if settings.is_production:
        logger.warning(f"[SECURITY] Someone tried to access reset-password endpoint from production")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endpoint not found"
        )
    
    # Validate input
    email = body.get("email")
    new_password = body.get("new_password")
    
    if not email or not new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both email and new_password are required"
        )
    
    logger.info(f"[DEBUG] Password reset requested for: {email}")
    
    async with async_session() as db:
        try:
            # Find user
            stmt = select(User).where(User.email == email)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Hash new password
            new_hash = bcrypt.hashpw(
                new_password.encode('utf-8'),
                bcrypt.gensalt()
            ).decode('utf-8')
            
            # Update user
            user.password_hash = new_hash
            await db.commit()
            
            logger.info(f"[DEBUG] Password reset successful for: {email}")
            
            return {
                "success": True,
                "message": f"Password reset successful for {email}",
                "new_hash_preview": new_hash[:30] + "...",
                "note": "This endpoint is only available in development"
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"[DEBUG] Password reset error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Reset error: {str(e)}"
            )
