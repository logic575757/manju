import json
import time
from typing import AsyncGenerator, Any, Dict, Optional


def sse_event(event: str, data: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def sse_done(data: Optional[Dict] = None) -> str:
    payload = data or {"status": "done"}
    return f"event: done\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def sse_error(message: str, code: str = "error") -> str:
    return f"event: error\ndata: {json.dumps({'message': message, 'code': code}, ensure_ascii=False)}\n\n"


async def stream_text_chunks(
    text: str,
    chunk_size: int = 4,
    delay_ms: int = 15,
    event: str = "delta",
) -> AsyncGenerator[str, None]:
    import asyncio
    buf = ""
    for ch in text:
        buf += ch
        if len(buf) >= chunk_size or ch in "\n。！？；，":
            yield sse_event(event, {"text": buf})
            buf = ""
            await asyncio.sleep(delay_ms / 1000.0)
    if buf:
        yield sse_event(event, {"text": buf})


async def stream_object(
    obj: Any,
    delay_ms: int = 20,
    event: str = "delta",
    field: str = "text",
) -> AsyncGenerator[str, None]:
    text = json.dumps(obj, ensure_ascii=False) if not isinstance(obj, str) else obj
    async for chunk in stream_text_chunks(text, chunk_size=6, delay_ms=delay_ms, event=event):
        yield chunk


async def stream_phases(
    phases: list,
) -> AsyncGenerator[str, None]:
    import asyncio
    for phase in phases:
        event_type = phase.get("event", "phase")
        yield sse_event(event_type, phase.get("data", {}))
        wait_ms = phase.get("wait_ms", 200)
        if wait_ms > 0:
            await asyncio.sleep(wait_ms / 1000.0)
        text = phase.get("text")
        if text:
            async for chunk in stream_text_chunks(text, delay_ms=phase.get("delay_ms", 12)):
                yield chunk
