import json
import time
from datetime import datetime
from typing import Optional, Dict, Any, AsyncGenerator

from sqlalchemy.orm import Session

from config import settings
from database import SessionLocal
from models import AiCall, AiProvider


def _decrypt_key(cipher: str) -> str:
    """简易"解密"：当前直接返回明文（api_key_enc 字段存的即为明文 API Key）。
    未来若需加密可在此实现，保持 AiService 对加密逻辑无感知。"""
    return cipher or ""


class AiService:
    def __init__(self, db: Session, provider_name: Optional[str] = None, task_key: Optional[str] = None):
        self.db = db
        self.provider_name = provider_name
        self.task_key = task_key
        self._provider = None
        self._provider_row = None

    def _resolve_provider(self, task_key: str) -> AiProvider:
        """根据 task_key 解析应使用的 AiProvider 行。

        优先级：
        1. 构造时传入的 provider_name（显式指定）
        2. ai_providers 表中 is_active=true 且 task_bindings 包含 task_key 的（按 priority 升序）
        3. ai_providers 表中 is_active=true 且 task_bindings 包含 "*" 的默认 provider
        4. 配置文件中的 DEFAULT_LLM_PROVIDER
        5. 回退到 mock
        """
        if self.provider_name:
            row = self.db.query(AiProvider).filter(
                AiProvider.name == self.provider_name, AiProvider.is_active == True
            ).first()
            if row:
                return row

        candidates = self.db.query(AiProvider).filter(AiProvider.is_active == True).all()

        def binds(bindings):
            if isinstance(bindings, list):
                return set(bindings)
            if isinstance(bindings, str):
                return {x.strip() for x in bindings.split(",") if x.strip()}
            return set()

        specific = [p for p in candidates if task_key in binds(p.task_bindings)]
        if specific:
            specific.sort(key=lambda p: (p.priority or 1000, p.id))
            return specific[0]

        wildcards = [p for p in candidates if "*" in binds(p.task_bindings)]
        if wildcards:
            wildcards.sort(key=lambda p: (p.priority or 1000, p.id))
            # 配置文件里明确指定了非 mock 默认 provider，且没有 LLM key 时不要盲目用第一个
            # 如果 env 配置了 llm_api_key，优先使用名为 default_llm_provider 的那一个
            if settings.default_llm_provider and settings.default_llm_provider != "mock":
                for p in wildcards:
                    if p.name == settings.default_llm_provider:
                        return p
            for p in wildcards:
                if p.name == "mock":
                    continue
                if _decrypt_key(p.api_key_enc):
                    return p
            return wildcards[0]

        return self.db.query(AiProvider).filter(AiProvider.name == "mock").first()

    def _get_provider(self, task_key: str):
        """根据 provider 行实例化对应的 Provider 对象。"""
        from ai.mock_provider import get_provider as get_mock

        row = self._resolve_provider(task_key)
        self._provider_row = row
        if row is None or row.provider == "mock" or not _decrypt_key(row.api_key_enc):
            self.provider_name = (row.name if row else "mock")
            return get_mock()

        from ai.llm_provider import get_provider as get_llm
        timeout = settings.llm_timeout
        self.provider_name = row.name
        return get_llm(row.base_url, _decrypt_key(row.api_key_enc), row.model_name, timeout=timeout)

    def _log_call_start(
        self,
        user_id: int,
        task_key: str,
        script_id: Optional[int] = None,
        version_id: Optional[int] = None,
        request_body: Optional[dict] = None,
    ) -> AiCall:
        provider = self._provider_row
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

    def _log_call_end(self, call: AiCall, status: str = "success", error_msg: str = None,
                      latency_ms: int = 0, input_tokens: int = 0, output_tokens: int = 0):
        call.status = status
        call.error_msg = error_msg
        call.latency_ms = latency_ms
        call.input_tokens = input_tokens
        call.output_tokens = output_tokens
        self.db.commit()

    @staticmethod
    def _parse_sse_usage(chunk: str, state: dict):
        """从 SSE 文本块里提取 delta 累计字符数，以及 done 事件中的真实 usage 信息。"""
        if chunk.startswith("data:"):
            try:
                data = json.loads(chunk.split("data:", 1)[1].strip())
            except Exception:
                return
            if isinstance(data, dict) and "usage" in data and isinstance(data["usage"], dict):
                u = data["usage"]
                if u.get("prompt_tokens"):
                    state["input_tokens"] = max(state.get("input_tokens", 0), int(u["prompt_tokens"]))
                if u.get("completion_tokens"):
                    state["output_tokens"] = max(state.get("output_tokens", 0), int(u["completion_tokens"]))

    async def stream(
        self,
        task_key: str,
        method_name: str,
        params: dict,
        user_id: int,
        script_id: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        from ai.sse import sse_error

        provider = self._get_provider(task_key)
        call = self._log_call_start(
            user_id=user_id,
            task_key=task_key,
            script_id=script_id,
            request_body=params,
        )
        start = time.time()
        output_chars = 0
        state: Dict[str, Any] = {"input_tokens": 0, "output_tokens": 0}

        try:
            method = getattr(provider, method_name)
            async for chunk in method(params):
                output_chars += len(chunk)
                self._parse_sse_usage(chunk, state)
                yield chunk
            elapsed = int((time.time() - start) * 1000)
            in_tok = state["input_tokens"]
            out_tok = state["output_tokens"] or (output_chars // 4 if output_chars else 0)
            self._log_call_end(call, status="success", latency_ms=elapsed,
                               input_tokens=in_tok, output_tokens=out_tok)
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            self._log_call_end(call, status="error", error_msg=str(e), latency_ms=elapsed)
            yield sse_error(str(e))


def get_ai_service(db: Session, provider_name: Optional[str] = None, task_key: Optional[str] = None) -> AiService:
    return AiService(db, provider_name=provider_name, task_key=task_key)
