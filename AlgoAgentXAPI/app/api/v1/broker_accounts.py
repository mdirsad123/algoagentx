from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
import secrets
from uuid import UUID
from decimal import Decimal
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_current_user, get_db
from ...core.config import settings
from ...db.models import BrokerAccount, BrokerProvider, BrokerOAuthState, StrategyDeployment, BrokerInstrument, BrokerOrderExecutionLog
from ...schemas.live_trading import BrokerAccountCreate, BrokerAccountOut, BrokerAccountUpdate, BrokerProviderOut, UpstoxBrokerAccountCreate
from ...services.brokers.factory import get_broker_adapter
from ...services.brokers.upstox import UpstoxAdapter
from ...services.brokers.ctrader import CTraderAdapter
from ...utils.api_response import success_response
from ...utils.credential_crypto import encrypt_credential
from .live_common import dump_list, dump_one, get_broker_account_or_404, is_admin, user_id_from

router = APIRouter()


BROKER_STATUS_CONNECTED = "CONNECTED"
BROKER_STATUS_DISCONNECTED = "DISCONNECTED"
BROKER_STATUS_ERROR = "ERROR"
BROKER_STATUS_PENDING_AUTH = "PENDING_AUTH"
BROKER_STATUS_AGENT_OFFLINE = "AGENT_OFFLINE"
BROKER_STATUS_PENDING_ACCOUNT_SYNC = "PENDING_ACCOUNT_SYNC"
BROKER_STATUS_COMING_SOON = "COMING_SOON"
CRYPTO_BROKER_CODES = {"BINANCE", "BYBIT", "OKX"}
OAUTH_BROKER_CODES = {"UPSTOX", "CTRADER", "CTRADER_API"}
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




def _broker_redirect_base_url() -> str:
    return str(
        getattr(settings, "broker_redirect_base_url", None)
        or getattr(settings, "public_api_base_url", None)
        or getattr(settings, "api_base_url", None)
        or "http://localhost:8000"
    ).rstrip("/")


def _broker_callback_uri(broker_code: str) -> str:
    code = str(broker_code or "").upper().strip()
    if code == "UPSTOX" and getattr(settings, "upstox_redirect_uri", None):
        return str(settings.upstox_redirect_uri).strip()
    if code in {"CTRADER", "CTRADER_API"} and getattr(settings, "ctrader_redirect_uri", None):
        return str(settings.ctrader_redirect_uri).strip()
    slug = "ctrader" if code in {"CTRADER", "CTRADER_API"} else code.lower()
    return f"{_broker_redirect_base_url()}/api/v1/broker-accounts/{slug}/callback"


def _provider_code_from_path(code: str) -> str:
    normalized = str(code or "").upper().strip().replace("-", "_")
    if normalized == "CTRADER_API":
        return "CTRADER"
    return normalized

def _frontend_url(path: str) -> str:
    base = (settings.web_origin or "http://localhost:3000").rstrip("/")
    if not path.startswith("/"):
        path = "/" + path
    return base + path


def _oauth_redirect(path: str, broker: str, connected: bool, error: str | None = None) -> RedirectResponse:
    params = {"broker": broker.lower(), "connected": "true" if connected else "false"}
    if error:
        params["error"] = _safe_oauth_callback_error(error)
    sep = "&" if "?" in path else "?"
    return RedirectResponse(_frontend_url(f"{path}{sep}{urlencode(params)}"), status_code=302)


def _safe_oauth_callback_error(error: str | None) -> str:
    text = str(error or "").strip()
    lower = text.lower()
    if not text:
        return "OAuth connection failed. Please try again."
    if "redirect" in lower:
        return "Redirect URI mismatch. Use the exact Redirect URI shown in AlgoAgentX inside your broker developer app."
    if "invalid_client" in lower or "client id" in lower or "client secret" in lower or "unauthorized" in lower:
        return "Invalid client ID or client secret. Please verify your broker developer app credentials."
    if "access_denied" in lower or "denied" in lower:
        return "User denied permission. Please approve access to connect your broker account."
    if "expired" in lower or "invalid_grant" in lower:
        return "The authorization code expired. Please reconnect and approve the OAuth request again."
    if "token" in lower:
        return "Token exchange failed. Please check your Client ID, Client Secret, and Redirect URI."
    return text[:220]


