import asyncio
import json
import time
import traceback
from datetime import datetime
from typing import Optional, Dict, Any

import httpx

from config import settings
from database import SessionLocal
from models import (
    AiTask, AiCall,
    TASK_STATUS_SUCCESS,
    ERROR_CLASS_NETWORK, ERROR_CLASS_TIMEOUT, ERROR_CLASS_RATE_LIMIT,
    ERROR_CLASS_AUTH, ERROR_CLASS_BAD_REQUEST, ERROR_CLASS_PARSE,
    ERROR_CLASS_PROVIDER, ERROR_CLASS_UNKNOWN, ERROR_CLASS_CANCELLED,
)
from ai.queue import get_queue, TaskQueue
from ai.service import AiService


TASK_KEY_TO_METHOD = {
    "generate_outline": "generate_outline",
    "review_outline": "review_outline",
    "modify_outline_module": "modify_module",
    "batch_modify_outline": "batch_modify",
    "generate_characters": "generate_characters",
    "review_characters": "review_characters",
    "generate_episode": "generate_episode",
    "review_episode": "review_episode",
    "fix_episode": "fix_episode",
    "rewrite_segment": "rewrite_segment",
    "parse_import": "parse_import",
}


def classify_error(e: Exception) -> str:
    msg = str(e).lower()
    if isinstance(e, asyncio.CancelledError):
        return ERROR_CLASS_CANCELLED
    if isinstance(e, asyncio.TimeoutError) or "timeout" in msg or "timed out" in msg:
        return ERROR_CLASS_TIMEOUT
    if isinstance(e, httpx.NetworkError) or "connection" in msg or "dns" in msg or "reset" in msg:
        return ERROR_CLASS_NETWORK
    if isinstance(e, httpx.HTTPStatusError):
        code = e.response.status_code if hasattr(e, "response") else 0
        if code in (401, 403):
            return ERROR_CLASS_AUTH
        if code == 400:
            return ERROR_CLASS_BAD_REQUEST
        if code in (429, 529):
            return ERROR_CLASS_RATE_LIMIT
        if code >= 500:
            return ERROR_CLASS_PROVIDER
    if "json" in msg or "parse" in msg or "decode" in msg:
        return ERROR_CLASS_PARSE
    if "rate" in msg or "too many" in msg or "429" in msg:
        return ERROR_CLASS_RATE_LIMIT
    if "auth" in msg or "api key" in msg or "unauthorized" in msg or "forbidden" in msg:
        return ERROR_CLASS_AUTH
    return ERROR_CLASS_UNKNOWN


def is_retryable(error_class: str) -> bool:
    return error_class in (ERROR_CLASS_NETWORK, ERROR_CLASS_TIMEOUT, ERROR_CLASS_RATE_LIMIT, ERROR_CLASS_PROVIDER)


