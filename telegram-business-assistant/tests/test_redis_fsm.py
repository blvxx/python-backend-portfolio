"""Integration tests for Redis-backed FSM persistence across instances."""

import asyncio  # noqa: I001
import os
import uuid

import pytest
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from src.states import RequestFlow


REDIS_URL = os.getenv("REDIS_URL")
pytestmark = pytest.mark.skipif(not REDIS_URL, reason="REDIS_URL is not configured")


@pytest.mark.asyncio
async def test_fsm_state_survives_storage_reconnect_and_is_shared() -> None:
    assert REDIS_URL is not None
    key = StorageKey(
        bot_id=910001,
        chat_id=920000 + uuid.uuid4().int % 100000,
        user_id=930001,
    )
    redis_one = Redis.from_url(REDIS_URL, decode_responses=True)
    redis_two = Redis.from_url(REDIS_URL, decode_responses=True)
    first = RedisStorage(redis=redis_one)
    second = RedisStorage(redis=redis_two)

    try:
        await first.set_state(key, RequestFlow.waiting_contact)
        await first.set_data(key, {"selected_service": "Support"})

        assert await second.get_state(key) == RequestFlow.waiting_contact.state
        assert await second.get_data(key) == {"selected_service": "Support"}

        first_isolation = first.create_isolation()
        second_isolation = second.create_isolation()
        order: list[str] = []
        first_acquired = asyncio.Event()
        release_first = asyncio.Event()

        async def hold_first_lock() -> None:
            async with first_isolation.lock(key):
                order.append("first")
                first_acquired.set()
                await release_first.wait()

        async def wait_for_second_lock() -> None:
            await first_acquired.wait()
            async with second_isolation.lock(key):
                order.append("second")

        first_task = asyncio.create_task(hold_first_lock())
        await first_acquired.wait()
        second_task = asyncio.create_task(wait_for_second_lock())
        await asyncio.sleep(0.05)
        assert order == ["first"]
        release_first.set()
        await asyncio.gather(first_task, second_task)
        assert order == ["first", "second"]

        await first.close()
        first = RedisStorage(
            redis=Redis.from_url(REDIS_URL, decode_responses=True)
        )
        assert await first.get_state(key) == RequestFlow.waiting_contact.state
        assert await first.get_data(key) == {"selected_service": "Support"}
    finally:
        await first.set_state(key, None)
        await first.set_data(key, {})
        await first.close()
        await second.close()