async def _refresh_ctrader_token_if_needed(row: BrokerAccount, db: AsyncSession, force: bool = False) -> None:
    code = str(row.broker_code or row.broker_name or "").upper()
    if code not in {"CTRADER", "CTRADER_API"}:
        return
    now = datetime.now(timezone.utc)
    expires_at = row.token_expires_at
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if not force and expires_at and expires_at > now + timedelta(minutes=2):
        return
    if not row.encrypted_refresh_token:
        return
    adapter = CTraderAdapter(row)
    token_payload = await adapter.refresh_access_token()
    access_token = token_payload.get("accessToken") or token_payload.get("access_token")
    refresh_token = token_payload.get("refreshToken") or token_payload.get("refresh_token")
    token_expires_at = CTraderAdapter.token_expiry_from_payload(token_payload)
    if access_token:
        row.encrypted_token = encrypt_credential(str(access_token))
    if refresh_token:
        row.encrypted_refresh_token = encrypt_credential(str(refresh_token))
    if token_expires_at:
        row.token_expires_at = token_expires_at
    row.metadata_json = {**(row.metadata_json or {}), "ctrader_token_refreshed_at": now.isoformat()}
    await db.commit()


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




def _is_ctrader_account(row: BrokerAccount) -> bool:
    return str(row.broker_code or row.broker_name or "").upper() in {"CTRADER", "CTRADER_API"}


def _selected_ctrader_account(row: BrokerAccount) -> dict:
    meta = row.metadata_json or {}
    selected = meta.get("ctrader_selected_account") if isinstance(meta, dict) else None
    return selected if isinstance(selected, dict) else {}


def _ctrader_account_list(meta: dict | None) -> list[dict]:
    value = (meta or {}).get("ctrader_accounts") if isinstance(meta, dict) else None
    return value if isinstance(value, list) else []


