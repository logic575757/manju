"""通用 LLM Provider —— OpenAI 兼容协议，支持动态从 DB 读取 skill 配置。

设计：
- 底层 _chat() 直接对接 /chat/completions 流式 SSE，yield {delta}|{usage,full_text}
- _extract_json() 鲁棒提取 JSON（支持 ```json 包裹 / 括号不闭合兜底）
- run_skill() 是统一入口：传入 AiSkill 行 + PromptTemplate 行 + params，
  负责模板渲染 → 流式 phase/delta → JSON 解析 → 可选 result_key 包装 → progress 事件 → done/error
- 所有 11 个 skill 共用同一个 run_skill()，不再需要为每个 skill 写一个方法；
  skill 的差异化完全通过 DB 中的 prompt 模板 + temperature + result_key 配置实现。
- 如果需要添加新 skill：在 ai/skills_registry.py 加一条元数据+prompt，跑 seed.py，即可生效。
"""
from __future__ import annotations

import json
import re
import time
from typing import AsyncGenerator, Any, Dict, Optional

import httpx

from ai.sse import sse_event, sse_done, sse_error


class LLMProvider:
    """OpenAI 兼容协议 LLM Provider（DeepSeek/豆包/Qwen/智谱/Moonshot/Ollama/vLLM/one-api 等）。"""

    def __init__(self, base_url: str, api_key: str, model: str, timeout: int = 240):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    # ==================== 底层 HTTP 流式调用 ====================

    async def _chat(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        json_mode: bool = True,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        body: Dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": True,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}

        full_text_parts: list[str] = []
        usage: Dict[str, int] = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", url, headers=headers, json=body) as resp:
                if resp.status_code != 200:
                    err_text = await resp.aread()
                    raise RuntimeError(f"LLM HTTP {resp.status_code}: {err_text[:500]}")
                async for raw_line in resp.aiter_lines():
                    line = raw_line.strip()
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    u = chunk.get("usage")
                    if isinstance(u, dict):
                        for k in ("prompt_tokens", "completion_tokens", "total_tokens"):
                            if u.get(k):
                                usage[k] = max(usage[k], int(u[k]))
                    choices = chunk.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta") or {}
                    content = delta.get("content")
                    if content:
                        full_text_parts.append(content)
                        yield {"delta": content}

        yield {"usage": usage, "full_text": "".join(full_text_parts)}

    @staticmethod
    def _extract_json(text: str) -> Any:
        if not text or not text.strip():
            raise ValueError("模型返回为空")
        text = text.strip()
        m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if m:
            text = m.group(1).strip()
        first_obj = text.find("{")
        first_arr = text.find("[")
        starts = [i for i in (first_obj, first_arr) if i != -1]
        if not starts:
            raise ValueError(f"无法解析 JSON: {text[:200]}")
        start = min(starts)
        open_ch = text[start]
        close_ch = "}" if open_ch == "{" else "]"
        depth = 0
        in_str = False
        escape = False
        for i in range(start, len(text)):
            ch = text[i]
            if in_str:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_str = False
            else:
                if ch == '"':
                    in_str = True
                elif ch == open_ch:
                    depth += 1
                elif ch == close_ch:
                    depth -= 1
                    if depth == 0:
                        return json.loads(text[start : i + 1])
        return json.loads(text[start:])

    # ==================== Prompt 模板渲染 ====================

    @staticmethod
    def _render_template(template: str, context: Dict[str, Any]) -> str:
        """把 template 中的 {key} / {key.sub} 占位符替换成 context 中的 JSON 字符串。"""
        def _repl(m: re.Match) -> str:
            key = m.group(1).strip()
            parts = key.split(".")
            v: Any = context
            for p in parts:
                if isinstance(v, dict):
                    v = v.get(p)
                else:
                    v = None
                    break
            if v is None:
                return ""
            if isinstance(v, (dict, list)):
                return json.dumps(v, ensure_ascii=False, indent=2)
            return str(v)

        return re.sub(r"\{([a-zA-Z_][\w.]*(?:_json)?)\}", _repl, template)

    # ==================== 统一 skill 入口 ====================

    async def run_skill(
        self,
        task_key: str,
        params: Dict[str, Any],
        skill_meta: Dict[str, Any],
        system_prompt: str,
        user_prompt_template: str,
    ) -> AsyncGenerator[str, None]:
        """通用 skill 执行流程。

        params: API 层传入的原始参数（dict）
        skill_meta: AiSkill 行上的关键字段（temperature/result_key/stream_progress/name 等）
        system_prompt / user_prompt_template: 从 prompt_templates 表读出的模板
        """
        temperature = float(skill_meta.get("temperature", 0.7))
        result_key = skill_meta.get("result_key")
        stream_progress = bool(skill_meta.get("stream_progress", False))
        phase_name = skill_meta.get("name", task_key)
        max_tokens = int(skill_meta.get("max_tokens", 4096))

        # 准备渲染上下文：把 params 展平，并把复杂对象额外提供 *_json 版本
        ctx: Dict[str, Any] = dict(params or {})
        for k, v in list(ctx.items()):
            if isinstance(v, (dict, list)):
                ctx[f"{k}_json"] = v
        ctx.setdefault("config_json", params.get("config") if isinstance(params.get("config"), dict) else params)

        user_prompt = self._render_template(user_prompt_template, ctx)

        yield sse_event("phase", {"phase": "thinking", "message": f"正在{phase_name}..."})

        full_text_parts: list[str] = []
        usage: Dict[str, int] = {}
        t0 = time.time()
        try:
            async for item in self._chat(system_prompt, user_prompt, temperature=temperature, max_tokens=max_tokens):
                if "delta" in item:
                    full_text_parts.append(item["delta"])
                    yield sse_event("delta", {"text": item["delta"]})
                else:
                    usage = item.get("usage", usage)

            try:
                parsed = self._extract_json("".join(full_text_parts))
            except Exception as e:
                snippet = "".join(full_text_parts)
                yield sse_error(f"输出 JSON 解析失败：{e}; 原始片段: {snippet[:600]}")
                return

            # 对于 stream_progress 的 skill（如 batch_modify），结果是一个列表，发出进度事件
            if stream_progress and isinstance(parsed, dict):
                items_to_progress = None
                total_field = None
                for candidate_key in ("modules", "characters", "candidates", "issues"):
                    if candidate_key in parsed and isinstance(parsed[candidate_key], list):
                        items_to_progress = parsed[candidate_key]
                        total_field = candidate_key
                        break
                if items_to_progress is not None:
                    for i, it in enumerate(items_to_progress):
                        item_id = ""
                        if isinstance(it, dict):
                            item_id = it.get("id") or it.get("moduleId") or it.get("characterId") or ""
                        yield sse_event("progress", {
                            "current": i + 1,
                            "total": len(items_to_progress),
                            "field": total_field,
                            "item_id": item_id,
                        })

            # 包装 result_key（如果配置了）
            if result_key:
                if isinstance(parsed, dict) and result_key in parsed and len(parsed) <= 5:
                    result = parsed
                else:
                    result = {result_key: parsed}
            else:
                result = parsed if isinstance(parsed, dict) else {"result": parsed}

            elapsed = int((time.time() - t0) * 1000)
            yield sse_event("result", result)
            yield sse_done({
                **(result if isinstance(result, dict) else {"result": result}),
                "usage": usage,
                "elapsed_ms": elapsed,
            })
        except Exception as e:
            yield sse_error(str(e))


_provider_singleton: Optional["LLMProvider"] = None


def get_provider(base_url: str, api_key: str, model: str, timeout: int = 240) -> LLMProvider:
    global _provider_singleton
    if (
        _provider_singleton is None
        or _provider_singleton.base_url != base_url.rstrip("/")
        or _provider_singleton.api_key != api_key
        or _provider_singleton.model != model
    ):
        _provider_singleton = LLMProvider(base_url, api_key, model, timeout=timeout)
    return _provider_singleton
