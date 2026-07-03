"""GenerationGate unit tests - concurrency cap, queue-full, FIFO, positions."""

from __future__ import annotations

import asyncio

import pytest

from app.services.generation_gate import GenerationGate, QueueFull

pytestmark = pytest.mark.asyncio


async def test_admits_up_to_max_concurrent_without_queueing():
    gate = GenerationGate(max_concurrent=2, max_queue=2)
    t1 = await gate.admit()
    t2 = await gate.admit()
    assert not t1.queued and not t2.queued
    assert gate.running == 2


async def test_queue_full_raises_busy():
    gate = GenerationGate(max_concurrent=1, max_queue=1)
    running = await gate.admit()       # occupies the only slot
    queued = await gate.admit()        # fills the only queue spot
    assert queued.queued
    with pytest.raises(QueueFull):
        await gate.admit()             # running + queue at capacity -> busy
    await running.release()
    await queued.release()


async def test_release_promotes_queued_ticket():
    gate = GenerationGate(max_concurrent=1, max_queue=3)
    running = await gate.admit()
    queued = await gate.admit()
    agen = queued.wait_for_slot()
    pos = await agen.__anext__()
    assert pos == 1                    # waiting at position 1
    await running.release()            # frees the slot -> promotes `queued`
    with pytest.raises(StopAsyncIteration):
        await agen.__anext__()         # promoted: no more positions
    assert not queued.queued
    await queued.release()


async def test_fifo_ordering():
    gate = GenerationGate(max_concurrent=1, max_queue=5)
    running = await gate.admit()
    order: list[int] = []

    async def worker(n: int) -> None:
        ticket = await gate.admit()
        async for _ in ticket.wait_for_slot():
            pass
        order.append(n)
        await ticket.release()

    tasks = [asyncio.create_task(worker(i)) for i in range(3)]
    await asyncio.sleep(0.05)          # let all three queue in creation order
    await running.release()            # drains the queue one at a time
    await asyncio.gather(*tasks)
    assert order == [0, 1, 2]


async def test_no_queue_event_under_free_capacity():
    gate = GenerationGate(max_concurrent=2, max_queue=2)
    ticket = await gate.admit()
    positions = [p async for p in ticket.wait_for_slot()]
    assert positions == []             # ran immediately, no waiting positions
    await ticket.release()


async def test_promoted_then_disconnected_release_frees_slot():
    """BC3 regression: a promoted-but-never-observed ticket must free its slot.

    ``_pump`` promotes a queued waiter (pops it, ``_running += 1``,
    ``waiter.promoted = True``) but the client can disconnect BEFORE
    ``wait_for_slot()`` resumes to copy the promotion onto ``ticket._promoted``.
    Release must still decrement ``_running`` (honouring ``waiter.promoted``),
    otherwise the slot leaks permanently and the gate bricks at capacity.
    """
    gate = GenerationGate(max_concurrent=1, max_queue=3)
    running = await gate.admit()
    queued = await gate.admit()
    agen = queued.wait_for_slot()
    assert await agen.__anext__() == 1          # waiting at position 1

    # Free the only slot: _pump promotes `queued` (waiter.promoted -> True,
    # _running stays at 1) but we DO NOT resume `agen`, modelling a client that
    # disconnected the instant it was promoted.
    await running.release()
    assert queued._waiter.promoted is True      # gate promoted it
    assert queued._promoted is False            # ticket never observed it
    assert gate.running == 1                     # slot held by the gone client

    # The stream teardown's `finally: await ticket.release()` runs on disconnect.
    await queued.release()
    assert gate.running == 0                      # no leak

    # Gate is not bricked: a fresh request is admitted to run immediately.
    fresh = await gate.admit()
    assert not fresh.queued
    assert gate.running == 1
    await fresh.release()
    assert gate.running == 0


async def test_release_survives_task_cancellation():
    """BC3 regression: release is shielded, so cancelling the releasing task
    (as happens when a client disconnect cancels the SSE task at teardown) must
    not lose the slot accounting."""
    gate = GenerationGate(max_concurrent=1, max_queue=1)
    running = await gate.admit()
    assert gate.running == 1

    async def releaser() -> None:
        await running.release()

    task = asyncio.create_task(releaser())
    await asyncio.sleep(0)          # let releaser reach the shielded await
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    # Despite the cancellation, the shielded release ran to completion.
    await asyncio.sleep(0.01)
    assert gate.running == 0
