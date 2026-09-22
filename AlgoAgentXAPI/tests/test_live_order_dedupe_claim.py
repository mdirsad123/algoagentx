import asyncio

from app.services.live.live_event_bus import LiveEventBus


class _Redis:
    def __init__(self):
        self.values = {}

    async def set(self, key, value, **kwargs):
        if kwargs.get("nx") and key in self.values:
            return False
        self.values[key] = value
        return True

    async def get(self, key):
        return self.values.get(key)


def test_only_one_worker_can_claim_identical_broker_side_effect():
    async def scenario():
        bus = LiveEventBus(_Redis())
        first, second = await asyncio.gather(
            bus.claim_order_dedupe("same-order", "request-a"),
            bus.claim_order_dedupe("same-order", "request-b"),
        )
        assert sorted((first, second)) == [False, True]
        assert bus.order_dedupe_in_progress(await bus.get_order_dedupe("same-order"))

    asyncio.run(scenario())
