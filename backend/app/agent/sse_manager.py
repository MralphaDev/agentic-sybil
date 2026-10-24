
# app/agent/sse_manager.py

import asyncio
import json
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Callable


EventCallback = Callable[[str, Any], None]

_current_event_callback: ContextVar[EventCallback | None] = ContextVar(
    "current_event_callback",
    default=None,
)


def get_current_event_callback() -> EventCallback | None:
    return _current_event_callback.get()


def set_current_event_callback(callback: EventCallback):
    return _current_event_callback.set(callback)


def reset_current_event_callback(token) -> None:
    _current_event_callback.reset(token)


class InvestigationRun:
    def __init__(self, run_id: str):
        self.run_id = run_id
        self.queue: asyncio.Queue[dict] = asyncio.Queue()
        self.result: Any = None
        self.error: str | None = None
        self.status = "starting"
        self.created_at = datetime.now(timezone.utc).isoformat()

    async def emit(self, event_type: str, data: Any = None):
        await self.queue.put({
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data,
        })


runs: dict[str, InvestigationRun] = {}


def create_run() -> InvestigationRun:
    run_id = str(uuid.uuid4())
    run = InvestigationRun(run_id)
    runs[run_id] = run
    return run


def get_run(run_id: str) -> InvestigationRun | None:
    return runs.get(run_id)


def encode_sse(event: dict) -> str:
    return f"data: {json.dumps(event, default=str)}\n\n"
