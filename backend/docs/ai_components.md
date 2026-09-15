# AI 组件文档

最后更新：2026-09-11

## 架构总览

```
                    ┌─────────────────────────────────────────────────┐
                    │           api/ai.py  (11 个 SSE 端点)            │
                    │  outline/characters/episode/import ...           │
                    └───────────────┬─────────────────────────────────┘
                                    │ 依赖
                                    ▼
                    ┌─────────────────────────────────────────────────┐
                    │         ai/service.py  AiService                │
                    │  · 路由解析（name → task_bindings → "*" → 配置）│
                    │  · SSE 事件封装（phase/delta/result/done）      │
                    │  · ai_calls 日志记录 + token 用量               │
                    └───────────┬─────────────────────┬───────────────┘
                                │ provider 选择        ▲
                                ▼                      │ fallback
              ┌──────────────────────────┐    ┌──────────────────────────┐
              │ ai/llm_provider.py       │    │ ai/mock_provider.py      │
              │ LLMProvider (OpenAI协议) │    │ MockProvider (离线假数据)│
              │ 真实 HTTP 流式           │    │ 开发/演示用              │
              └────────┬─────────────────┘    └──────────────────────────┘
                       │ httpx async
                       ▼
              ┌──────────────────────────┐
              │ 第三方 LLM（DeepSeek/豆包 │
              │  /Qwen/智谱/Moonshot/Ollama│
              │  /vLLM/one-api/new-api)  │
              └──────────────────────────┘
```

## 核心模块

### 1. ai/llm_provider.py — 真实大模型引擎

**类：** `LLMProvider(base_url, api_key, model, timeout=120)`

**设计要点：**