class WorkerPool:
    def __init__(self, concurrency: Optional[int] = None):
        self.concurrency = concurrency or settings.queue_max_concurrency
        self.queue: TaskQueue = get_queue()
        self._tasks = []
        self._stop = asyncio.Event()

    async def start(self):
        for i in range(self.concurrency):
            self._tasks.append(asyncio.create_task(self._worker_loop(i)))

    async def stop(self):
        self._stop.set()
        for t in self._tasks:
            t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)

    async def _worker_loop(self, idx: int):
        while not self._stop.is_set():
            try:
                await self._drain_one()
            except Exception as e:
                print(f"[worker-{idx}] drain error: {e}")
                traceback.print_exc()
                await asyncio.sleep(2)
            await asyncio.sleep(settings.queue_poll_interval)

    async def _drain_one(self):
        db = SessionLocal()
        try:
            task = self.queue.claim_next(db)
            if task is None:
                return
            await self._run_task(task.id)
        finally:
            db.close()

    async def _run_task(self, task_id: int):
        db = SessionLocal()
        call_row: Optional[AiCall] = None
        start = time.time()
        exec_start = time.time()
        error_class: Optional[str] = None
        error_msg: Optional[str] = None
        state = {"input_tokens": 0, "output_tokens": 0}
        result_json = None
        result_text_parts = []
        cancelled = False

        try:
            task = db.query(AiTask).filter(AiTask.id == task_id).first()
            if not task:
                return
            if task.status == "cancelled":
                return

            svc = AiService(db)
            method_name = TASK_KEY_TO_METHOD.get(task.task_key)
            if not method_name:
                raise RuntimeError(f"未知 task_key: {task.task_key}")

            svc._get_provider(task.task_key)
            provider_row = svc._provider_row
            task.provider_id = provider_row.id if provider_row else None
            task.provider_name = provider_row.name if provider_row else "mock"
            task.model_name = provider_row.model_name if provider_row else "mock"
            db.commit()

            call_row = AiCall(
                queue_task_id=task.id,
                user_id=task.user_id,
                script_id=task.script_id,
                version_id=task.version_id,
                task_key=task.task_key,
                provider_id=task.provider_id,
                provider_name=task.provider_name,
                model_name=task.model_name or "mock",
                status="streaming",
                request_body=task.params,
                attempt=task.attempts,
                queue_wait_ms=task.queue_wait_ms,
                created_at=datetime.utcnow(),
            )
            db.add(call_row)
            db.commit()
            db.refresh(call_row)

            exec_start = time.time()
            last_heartbeat = time.time()

            provider = svc._get_provider(task.task_key)
            method = getattr(provider, method_name)

            provider_error: Optional[str] = None

            async with asyncio.timeout(settings.queue_task_timeout):
                async for chunk in method(task.params or {}):
                    db.expire_all()
                    task = db.query(AiTask).filter(AiTask.id == task_id).first()
                    if not task or task.status == "cancelled":
                        cancelled = True
                        raise asyncio.CancelledError()

                    if chunk.startswith("event:"):
                        lines = chunk.splitlines()
                        ev_type = ""
                        data = ""
                        for line in lines:
                            if line.startswith("event:"):
                                ev_type = line.split("event:", 1)[1].strip()
                            elif line.startswith("data:"):
                                data = line.split("data:", 1)[1].strip()
                        if ev_type == "phase":
                            try:
                                payload = json.loads(data)
                                phase_text = payload.get("phase") or payload.get("message", "")
                                prog = payload.get("progress")
                                self.queue.emit_phase(db, task_id, phase_text, progress=prog)
                            except Exception:
                                self.queue.emit_phase(db, task_id, data)
                        elif ev_type == "progress":
                            try:
                                payload = json.loads(data)
                                cur = payload.get("current")
                                tot = payload.get("total")
                                if isinstance(cur, int) and isinstance(tot, int) and tot > 0:
                                    pct = min(99, int(cur * 99 / tot))
                                else:
                                    pct = int(payload.get("progress", 0) or 0)
                                self.queue.emit_progress(db, task_id, pct, phase=payload.get("phase"))
                            except Exception:
                                pass
                        elif ev_type == "delta":
                            try:
                                payload = json.loads(data)
                                txt = payload.get("text") or payload.get("delta", "")
                            except Exception:
                                txt = data
                            if txt:
                                result_text_parts.append(txt)
                                self.queue.emit_delta(db, task_id, txt)
                        elif ev_type == "result":
                            try:
                                result_json = json.loads(data)
                            except Exception:
                                result_json = data
                        elif ev_type == "done":
                            try:
                                payload = json.loads(data)
                                if isinstance(payload, dict):
                                    u = payload.get("usage")
                                    if isinstance(u, dict):
                                        if u.get("prompt_tokens"):
                                            state["input_tokens"] = max(state["input_tokens"], int(u["prompt_tokens"]))
                                        if u.get("completion_tokens"):
                                            state["output_tokens"] = max(state["output_tokens"], int(u["completion_tokens"]))
                                    if result_json is None:
                                        result_json = {k: v for k, v in payload.items()
                                                       if k not in ("usage", "elapsed_ms")}
                            except Exception:
                                pass
                        elif ev_type == "error":
                            try:
                                payload = json.loads(data)
                                provider_error = payload.get("message", data) if isinstance(payload, dict) else data
                            except Exception:
                                provider_error = data
                        self._extract_usage(chunk, state)

                    if time.time() - last_heartbeat > settings.queue_heartbeat_interval:
                        self.queue.heartbeat(db, task_id)
                        last_heartbeat = time.time()

            if provider_error:
                raise RuntimeError(provider_error)

            exec_ms = int((time.time() - exec_start) * 1000)
            in_tok = state["input_tokens"]
            out_tok = state["output_tokens"] or (sum(len(p) for p in result_text_parts) // 4)
            result_text = "".join(result_text_parts)
            if result_json is None and result_text:
                try:
                    stripped = result_text.strip()
                    if stripped.startswith("```"):
                        lines = stripped.splitlines()
                        if lines and lines[0].startswith("```"):
                            lines = lines[1:]
                        if lines and lines[-1].strip().startswith("```"):
                            lines = lines[:-1]
                        stripped = "\n".join(lines).strip()
                    result_json = json.loads(stripped)
                except Exception:
                    result_json = None

            self.queue.mark_success(
                db, task_id,
                result_json=result_json, result_text=result_text,
                input_tokens=in_tok, output_tokens=out_tok,
                exec_ms=exec_ms,
            )
            if call_row is not None:
                call_row.status = "success"
                call_row.latency_ms = exec_ms
                call_row.input_tokens = in_tok
                call_row.output_tokens = out_tok
                db.commit()

        except asyncio.CancelledError:
            exec_ms = int((time.time() - exec_start) * 1000)
            cancelled = True
            self.queue.mark_failed(db, task_id, ERROR_CLASS_CANCELLED, "任务已取消",
                                   will_retry=False, exec_ms=exec_ms)
            if call_row is not None:
                call_row.status = "cancelled"
                call_row.error_class = ERROR_CLASS_CANCELLED
                call_row.error_msg = "任务已取消"
                call_row.latency_ms = exec_ms
                db.commit()
        except Exception as e:
            exec_ms = int((time.time() - exec_start) * 1000)
            error_class = classify_error(e)
            error_msg = f"{type(e).__name__}: {e}"
            task = db.query(AiTask).filter(AiTask.id == task_id).first()
            will_retry = is_retryable(error_class) and task and task.attempts < task.max_retries
            self.queue.mark_failed(db, task_id, error_class, error_msg,
                                   will_retry=will_retry, exec_ms=exec_ms)
            if call_row is not None:
                call_row.status = "error" if not will_retry else "retry"
                call_row.error_class = error_class
                call_row.error_msg = error_msg
                call_row.latency_ms = exec_ms
                db.commit()
        finally:
            db.close()

    @staticmethod
    def _extract_usage(chunk: str, state: dict):
        if "usage" not in chunk:
            return
        try:
            for line in chunk.splitlines():
                if line.startswith("data:"):
                    raw = line.split("data:", 1)[1].strip()
                    if raw in ("[DONE]", ""):
                        continue
                    data = json.loads(raw)
                    u = data.get("usage") if isinstance(data, dict) else None
                    if isinstance(u, dict):
                        if u.get("prompt_tokens"):
                            state["input_tokens"] = max(state["input_tokens"], int(u["prompt_tokens"]))
                        if u.get("completion_tokens"):
                            state["output_tokens"] = max(state["output_tokens"], int(u["completion_tokens"]))
        except Exception:
            pass


_pool_instance: Optional[WorkerPool] = None


async def start_workers():
    global _pool_instance
    if _pool_instance is not None:
        return
    _pool_instance = WorkerPool()
    await _pool_instance.start()
    print(f"[queue] Worker pool started, concurrency={_pool_instance.concurrency}")


async def stop_workers():
    global _pool_instance
    if _pool_instance is not None:
        await _pool_instance.stop()
        _pool_instance = None
