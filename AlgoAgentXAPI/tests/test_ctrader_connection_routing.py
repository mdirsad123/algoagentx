import asyncio

from app.services.brokers.ctrader_connection_manager import (
    PT_EXECUTION_EVENT,
    PT_GET_TRENDBARS_RES,
    PersistentCTraderConnection,
    TrendbarSubscription,
    _PendingRequest,
)


def test_response_is_correlated_by_client_message_id():
    async def scenario():
        connection = PersistentCTraderConnection(
            environment="DEMO", client_id="client", client_secret="secret"
        )
        future = asyncio.get_running_loop().create_future()
        connection._pending["request-1"] = _PendingRequest(
            future=future, expected_types={PT_GET_TRENDBARS_RES}
        )
        await connection._route_message({
            "clientMsgId": "request-1",
            "payloadType": PT_GET_TRENDBARS_RES,
            "payload": {"trendbar": [{"utcTimestampInMinutes": 1}]},
        }, PT_GET_TRENDBARS_RES)
        assert (await future)["trendbar"][0]["utcTimestampInMinutes"] == 1

    asyncio.run(scenario())


def test_reconnect_registry_restores_accounts_spots_and_trendbars():
    async def scenario():
        connection = PersistentCTraderConnection(
            environment="DEMO", client_id="client", client_secret="secret"
        )
        connection._account_tokens[1] = "token"
        connection._spot_subscriptions[1] = {100, 200}
        connection._trendbar_subscriptions.add(TrendbarSubscription(1, 100, 5))
        calls = []

        async def fake_request(payload_type, payload, expected_type, **_kwargs):
            calls.append((payload_type, payload, expected_type))
            return {}

        connection._request_connected = fake_request
        await connection._restore_registry()
        assert len(calls) == 3
        assert calls[0][1]["ctidTraderAccountId"] == 1
        assert calls[1][1]["symbolId"] == [100, 200]
        assert calls[2][1]["period"] == 5

    asyncio.run(scenario())


def test_failed_account_auth_is_not_cached_as_authorized():
    async def scenario():
        connection = PersistentCTraderConnection(
            environment="DEMO", client_id="client", client_secret="secret"
        )
        connection._connected.set()
        calls = 0

        async def failed_request(*_args, **_kwargs):
            nonlocal calls
            calls += 1
            raise ValueError("CH_ACCESS_TOKEN_INVALID")

        connection.request = failed_request
        for _ in range(2):
            try:
                await connection.authorize_account(1, "bad-token")
            except ValueError:
                pass
        assert calls == 2
        assert 1 not in connection._authorized_accounts

    asyncio.run(scenario())


def test_trade_future_waits_for_fill_after_ack():
    async def scenario():
        connection = PersistentCTraderConnection(
            environment="DEMO", client_id="client", client_secret="secret"
        )
        future = asyncio.get_running_loop().create_future()
        stages = []

        async def ack(_payload):
            stages.append("ack")

        async def fill(_payload):
            stages.append("fill")

        pending = _PendingRequest(
            future=future,
            expected_types={PT_EXECUTION_EVENT},
            trade=True,
            client_order_id="AX-1",
            on_ack=ack,
            on_fill=fill,
        )
        connection._pending["request-2"] = pending
        connection._pending_by_client_order_id["AX-1"] = "request-2"
        accepted = {"executionType": 2, "order": {"clientOrderId": "AX-1"}}
        await connection._route_message({"payloadType": PT_EXECUTION_EVENT, "payload": accepted}, PT_EXECUTION_EVENT)
        assert not future.done()
        filled = {"executionType": 3, "order": {"clientOrderId": "AX-1", "orderId": 42}}
        await connection._route_message({"payloadType": PT_EXECUTION_EVENT, "payload": filled}, PT_EXECUTION_EVENT)
        assert (await future)["executionType"] == 3
        await asyncio.gather(*pending.callback_tasks)
        assert stages == ["ack", "fill"]

    asyncio.run(scenario())


def test_partial_fill_does_not_complete_order_as_fully_filled():
    async def scenario():
        connection = PersistentCTraderConnection(
            environment="DEMO", client_id="client", client_secret="secret"
        )
        future = asyncio.get_running_loop().create_future()
        fill_events = []

        async def filled(payload):
            fill_events.append(payload["executionType"])

        pending = _PendingRequest(
            future=future, expected_types={PT_EXECUTION_EVENT},
            trade=True, client_order_id="AX-partial", on_fill=filled,
        )
        connection._pending["request"] = pending
        connection._pending_by_client_order_id["AX-partial"] = "request"
        await connection._route_message({
            "payloadType": PT_EXECUTION_EVENT,
            "payload": {"executionType": 11, "order": {"clientOrderId": "AX-partial"}},
        }, PT_EXECUTION_EVENT)
        assert not future.done()
        assert pending.callback_tasks == []
        await connection._route_message({
            "payloadType": PT_EXECUTION_EVENT,
            "payload": {"executionType": 3, "order": {"clientOrderId": "AX-partial"}},
        }, PT_EXECUTION_EVENT)
        assert (await future)["executionType"] == 3
        await asyncio.gather(*pending.callback_tasks)
        assert fill_events == [3]

    asyncio.run(scenario())
