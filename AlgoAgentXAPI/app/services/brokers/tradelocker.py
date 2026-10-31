"""TradeLocker REST broker adapter. Independent of cTrader and MT5.

TradeLocker POST/DELETE acknowledgements are not fill confirmations. The caller
must reconcile with broker positions/orders before marking a local trade filled.
"""
from __future__ import annotations

import asyncio
import os
import time
import logging
import hashlib
import math
import json
from email.utils import parsedate_to_datetime
from weakref import WeakKeyDictionary
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
import httpx

from ...utils.credential_crypto import decrypt_credential
from .base import BrokerAdapter, BrokerConnectionResult, BrokerOrderRequest, BrokerOrderResult
from .request_context import order_request_context, check_order_deadline, mark_order_submission
from ...core.redis_manager import redis_manager

logger = logging.getLogger(__name__)

# Adapter instances are deliberately short-lived (API, runner, sync workers).
# Reusing JWT and stable account schema INSIDE one process avoids a fresh auth
# and configuration request for every independent deployment/copy evaluation.
# Account credentials and selected account must never share a cache entry.
_SESSION_CACHE: dict[str, dict[str, Any]] = {}
_SESSION_LOCKS: dict[str, asyncio.Lock] = {}
_RATE_LIMIT_UNTIL: dict[str, float] = {}
_HTTP_CLIENTS: WeakKeyDictionary = WeakKeyDictionary()
_METADATA_LOCKS: dict[str, asyncio.Lock] = {}


def _account_key(environment: str, email: str, server: str, account_id: str, password: str) -> str:
    data = "\0".join((environment, email, server, account_id, password))
    return hashlib.sha256(data.encode('utf-8')).hexdigest()


def _retry_after_seconds(value: str | None) -> float:
    try:
        # Never shorten a broker's cooldown. HTTP-date is valid Retry-After too.
        return max(0.0, float(value)) if value else 10.0
    except (ValueError, TypeError):
        try:
            return max(0.0, parsedate_to_datetime(value).timestamp() - time.time())
        except (ValueError, TypeError, OverflowError):
            return 10.0


def _number(value):
    try:
        return Decimal(str(value)) if value is not None else None
    except (ValueError, ArithmeticError):
        return None


