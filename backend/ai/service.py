import json
import time
from datetime import datetime
from typing import Optional, Dict, Any, AsyncGenerator

from sqlalchemy.orm import Session
from sqlalchemy import func

from database import SessionLocal
from models import AiCall, AiTask, AiProvider, User


class AiService:
    def __init__(self, db: Session, provider_name: str = "mock"):
        self.db = db
        self.provider_name = provider_name
        self._provider = None

    def _get_provider(self):
        from ai.mock_provider import get_provider
        return get_provider()

    def _log_call_start(
        self,
        user_id: int,
        task_key: str,
        script_id: Optional[int] = None,
        version_id: Optional[int] = None,
        request_body: Optional[dict] = None,
    ) -> AiCall:
        provider = self.db.query(AiProvider).filter(AiProvider.name == self.provider_name).first()
        call = AiCall(
            user_id=user_id,
            script_id=script_id,
            version_id=version_id,
            task_key=task_key,
            provider_id=provider.id if provider else None,
            model_name=provider.model_name if provider else "mock",
            status="streaming",
            request_body=request_body,
            created_at=datetime.utcnow(),
        )
        self.db.add(call)
        self.db.commit()
        self.db.refresh(call)
        return call

    def _log_call_end(self, call: AiCall, status: str = "success", error_msg: str = None, latency_ms: int = 0, input_tokens: int = 0, output_tokens: int = 0):
        call.status = status
        call.error_msg = error_msg
        call.latency_ms = latency_ms
        call.input_tokens = input_tokens
        call.output_tokens = output_tokens
        self.db.commit()

    async def stream(
        self,
        task_key: str,
        method_name: str,
        params: dict,
        user_id: int,
        script_id: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        from ai.sse import sse_event, sse_done, sse_error
        import asyncio

        call = self._log_call_start(
            user_id=user_id,
            task_key=task_key,
            script_id=script_id,
            request_body=params,
        )
        start = time.time()
        output_chars = 0

        try:
            provider = self._get_provider()
            method = getattr(provider, method_name)
            async for chunk in method(params):
                output_chars += len(chunk)
                yield chunk
            elapsed = int((time.time() - start) * 1000)
            self._log_call_end(call, status="success", latency_ms=elapsed, output_tokens=output_chars // 4)
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            self._log_call_end(call, status="error", error_msg=str(e), latency_ms=elapsed)
            yield sse_error(str(e))


def get_ai_service(db: Session, provider_name: str = "mock") -> AiService:
    return AiService(db, provider_name)
