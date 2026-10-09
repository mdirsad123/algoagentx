"""TradeLocker REST broker adapter. Independent of cTrader and MT5.

TradeLocker POST/DELETE acknowledgements are not fill confirmations. The caller
must reconcile with broker positions/orders before marking a local trade filled.
"""
from __future__ import annotations

import asyncio
import os
import time
from decimal import Decimal
from typing import Any
import httpx

from ...utils.credential_crypto import decrypt_credential
from .base import BrokerAdapter, BrokerConnectionResult, BrokerOrderRequest, BrokerOrderResult


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

    async def _request(self, method: str, path: str, *, params=None, body=None, auth=True):
        headers = {'Accept': 'application/json'}
        if auth:
            headers['Authorization'] = f'Bearer {await self._token()}'
        if self.acc_num is not None:
            headers['accNum'] = str(self.acc_num)
        developer_key = os.environ.get('TRADELOCKER_DEVELOPER_API_KEY', '').strip()
        if developer_key:
            headers['tl-developer-api-key'] = developer_key
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=False) as client:
            response = await client.request(method, self.base + path, headers=headers, params=params, json=body)
        if response.status_code == 429:
            raise RuntimeError('TradeLocker API rate limit reached; retry later (do not duplicate an order).')
        if response.status_code >= 400:
            raise RuntimeError(f'TradeLocker {method} {path} returned HTTP {response.status_code}. Check credentials, account and trading rules.')
        if response.status_code == 204 or not response.content:
            return {'s': 'ok'}
        data = response.json()
        if data.get('s') not in (None, 'ok'):
            raise RuntimeError(f'TradeLocker API returned status {data.get("s")!r}')
        return data

    async def _token(self):
        if self._access_token and time.monotonic() < self._access_expiry:
            return self._access_token
        if not all((self.email, self.password, self.server)):
            raise ValueError('TradeLocker email, password and server are required')
        payload = await self._request('POST', '/auth/jwt/token', body={'email': self.email, 'password': self.password, 'server': self.server}, auth=False)
        info = payload.get('d', payload)
        self._access_token = info.get('accessToken') or info.get('access_token')
        if not self._access_token:
            raise RuntimeError('TradeLocker authentication did not return accessToken')
        self._access_expiry = time.monotonic() + min(int(info.get('expiresIn') or 600), 600) - 30
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

    async def get_account_info(self):
        self._require_selected()
        accounts = (await self._request('GET', '/trade/accounts')).get('d') or []
        selected = next((x for x in accounts if str(x.get('id')) == self.account_id), None)
        if not selected:
            raise ValueError('TradeLocker accountId is not available for the selected credentials/environment')
        config = (await self._request('GET', '/trade/config')).get('d') or {}
        state = (await self._request('GET', f'/trade/accounts/{self.account_id}/state')).get('d') or {}
        details = self._mapped_details(config, state)
        return {'account': selected, 'state': details, 'account_id': self.account_id, 'acc_num': self.acc_num}


    async def test_connection(self):
        try:
            info = await self.get_account_info()
            account = info['account']
            return BrokerConnectionResult(True, 'TradeLocker authenticated and selected trading account verified.',
                account_login=self.account_id, server=self.server, currency=account.get('currency'),
                balance=self._account_value(info['state'], 'balance', 'accountBalance'),
                equity=self._account_value(info['state'], 'equity', 'accountEquity'),
                raw={'environment': self.environment, 'account': account, 'state': info['state'],
                     'account_id': self.account_id, 'acc_num': self.acc_num})
        except Exception as exc:
            return BrokerConnectionResult(False, str(exc), account_login=self.account_id or self.email,
                server=self.server, raw={'provider': 'TRADELOCKER'})

    async def _instruments(self):
        self._require_selected()
        if self._instrument_cache is None:
            result = await self._request('GET', f'/trade/accounts/{self.account_id}/instruments')
            self._instrument_cache = result.get('d', {}).get('instruments') or []
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
                body['strategyId'] = str(order_request.idempotency_key)[:31]
            result = await self._request('POST', f'/trade/accounts/{self.account_id}/orders', body=body)
            order_id = str((result.get('d') or {}).get('orderId') or '')
            if not order_id:
                raise RuntimeError('TradeLocker did not return orderId; reconcile before retrying')
            return BrokerOrderResult(True, 'PLACED', 'TradeLocker order accepted; broker fill confirmation pending.', broker_order_id=order_id,
                raw_response={'orderId': order_id, 'requires_reconciliation': True})
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
            return BrokerOrderResult(False, 'ERROR', str(exc))

    async def _table(self, key, config_key):
        self._require_selected()
        config = (await self._request('GET', '/trade/config')).get('d') or {}
        rows = (await self._request('GET', f'/trade/accounts/{self.account_id}/{key}')).get('d', {}).get(key) or []
        fields = config.get(config_key) or []
        if isinstance(fields, dict):
            fields = fields.get('columns') or fields.get('fields') or []
        columns = [str(c.get('name') or c.get('id')) if isinstance(c, dict) else str(c) for c in fields]
        if not columns and rows:
            raise RuntimeError(f'TradeLocker {config_key} column metadata unavailable; refusing unsafe positional mapping')
        return [dict(zip(columns, r)) if isinstance(r, list) else r for r in rows]

    async def get_positions(self, symbol=None):
        positions = await self._table('positions', 'positionsConfig')
        if symbol:
            inst = await self._instrument(symbol)
            positions = [p for p in positions if str(p.get('tradableInstrumentId')) == str(inst['tradableInstrumentId'])]
        return positions

    async def get_orders(self):
        return await self._table('orders', 'ordersConfig')

    async def get_rates(self, symbol, timeframe, count=300):
        inst = await self._instrument(symbol)
        resolution = str(timeframe).lower()
        supported = {'m1': '1m', 'm5': '5m', 'm15': '15m', 'm30': '30m', 'h1': '1H', 'h4': '4H', 'd1': '1D'}
        resolution = supported.get(resolution, timeframe)
        seconds = {'1m': 60, '5m': 300, '15m': 900, '30m': 1800, '1H': 3600, '4H': 14400, '1D': 86400}
        if resolution not in seconds:
            raise ValueError(f'Unsupported TradeLocker timeframe: {timeframe}')
        end = int(time.time() * 1000)
        start = end - (max(1, min(int(count), 20000)) + 10) * seconds[resolution] * 1000
        result = await self._request('GET', '/trade/history', params={'routeId': self._route(inst, 'INFO'), 'tradableInstrumentId': inst['tradableInstrumentId'], 'resolution': resolution, 'from': start, 'to': end})
        return [{'time': x['t'], 'open': x['o'], 'high': x['h'], 'low': x['l'], 'close': x['c'], 'volume': x.get('v')} for x in (result.get('d') or {}).get('barDetails', [])][-count:]
