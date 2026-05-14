from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_current_user, get_db
from ...db.compat import as_uuid_or_str, column_text, table_has_column
from ...db.models import StrategyRequest
from ...schemas.strategy_requests import StrategyRequestCreate
from ...utils.api_response import success_response

router = APIRouter()


def _serialize(req: StrategyRequest) -> dict:
    return {
        "id": str(req.id),
        "user_id": str(req.user_id),
        "title": req.title,
        "name": req.title,
        "strategy_type": req.strategy_type,
        "strategyType": req.strategy_type,
        "market": req.market,
        "timeframe": req.timeframe,
        "indicators": req.indicators,
        "entry_rules": req.entry_rules,
        "exit_rules": req.exit_rules,
        "risk_rules": req.risk_rules,
        "confirmation_rules": getattr(req, "confirmation_rules", None),
        "invalidation_rules": getattr(req, "invalidation_rules", None),
        "trade_management_rules": getattr(req, "trade_management_rules", None),
        "notes": req.notes,
        "attachments": [],
        "attachment_count": 0,
        "attachmentCount": 0,
        "description": req.notes or req.entry_rules,
        "status": req.status,
        "admin_notes": req.admin_notes,
        "assigned_to": str(req.assigned_to) if getattr(req, "assigned_to", None) else None,
        "deployed_strategy_id": str(req.deployed_strategy_id) if getattr(req, "deployed_strategy_id", None) else None,
        "deployedStrategyId": str(req.deployed_strategy_id) if getattr(req, "deployed_strategy_id", None) else None,
        "created_at": req.created_at.isoformat() if req.created_at else None,
        "updated_at": req.updated_at.isoformat() if req.updated_at else None,
        "lastUpdated": req.updated_at.isoformat() if req.updated_at else (req.created_at.isoformat() if req.created_at else None),
    }


async def _create_request_row(
    db: AsyncSession,
    *,
    user_id: UUID,
    title: str,
    strategy_type: str | None,
    market: str | None,
    timeframe: str | None,
    indicators: dict | None,
    entry_rules: str,
    exit_rules: str,
    risk_rules: str,
    confirmation_rules: str | None = None,
    invalidation_rules: str | None = None,
    trade_management_rules: str | None = None,
    notes: str | None = None,
) -> StrategyRequest:
    request_id = uuid4()
    has_legacy_strategy_name = await table_has_column(db, "strategy_requests", "strategy_name")
    has_legacy_strategy_description = await table_has_column(db, "strategy_requests", "strategy_description")

    if has_legacy_strategy_name or has_legacy_strategy_description:
        columns = [
            "id",
            "user_id",
            "title",
            "strategy_type",
            "market",
            "timeframe",
            "indicators",
            "entry_rules",
            "exit_rules",
            "risk_rules",
            "confirmation_rules",
            "invalidation_rules",
            "trade_management_rules",
            "notes",
            "status",
        ]
        values: dict = {
            "id": request_id,
            "user_id": user_id,
            "title": title,
            "strategy_type": strategy_type,
            "market": market,
            "timeframe": timeframe,
            "indicators": indicators,
            "entry_rules": entry_rules,
            "exit_rules": exit_rules,
            "risk_rules": risk_rules,
            "confirmation_rules": confirmation_rules,
            "invalidation_rules": invalidation_rules,
            "trade_management_rules": trade_management_rules,
            "notes": notes,
            "status": "UNDER_DEVELOPMENT",
        }

        if has_legacy_strategy_name:
            columns.append("strategy_name")
            values["strategy_name"] = title

        if has_legacy_strategy_description:
            columns.append("strategy_description")
            values["strategy_description"] = notes or entry_rules

        columns_sql = ", ".join(columns)
        values_sql = ", ".join(f":{column}" for column in columns)

        await db.execute(
            text(f"INSERT INTO strategy_requests ({columns_sql}) VALUES ({values_sql})"),
            values,
        )
        await db.commit()

        return (
            await db.execute(
                select(StrategyRequest).where(column_text(StrategyRequest.id) == str(request_id))
            )
        ).scalar_one()

    row = StrategyRequest(
        id=request_id,
        user_id=user_id,
        title=title,
        strategy_type=strategy_type,
        market=market,
        timeframe=timeframe,
        indicators=indicators,
        entry_rules=entry_rules,
        exit_rules=exit_rules,
        risk_rules=risk_rules,
        confirmation_rules=getattr(request_data, "confirmation_rules", None),
        invalidation_rules=getattr(request_data, "invalidation_rules", None),
        trade_management_rules=getattr(request_data, "trade_management_rules", None),
        notes=notes,
        status="UNDER_DEVELOPMENT",
    )

    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_strategy_request(request_data: StrategyRequestCreate, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    row = await _create_request_row(
        db,
        user_id=as_uuid_or_str(current_user["user_id"]),
        title=request_data.title.strip(),
        strategy_type=(request_data.strategy_type or "").strip() or None,
        market=(request_data.market or "").strip() or None,
        timeframe=(request_data.timeframe or "").strip() or None,
        indicators=request_data.indicators,
        entry_rules=request_data.entry_rules.strip(),
        exit_rules=request_data.exit_rules.strip(),
        risk_rules=request_data.risk_rules.strip(),
        notes=(request_data.notes or "").strip() or None,
    )

    return success_response(_serialize(row), "Strategy request submitted successfully")


@router.get("/me")
async def get_user_strategy_requests(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(StrategyRequest).where(column_text(StrategyRequest.user_id) == str(current_user["user_id"])).order_by(StrategyRequest.created_at.desc()))).scalars().all()
    data = [_serialize(r) for r in rows]
    return success_response(data, "No data found" if not data else None)