- 统一使用 **OpenAI Chat Completions 兼容协议**（`POST {base_url}/chat/completions`）。国内绝大多数模型厂商（DeepSeek、豆包、通义 Qwen、智谱 GLM、Moonshot Kimi、零一万物、百度千帆兼容模式）以及本地/中转方案（Ollama、vLLM、one-api、new-api）全部支持此协议，接入时只需换 `base_url` + `api_key` + `model_name`，**无需改代码**。
- **异步 httpx 流式**（`async with client.stream("POST", ...)`），逐 chunk 解析 SSE `data: {json}`，支持长文本逐字打字机输出。
- **结构化 JSON 输出**：请求时带 `response_format={"type": "json_object"}`，强制模型返回合法 JSON；客户端 `_extract_json()` 方法带三重容错（去 \`\`\`json 围栏 → 花括号深度扫描 + 字符串/转义感知 → 失败返回 None）。
- **Token 用量提取**：从最后一个带 `usage` 字段的 chunk 中读出 `prompt_tokens / completion_tokens / total_tokens`，由 service 层写入 ai_calls。
- **11 个任务方法**（与 MockProvider 一致，接口对齐）：
  - `generate_outline / review_outline / modify_module / batch_modify`
  - `review_characters / generate_characters`
  - `generate_episode / review_episode / fix_episode / rewrite_segment`
  - `parse_import`
- 每个方法的 system_prompt 明确规定 JSON schema（字段、含义、范围），user_prompt 从传入参数拼接。
- **单例工厂** `get_provider(base_url, api_key, model, timeout)`：按 (base_url, api_key, model) 三元组复用实例，避免重复建 httpx client。

**关键常量：**

- `VALID_TASK_KEYS`：11 个合法任务标识，供上层做 bindings 校验
  ```
  generate_outline / review_outline / modify_outline_module / batch_modify_outline /
  generate_characters / review_characters /
  generate_episode / review_episode / fix_episode / rewrite_segment /
  parse_import
  ```

### 2. ai/service.py — 路由与 SSE 编排

**类：** `AiService(db, provider_name=None, task_key=None)`

**Provider 解析优先级（_resolve_provider）：**

1. **显式指定** `provider_name`（前端/调试时点名用哪个模型）
2. **任务绑定** `task_bindings` 包含该 task_key（is_active=true + priority 升序）
3. **通配兜底** `task_bindings` 包含 `"*"`（is_active=true + priority 升序）
4. **环境变量默认** `DEFAULT_LLM_PROVIDER / LLM_BASE_URL / LLM_API_KEY / LLM_MODEL`
5. **Mock 兜底**（防止配置为空时崩溃）

满足任一即停，越靠前优先级越高。这样可以做到：
- outline 生成走最强模型（如 deepseek-chat，priority=5）
- 剧集生成走便宜模型（如 qwen-turbo，priority=10，绑定 generate_episode）
- 没有专门绑定时走默认通配模型
- 全部没配就走 Mock（开发演示不报错）

**SSE 事件契约**（所有 11 个 AI 接口统一输出）：

| event     | data 字段                  | 触发时机                        |
|-----------|---------------------------|---------------------------------|
| `phase`   | message                   | 阶段切换（准备/生成中/结构化…） |
| `delta`   | text                      | 流式文字增量（打字机）          |
| `progress`| percent, message          | 多步任务的整体进度（0-100）     |
| `result`  | 任务相关结构（outline/...）| 最终完整结果                    |
| `done`    | （空）                    | 正常结束                        |
| `error`   | message                   | 异常                            |

HTTP 头固定为 `text/event-stream` + `Cache-Control: no-cache` + `Connection: keep-alive` + `X-Accel-Buffering: no`（反 Nginx 缓冲，保证真流式）。

**日志落库：** 每次调用写一条 `ai_calls` 记录，含 user_id / script_id / version_id / task_key / provider_id / model_name / input_tokens / output_tokens / latency_ms / status / error_msg / request_body；真实 usage 来自 LLM，缺失时退化为字符数/4 估算。

### 3. ai/mock_provider.py — 离线假数据引擎

- 与 LLMProvider 方法签名完全对齐的 mock 实现，返回预设的 JSON 结构和流式伪增量
- 未配任何真实模型时自动生效，保证前端在开发/演示环境有数据
- **永远不要删除 mock provider**（内置保护，DELETE 接口返回 400）

### 4. ai/sse.py — SSE 辅助工具

- `sse_event(event, data)`：把 dict/str 序列化为 `event: xxx\ndata: {...}\n\n` 单帧格式
- 自动处理中文、JSON 序列化、换行

## API 层

### api/ai.py — 11 个业务 SSE 端点

全部 POST + 鉴权 + StreamingResponse，每个端点的参数从 body 取（script 相关的从 DB 取 content），调 `AiService.stream(task_key, payload)` 直接返回。

| 方法 | 路径 | task_key |
|------|------|----------|
| POST | /api/ai/outline/generate | generate_outline |
| POST | /api/ai/outline/review | review_outline |
| POST | /api/ai/outline/modify-module | modify_outline_module |
| POST | /api/ai/outline/batch-modify | batch_modify_outline |
| POST | /api/ai/characters/generate | generate_characters |
| POST | /api/ai/characters/review | review_characters |
| POST | /api/ai/episode/generate | generate_episode |
| POST | /api/ai/episode/review | review_episode |
| POST | /api/ai/episode/fix | fix_episode |
| POST | /api/ai/episode/rewrite-segment | rewrite_segment |
| POST | /api/ai/import/parse | parse_import |

### api/ai_providers.py — 模型管理 CRUD

| 方法 | 路径 | 功能 |
|------|------|------|
| GET    | /api/ai-providers                 | 列表（按 priority 升序，api_key 脱敏） |
| POST   | /api/ai-providers                 | 新增（name 唯一；task_bindings 校验） |
| GET    | /api/ai-providers/{name}          | 详情 |
| PUT    | /api/ai-providers/{name}          | 部分更新（支持任意字段组合） |
| DELETE | /api/ai-providers/{name}          | 删除（内置 mock 不可删） |
| POST   | /api/ai-providers/{name}/activate | 启/停（?active=true\|false） |
| POST   | /api/ai-providers/{name}/bindings | 设置 task_bindings（合法 task_key 或 ["*"]） |
| POST   | /api/ai-providers/{name}/set-default | 设为全局默认（priority=10, bindings=["*"]，其他非 mock 被提权到 20） |
| POST   | /api/ai-providers/{name}/test     | 真实联通测试（非流式发 ping，返回 ok/reply/usage/error） |

**api_key 脱敏规则：** 长度 ≥ 8 时显示前 6 位 + `****` + 后 4 位（如 `sk-123****cdef`）；不足 8 位显示 `****`；空返回空字符串。

**Pydantic Schema（schemas/__init__.py）：**
- `AiProviderIn`：创建入参（name/provider/model_name/base_url/api_key/task_bindings/is_active/priority）
- `AiProviderUpdate`：更新入参（全部 Optional）
- `AiProviderOut`：出参（has_key/key_preview 替换原始 api_key）
- `AiProviderBindReq`：{task_bindings: [...]}
- `AiProviderTestResult`：{ok, provider, model, reply, usage, error}

> ⚠️ 三个带 `model_name` 字段的 schema 都设置了 `model_config = {"protected_namespaces": ()}`，避免 Pydantic v2 的 `model_` 保护命名空间告警。

## 数据层

### 表：ai_providers（models.AiProvider）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK | |
| name | VARCHAR(64) UNIQUE | 标识名（如 deepseek-chat / doubao-pro-32k）|
| provider | VARCHAR(32) | 协议类型：openai / mock（预留 anthropic/qwen/doubao/custom）|
| model_name | VARCHAR(128) | 实际模型名（传给 API 的 model 字段）|
| base_url | VARCHAR(255) | API endpoint 根（如 https://api.deepseek.com/v1）|
| api_key_enc | VARCHAR(512) | API Key（目前明文存；预留 `_decrypt_key` 加解密钩子）|
| task_bindings | JSON | 绑定的 task_key 数组，`["*"]` 表示全任务兜底 |
| is_active | BOOLEAN DEFAULT true | 启用开关 |
| priority | INT DEFAULT 0 | 优先级（数字越小越优先；set-default 会设为 10）|
| created_at | DATETIME | |

### 表：prompt_templates（models.PromptTemplate）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK | |
| task_key | VARCHAR(64) INDEX | 11 个任务之一 |
| version | VARCHAR(16) | v1 / v2 ...（UNIQUE(task_key, version)，支持 A/B 测试）|
| system_prompt | TEXT | 系统提示词 |
| user_prompt_template | TEXT | 用户提示词模板（可含 {variables}）|
| variables | JSON | 变量 schema |
| is_active | BOOLEAN DEFAULT true | |
| created_at | DATETIME | |

seed.py 初始化 v1 版本 11 条中文结构化提示词，每个都明确规定 JSON schema。

### 表：ai_calls（models.AiCall）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK AUTO_INCREMENT | |
| user_id | INT FK→users | 调用者 |
| script_id | INT FK→scripts NULL | 关联剧本（可选）|
| version_id | INT FK→script_versions NULL | 关联版本（可选）|
| task_key | VARCHAR(64) INDEX | 任务类型 |
| provider_id | INT FK→ai_providers | 使用的模型 |
| model_name | VARCHAR(128) | 模型名快照（模型被删也能审计）|
| input_tokens | INT DEFAULT 0 | 提示 token |
| output_tokens | INT DEFAULT 0 | 生成 token |
| latency_ms | INT DEFAULT 0 | 耗时毫秒 |
| status | VARCHAR(16) | success/failed/timeout/cancelled |
| error_msg | TEXT NULL | 错误信息 |
| request_body | JSON NULL | 请求快照（脱敏后）|
| created_at | DATETIME INDEX | |

### 表：ai_tasks（models.AiTask）— 任务队列/断线续传

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK | |
| task_key | VARCHAR(64) INDEX | |
| script_id | INT FK→scripts NULL | |
| user_id | INT FK→users | |
| status | VARCHAR(16) INDEX | pending/streaming/done/failed/cancelled |
| progress | TINYINT DEFAULT 0 | 0-100 |
| params | JSON NULL | 调用参数 |
| result_ref | VARCHAR(255) NULL | 结果存储引用（预留）|
| error_msg | TEXT NULL | |
| started_at / finished_at | DATETIME NULL | |
| created_at | DATETIME | |

## 配置（.env）

```ini
# LLM 默认配置（留空则走 Mock；在后台模型管理页录入更灵活）
DEFAULT_LLM_PROVIDER=mock        # 默认路由策略：mock / 某个 provider name
LLM_BASE_URL=                    # 如 https://api.deepseek.com/v1
LLM_API_KEY=                     # sk-xxx
LLM_MODEL=                       # 如 deepseek-chat
LLM_TIMEOUT=120                  # 秒
```

环境变量配置是"兜底默认"；推荐通过 `/api/ai-providers` 增删改，支持多模型并存、任务级绑定、故障切换。

## 前端接入指南

1. **登录拿 JWT**：`POST /api/auth/login` → 所有后续请求带 `Authorization: Bearer <token>`
2. **管理模型**：`/api/ai-providers` 系列接口做增删改查；创建完可点"测试连通性"按钮
3. **调用 AI**：所有 `/api/ai/...` 接口用 POST，`Accept: text/event-stream`，用 `EventSource` 或 `fetch` + `ReadableStream` 消费：
   ```js
   const res = await fetch('/api/ai/outline/generate', {
     method: 'POST',
     headers: {'Content-Type':'application/json','Authorization':`Bearer ${token}`},
     body: JSON.stringify(payload),
   });
   const reader = res.body.getReader();
   const decoder = new TextDecoder();
   let buffer = '';
   while (true) {
     const {done, value} = await reader.read();
     if (done) break;
     buffer += decoder.decode(value, {stream:true});
     const frames = buffer.split('\n\n');
     buffer = frames.pop();
     for (const f of frames) {
       const lines = f.split('\n');
       const event = lines.find(l=>l.startsWith('event:'))?.slice(6).trim();
       const data = lines.find(l=>l.startsWith('data:'))?.slice(5).trim();
       if (event && data) {
         const payload = JSON.parse(data);
         // 根据 event 做 UI 响应：phase 更新提示、delta 打字机追加、result 落库、done 关闭
       }
     }
   }
   ```
4. **调用前的 provider 选择**：前端可以传 `?provider=<name>` 点名模型，不传则由后端按 task_bindings → 通配 → 配置 → Mock 的顺序自动选。

## 扩展新协议（未来）

目前 `LLMProvider` 只实现了 OpenAI 兼容协议。要支持 Anthropic、Gemini 等非兼容协议：

1. 在 `ai/` 目录下新建 `anthropic_provider.py`，实现同样的 11 个 async 方法签名 + `_chat` 底层
2. 在 `ai/service.py` 的 `_get_provider()` 里加分支：`elif p.provider == "anthropic": return AnthropicProvider(...)`
3. 在 `api/ai_providers.py` 的 provider 枚举校验里加上 `"anthropic"`
4. 在 `.env` 或 DB 中录入模型即可，业务接口零改动