def _money_or_none(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except Exception:
        return None


def _ctrader_connection_from_selected(row: BrokerAccount, selected: dict | None = None) -> dict:
    account = selected if isinstance(selected, dict) else _selected_ctrader_account(row)
    return {
        "connected": row.status == BROKER_STATUS_CONNECTED,
        "message": (row.metadata_json or {}).get("safe_message") or "cTrader OAuth connected. Sync account to refresh balance and symbols.",
        "account_login": account.get("account_number") or row.login_id,
        "server": row.server_name,
        "balance": account.get("balance"),
        "equity": account.get("equity"),
        "currency": account.get("currency"),
        "raw": {"provider": "CTRADER", "selected_account": account or None, "orders_enabled": False},
    }


async def _save_ctrader_symbols(db: AsyncSession, symbols: list[dict]) -> int:
    saved = 0
    for item in symbols:
        symbol_name = str(item.get("symbol_name") or item.get("symbol_id") or "").strip().upper()
        if not symbol_name:
            continue
        instrument_key = str(item.get("symbol_id") or symbol_name)
        row = (await db.execute(
            select(BrokerInstrument).where(
                BrokerInstrument.broker_provider_code == "CTRADER",
                BrokerInstrument.instrument_key == instrument_key,
            )
        )).scalar_one_or_none()
        if not row:
            row = BrokerInstrument(
                broker_provider_code="CTRADER",
                exchange="CTRADER",
                trading_symbol=symbol_name,
                instrument_key=instrument_key,
                segment="FOREX_CFD",
            )
            db.add(row)
        row.trading_symbol = symbol_name
        row.name = symbol_name
        row.exchange = "CTRADER"
        row.segment = "FOREX_CFD"
        row.tick_size = item.get("tick_size")
        row.lot_size = int(float(item.get("volume_step") or 1)) if item.get("volume_step") not in (None, "") else row.lot_size
        row.is_active = True
        row.metadata_json = {
            "symbol_id": item.get("symbol_id"),
            "base_asset": item.get("base_asset"),
            "quote_asset": item.get("quote_asset"),
            "pip_size": item.get("pip_size"),
            "tick_size": item.get("tick_size"),
            "min_volume": item.get("min_volume"),
            "max_volume": item.get("max_volume"),
            "volume_step": item.get("volume_step"),
            "raw": item.get("raw"),
        }
        saved += 1
    return saved


def _sanitize_order_payload(payload: dict | None) -> dict:
    blocked = {"token", "access_token", "refresh_token", "secret", "client_secret", "password", "api_secret"}
    clean: dict = {}
    for key, value in (payload or {}).items():
        clean[key] = "***" if key.lower() in blocked else value
    return clean


def _is_demo_ctrader_selected(selected: dict | None, row: BrokerAccount) -> bool:
    mode = str((selected or {}).get("account_type") or row.mode or settings.ctrader_env or "DEMO").upper()
    return "LIVE" not in mode and mode != "REAL"


async def _find_ctrader_symbol_meta(db: AsyncSession, symbol: str, row: BrokerAccount) -> dict | None:
    clean = str(symbol or "").strip().upper()
    if not clean:
        return None
    meta = row.metadata_json or {}
    preview = meta.get("ctrader_symbols_preview") if isinstance(meta, dict) else None
    if isinstance(preview, list):
        for item in preview:
            if not isinstance(item, dict):
                continue
            candidates = [item.get("symbol_name"), item.get("trading_symbol"), item.get("symbol"), item.get("instrument_key"), item.get("symbol_id")]
            if any(str(value or "").upper() == clean for value in candidates):
                return item
    db_symbol = (await db.execute(
        select(BrokerInstrument).where(
            BrokerInstrument.broker_provider_code == "CTRADER",
            func.upper(BrokerInstrument.trading_symbol) == clean,
        )
    )).scalar_one_or_none()
    if db_symbol:
        return {
            "symbol_id": (db_symbol.metadata_json or {}).get("symbol_id") if isinstance(db_symbol.metadata_json, dict) else None,
            "symbol_name": db_symbol.trading_symbol,
            "tick_size": str(db_symbol.tick_size) if db_symbol.tick_size is not None else None,
            "min_volume": (db_symbol.metadata_json or {}).get("min_volume") if isinstance(db_symbol.metadata_json, dict) else None,
            "max_volume": (db_symbol.metadata_json or {}).get("max_volume") if isinstance(db_symbol.metadata_json, dict) else None,
            "volume_step": (db_symbol.metadata_json or {}).get("volume_step") if isinstance(db_symbol.metadata_json, dict) else None,
            "raw": db_symbol.metadata_json or {},
        }
    return None


@router.get("/{broker_code}/redirect-uri")
async def get_broker_redirect_uri(broker_code: str, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    code = _provider_code_from_path(broker_code)
    provider = (await db.execute(select(BrokerProvider).where(BrokerProvider.code == code))).scalar_one_or_none()
    if not provider or not provider.is_enabled:
        raise HTTPException(status_code=404, detail="Broker provider is not available")
    if code not in OAUTH_BROKER_CODES:
        raise HTTPException(status_code=400, detail="This broker does not use OAuth redirect URI setup")
    return success_response({"broker_code": code, "redirect_uri": _broker_callback_uri(code)})


@router.post("/{broker_code}/oauth/initiate")
async def initiate_broker_oauth(
    broker_code: str,
    payload: dict | None = None,
    redirect_after: str | None = "/brokers",
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    code = _provider_code_from_path(broker_code)
    if code not in OAUTH_BROKER_CODES:
        raise HTTPException(status_code=400, detail="This broker does not support OAuth connection")
    provider = (await db.execute(select(BrokerProvider).where(BrokerProvider.code == code))).scalar_one_or_none()
    if not provider or not provider.is_enabled:
        raise HTTPException(status_code=400, detail="Broker provider is disabled")
    payload = payload or {}
    account = None
    broker_account_id = payload.get("broker_account_id") or payload.get("account_id")
    if broker_account_id:
        account = await get_broker_account_or_404(db, UUID(str(broker_account_id)), current_user)
        if str(account.broker_code or account.broker_name or "").upper() not in {code, "CTRADER_API" if code == "CTRADER" else code}:
            raise HTTPException(status_code=400, detail="Broker account does not match selected OAuth provider")
    state_value = secrets.token_urlsafe(32)
    try:
        if code == "UPSTOX":
            auth_url = UpstoxAdapter(account).build_login_url(state_value)
        elif code == "CTRADER":
            auth_url = CTraderAdapter(account).build_login_url(state_value, scope="accounts")
        else:
            raise ValueError("OAuth provider is not implemented yet")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    state_row = BrokerOAuthState(
        user_id=(account.user_id if account else user_id_from(current_user)),
        broker_provider_code=code,
        broker_account_id=(account.id if account else None),
        state=state_value,
        redirect_after=redirect_after or payload.get("redirect_after") or "/brokers",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
    )
    db.add(state_row)
    await db.commit()
    return success_response({"auth_url": auth_url, "state": state_value, "broker_account_id": str(account.id) if account else None})


@router.post("/ctrader/connect")
async def connect_ctrader_oauth(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Create/update a cTrader OAuth broker account and return the cTrader authorization URL.

    Secrets are encrypted at rest and never returned. The redirect URI is generated by the
    backend from BROKER_REDIRECT_BASE_URL / PUBLIC_API_BASE_URL / API_BASE_URL.
    """
    provider = (await db.execute(select(BrokerProvider).where(BrokerProvider.code == "CTRADER"))).scalar_one_or_none()
    if not provider or not provider.is_enabled:
        raise HTTPException(status_code=400, detail="cTrader provider is disabled")

    account_label = str(payload.get("account_label") or "cTrader Open API").strip() or "cTrader Open API"
    client_id = str(payload.get("client_id") or payload.get("oauth_client_id") or "").strip()
    client_secret = str(payload.get("client_secret") or payload.get("encrypted_client_secret") or "").strip()
    redirect_uri = _broker_callback_uri("CTRADER")
    provided_redirect_uri = str(payload.get("redirect_uri") or payload.get("oauth_redirect_uri") or "").strip()
    if provided_redirect_uri and provided_redirect_uri != redirect_uri:
        raise HTTPException(status_code=400, detail="Redirect URI mismatch. Copy the exact cTrader Redirect URI shown by AlgoAgentX into your cTrader Open API application.")
    if not client_id:
        raise HTTPException(status_code=400, detail="cTrader Client ID / API Key is required")
    if not client_secret:
        raise HTTPException(status_code=400, detail="cTrader Client Secret is required")

    account = None
    broker_account_id = payload.get("broker_account_id") or payload.get("account_id")
    if broker_account_id:
        account = await get_broker_account_or_404(db, UUID(str(broker_account_id)), current_user)
        if str(account.broker_code or account.broker_name or "").upper() not in {"CTRADER", "CTRADER_API"}:
            raise HTTPException(status_code=400, detail="Broker account is not a cTrader account")
    if not account:
        account = BrokerAccount(user_id=user_id_from(current_user), broker_provider_id=provider.id, broker_name="CTRADER", broker_code="CTRADER", auth_type="OAUTH2", account_label=account_label, mode="DEMO")

    account.broker_provider_id = provider.id
    account.broker_name = "CTRADER"
    account.broker_code = "CTRADER"
    account.auth_type = "OAUTH2"
    account.account_label = account_label
    account.mode = "DEMO"
    # Keep DISCONNECTED before OAuth for backward compatibility with older DB check constraints.
    # The pending auth state is stored in metadata_json until the safe migration is applied.
    account.status = BROKER_STATUS_DISCONNECTED
    account.server_name = f"cTrader Open API ({str(settings.ctrader_env or 'demo').lower()})"
    account.oauth_client_id = client_id
    account.encrypted_client_secret = encrypt_credential(client_secret)
    account.oauth_redirect_uri = redirect_uri
    account.metadata_json = {**(account.metadata_json or {}), "provider": "CTRADER", "market": "FOREX_CFD", "setup_mode": "OAUTH", "orders_enabled": False, "oauth_status": "PENDING_AUTH", "safe_message": "cTrader credentials saved; complete OAuth authorization."}
    db.add(account)
    await db.flush()

    state_value = secrets.token_urlsafe(32)
    try:
        auth_url = CTraderAdapter(account).build_login_url(state_value, scope="accounts")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    state_row = BrokerOAuthState(
        user_id=account.user_id,
        broker_provider_code="CTRADER",
        broker_account_id=account.id,
        state=state_value,
        redirect_after=str(payload.get("redirect_after") or "/brokers"),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
    )
    db.add(state_row)
    await db.commit()
    await db.refresh(account)
    return success_response({"auth_url": auth_url, "state": state_value, "broker_account_id": str(account.id), "redirect_uri": redirect_uri}, "Open cTrader OAuth to finish connection")


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


@router.get("/ctrader/callback")
async def ctrader_oauth_callback(code: str | None = None, state: str | None = None, error: str | None = None, db: AsyncSession = Depends(get_db)):
    redirect_base = "/brokers"
    if error:
        return _oauth_redirect(redirect_base, "ctrader", False, error)
    if not code or not state:
        return _oauth_redirect(redirect_base, "ctrader", False, "Missing OAuth code or state. Please start the cTrader connection again.")
    state_row = (await db.execute(select(BrokerOAuthState).where(BrokerOAuthState.state == state))).scalar_one_or_none()
    if not state_row or state_row.broker_provider_code not in {"CTRADER", "CTRADER_API"}:
        return _oauth_redirect(redirect_base, "ctrader", False, "Invalid OAuth state. Please reconnect cTrader from AlgoAgentX.")
    redirect_base = state_row.redirect_after or "/brokers"
    now = datetime.now(timezone.utc)
    expires_at = state_row.expires_at.replace(tzinfo=timezone.utc) if state_row.expires_at.tzinfo is None else state_row.expires_at
    if state_row.consumed_at is not None or expires_at < now:
        return _oauth_redirect(redirect_base, "ctrader", False, "The cTrader OAuth session expired. Please reconnect and approve again.")
    provider = (await db.execute(select(BrokerProvider).where(BrokerProvider.code == "CTRADER"))).scalar_one_or_none()
    if not provider or not provider.is_enabled:
        return _oauth_redirect(redirect_base, "ctrader", False, "cTrader provider is disabled")
    try:
        account = None
        if state_row.broker_account_id:
            account = (await db.execute(select(BrokerAccount).where(BrokerAccount.id == state_row.broker_account_id))).scalar_one_or_none()
            if not account:
                return _oauth_redirect(redirect_base, "ctrader", False, "cTrader broker account was not found. Please reconnect.")
        adapter = CTraderAdapter(account)
        token_payload = await adapter.exchange_code_for_token(code)
        access_token = token_payload.get("accessToken") or token_payload.get("access_token")
        refresh_token = token_payload.get("refreshToken") or token_payload.get("refresh_token")
        token_expires_at = CTraderAdapter.token_expiry_from_payload(token_payload)
        if not account:
            account = (await db.execute(select(BrokerAccount).where(BrokerAccount.user_id == state_row.user_id, BrokerAccount.broker_code == "CTRADER").order_by(BrokerAccount.created_at.desc()))).scalars().first()
        if not account:
            account = BrokerAccount(user_id=state_row.user_id, broker_provider_id=provider.id, broker_name="CTRADER", broker_code="CTRADER", auth_type="OAUTH2", account_label="cTrader Open API", mode="DEMO")
        account.broker_provider_id = provider.id
        account.broker_name = "CTRADER"
        account.broker_code = "CTRADER"
        account.auth_type = "OAUTH2"
        account.status = "CONNECTED"
        account.server_name = f"cTrader Open API ({str(settings.ctrader_env or 'demo').lower()})"
        account.login_id = "cTrader ID"
        account.encrypted_token = encrypt_credential(str(access_token))
        account.encrypted_refresh_token = encrypt_credential(str(refresh_token)) if refresh_token else account.encrypted_refresh_token
        account.token_expires_at = token_expires_at
        account.last_connected_at = now
        account.metadata_json = {**(account.metadata_json or {}), "provider": "CTRADER", "market": "FOREX_CFD", "setup_mode": "OAUTH", "orders_enabled": False, "token_type": token_payload.get("tokenType") or token_payload.get("token_type"), "connected_at": now.isoformat(), "sync_status": "PENDING_ACCOUNT_SYNC", "safe_message": "cTrader OAuth connected. Click Sync to fetch trading account, balance, and symbols; order execution disabled in this phase."}
        db.add(account)
        state_row.consumed_at = now
        await db.commit()
        return _oauth_redirect(redirect_base, "ctrader", True)
    except Exception as exc:
        state_row.consumed_at = now
        await db.commit()
        return _oauth_redirect(redirect_base, "ctrader", False, str(exc))


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
    if values["broker_code"] in {"CTRADER", "CTRADER_API"}:
        values["broker_name"] = "CTRADER"
        values["broker_code"] = "CTRADER"
        values["auth_type"] = "OAUTH2"
        values["mode"] = "DEMO"
        values["status"] = values.get("status") or BROKER_STATUS_DISCONNECTED
        values["server_name"] = values.get("server_name") or f"cTrader Open API ({str(settings.ctrader_env or 'demo').lower()})"
        values["oauth_redirect_uri"] = values.get("oauth_redirect_uri") or _broker_callback_uri("CTRADER")
        values["metadata_json"] = {**(values.get("metadata_json") or {}), "provider": "CTRADER", "market": "FOREX_CFD", "setup_mode": "OAUTH", "orders_enabled": False, "oauth_status": "PENDING_AUTH"}
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
    if active_code in {"CTRADER", "CTRADER_API"}:
        values["broker_name"] = "CTRADER"
        values["broker_code"] = "CTRADER"
        values["auth_type"] = "OAUTH2"
        values["mode"] = "DEMO"
        values["status"] = values.get("status") or BROKER_STATUS_DISCONNECTED
        values["server_name"] = values.get("server_name") or f"cTrader Open API ({str(settings.ctrader_env or 'demo').lower()})"
        values["oauth_redirect_uri"] = values.get("oauth_redirect_uri") or _broker_callback_uri("CTRADER")
        values["metadata_json"] = {**(row.metadata_json or {}), **(values.get("metadata_json") or {}), "provider": "CTRADER", "market": "FOREX_CFD", "setup_mode": "OAUTH", "orders_enabled": False, "oauth_status": "PENDING_AUTH"}
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
        await _refresh_ctrader_token_if_needed(row, db)
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



@router.get("/{broker_account_id}/ctrader/accounts")
async def get_ctrader_accounts(broker_account_id: UUID, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    row = await get_broker_account_or_404(db, broker_account_id, current_user)
    if not _is_ctrader_account(row):
        raise HTTPException(status_code=400, detail="Broker account is not a cTrader account")
    try:
        await _refresh_ctrader_token_if_needed(row, db)
        adapter = CTraderAdapter(row)
        accounts = await adapter.fetch_accounts()
        meta = row.metadata_json or {}
        selected = _selected_ctrader_account(row)
        # Auto-select when exactly one account is available.
        if len(accounts) == 1 and not selected:
            selected = accounts[0]
            row.login_id = selected.get("account_number") or selected.get("ctrader_account_id") or row.login_id
            row.status = BROKER_STATUS_CONNECTED
            row.last_connected_at = datetime.now(timezone.utc)
        row.metadata_json = {**meta, "ctrader_accounts": accounts, "ctrader_selected_account": selected or None, "sync_status": "ACCOUNT_SELECTION_REQUIRED" if len(accounts) > 1 and not selected else "ACCOUNT_SYNCED", "safe_message": "cTrader accounts synced." if accounts else "No cTrader trading account found for this OAuth permission."}
        if hasattr(row, "last_connection_result"):
            row.last_connection_result = _ctrader_connection_from_selected(row, selected)
        await db.commit()
        await db.refresh(row)
        return success_response({"broker_account": dump_one(BrokerAccountOut, row), "accounts": accounts, "selected_account": selected or None})
    except Exception as exc:
        row.status = BROKER_STATUS_ERROR
        row.metadata_json = {**(row.metadata_json or {}), "safe_message": _safe_oauth_callback_error(str(exc)), "sync_error": str(exc)}
        await db.commit()
        raise HTTPException(status_code=400, detail=_safe_oauth_callback_error(str(exc))) from exc


@router.post("/{broker_account_id}/ctrader/select-account")
async def select_ctrader_account(broker_account_id: UUID, payload: dict, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    row = await get_broker_account_or_404(db, broker_account_id, current_user)
    if not _is_ctrader_account(row):
        raise HTTPException(status_code=400, detail="Broker account is not a cTrader account")
    account_id = str(payload.get("account_id") or payload.get("ctrader_account_id") or payload.get("account_number") or "").strip()
    if not account_id:
        raise HTTPException(status_code=400, detail="Account selection required")
    accounts = _ctrader_account_list(row.metadata_json)
    selected = None
    for account in accounts:
        if str(account.get("ctrader_account_id") or account.get("account_number")) == account_id:
            selected = account
            break
    if not selected:
        try:
            await _refresh_ctrader_token_if_needed(row, db)
            selected = await CTraderAdapter(row).fetch_account_info(account_id)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=_safe_oauth_callback_error(str(exc))) from exc
    row.login_id = selected.get("account_number") or selected.get("ctrader_account_id") or row.login_id
    row.status = BROKER_STATUS_CONNECTED
    row.last_connected_at = datetime.now(timezone.utc)
    row.metadata_json = {**(row.metadata_json or {}), "ctrader_selected_account": selected, "sync_status": "ACCOUNT_SELECTED", "safe_message": "cTrader trading account selected."}
    if hasattr(row, "last_connection_result"):
        row.last_connection_result = _ctrader_connection_from_selected(row, selected)
    await db.commit()
    await db.refresh(row)
    return success_response({"broker_account": dump_one(BrokerAccountOut, row), "selected_account": selected}, "cTrader account selected")


@router.post("/{broker_account_id}/sync")
async def sync_broker_account(broker_account_id: UUID, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    row = await get_broker_account_or_404(db, broker_account_id, current_user)
    if not _is_ctrader_account(row):
        # Existing non-cTrader brokers keep the safe test behavior.
        adapter = get_broker_adapter(row, db)
        result = await adapter.test_connection()
        payload = _connection_payload(result)
        row.status = _standard_status_for(row, result.connected, result.message)
        row.last_connection_result = payload if hasattr(row, "last_connection_result") else row.last_connection_result
        if result.connected:
            row.last_connected_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(row)
        return success_response({"broker_account": dump_one(BrokerAccountOut, row), "connection": payload}, "Broker synced")
    try:
        await _refresh_ctrader_token_if_needed(row, db)
        adapter = CTraderAdapter(row)
        meta = row.metadata_json or {}
        selected = _selected_ctrader_account(row)
        accounts = _ctrader_account_list(meta)
        if not accounts:
            accounts = await adapter.fetch_accounts()
        if len(accounts) == 1 and not selected:
            selected = accounts[0]
        if not selected and len(accounts) > 1:
            row.status = BROKER_STATUS_CONNECTED
            row.metadata_json = {**meta, "ctrader_accounts": accounts, "sync_status": "ACCOUNT_SELECTION_REQUIRED", "safe_message": "Multiple cTrader accounts found. Select one trading account to sync balance."}
            await db.commit()
            await db.refresh(row)
            return success_response({"broker_account": dump_one(BrokerAccountOut, row), "accounts": accounts, "requires_account_selection": True}, "Select cTrader trading account")
        if not selected:
            raise ValueError("No cTrader account found. Make sure your cTrader Open API app has account permission and reconnect.")
        selected_id = str(selected.get("ctrader_account_id") or selected.get("account_number"))
        try:
            selected = await adapter.fetch_account_info(selected_id)
        except Exception:
            # Some bridges return balance in the account list only; keep existing selected data.
            pass
        symbols = await adapter.fetch_symbols(selected_id)
        saved_symbols = await _save_ctrader_symbols(db, symbols)
        row.status = BROKER_STATUS_CONNECTED
        row.login_id = selected.get("account_number") or selected.get("ctrader_account_id") or row.login_id
        row.last_connected_at = datetime.now(timezone.utc)
        row.metadata_json = {
            **meta,
            "ctrader_accounts": accounts,
            "ctrader_selected_account": selected,
            "ctrader_symbols_synced": saved_symbols,
            "ctrader_symbols_preview": symbols[:25],
            "sync_status": "ACCOUNT_SYNCED",
            "last_sync_at": datetime.now(timezone.utc).isoformat(),
            "safe_message": "cTrader account, balance, and symbols synced." if saved_symbols else "cTrader account synced. Symbol sync bridge is not configured yet.",
        }
        if hasattr(row, "last_connection_result"):
            row.last_connection_result = _ctrader_connection_from_selected(row, selected)
        await db.commit()
        await db.refresh(row)
        return success_response({"broker_account": dump_one(BrokerAccountOut, row), "selected_account": selected, "accounts": accounts, "symbols_synced": saved_symbols, "symbols_preview": symbols[:25]}, "cTrader synced")
    except Exception as exc:
        message = _safe_oauth_callback_error(str(exc))
        if "endpoint" in str(exc).lower() or "protobuf" in str(exc).lower():
            message = str(exc)
        row.status = BROKER_STATUS_ERROR
        row.metadata_json = {**(row.metadata_json or {}), "sync_status": "ERROR", "safe_message": message, "sync_error": str(exc)}
        await db.commit()
        raise HTTPException(status_code=400, detail=message) from exc


@router.post("/{broker_account_id}/ctrader/test-order")
async def place_ctrader_test_order(broker_account_id: UUID, payload: dict, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    row = await get_broker_account_or_404(db, broker_account_id, current_user)
    if not _is_ctrader_account(row):
        raise HTTPException(status_code=400, detail="Broker account is not a cTrader account")
    selected = _selected_ctrader_account(row)
    if not selected:
        raise HTTPException(status_code=400, detail="Account selection required before placing cTrader demo orders. Sync and select a cTrader trading account first.")
    if str(row.status or "").upper() != BROKER_STATUS_CONNECTED:
        raise HTTPException(status_code=400, detail="cTrader broker account must be CONNECTED before placing demo orders. Test or Sync the account first.")
    if not _is_demo_ctrader_selected(selected, row):
        raise HTTPException(status_code=400, detail="cTrader live order execution is disabled in this phase.")

    symbol = str(payload.get("symbol") or "").strip().upper()
    side = str(payload.get("side") or "BUY").strip().upper()
    volume_raw = payload.get("volume") or payload.get("quantity")
    if not symbol:
        raise HTTPException(status_code=400, detail="Symbol is required")
    if side not in {"BUY", "SELL"}:
        raise HTTPException(status_code=400, detail="Side must be BUY or SELL")
    try:
        volume = Decimal(str(volume_raw))
        if volume <= 0:
            raise ValueError()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Volume must be greater than zero") from exc

    symbol_meta = await _find_ctrader_symbol_meta(db, symbol, row)
    request_payload = {
        "symbol": symbol,
        "side": side,
        "volume": str(volume),
        "stop_loss": payload.get("stop_loss"),
        "take_profit": payload.get("take_profit"),
        "client_order_id": payload.get("client_order_id") or f"aax-ctrader-demo-{secrets.token_hex(6)}",
        "comment": payload.get("comment") or "AlgoAgentX cTrader DEMO test order",
        "selected_account": {
            "ctrader_account_id": selected.get("ctrader_account_id"),
            "account_number": selected.get("account_number"),
            "account_type": selected.get("account_type"),
            "currency": selected.get("currency"),
        },
        "symbol_meta": symbol_meta or {},
    }
    log = BrokerOrderExecutionLog(
        user_id=user_id_from(current_user),
        broker_account_id=row.id,
        broker_provider_code="CTRADER",
        execution_mode="DEMO",
        symbol=symbol,
        side=side,
        volume=volume,
        request_payload=_sanitize_order_payload(request_payload),
        status="PENDING",
        client_order_id=request_payload["client_order_id"],
    )
    db.add(log)
    await db.flush()

    adapter = CTraderAdapter(row)
    try:
        result = await adapter.place_demo_market_order(
            selected_account=selected,
            symbol_meta=symbol_meta,
            symbol=symbol,
            side=side,
            volume=volume,
            stop_loss=payload.get("stop_loss"),
            take_profit=payload.get("take_profit"),
            client_order_id=request_payload["client_order_id"],
            comment=request_payload["comment"],
        )
        log.status = "SUCCESS" if result.success else "FAILED"
        log.error_message = None if result.success else result.message
        log.broker_order_id = result.broker_order_id
        log.response_payload = _sanitize_order_payload({"status": result.status, "message": result.message, "broker_order_id": result.broker_order_id, "executed_price": str(result.executed_price) if result.executed_price is not None else None, "raw": result.raw_response or {}})
        row.last_connection_result = {**(row.last_connection_result or {}), "last_ctrader_test_order": log.response_payload}
        row.metadata_json = {**(row.metadata_json or {}), "safe_message": result.message, "last_ctrader_test_order_at": datetime.now(timezone.utc).isoformat()}
        await db.commit()
        await db.refresh(log)
        await db.refresh(row)
        if not result.success:
            raise HTTPException(status_code=400, detail=result.message)
        return success_response({
            "order_id": result.broker_order_id,
            "status": result.status,
            "symbol": symbol,
            "side": side,
            "volume": str(volume),
            "broker_account": dump_one(BrokerAccountOut, row),
            "execution_log_id": str(log.id),
            "message": result.message,
        }, "cTrader demo order placed")
    except HTTPException:
        raise
    except Exception as exc:
        message = CTraderAdapter._safe_order_error(exc)
        log.status = "FAILED"
        log.error_message = message
        log.response_payload = {"status": "FAILED", "message": message}
        row.metadata_json = {**(row.metadata_json or {}), "safe_message": message, "last_ctrader_test_order_error": message}
        await db.commit()
        raise HTTPException(status_code=400, detail=message) from exc


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