class TradeLockerAdapter(BrokerAdapter):
    def __init__(self, account):
        self.account = account
        self.meta = account.metadata_json or {}
        self.environment = str(self.meta.get('tradelocker_environment') or 'demo').lower()
        if self.environment not in ('demo', 'live'):
            raise ValueError('TradeLocker environment must be demo or live')
        self.base = f'https://{self.environment}.tradelocker.com/backend-api'
        self.email = str(account.login_id or '').strip()
        self.password = decrypt_credential(account.encrypted_password) or ''
        self.server = str(account.server_name or '').strip()
        self.account_id = str(self.meta.get('tradelocker_account_id') or '').strip()
        self.acc_num = self.meta.get('tradelocker_acc_num')
        self._access_token = None
        self._access_expiry = 0.0
        self._instrument_cache = None
        self._config_cache = None
        self._session_key = _account_key(self.environment, self.email, self.server, self.account_id, self.password)
        self._session_key = hashlib.sha256(f'{self._session_key}:{self.acc_num}'.encode()).hexdigest()

    def _http_client(self):
        # Connection pools must never cross event loops or credential/account scopes.
        clients = _HTTP_CLIENTS.setdefault(asyncio.get_running_loop(), {})
        key = getattr(self, '_session_key', self.base)
        client = clients.get(key)
        if client is None or client.is_closed:
            client = clients[key] = httpx.AsyncClient(timeout=20.0, follow_redirects=False)
        return client

    async def _cooldown(self, wait=None):
        # An IP-wide/environment cooldown is deliberately conservative: workers
        # behind the same Docker egress must not independently hammer a 429.
        key = f'tradelocker:cooldown:{self.environment}'
        if wait is not None:
            _RATE_LIMIT_UNTIL[key] = max(_RATE_LIMIT_UNTIL.get(key, 0), time.monotonic() + wait)
        client = redis_manager.client
        if client is not None:
            try:
                if wait is not None:
                    await client.eval("if redis.call('pttl',KEYS[1]) < tonumber(ARGV[1]) then redis.call('psetex',KEYS[1],ARGV[1],'1') end return 1",
                                      1, key, max(1, math.ceil(wait * 1000)))
                return max(0, (await client.pttl(key)) / 1000,
                           _RATE_LIMIT_UNTIL.get(key, 0) - time.monotonic())
            except Exception:
                # A broken distributed limiter must not result in an API storm.
                raise RuntimeError('TradeLocker shared request coordinator unavailable') from None
        return max(0, _RATE_LIMIT_UNTIL.get(key, 0) - time.monotonic())

    async def _request(self, method: str, path: str, *, params=None, body=None, auth=True):
        headers = {'Accept': 'application/json'}
        check_order_deadline()
        context = order_request_context.get()
        client = redis_manager.client
        if client is not None:
            priority_key = f'tradelocker:entry-priority:{self.environment}'
            if context is not None:
                await client.set(priority_key, '1', px=2000)
            elif method == 'GET' and (path == '/trade/accounts' or path.endswith('/orders') or path.endswith('/ordersHistory')) and await client.exists(priority_key):
                # Background polling yields rather than queues stale work. Close
                # and protection writes are never deferred by this priority gate.
                raise RuntimeError('TradeLocker background read deferred for order-critical requests')
        if auth:
            headers['Authorization'] = f'Bearer {await self._token()}'
        if self.acc_num is not None:
            headers['accNum'] = str(self.acc_num)
        developer_key = os.environ.get('TRADELOCKER_DEVELOPER_API_KEY', '').strip()
        if developer_key:
            headers['tl-developer-api-key'] = developer_key
        deadline = min(time.time() + 15, context.deadline if context else float('inf'))
        safe_read = method.upper() == 'GET' or path == '/auth/jwt/token'
        response = None
        for attempt in range(3):
            check_order_deadline()
            wait = await self._cooldown()
            if wait:
                if not safe_read or not context or time.time() + wait >= deadline:
                    raise RuntimeError('TradeLocker API rate limit cooldown exceeds request budget')
                await asyncio.sleep(wait)
            check_order_deadline()
            if method == 'POST' and path.endswith('/orders'):
                mark_order_submission()
            started = time.monotonic()
            try:
                response = await self._http_client().request(method, self.base + path, headers=headers, params=params, json=body)
            except httpx.TransportError:
                if not safe_read or attempt == 2 or time.time() + 2 ** attempt >= deadline:
                    raise
                await asyncio.sleep(2 ** attempt)
                continue
            logger.info('TRADELOCKER_REQUEST account=%s method=%s path=%s status=%s attempt=%s duration_ms=%.3f',
                        self.account_id, method, path, response.status_code, attempt + 1,
                        (time.monotonic() - started) * 1000)
            if context:
                context.metrics['http_requests'] = context.metrics.get('http_requests', 0) + 1
                context.metrics['retry_attempts'] = context.metrics.get('retry_attempts', 0) + int(attempt > 0)
                context.metrics['http_429_count'] = context.metrics.get('http_429_count', 0) + int(response.status_code == 429)
            if response.status_code == 429:
                wait = _retry_after_seconds(response.headers.get('Retry-After'))
                await self._cooldown(wait)
            elif response.status_code >= 500:
                if not safe_read:
                    raise httpx.TransportError('TradeLocker submission returned ambiguous gateway error; reconcile before retry')
                if response.status_code not in (502, 503, 504):
                    break
                wait = max(2 ** attempt, _retry_after_seconds(response.headers['Retry-After']) if 'Retry-After' in response.headers else 0)
            else:
                break
            # Do not automatically retry writes, even on an HTTP rejection.
            if not safe_read or attempt == 2 or time.time() + wait >= deadline:
                raise RuntimeError(f'TradeLocker HTTP {response.status_code}; bounded request budget exhausted')
            await asyncio.sleep(wait)
        if response.status_code >= 400:
            if response.status_code in (401, 403):
                _SESSION_CACHE.pop(getattr(self, '_session_key', None), None)
                self._access_token, self._access_expiry = None, 0
            raise RuntimeError(f'TradeLocker {method} {path} returned HTTP {response.status_code}. Check credentials, account and trading rules.')
        if response.status_code == 204 or not response.content:
            return {'s': 'ok'}
        try:
            data = response.json()
        except ValueError:
            if not safe_read:
                raise httpx.TransportError('TradeLocker returned malformed submission acknowledgement; reconcile before retry') from None
            raise
        if not isinstance(data, dict):
            if not safe_read:
                raise httpx.TransportError('TradeLocker returned invalid submission acknowledgement; reconcile before retry')
            raise RuntimeError('TradeLocker returned an invalid read response')
        if data.get('s') not in (None, 'ok') and not (path == '/trade/history' and data.get('s') == 'no_data'):
            raise RuntimeError(f'TradeLocker API returned status {data.get("s")!r}')
        return data

    async def _token(self):
        if self._access_token and time.monotonic() < self._access_expiry:
            return self._access_token
        if not all((self.email, self.password, self.server)):
            raise ValueError('TradeLocker email, password and server are required')
        key = getattr(self, '_session_key', None)
        if key:
            cached = _SESSION_CACHE.get(key) or {}
            if cached.get('token') and time.monotonic() < cached.get('expiry', 0):
                self._access_token, self._access_expiry = cached['token'], cached['expiry']
                return self._access_token
            lock = _SESSION_LOCKS.setdefault(key, asyncio.Lock())
            async with lock:
                cached = _SESSION_CACHE.get(key) or {}
                if cached.get('token') and time.monotonic() < cached.get('expiry', 0):
                    self._access_token, self._access_expiry = cached['token'], cached['expiry']
                    return self._access_token
                return await self._refresh_token(key)
        return await self._refresh_token(None)

    async def _refresh_token(self, key):
        payload = await self._request('POST', '/auth/jwt/token', body={
            'email': self.email, 'password': self.password, 'server': self.server,
        }, auth=False)
        info = payload.get('d', payload)
        self._access_token = info.get('accessToken') or info.get('access_token')
        if not self._access_token:
            raise RuntimeError('TradeLocker authentication did not return accessToken')
        self._access_expiry = time.monotonic() + max(1, min(int(info.get('expiresIn') or 600), 600) - 30)
        if key:
            cached = _SESSION_CACHE.setdefault(key, {})
            cached['token'], cached['expiry'] = self._access_token, self._access_expiry
        return self._access_token

    async def get_available_accounts(self):
        # No accNum header is required for the JWT account-list endpoint.
        data = await self._request('GET', '/auth/jwt/all-accounts')
        payload = data.get('d', data)
        accounts = payload.get('accounts', []) if isinstance(payload, dict) else payload
        if not isinstance(accounts, list):
            raise RuntimeError('TradeLocker account listing has an unexpected response shape')
        return [{'id': str(x['id']), 'accNum': int(x['accNum']),
                 'name': str(x.get('name') or x['id'])}
                for x in accounts if isinstance(x, dict) and x.get('id') is not None and x.get('accNum') is not None]

    @staticmethod
    def _mapped_details(config, state):
        field_config = config.get('accountDetailsConfig') or {}
        columns = field_config.get('columns') or []
        names = [(col.get('id') or col.get('name')) if isinstance(col, dict) else str(col) for col in columns]
        values = state.get('accountDetailsData') or []
        if not names or len(names) != len(values):
            raise RuntimeError('TradeLocker account-details configuration does not match state fields')
        return dict(zip(names, values))

    @staticmethod
    def _account_value(details, *names):
        normalized = {''.join(ch for ch in str(k).lower() if ch.isalnum()): v for k, v in details.items()}
        for key in names:
            value = normalized.get(''.join(ch for ch in key.lower() if ch.isalnum()))
            if value is not None:
                return _number(value)
        return None

    def _require_selected(self):
        if not self.account_id or self.acc_num is None:
            raise ValueError('Select a TradeLocker accountId and accNum in broker setup before syncing or trading.')

    async def _config(self):
        if self._config_cache is None:
            key = getattr(self, '_session_key', None)
            cached = _SESSION_CACHE.get(key, {}) if key else {}
            if cached.get('config') and time.monotonic() < cached.get('config_expiry', 0):
                self._config_cache = cached['config']
            else:
                self._config_cache = (await self._request('GET', '/trade/config')).get('d') or {}
                if key and self._config_cache:
                    _SESSION_CACHE.setdefault(key, {}).update(config=self._config_cache, config_expiry=time.monotonic() + 120)
        return self._config_cache

    async def get_account_info(self):
        self._require_selected()
        selected = await self._selected_account_metadata()
        config = await self._config()
        state = (await self._request('GET', f'/trade/accounts/{self.account_id}/state')).get('d') or {}
        details = self._mapped_details(config, state)
        return {
            'connected': True,
            'message': 'TradeLocker account state refreshed.',
            'account_login': self.account_id,
            'server': self.server,
            'currency': selected.get('currency'),
            'balance': self._account_value(details, 'balance', 'accountBalance'),
            'equity': self._account_value(details, 'equity', 'accountEquity'),
            'free_margin': self._account_value(details, 'freeMargin', 'availableFunds', 'marginAvailable'),
            'unrealized_pnl': self._account_value(details, 'unrealizedPl', 'unrealizedPnl'),
            'account': selected, 'state': details,
            'account_id': self.account_id, 'acc_num': self.acc_num,
        }

    async def _selected_account_metadata(self):
        key = getattr(self, '_session_key', None)
        cache_key = f'{key}:metadata'
        async with _METADATA_LOCKS.setdefault(cache_key, asyncio.Lock()):
            cached = _SESSION_CACHE.get(key, {}) if key else {}
            hit = bool(cached.get('selected_account') and time.monotonic() < cached.get('account_expiry', 0))
            context = order_request_context.get()
            if context:
                context.metrics['account_metadata_cache_hit'] = hit
            if hit:
                return dict(cached['selected_account'])
            redis = redis_manager.client
            redis_key = f'tradelocker:account-metadata:{key}'
            if key and redis is not None:
                shared = await redis.get(redis_key)
                if shared:
                    selected = json.loads(shared)
                    if str(selected.get('id')) == self.account_id and str(selected.get('accNum')) == str(self.acc_num):
                        _SESSION_CACHE.setdefault(key, {}).update(selected_account=selected, account_expiry=time.monotonic() + 60)
                        if context:
                            context.metrics['account_metadata_cache_hit'] = True
                        return dict(selected)
            accounts = (await self._request('GET', '/trade/accounts')).get('d')
            if not isinstance(accounts, list):
                raise ValueError('TradeLocker account list unavailable; account validation failed closed')
            selected = next((x for x in accounts if isinstance(x, dict) and str(x.get('id')) == self.account_id), None)
            if not selected or (selected.get('accNum') is not None and str(selected['accNum']) != str(self.acc_num)):
                raise ValueError('TradeLocker selected accountId/accNum is not available for these credentials')
            # Retain stable identity only; equity/balance ALWAYS come from /state.
            selected = {k: selected[k] for k in ('id', 'accNum', 'name', 'currency') if k in selected}
            if key:
                _SESSION_CACHE.setdefault(key, {}).update(selected_account=selected, account_expiry=time.monotonic() + 3600)
                if redis is not None:
                    await redis.set(redis_key, json.dumps(selected), ex=3600)
            return dict(selected)


    async def test_connection(self):
        try:
            info = await self.get_account_info()
            account = info['account']
            return BrokerConnectionResult(True, 'TradeLocker authenticated and selected trading account verified.',
                account_login=self.account_id, server=self.server, currency=account.get('currency'),
                balance=info['balance'],
                equity=info['equity'],
                raw={'environment': self.environment, 'account': account, 'state': info['state'],
                     'account_id': self.account_id, 'acc_num': self.acc_num})
        except Exception as exc:
            return BrokerConnectionResult(False, str(exc), account_login=self.account_id or self.email,
                server=self.server, raw={'provider': 'TRADELOCKER'})

    async def _instruments(self):
        self._require_selected()
        if self._instrument_cache is None:
            key = getattr(self, '_session_key', None)
            cached = _SESSION_CACHE.get(key, {}) if key else {}
            if cached.get('instruments') and time.monotonic() < cached.get('instruments_expiry', 0):
                self._instrument_cache = cached['instruments']
            else:
                result = await self._request('GET', f'/trade/accounts/{self.account_id}/instruments')
                data = result.get('d') or {}
                if not isinstance(data, dict) or not isinstance(data.get('instruments'), list):
                    raise RuntimeError('TradeLocker instruments response missing valid instruments list')
                self._instrument_cache = data['instruments']
                if key:
                    _SESSION_CACHE.setdefault(key, {}).update(instruments=self._instrument_cache, instruments_expiry=time.monotonic() + 120)
        return self._instrument_cache

    async def get_symbols(self, query=None, limit=200):
        data = []
        for inst in await self._instruments():
            symbol = str(inst.get('name') or inst.get('symbol') or '').strip()
            if not symbol or (query and query.upper() not in symbol.upper()):
                continue
            routes = inst.get('routes') or []
            data.append({'symbol': symbol, 'symbol_name': symbol, 'trading_symbol': symbol,
                'instrument_key': str(inst.get('tradableInstrumentId') or ''),
                'tradableInstrumentId': inst.get('tradableInstrumentId'), 'routes': routes,
                'description': inst.get('description'), 'metadata_json': inst})
            if len(data) >= limit:
                break
        return data

    async def _instrument(self, symbol):
        target = ''.join(c for c in symbol.upper() if c.isalnum())
        for inst in await self._instruments():
            name = str(inst.get('name') or inst.get('symbol') or '')
            if name.upper() == symbol.upper():
                return inst
        matches = [x for x in await self._instruments() if ''.join(c for c in str(x.get('name') or x.get('symbol') or '').upper() if c.isalnum()) == target]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise ValueError(f'TradeLocker symbol {symbol!r} maps to multiple broker instruments; select an exact symbol.')
        # Allow a canonical six-letter FX/metal symbol to resolve to a single
        # account-specific suffix (XAUUSD -> XAUUSD.X). Never guess if ambiguous.
        if len(target) == 6 and target.isalpha():
            suffix_matches = [inst for inst in await self._instruments()
                              if ''.join(c for c in str(inst.get('name') or inst.get('symbol') or '').upper()
                                         if c.isalnum()).startswith(target)]
            if len(suffix_matches) == 1:
                return suffix_matches[0]
            if len(suffix_matches) > 1:
                raise ValueError(f'TradeLocker symbol {symbol!r} has multiple suffixed matches; select exact broker symbol.')
        raise ValueError(f'TradeLocker symbol {symbol!r} not found or ambiguous. Choose the exact broker symbol.')

    @staticmethod
    def _route(inst, route_type):
        routes = inst.get('routes') or []
        for route in routes:
            if isinstance(route, dict) and str(route.get('type') or route.get('routeType') or route.get('name') or '').upper() == route_type:
                return route.get('id') or route.get('routeId')
        raise ValueError(f'TradeLocker {route_type} route unavailable for selected instrument; refusing order.')

    async def get_quote(self, symbol):
        inst = await self._instrument(symbol)
        result = await self._request('GET', '/trade/quotes', params={'routeId': self._route(inst, 'INFO'), 'tradableInstrumentId': inst['tradableInstrumentId']})
        q = result.get('d') or {}
        return {'symbol': symbol, 'bid': q.get('bp'), 'ask': q.get('ap'), 'raw': q}

    async def place_market_order(self, order_request: BrokerOrderRequest):
        # Feature flag deliberately defaults to OFF, including demo accounts.
        if os.environ.get('TRADELOCKER_ORDER_EXECUTION_ENABLED', 'false').lower() != 'true':
            return BrokerOrderResult(False, 'REJECTED', 'TradeLocker order execution is disabled until demo reconciliation is validated.')
        if self.environment == 'live' and os.environ.get('TRADELOCKER_LIVE_EXECUTION_ENABLED', 'false').lower() != 'true':
            return BrokerOrderResult(False, 'REJECTED', 'TradeLocker live order execution is not enabled.')
        try:
            self._require_selected()
            inst = await self._instrument(order_request.symbol)
            if order_request.qty <= 0:
                raise ValueError('Order quantity must be positive')
            side = order_request.side.lower()
            if side not in ('buy', 'sell'):
                raise ValueError('Order side must be BUY or SELL')
            if order_request.order_type.upper() != 'MARKET':
                raise ValueError('This adapter currently supports MARKET execution only')
            body = {'qty': float(order_request.qty), 'routeId': self._route(inst, 'TRADE'),
                'side': side, 'validity': 'IOC', 'type': 'market', 'price': 0,
                'tradableInstrumentId': inst['tradableInstrumentId']}
            if order_request.stop_loss is not None:
                body.update(stopLoss=float(order_request.stop_loss), stopLossType='absolute')
            if order_request.target is not None:
                body.update(takeProfit=float(order_request.target), takeProfitType='absolute')
            if order_request.idempotency_key:
                body['strategyId'] = 'AX-' + hashlib.sha256(str(order_request.idempotency_key).encode()).hexdigest()[:28]
            result = await self._request('POST', f'/trade/accounts/{self.account_id}/orders', body=body)
            acknowledgement = result.get('d')
            if not isinstance(acknowledgement, dict):
                raise httpx.TransportError('TradeLocker order response has invalid data; reconcile before retrying')
            order_id = str(acknowledgement.get('orderId') or '')
            if not order_id:
                raise httpx.TransportError('TradeLocker order response has no orderId; reconcile before retrying')
            return BrokerOrderResult(True, 'PLACED', 'TradeLocker order accepted; broker fill confirmation pending.', broker_order_id=order_id,
                raw_response={'orderId': order_id, 'requires_reconciliation': True,
                              'resolved_symbol': str(inst.get('name') or inst.get('symbol') or order_request.symbol),
                              'tradableInstrumentId': inst['tradableInstrumentId']})
        except (httpx.TransportError, httpx.TimeoutException) as exc:
            # A POST may reach the broker before the response is lost. Never
            # permit automatic duplicate sending for this same signal.
            return BrokerOrderResult(False, 'UNCERTAIN', f'TradeLocker entry outcome unknown; reconcile manually before retry: {exc}',
                                     raw_response={'requires_reconciliation': True, 'order_outcome_unknown': True})
        except TimeoutError:
            return BrokerOrderResult(False, 'SKIPPED', 'Signal expired before TradeLocker submission')
        except Exception as exc:
            return BrokerOrderResult(False, 'ERROR', str(exc))

    async def close_position(self, position_id_or_symbol, side, qty):
        if os.environ.get('TRADELOCKER_ORDER_EXECUTION_ENABLED', 'false').lower() != 'true' or (self.environment == 'live' and os.environ.get('TRADELOCKER_LIVE_EXECUTION_ENABLED', 'false').lower() != 'true'):
            return BrokerOrderResult(False, 'REJECTED', 'TradeLocker position closing disabled by safety gate.')
        if not str(position_id_or_symbol).isdigit():
            return BrokerOrderResult(False, 'REJECTED', 'TradeLocker close requires numeric position ID, never a symbol.')
        try:
            if qty < 0:
                raise ValueError('Close quantity cannot be negative')
            await self._request('DELETE', f'/trade/positions/{position_id_or_symbol}', body={'qty': float(qty)})
            return BrokerOrderResult(True, 'PLACED', 'Close requested; reconcile actual position quantity.', broker_order_id=str(position_id_or_symbol), raw_response={'requires_reconciliation': True})
        except Exception as exc:
            # A timeout/transport failure can occur AFTER the broker accepted the
            # DELETE. Never retry a partial close blindly; reconcile first.
            return BrokerOrderResult(False, 'UNCERTAIN', f'TradeLocker close outcome unknown: {exc}')

    async def _table(self, key, config_key, *, params=None):
        self._require_selected()
        config = await self._config()
        payload = (await self._request('GET', f'/trade/accounts/{self.account_id}/{key}', params=params)).get('d')
        if not isinstance(payload, dict) or not isinstance(payload.get(key), list):
            raise RuntimeError(f'TradeLocker {key} response missing valid {key} list; cannot infer zero open positions')
        rows = payload[key]
        fields = config.get(config_key) or []
        if isinstance(fields, dict):
            fields = fields.get('columns') or fields.get('fields') or []
        columns = [str(c.get('name') or c.get('id')) if isinstance(c, dict) else str(c) for c in fields]
        if not columns:
            raise RuntimeError(f'TradeLocker {config_key} column metadata unavailable; refusing unsafe positional mapping')
        mapped = []
        for row in rows:
            if isinstance(row, list):
                if len(row) != len(columns):
                    raise RuntimeError(f'TradeLocker {key} row/schema length mismatch; position state cannot be trusted')
                mapped.append(dict(zip(columns, row)))
            elif isinstance(row, dict):
                mapped.append(row)
            else:
                raise RuntimeError(f'TradeLocker {key} returned an unexpected row shape')
        return mapped

    async def get_positions(self, symbol=None):
        positions = await self._table('positions', 'positionsConfig')
        instruments = await self._instruments()
        by_id = {str(inst.get('tradableInstrumentId')): inst for inst in instruments
                 if inst.get('tradableInstrumentId') is not None}
        selected_id = None
        if symbol:
            selected_id = str((await self._instrument(symbol))['tradableInstrumentId'])
        normalized = []
        for raw in positions:
            instrument_id = str(raw.get('tradableInstrumentId') or '')
            if selected_id is not None and instrument_id != selected_id:
                continue
            if not raw.get('id') or not instrument_id or raw.get('qty') is None:
                raise RuntimeError('TradeLocker position missing id, instrument id or quantity; refusing unsafe sync')
            inst = by_id.get(instrument_id)
            if inst is None:
                # Broker truth must still count an instrument that this cached
                # catalogue cannot name; never silently hide an open position.
                name = f'TRADELOCKER_INSTRUMENT_{instrument_id}'
            else:
                name = str(inst.get('name') or inst.get('symbol') or '').strip()
                if not name:
                    raise RuntimeError('TradeLocker instrument has no symbol; refusing unsafe sync')
            normalized.append({**raw, 'symbol': name, 'broker_position_id': str(raw['id'])})
        return normalized

    async def get_orders(self):
        # Non-final orders only; final fills are fetched selectively when the
        # DB still has a PLACED/UNCONFIRMED entry.
        return await self._table('orders', 'ordersConfig')

    async def get_order_history(self, broker_order_ids, *, strategy_ids=()):
        ids = {str(x) for x in broker_order_ids if x is not None}
        strategies = {str(x) for x in strategy_ids if x}
        if not ids and not strategies:
            return []
        now_ms = int(time.time() * 1000)
        final = await self._table('ordersHistory', 'ordersHistoryConfig',
                                  params={'from': now_ms - 2 * 86400000, 'to': now_ms})
        return [order for order in final if str(order.get('id') or '') in ids
                or str(order.get('strategyId') or '') in strategies]

    # Broker candles are independent from the MT5/cTrader data and order paths.
    # TradeLocker /trade/history is a date-range API, not a count-based one.
    _HISTORY_RESOLUTIONS = {
        'm1': ('1m', 60), '1m': ('1m', 60),
        'm5': ('5m', 300), '5m': ('5m', 300),
        'm15': ('15m', 900), '15m': ('15m', 900),
        'm30': ('30m', 1800), '30m': ('30m', 1800),
        'h1': ('1H', 3600), '1h': ('1H', 3600),
        'h4': ('4H', 14400), '4h': ('4H', 14400),
        'd1': ('1D', 86400), '1d': ('1D', 86400),
    }

    @classmethod
    def _history_resolution(cls, timeframe):
        result = cls._HISTORY_RESOLUTIONS.get(str(timeframe).strip().lower())
        if result is None:
            raise ValueError(f'Unsupported TradeLocker timeframe: {timeframe}')
        return result

    @staticmethod
    def _normalize_history_bars(raw_bars, *, symbol, before_ms=None):
        """Only accept complete, correctly ordered, finite OHLC candles.

        An M5 candle whose close equals its low is valid and MUST NOT be
        rejected merely for that equality. Preserve raw REST OHLC for audits.
        """
        if not isinstance(raw_bars, list):
            raise ValueError('TradeLocker history barDetails must be a list')
        by_timestamp = {}
        for bar in raw_bars:
            if not isinstance(bar, dict) or any(k not in bar or bar[k] is None for k in ('t', 'o', 'h', 'l', 'c')):
                logger.warning('Skipping incomplete TradeLocker history bar')
                continue
            try:
                timestamp_ms = int(bar['t'])
                open_, high, low, close = (float(bar[k]) for k in ('o', 'h', 'l', 'c'))
                volume = float(bar['v']) if bar.get('v') is not None else None
                valid = (
                    timestamp_ms > 1_000_000_000_000
                    and (before_ms is None or timestamp_ms < before_ms)
                    and all(math.isfinite(x) and x > 0 for x in (open_, high, low, close))
                    and low <= min(open_, close) <= high
                    and low <= max(open_, close) <= high
                    and (volume is None or (math.isfinite(volume) and volume >= 0))
                )
                if not valid:
                    raise ValueError('invalid timestamp or OHLC range')
                timestamp = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
            except (ValueError, TypeError, OverflowError, OSError):
                logger.warning('Skipping invalid TradeLocker history OHLC/timestamp')
                continue
            by_timestamp[timestamp_ms] = {
                'symbol': symbol, 'candle_time': timestamp,
                'open': open_, 'high': high, 'low': low, 'close': close,
                'volume': volume,
                'raw_payload': {'provider': 'TRADELOCKER', 't': timestamp_ms,
                                'o': bar['o'], 'h': bar['h'], 'l': bar['l'],
                                'c': bar['c'], 'v': bar.get('v')},
            }
        return [by_timestamp[k] for k in sorted(by_timestamp)]

    async def _history_page(self, instrument, resolution, start_ms, end_ms, symbol, *, before_ms=None):
        response = await self._request('GET', '/trade/history', params={
            'routeId': self._route(instrument, 'INFO'),
            'tradableInstrumentId': instrument['tradableInstrumentId'],
            'resolution': resolution, 'from': start_ms, 'to': end_ms,
        })
        if response.get('s') == 'no_data':
            return [], (response.get('d') or {}).get('nb') or response.get('nb')
        payload = response.get('d') or {}
        return self._normalize_history_bars(payload.get('barDetails') or [], symbol=symbol, before_ms=before_ms), None

    async def get_rates(self, symbol, timeframe, count=300):
        """Keep the original single REST request for short live refreshes."""
        inst = await self._instrument(symbol)
        resolution, bar_seconds = self._history_resolution(timeframe)
        requested = max(1, int(count))
        end_ms = int(time.time() * 1000)
        # Short current-candle refresh remains unchanged. TradeLocker rejects
        # API windows that exceed 20,000 bars, hence the existing 6k cap.
        start_ms = end_ms - (max(1, min(requested, 6000)) * 2 + 10) * bar_seconds * 1000
        rows, _ = await self._history_page(inst, resolution, start_ms, end_ms, symbol)
        return rows[-requested:]

    async def get_rates_history(self, symbol, timeframe, count=300, *, before=None):
        """Background ONLY: cursor-based TradeLocker historical warmup.

        Runs on live_history_worker, not the strategy worker or every M5 tick.
        Every request is bounded below TradeLocker's 20k-bars/window limit;
        cursor uses the oldest returned *open timestamp*, never wall time.
        """
        inst = await self._instrument(symbol)
        resolution, bar_seconds = self._history_resolution(timeframe)
        required = max(1, min(int(count), 30_000))
        if before is None:
            end_ms = int(time.time() * 1000)
        elif isinstance(before, datetime):
            if before.tzinfo is None:
                raise ValueError('History before cursor must have UTC timezone')
            end_ms = int(before.timestamp() * 1000) - 1  # exclusive cursor
        else:
            raise ValueError('History before cursor must be a datetime')

        collected = {}
        page_bars = 1500
        # 20k M5 bars generally spans many weeks. Limit iteration and stop if
        # the broker repeatedly returns the same candles or no older data.
        max_pages = max(3, min(80, (required + page_bars - 1) // page_bars + 15))
        for _ in range(max_pages):
            remaining = required - len(collected)
            if remaining <= 0:
                break
            wanted = min(page_bars, remaining)
            # ~3x for overnight/weekend gaps. Always <20k nominal bars/API call.
            window_bars = min(19_000, wanted * 3 + 120)
            start_ms = end_ms - window_bars * bar_seconds * 1000
            rows, earlier_available = await self._history_page(
                inst, resolution, start_ms, end_ms, symbol, before_ms=end_ms + 1,
            )
            if not rows:
                # API may provide 'nb' pointing to the next available older bar.
                try:
                    older_ms = int(earlier_available)
                except (ValueError, TypeError):
                    break
                if not 1_000_000_000_000 < older_ms < start_ms:
                    break
                end_ms = older_ms
                continue
            # Keep newest requested bars in the page, then advance before the
            # OLDEST selected bar so an overlapping server page never loops.
            selected = rows[-wanted:]
            for row in selected:
                ms = int(row['candle_time'].timestamp() * 1000)
                collected[ms] = row
            oldest_ms = int(selected[0]['candle_time'].timestamp() * 1000)
            if oldest_ms >= end_ms:
                break
            end_ms = oldest_ms - 1
            if len(rows) < wanted and oldest_ms <= start_ms + bar_seconds * 1000:
                # Full requested time window was scanned, continue backwards.
                continue
        return [collected[k] for k in sorted(collected)][-required:]
