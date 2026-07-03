"""Global concurrency limiter + FIFO queue for generations.

A public demo must bound RAM: only a few generations may run at once. This gate
admits up to ``max_concurrent`` concurrent generations; excess requests wait in a
bounded FIFO queue (streamed their position); beyond the queue limit a request is
cleanly rejected as "busy".

Usage (in the SSE endpoint):

    try:
        ticket = await gate.admit()
    except QueueFull:
        ... emit busy ...; return
    async for position in ticket.wait_for_slot():
        ... emit queue position ...
    try:
        ... run generation ...
    finally:
        await ticket.release()

Everything is asyncio-single-threaded; the small critical sections are guarded by
an ``asyncio.Lock`` so admit/release/promote stay consistent.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field


class QueueFull(Exception):
    """Raised by ``admit()`` when running + queued is at the hard limit."""


@dataclass(slots=True)
class _Waiter:
    event: asyncio.Event = field(default_factory=asyncio.Event)
    promoted: bool = False


class Ticket:
    """Admission ticket. Either running immediately or queued behind others."""

    def __init__(self, gate: GenerationGate, waiter: _Waiter | None) -> None:
        self._gate = gate
        self._waiter = waiter
        self._promoted = waiter is None  # waiter is None => admitted as running
        self._released = False

    @property
    def queued(self) -> bool:
        return self._waiter is not None and not self._promoted

    async def wait_for_slot(self) -> AsyncIterator[int]:
        """Yield the 1-based queue position until a slot is acquired.

        Yields nothing when the ticket was admitted to run immediately (so a
        request under free capacity sees no queue events at all).
        """
        if self._waiter is None:
            return
        last = -1
        while True:
            pos = self._gate._position(self._waiter)
            if pos == 0 or self._waiter.promoted:
                self._promoted = True
                return
            if pos != last:
                last = pos
                yield pos
            await self._waiter.event.wait()
            self._waiter.event.clear()

    async def release(self) -> None:
        if self._released:
            return
        self._released = True
        # Shield the release so a cancellation at teardown (client disconnect
        # cancels the SSE task, unwinding this `finally`) cannot interrupt the
        # slot accounting before it completes. Losing a release permanently
        # leaks a running slot and, at GEN_MAX_CONCURRENT, bricks /chat.
        await asyncio.shield(self._gate._release(self))


class GenerationGate:
    """Concurrency semaphore + bounded FIFO queue."""

    def __init__(self, *, max_concurrent: int, max_queue: int) -> None:
        self.max_concurrent = max(1, int(max_concurrent))
        self.max_queue = max(0, int(max_queue))
        self._running = 0
        self._waiters: list[_Waiter] = []
        self._lock = asyncio.Lock()

    @property
    def running(self) -> int:
        return self._running

    @property
    def queued(self) -> int:
        return len(self._waiters)

    async def admit(self) -> Ticket:
        async with self._lock:
            if self._running < self.max_concurrent:
                self._running += 1
                return Ticket(self, waiter=None)
            if len(self._waiters) >= self.max_queue:
                raise QueueFull()
            waiter = _Waiter()
            self._waiters.append(waiter)
            return Ticket(self, waiter=waiter)

    def _position(self, waiter: _Waiter) -> int:
        if waiter.promoted:
            return 0
        try:
            return self._waiters.index(waiter) + 1
        except ValueError:
            return 0

    def _pump(self) -> None:
        # Promote queued waiters while there is capacity.
        while self._waiters and self._running < self.max_concurrent:
            waiter = self._waiters.pop(0)
            self._running += 1
            waiter.promoted = True
            waiter.event.set()
        # Wake the rest so they refresh their (now smaller) position.
        for waiter in self._waiters:
            waiter.event.set()

    async def _release(self, ticket: Ticket) -> None:
        async with self._lock:
            # A ticket holds a running slot if EITHER it observed its own
            # promotion (``ticket._promoted``) OR the gate promoted its waiter.
            # ``waiter.promoted`` is the AUTHORITATIVE signal: ``_pump`` sets it
            # (and increments ``_running``) while popping the waiter out of the
            # queue, but the client may disconnect before ``wait_for_slot()``
            # resumes to copy that promotion onto ``ticket._promoted``. Keying
            # release off ``ticket._promoted`` alone would then match neither
            # branch and silently leak the slot (BC3).
            holds_slot = ticket._promoted or (
                ticket._waiter is not None and ticket._waiter.promoted
            )
            if holds_slot:
                # The ticket was occupying a running slot.
                self._running = max(0, self._running - 1)
            elif ticket._waiter is not None and ticket._waiter in self._waiters:
                # Released while still queued (e.g. client disconnect).
                self._waiters.remove(ticket._waiter)
            self._pump()
