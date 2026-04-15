from __future__ import annotations

from uuid import UUID
from sqlalchemy import String, cast, text
from sqlalchemy.ext.asyncio import AsyncSession


def as_uuid_or_str(value):
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except Exception:
        return str(value)


def column_text(column):
    return cast(column, String)


async def table_has_column(db: AsyncSession, table_name: str, column_name: str) -> bool:
    try:
        bind = db.get_bind()
        dialect = bind.dialect.name if bind is not None else ""
        if dialect == "sqlite":
            result = await db.execute(text(f"PRAGMA table_info({table_name})"))
            return any(row[1] == column_name for row in result.fetchall())
        result = await db.execute(text("""
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = :table_name AND column_name = :column_name
            LIMIT 1
        """), {"table_name": table_name, "column_name": column_name})
        return result.scalar() is not None
    except Exception:
        return False
