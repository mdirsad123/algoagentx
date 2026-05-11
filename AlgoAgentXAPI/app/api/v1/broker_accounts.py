from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
import secrets
from uuid import UUID
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_current_user, get_db
from ...core.config import settings
from ...db.models import BrokerAccount, BrokerProvider, BrokerOAuthState, StrategyDeployment
from ...schemas.live_trading import BrokerAccountCreate, BrokerAccountOut, BrokerAccountUpdate, BrokerProviderOut, UpstoxBrokerAccountCreate
from ...services.brokers.factory import get_broker_adapter
from ...services.brokers.upstox import UpstoxAdapter
from ...utils.api_response import success_response
from ...utils.credential_crypto import encrypt_credential
from .live_common import dump_list, dump_one, get_broker_account_or_404, is_admin, user_id_from

router = APIRouter()


BROKER_STATUS_CONNECTED = "CONNECTED"
BROKER_STATUS_DISCONNECTED = "DISCONNECTED"
BROKER_STATUS_ERROR = "ERROR"
BROKER_STATUS_PENDING_AUTH = "PENDING_AUTH"
BROKER_STATUS_AGENT_OFFLINE = "AGENT_OFFLINE"
BROKER_STATUS_COMING_SOON = "COMING_SOON"
CRYPTO_BROKER_CODES = {"BINANCE", "BYBIT", "OKX"}
ACTIVE_DEPLOYMENT_STATUSES = {"RUNNING", "PAUSED", "DRAFT", "PENDING", "APPROVED"}


def _safe_message(message: str | None) -> str:
    text = str(message or "").strip()
    lower = text.lower()
    if "metatrader5" in lower or "python package" in lower or "terminal is not available" in lower:
        return "MT5 Agent is not connected. Please start AlgoAgentX MT5 Agent on your Windows PC or VPS."
    if "unsupported broker adapter" in lower:
        return "This broker is prepared but connection is not implemented yet."
    return text or "Broker connection check completed."


def _standard_status_for(row: BrokerAccount, connected: bool, message: str | None = None) -> str:
    code = str(row.broker_code or row.broker_name or "").upper()
    lower = str(message or "").lower()
    if connected:
        return BROKER_STATUS_CONNECTED
    if code == "MT5" and ("agent" in lower or "terminal" in lower or "heartbeat" in lower):
        return BROKER_STATUS_AGENT_OFFLINE
    if code == "UPSTOX" and ("missing" in lower or "expired" in lower or "reconnect" in lower or "token" in lower):
        return BROKER_STATUS_PENDING_AUTH
    if "coming soon" in lower or "not implemented" in lower:
        return BROKER_STATUS_COMING_SOON
    return BROKER_STATUS_ERROR


def _connection_payload(result) -> dict:
    return {
        "connected": bool(result.connected),
        "message": result.message,
        "account_login": result.account_login,
        "server": result.server,
        "balance": str(result.balance) if result.balance is not None else None,
        "equity": str(result.equity) if result.equity is not None else None,
        "currency": result.currency,
        "raw": result.raw,
    }


def _frontend_url(path: str) -> str:
    base = (settings.web_origin or "http://localhost:3000").rstrip("/")
    if not path.startswith("/"):
        path = "/" + path
    return base + path


def _upstox_expiry_from_payload(payload: dict) -> datetime:
    raw = payload.get("expires_at") or payload.get("expires_in")
    if raw:
        try:
            text = str(raw).strip()
            if text.isdigit():
                ts = int(text)
                if ts > 10_000_000_000:
                    ts = ts / 1000
                if ts > 100_000:
                    return datetime.fromtimestamp(ts, tz=timezone.utc)
                return datetime.now(timezone.utc) + timedelta(seconds=ts)
        except Exception:
            pass
    now_utc = datetime.now(timezone.utc)
    ist_now = now_utc + timedelta(hours=5, minutes=30)
    expiry_ist = datetime.combine(ist_now.date(), time(3, 30), tzinfo=timezone.utc)
    if ist_now.time() >= time(3, 30):
        expiry_ist = expiry_ist + timedelta(days=1)
    return expiry_ist - timedelta(hours=5, minutes=30)


