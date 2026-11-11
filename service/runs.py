"""A bounded, local research worker; event readers never own the work."""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from time import monotonic
from uuid import uuid4

from agents.graph_agent import CryptoAnalysisGraph
from service.store import ACTIVE_STATES, ReportStore

log = logging.getLogger(__name__)


class QueueFullError(Exception):
    pass


class ResearchRuns:
    def __init__(self, store: ReportStore):
        self.store = store
        self.queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=8)
        self.lock = asyncio.Lock()

    @asynccontextmanager
    async def lifespan(self, _app):
        await asyncio.to_thread(self.store.interrupt_runs)
        worker = asyncio.create_task(self._work())
        try:
            yield
        finally:
            worker.cancel()
            with suppress(asyncio.CancelledError):
                await worker
            await asyncio.to_thread(self.store.interrupt_runs)
            while not self.queue.empty():
                self.queue.get_nowait()
                self.queue.task_done()

    async def submit(self, symbol: str, demo_mode: bool) -> dict:
        async with self.lock:
            if self.queue.full():
                raise QueueFullError
            run = await asyncio.to_thread(self.store.create_run, str(uuid4()), symbol, demo_mode)
            self.queue.put_nowait(run)
            return run

    async def _work(self):
        while True:
            run = await self.queue.get()
            run_id = run["run_id"]

            async def progress(data):
                await asyncio.to_thread(self.store.record_progress, run_id, data)

            try:
                if not await asyncio.to_thread(self.store.start_run, run_id):
                    continue
                agent = CryptoAnalysisGraph(verbose=False, demo_mode=run["demo_mode"])
                async with asyncio.timeout(720):
                    report = await agent.arun(run["symbol"], run_id=run_id, on_progress=progress)
                await asyncio.to_thread(self.store.finish_run, run_id, report)
            except Exception as exc:
                log.error("Research %s failed (%s)", run_id, type(exc).__name__)
                error = "timeout" if isinstance(exc, TimeoutError) else "execution_failed"
                await asyncio.to_thread(self.store.finish_run, run_id, error=error)
            finally:
                self.queue.task_done()

    async def events(self, run_id: str, cursor: int) -> AsyncIterator[str]:
        yield "retry: 1500\n\n"
        keepalive = monotonic() + 15
        while True:
            run, events = await asyncio.to_thread(self.store.events_after, run_id, cursor)
            for seq, kind, data in events:
                yield f"id: {seq}\nevent: {kind}\ndata: {data}\n\n"
                cursor = seq
                keepalive = monotonic() + 15
                if kind == "terminal":
                    return
            if run is None or (run["state"] not in ACTIVE_STATES and cursor >= run["cursor"]):
                return
            if not events:
                if monotonic() >= keepalive:
                    yield ": keepalive\n\n"
                    keepalive = monotonic() + 15
                await asyncio.sleep(0.25)
