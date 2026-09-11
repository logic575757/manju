import json
import re
import time
from typing import AsyncGenerator, Any, Dict, Optional

import httpx

from ai.sse import sse_event, sse_done, sse_error


class LLMProvider:
    """OpenAI 兼容协议的 LLM Provider（支持流式 SSE、JSON 输出）。

    兼容 OpenAI / DeepSeek / 通义千问(qwen) / 豆包(ark) / 智谱(glm) / Moonshot / 零一万物 /
    Ollama / vLLM / one-api / new-api 等所有实现 /chat/completions 协议的服务。
    """

    def __init__(self, base_url: str, api_key: str, model: str, timeout: int = 120):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    # ---------- 核心 HTTP 流式调用 ----------

    async def _chat(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        json_mode: bool = True,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """流式调用 /chat/completions，yield {"delta": str} 片段，结束时 yield {"usage": {...}, "full_text": str}。"""
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
        }
        # 尽可能使用 response_format=json_object（OpenAI/DeepSeek 支持；不支持的服务会忽略/报错，我们做兼容）
        if json_mode:
            body["response_format"] = {"type": "json_object"}

        full_text_parts = []
        usage: Dict[str, int] = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", url, headers=headers, json=body) as resp:
                if resp.status_code != 200:
                    err_text = await resp.aread()
                    raise RuntimeError(f"LLM 请求失败 HTTP {resp.status_code}: {err_text[:500]}")
                async for raw_line in resp.aiter_lines():
                    line = raw_line.strip()
                    if not line:
                        continue
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    # 提取 usage（部分服务在最后一帧给出；流式时可能为 null）
                    u = chunk.get("usage")
                    if isinstance(u, dict):
                        usage["prompt_tokens"] = u.get("prompt_tokens", usage["prompt_tokens"])
                        usage["completion_tokens"] = u.get("completion_tokens", usage["completion_tokens"])
                        usage["total_tokens"] = u.get("total_tokens", usage["total_tokens"])
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
        """从模型输出中鲁棒地提取 JSON 对象/数组，兼容 ```json ... ``` 包裹。"""
        if not text:
            raise ValueError("模型返回为空")
        text = text.strip()
        # 去掉 markdown 代码块
        m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if m:
            text = m.group(1).strip()
        # 找第一个 { 或 [
        first_obj = text.find("{")
        first_arr = text.find("[")
        starts = [i for i in (first_obj, first_arr) if i != -1]
        if not starts:
            raise ValueError(f"无法从模型输出中解析 JSON: {text[:200]}")
        start = min(starts)
        # 找到对应的结束括号
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
        # 如果括号没完全闭合，尝试直接 json.loads（容忍尾部缺失）
        return json.loads(text[start:])

    async def _stream_task(
        self,
        system_prompt: str,
        user_prompt: str,
        result_key: str,
        phase_message: str = "正在调用 AI 生成...",
        temperature: float = 0.7,
        post_process=None,
    ) -> AsyncGenerator[str, None]:
        """通用任务流：发送 phase → 流式 delta → 解析 JSON → 发送 result/done。"""
        yield sse_event("phase", {"phase": "thinking", "message": phase_message})
        full_text_parts = []
        usage: Dict[str, int] = {}
        t0 = time.time()
        try:
            async for item in self._chat(system_prompt, user_prompt, temperature=temperature):
                if "delta" in item:
                    full_text_parts.append(item["delta"])
                    yield sse_event("delta", {"text": item["delta"]})
                else:
                    usage = item.get("usage", usage)
            try:
                parsed = self._extract_json("".join(full_text_parts))
            except Exception as e:
                yield sse_error(f"模型输出 JSON 解析失败：{e}; 原始输出: {''.join(full_text_parts)[:500]}")
                return
            if post_process:
                parsed = post_process(parsed)
            result = {result_key: parsed} if isinstance(result_key, str) else parsed
            elapsed = int((time.time() - t0) * 1000)
            yield sse_event("result", result)
            yield sse_done({**result, "usage": usage, "elapsed_ms": elapsed})
        except Exception as e:
            yield sse_error(str(e))

    # ---------- 11 个业务方法（签名完全对齐 MockProvider）----------

    async def generate_outline(self, req: dict) -> AsyncGenerator[str, None]:
        config = req.get("config", req)
        system = (
            "你是一位资深短剧编剧，擅长男频女频爽点节奏、钩子设计和反转结构。"
            "请根据用户给出的配置生成短剧大纲。输出必须是严格的 JSON（不要包含任何解释或 markdown），"
            "根为对象，包含字段 outline（数组），每个元素结构："
            '{"id":"m1","index":1,"title":"模块标题","summary":"20-50字概要","goal":"主角阶段目标","conflict":"核心冲突","twist":"钩子/反转","ending":"落点"}。'
            "通常生成 12-16 个模块，覆盖 开篇/起势/发展/高潮/结局 完整节奏。"
        )
        user = json.dumps(config, ensure_ascii=False)
        async for ev in self._stream_task(system, user, "outline", "正在构思大纲结构与爽点节奏..."):
            yield ev

    async def review_outline(self, req: dict) -> AsyncGenerator[str, None]:
        system = (
            "你是一位短剧剧本审核专家。请从以下维度审核大纲："
            "1. 节奏与爽点密度 2. 钩子设计 3. 人物动机合理性 4. 逻辑硬伤 5. 情感冲突强度 6. 分集可行性。"
            "输出严格 JSON，根对象包含 issues(数组，每个元素：{moduleId?:string,severity:'high'|'medium'|'low',category:string,suggestion:string}) 与 score(0-100整数)。"
            "问题要具体到模块，给出可执行修改建议。"
        )
        user = json.dumps(req, ensure_ascii=False)
        async for ev in self._stream_task(system, user, None, "正在审核大纲..."):
            yield ev

    async def modify_module(self, req: dict) -> AsyncGenerator[str, None]:
        system = (
            "你是一位大纲修改专家。请根据用户指令修改指定大纲模块，保持其他模块不变。"
            "输出严格 JSON，根对象包含 module（新的模块对象，包含 id/index/title/summary/goal/conflict/twist/ending）。"
        )
        user = json.dumps(req, ensure_ascii=False)
        async for ev in self._stream_task(system, user, None, "正在修改大纲模块..."):
            yield ev

    async def batch_modify(self, req: dict) -> AsyncGenerator[str, None]:
        """批量修改：服务端循环调用单模块修改接口，这里直接返回已修改模块数组。"""
        system = (
            "你是一位大纲修改专家。请根据用户的批量修改指令，对指定模块进行修改。"
            "输出严格 JSON，根对象包含 modules（数组，每个为修改后的模块完整对象，包含 id/index/title/summary/goal/conflict/twist/ending）。"
            "只返回需要修改的那些模块，未提及的模块不要出现在数组中。"
        )
        user = json.dumps(req, ensure_ascii=False)
        yield sse_event("phase", {"phase": "thinking", "message": "正在批量修改大纲模块..."})
        full_text_parts = []
        try:
            async for item in self._chat(system, user, temperature=0.7):
                if "delta" in item:
                    full_text_parts.append(item["delta"])
                    yield sse_event("delta", {"text": item["delta"]})
                else:
                    pass
            parsed = self._extract_json("".join(full_text_parts))
            modules = parsed.get("modules", parsed) if isinstance(parsed, dict) else parsed
            modules_list = modules if isinstance(modules, list) else []
            # 模拟逐步完成的进度
            for i, mod in enumerate(modules_list):
                yield sse_event("progress", {"current": i + 1, "total": len(modules_list), "moduleId": mod.get("id")})
            yield sse_event("result", {"modified": len(modules_list), "modules": modules_list})
            yield sse_done({"modified": len(modules_list), "modules": modules_list})
        except Exception as e:
            yield sse_error(str(e))

    async def review_characters(self, req: dict) -> AsyncGenerator[str, None]:
        system = (
            "你是一位人物设定专家。请审核这些人物小传，关注："
            "1. 人物动机是否清晰 2. 人物关系是否有张力 3. 人设是否立体有反差 4. 是否工具人化 5. 台词风格辨识度。"
            "输出严格 JSON，根对象包含 issues(数组，每个元素：{characterId?:string,severity:'high'|'medium'|'low',category:string,suggestion:string})。"
        )
        user = json.dumps(req, ensure_ascii=False)
        async for ev in self._stream_task(system, user, None, "正在审核人物小传..."):
            yield ev

    async def generate_characters(self, req: dict) -> AsyncGenerator[str, None]:
        system = (
            "你是一位人物设计专家。请根据已有大纲和主角设定，补全配角/反派/关键功能性角色。"
            "输出严格 JSON，根对象包含 characters（数组），每个角色结构："
            '{"id":"cX","name":"姓名","role":"主角/女主/反派/女配/男配/功能性角色","age":0,'
            '"appearance":"外形描述（30-60字）","personality":"性格关键词","background":"背景前史","goal":"核心诉求",'
            '"arc":"人物弧光（起点→转折→终点）","voice":"台词风格","relationships":[{"targetId":"cX","type":"关系类型","description":"关系描述"}]}。'
            "生成 3-6 个角色。"
        )
        user = json.dumps(req, ensure_ascii=False)
        async for ev in self._stream_task(system, user, "characters", "正在设计人物小传...", temperature=0.8):
            yield ev

    async def generate_episode(self, req: dict) -> AsyncGenerator[str, None]:
        system = (
            "你是一位分镜编剧。请根据大纲上下文为指定集数生成分集分镜脚本。"
            "输出严格 JSON，根对象包含 episode 对象，结构为："
            '{"id":"eX","index":1,"title":"本集标题","summary":"本集概要60-120字",'
            '"duration":90,"cliffs":["钩子1","钩子2"],"acts":[{"id":"a1","index":1,"title":"","summary":"",'
            '"duration":30,"beats":[{"id":"b1","index":1,"title":"","summary":"","goal":"","conflict":"",'
            '"twist":"","duration":10,"camera":"景别/运镜","location":"场景","charactersInFrame":["c1"],'
            '"lines":[{"id":"l1","index":1,"characterId":"c1","text":"台词内容","emotion":"情绪","action":"动作提示",'
            '"voiceover":false,"duration":3}]}]}]}。'
            "注意：1. duration 单位为秒；2. 每集时长通常 60-120 秒；3. lines 中每个台词要指定 characterId；"
            "4. beats 层级的 duration 之和要等于 act.duration，acts 之和要等于 episode.duration；"
            "5. 每集结尾留钩子（cliffs）。"
        )
        user = json.dumps(req, ensure_ascii=False)
        async for ev in self._stream_task(system, user, "episode", "正在编写分集分镜...", temperature=0.8):
            yield ev

    async def review_episode(self, req: dict) -> AsyncGenerator[str, None]:
        system = (
            "你是一位剧本审核专家。请审核这一分集分镜，重点关注："
            "1. 节奏是否紧凑 2. 台词是否贴合人设 3. 钩子是否够强 4. 时长是否合理 5. 拍摄可行性 6. 人物动机连贯性。"
            "输出严格 JSON，根对象包含 issues(数组，每个元素：{actId?:string,beatId?:string,lineId?:string,severity:'high'|'medium'|'low',category:string,suggestion:string}) 与 score(0-100整数)。"
        )
        user = json.dumps(req, ensure_ascii=False)
        async for ev in self._stream_task(system, user, None, "正在审核分集..."):
            yield ev

    async def fix_episode(self, req: dict) -> AsyncGenerator[str, None]:
        system = (
            "你是一位剧本修改专家。请根据审核意见修改分集分镜，保留未被指出的部分不变，只修改有问题的段落。"
            "输出严格 JSON，根对象包含 episode（修改后完整的 episode 对象，结构同 generate_episode 的输出）。"
        )
        user = json.dumps(req, ensure_ascii=False)
        async for ev in self._stream_task(system, user, "episode", "正在修复分集问题..."):
            yield ev

    async def rewrite_segment(self, req: dict) -> AsyncGenerator[str, None]:
        system = (
            "你是一位剧本润色专家。请按照用户指令改写指定段落（台词/动作/旁白等），提供多个风格化候选版本。"
            "输出严格 JSON，根对象包含 candidates（数组，2-4个字符串候选）。每个候选应保持剧情逻辑不变但语气/风格符合指令。"
        )
        user = json.dumps(req, ensure_ascii=False)

        def pp(obj):
            if isinstance(obj, dict) and "candidates" in obj:
                return obj
            if isinstance(obj, list):
                return {"candidates": obj}
            if isinstance(obj, str):
                return {"candidates": [obj]}
            return {"candidates": []}

        async for ev in self._stream_task(system, user, None, "正在润色改写...", temperature=0.9, post_process=pp):
            yield ev

    async def parse_import(self, req: dict) -> AsyncGenerator[str, None]:
        system = (
            "你是一位剧本解析专家。请从用户提供的原始剧本/故事文本中，提取结构化大纲与人物信息。"
            "输出严格 JSON，根对象包含："
            'outline（数组，每个元素 {id,index,title,summary,goal,conflict,twist,ending}），'
            'characters（数组，每个元素 {id,name,role,age,appearance,personality,background,goal,arc,voice,relationships}），'
            'warnings（数组，字符串，表示识别到的不确定或缺失信息，可空）。'
            "若文本中某字段缺失，使用合理推断填充；id 使用 m1..mN、c1..cN。"
        )
        text = req.get("text", "") if isinstance(req, dict) else str(req)
        user = json.dumps({"text": text}, ensure_ascii=False)
        async for ev in self._stream_task(system, user, None, "正在解析导入文本..."):
            yield ev


_provider_singleton: Optional[LLMProvider] = None


def get_provider(base_url: str, api_key: str, model: str, timeout: int = 120) -> LLMProvider:
    """模块级工厂（签名兼容 mock_provider.get_provider）。"""
    global _provider_singleton
    if _provider_singleton is None or _provider_singleton.base_url != base_url.rstrip("/") \
            or _provider_singleton.api_key != api_key or _provider_singleton.model != model:
        _provider_singleton = LLMProvider(base_url, api_key, model, timeout=timeout)
    return _provider_singleton