def _safe_upstox_profile(payload: dict) -> dict:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    return UpstoxAdapter.safe_profile(data if isinstance(data, dict) else {})


async def _upstox_provider_or_400(db: AsyncSession) -> BrokerProvider:
    provider = (await db.execute(select(BrokerProvider).where(BrokerProvider.code == "UPSTOX"))).scalar_one_or_none()
    if not provider or not provider.is_enabled:
        raise HTTPException(status_code=400, detail="Upstox provider is disabled")
    return provider


async def _provider_for_payload(db: AsyncSession, values: dict) -> BrokerProvider | None:
    provider = None
    if values.get("broker_provider_id"):
        provider = (await db.execute(select(BrokerProvider).where(BrokerProvider.id == values["broker_provider_id"]))).scalar_one_or_none()
    elif values.get("broker_code") or values.get("broker_name"):
        code = str(values.get("broker_code") or values.get("broker_name") or "").upper().strip()
        provider = (await db.execute(select(BrokerProvider).where(BrokerProvider.code == code))).scalar_one_or_none()
    if provider and not provider.is_enabled:
        raise HTTPException(status_code=400, detail="Broker provider is disabled")
    return provider


@router.get("/providers/available")
async def list_available_broker_providers(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    rows = (await db.execute(select(BrokerProvider).where(BrokerProvider.is_enabled == True).order_by(BrokerProvider.code.asc()))).scalars().all()
    return success_response(dump_list(BrokerProviderOut, rows))


@router.post("/upstox", status_code=status.HTTP_201_CREATED)
async def create_upstox_byo_account(payload: UpstoxBrokerAccountCreate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    provider = await _upstox_provider_or_400(db)
    row = BrokerAccount(
        user_id=user_id_from(current_user),
        broker_provider_id=provider.id,
        broker_name="UPSTOX",
        broker_code="UPSTOX",
        auth_type="OAUTH2",
        account_label=payload.account_label,
        mode="DEMO",
        status="DISCONNECTED",
        server_name="Upstox API v2",
        oauth_client_id=payload.client_id.strip(),
        encrypted_client_secret=encrypt_credential(payload.client_secret.strip()),
        oauth_redirect_uri=payload.redirect_uri.strip(),
        metadata_json={"provider": "UPSTOX", "market": "INDIAN_EQUITY", "credential_mode": "BYO", "safe_message": "OAuth credentials saved; complete Upstox login."},
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return success_response(dump_one(BrokerAccountOut, row), "Upstox account created")


@router.get("/upstox/connect-url")
async def get_upstox_platform_connect_url(redirect_after: str | None = "/brokers", db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    await _upstox_provider_or_400(db)
    try:
        state_value = secrets.token_urlsafe(32)
        auth_url = UpstoxAdapter().build_login_url(state_value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    row = BrokerOAuthState(user_id=user_id_from(current_user), broker_provider_code="UPSTOX", state=state_value, redirect_after=redirect_after or "/brokers", expires_at=datetime.now(timezone.utc) + timedelta(minutes=15))
    db.add(row)
    await db.commit()
    return success_response({"auth_url": auth_url, "state": state_value, "broker_account_id": None})


@router.get("/{broker_account_id}/upstox/connect-url")
async def get_upstox_account_connect_url(broker_account_id: UUID, redirect_after: str | None = "/brokers", db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    await _upstox_provider_or_400(db)
    account = await get_broker_account_or_404(db, broker_account_id, current_user)
    if str(account.broker_code or account.broker_name).upper() != "UPSTOX":
        raise HTTPException(status_code=400, detail="Broker account is not an Upstox account")
    try:
        state_value = secrets.token_urlsafe(32)
        auth_url = UpstoxAdapter(account).build_login_url(state_value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    row = BrokerOAuthState(user_id=account.user_id, broker_provider_code="UPSTOX", broker_account_id=account.id, state=state_value, redirect_after=redirect_after or "/brokers", expires_at=datetime.now(timezone.utc) + timedelta(minutes=15))
    db.add(row)
    await db.commit()
    return success_response({"auth_url": auth_url, "state": state_value, "broker_account_id": str(account.id)})


@router.get("/upstox/callback")
async def upstox_oauth_callback(code: str | None = None, state: str | None = None, error: str | None = None, db: AsyncSession = Depends(get_db)):
    redirect_base = "/brokers"
    if error:
        return RedirectResponse(_frontend_url(f"{redirect_base}?broker=upstox&connected=false&error={error}"), status_code=302)
    if not code or not state:
        return RedirectResponse(_frontend_url(f"{redirect_base}?broker=upstox&connected=false&error=missing_code_or_state"), status_code=302)
    state_row = (await db.execute(select(BrokerOAuthState).where(BrokerOAuthState.state == state))).scalar_one_or_none()
    if not state_row or state_row.broker_provider_code != "UPSTOX":
        return RedirectResponse(_frontend_url(f"{redirect_base}?broker=upstox&connected=false&error=invalid_state"), status_code=302)
    redirect_base = state_row.redirect_after or "/brokers"
    now = datetime.now(timezone.utc)
    expires_at = state_row.expires_at.replace(tzinfo=timezone.utc) if state_row.expires_at.tzinfo is None else state_row.expires_at
    if state_row.consumed_at is not None or expires_at < now:
        return RedirectResponse(_frontend_url(f"{redirect_base}?broker=upstox&connected=false&error=expired_state"), status_code=302)
    provider = (await db.execute(select(BrokerProvider).where(BrokerProvider.code == "UPSTOX"))).scalar_one_or_none()
    if not provider or not provider.is_enabled:
        return RedirectResponse(_frontend_url(f"{redirect_base}?broker=upstox&connected=false&error=provider_disabled"), status_code=302)
    try:
        account = None
        if state_row.broker_account_id:
            account = (await db.execute(select(BrokerAccount).where(BrokerAccount.id == state_row.broker_account_id))).scalar_one_or_none()
            if not account:
                return RedirectResponse(_frontend_url(f"{redirect_base}?broker=upstox&connected=false&error=account_not_found"), status_code=302)
        adapter = UpstoxAdapter(account)
        token_payload = await adapter.exchange_code_for_token(code)
        profile = _safe_upstox_profile(token_payload)
        access_token = token_payload.get("access_token")
        refresh_token = token_payload.get("refresh_token")
        token_expires_at = _upstox_expiry_from_payload(token_payload)
        user_login = str(profile.get("user_id") or profile.get("email") or "UPSTOX")
        if not account:
            account = (await db.execute(select(BrokerAccount).where(BrokerAccount.user_id == state_row.user_id, BrokerAccount.broker_code == "UPSTOX").order_by(BrokerAccount.created_at.desc()))).scalars().first()
        if not account:
            account = BrokerAccount(user_id=state_row.user_id, broker_provider_id=provider.id, broker_name="UPSTOX", broker_code="UPSTOX", auth_type="OAUTH2", account_label="Upstox India", mode="DEMO")
        account.broker_provider_id = provider.id
        account.broker_name = "UPSTOX"
        account.broker_code = "UPSTOX"
        account.auth_type = "OAUTH2"
        account.status = "CONNECTED"
        account.server_name = "Upstox API v2"
        account.login_id = user_login
        account.encrypted_token = encrypt_credential(str(access_token))
        account.encrypted_refresh_token = encrypt_credential(str(refresh_token)) if refresh_token else account.encrypted_refresh_token
        account.token_expires_at = token_expires_at
        account.last_connected_at = now
        account.metadata_json = {**(account.metadata_json or {}), "provider": "UPSTOX", "market": "INDIAN_EQUITY", "profile": profile, "token_type": token_payload.get("token_type"), "connected_at": now.isoformat(), "safe_message": "Upstox OAuth connected"}
        db.add(account)
        state_row.consumed_at = now
        await db.commit()
        return RedirectResponse(_frontend_url(f"{redirect_base}?broker=upstox&connected=true"), status_code=302)
    except Exception as exc:
        state_row.consumed_at = now
        await db.commit()
        safe_error = urlencode({"error": str(exc)[:180]})
        return RedirectResponse(_frontend_url(f"{redirect_base}?broker=upstox&connected=false&{safe_error}"), status_code=302)


@router.get("")
async def list_broker_accounts(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    stmt = select(BrokerAccount).order_by(BrokerAccount.created_at.desc())
    if not is_admin(current_user):
        stmt = stmt.where(BrokerAccount.user_id == user_id_from(current_user))
    rows = (await db.execute(stmt)).scalars().all()
    return success_response(dump_list(BrokerAccountOut, rows))


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_broker_account(payload: BrokerAccountCreate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    values = payload.model_dump()
    provider = await _provider_for_payload(db, values)
    if provider:
        values["broker_provider_id"] = provider.id
        values["broker_name"] = provider.code
        values["broker_code"] = provider.code
        values["auth_type"] = provider.auth_type
    values["broker_name"] = str(values.get("broker_name") or values.get("broker_code") or "MT5").upper()
    values["broker_code"] = str(values.get("broker_code") or values["broker_name"]).upper()
    values["auth_type"] = str(values.get("auth_type") or ("MT5_AGENT" if values["broker_code"] == "MT5" else "OAUTH2")).upper()
    if values["broker_code"] in CRYPTO_BROKER_CODES:
        values["auth_type"] = "API_KEY_SECRET"
        values["mode"] = "DEMO"
        values["server_name"] = values.get("server_name") or f"{values['broker_code']} API"
        values["login_id"] = "API key saved"
        values["oauth_client_id"] = None
        if values["broker_code"] == "OKX" and not values.get("encrypted_api_passphrase"):
            raise HTTPException(status_code=400, detail="OKX API Passphrase is required")
    if values.get("mode") == "LIVE" and not (provider and getattr(provider, "is_live_enabled", False)):
        values["mode"] = "DEMO"
    values["status"] = values.get("status") or (BROKER_STATUS_PENDING_AUTH if values["broker_code"] == "UPSTOX" else BROKER_STATUS_DISCONNECTED)
    for secret_key in ("encrypted_password", "encrypted_token", "encrypted_refresh_token", "encrypted_client_secret", "encrypted_api_key", "encrypted_api_secret", "encrypted_api_passphrase"):
        if values.get(secret_key):
            values[secret_key] = encrypt_credential(values.get(secret_key))
    row = BrokerAccount(user_id=user_id_from(current_user), **values)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return success_response(dump_one(BrokerAccountOut, row), "Broker account created")


@router.get("/{broker_account_id}")
async def get_broker_account(broker_account_id: UUID, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    row = await get_broker_account_or_404(db, broker_account_id, current_user)
    return success_response(dump_one(BrokerAccountOut, row))


@router.patch("/{broker_account_id}")
async def update_broker_account(broker_account_id: UUID, payload: BrokerAccountUpdate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    row = await get_broker_account_or_404(db, broker_account_id, current_user)
    values = payload.model_dump(exclude_unset=True)
    provider = await _provider_for_payload(db, values) if (values.get("broker_provider_id") or values.get("broker_code") or values.get("broker_name")) else None
    if provider:
        values["broker_provider_id"] = provider.id
        values["broker_name"] = provider.code
        values["broker_code"] = provider.code
        values["auth_type"] = provider.auth_type
    active_code = str(values.get("broker_code") or row.broker_code or row.broker_name or "").upper()
    if active_code in CRYPTO_BROKER_CODES:
        values["auth_type"] = "API_KEY_SECRET"
        values["mode"] = "DEMO"
        values["server_name"] = values.get("server_name") or f"{active_code} API"
        values["login_id"] = "API key saved"
        values["oauth_client_id"] = None
        if active_code == "OKX" and not row.encrypted_api_passphrase and not values.get("encrypted_api_passphrase"):
            raise HTTPException(status_code=400, detail="OKX API Passphrase is required")
    for secret_key in ("encrypted_password", "encrypted_token", "encrypted_refresh_token", "encrypted_client_secret", "encrypted_api_key", "encrypted_api_secret", "encrypted_api_passphrase"):
        if values.get(secret_key) in {None, ""}:
            values.pop(secret_key, None)
        elif values.get(secret_key):
            values[secret_key] = encrypt_credential(values.get(secret_key))
    if values.get("broker_name"):
        values["broker_name"] = str(values["broker_name"]).upper()
    if values.get("broker_code"):
        values["broker_code"] = str(values["broker_code"]).upper()
    for key, value in values.items():
        setattr(row, key, value)
    if row.mode == "LIVE":
        row.mode = "DEMO"
    await db.commit()
    await db.refresh(row)
    return success_response(dump_one(BrokerAccountOut, row), "Broker account updated")


@router.delete("/{broker_account_id}")
async def delete_broker_account(
    broker_account_id: UUID,
    force: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    row = await get_broker_account_or_404(db, broker_account_id, current_user)
    active_rows = (await db.execute(
        select(StrategyDeployment)
        .where(StrategyDeployment.broker_account_id == row.id)
        .where(StrategyDeployment.status.in_(ACTIVE_DEPLOYMENT_STATUSES))
        .order_by(StrategyDeployment.created_at.desc())
        .limit(5)
    )).scalars().all()
    if active_rows and not force:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "This broker is used by active live deployments. Stop or move those deployments before deleting, or confirm force delete.",
                "requires_confirmation": True,
                "active_deployments": [
                    {"id": str(item.id), "name": item.name, "status": item.status, "instrument": item.instrument}
                    for item in active_rows
                ],
            },
        )
    # Safe delete: clear sensitive fields before removing the account row. Credentials are never returned to the frontend.
    row.encrypted_password = None
    row.encrypted_token = None
    row.encrypted_refresh_token = None
    row.encrypted_client_secret = None
    if hasattr(row, "encrypted_api_key"):
        row.encrypted_api_key = None
    if hasattr(row, "encrypted_api_secret"):
        row.encrypted_api_secret = None
    if hasattr(row, "encrypted_api_passphrase"):
        row.encrypted_api_passphrase = None
    await db.delete(row)
    await db.commit()
    return success_response({"id": str(broker_account_id), "forced": force}, "Broker account deleted")


@router.post("/{broker_account_id}/test")
async def test_broker_connection(broker_account_id: UUID, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    row = await get_broker_account_or_404(db, broker_account_id, current_user)
    try:
        adapter = get_broker_adapter(row, db)
        result = await adapter.test_connection()
        result.message = _safe_message(result.message)
    except Exception as exc:
        from ...services.brokers.base import BrokerConnectionResult
        result = BrokerConnectionResult(False, _safe_message(str(exc)), account_login=row.login_id, server=row.server_name, raw={"broker_code": row.broker_code or row.broker_name})
    payload = _connection_payload(result)
    row.status = _standard_status_for(row, result.connected, result.message)
    if result.connected:
        row.last_connected_at = datetime.now(timezone.utc)
    existing_meta = row.metadata_json or {}
    row.metadata_json = {**existing_meta, "last_test": payload, "provider": row.broker_code or row.broker_name, "safe_message": result.message}
    if hasattr(row, "last_connection_result"):
        row.last_connection_result = payload
    await db.commit()
    await db.refresh(row)
    return success_response({"broker_account": dump_one(BrokerAccountOut, row), "connection": payload}, "Broker connection tested")


@router.get("/{broker_account_id}/account-info")
async def get_broker_account_info(broker_account_id: UUID, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    row = await get_broker_account_or_404(db, broker_account_id, current_user)
    adapter = get_broker_adapter(row, db)
    info = await adapter.get_account_info()
    return success_response(info)


@router.get("/{broker_account_id}/symbols")
async def list_broker_symbols(broker_account_id: UUID, query: str | None = None, limit: int = 200, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    row = await get_broker_account_or_404(db, broker_account_id, current_user)
    adapter = get_broker_adapter(row, db)
    symbols = await adapter.get_symbols(query=query, limit=limit)
    return success_response(symbols)


@router.get("/{broker_account_id}/positions")
async def get_broker_positions(broker_account_id: UUID, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    row = await get_broker_account_or_404(db, broker_account_id, current_user)
    adapter = get_broker_adapter(row, db)
    positions = await adapter.get_positions()
    return success_response(positions)
