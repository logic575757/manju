# 剧本创作平台 · 项目基础文档（组件信息总表）

> 本文件是项目的唯一组件信息来源。每次会话涉及「组件 / 数据库 / 启动 / 端口 / 依赖 / AI 接口」等问题时，**必须先查这里**，不要凭记忆猜测环境状态。

## 1. 项目概览

- 项目名称：剧本创作平台（script creation platform）
- 定位：AI 辅助剧本创作，含大纲 / 人物 / 分集 / 导入解析等 11 个 AI 能力
- 技术栈：FastAPI（后端） + Vite 原生 JS 单页（前端） + MySQL 8.0（生产库）+ SQLite（可选兜底）

## 2. 组件清单

| 组件 | 技术/版本 | 位置 | 端口 | 状态 |
|------|-----------|------|------|------|
| 数据库 | MySQL 8.0.46 | 本机（沙箱内） | 3306 | **项目标准组件，本来就有** |
| 后端 | FastAPI + Python 3.11.15 | `/workspace/backend` | 8000 | 需手动启动 |
| 前端 | Vite 5（原生 JS SPA） | `/workspace/script-creation` | 5173 | 需手动启动 |
| AI 引擎 | MockProvider（默认）/ LLMProvider（OpenAI 协议） | `/workspace/backend/ai` | — | mock 默认 |

## 3. 数据库（MySQL，标准组件）

- **MySQL 是项目默认数据库，不是临时兜底**。`.env` 与 `config.py` 默认都指向 MySQL。
- 连接信息（来自 `/workspace/backend/.env`）：
  - host `127.0.0.1`，port `3306`
  - database `script_creation`（utf8mb4 / utf8mb4_unicode_ci）
  - user `script_user` / password `script_pass_2024`（`mysql_native_password`，已授权 `%` / `localhost` / `127.0.0.1`）
- 数据目录：`/var/lib/mysql`（已初始化）；socket：`/var/run/mysqld/mysqld.sock`
- root 登录：`mysql -u root`（root 用户，auth_socket 免密）

### 启动 MySQL（沙箱内无 systemd，需手动起）

```bash
mkdir -p /var/run/mysqld && chown mysql:mysql /var/run/mysqld
mysqld --user=mysql        # 前台常驻；或用 nohup 放后台
```

> 注意：`apt-get install mysql-server` 装完后进程不会自动常驻（policy-rc.d 拦截了 systemd 启动），所以每次需要手动跑上面的命令。

## 4. 后端（FastAPI）

- 目录：`/workspace/backend`，入口 `main.py`
- Python 解释器：`/root/.pyenv/versions/3.11.15/bin/python`
- 依赖：`requirements.txt`（已含 `httpx==0.28.1`，`ai/worker.py`、`ai/llm_provider.py`、`api/ai_providers.py` 均引用它）
- 健康检查：`GET /api/health`（**不是 `/health`**），返回 `{"status":"ok","service":"script-creation-api","queue_concurrency":3}`
- 启动后自动 `Base.metadata.create_all` 建表

### 启动后端（默认走 MySQL）

```bash
cd /workspace/backend
/root/.pyenv/versions/3.11.15/bin/python main.py
```

### 数据库选择逻辑（`config.py` 的 `database_url` 属性）

1. 若设置了环境变量 `DATABASE_URL` → 直接用（这就是之前落到 SQLite 的原因）
2. 否则 → `mysql+pymysql://script_user:script_pass_2024@127.0.0.1:3306/script_creation?charset=utf8mb4`

**要用 MySQL，就不要设置 `DATABASE_URL` 环境变量。** 只有在 MySQL 不可用时才临时用 `DATABASE_URL="sqlite:///./script_creation.db"` 兜底。

## 5. 前端（Vite）

- 目录：`/workspace/script-creation`，入口 `index.html`（单文件 SPA）
- `vite.config.js`：host `0.0.0.0`，port `5173`，`/api` 代理到 `http://127.0.0.1:8000`
- 依赖：`npm install`（devDependencies: vite ^5.4.0；dependencies: lucide）

### 启动前端

```bash
cd /workspace/script-creation
npm run dev
```

## 6. 一键启动顺序（完整）

```bash
# 1) MySQL
mkdir -p /var/run/mysqld && chown mysql:mysql /var/run/mysqld
nohup mysqld --user=mysql > /var/log/mysql/console.log 2>&1 &

# 2) 后端（默认 MySQL）
cd /workspace/backend && /root/.pyenv/versions/3.11.15/bin/python main.py

# 3) 前端
cd /workspace/script-creation && npm run dev
```

## 7. AI 能力清单（11 个接口，全部已联调）

详细架构见 `/workspace/backend/docs/ai_components.md`。task_key 与端点：

| task_key | 端点 |
|----------|------|
| generate_outline | POST /api/ai/outline/generate |
| review_outline | POST /api/ai/outline/review |
| modify_outline_module | POST /api/ai/outline/modify-module |
| batch_modify_outline | POST /api/ai/outline/batch-modify |
| generate_characters | POST /api/ai/characters/generate |
| review_characters | POST /api/ai/characters/review |
| generate_episode | POST /api/ai/episode/generate |
| review_episode | POST /api/ai/episode/review |
| fix_episode | POST /api/ai/episode/fix |
| rewrite_segment | POST /api/ai/episode/rewrite-segment |
| parse_import | POST /api/ai/import/parse |

- 默认 LLM provider 为 `mock`（`DEFAULT_LLM_PROVIDER=mock`），不调真实模型、离线返回假数据。
- 任务队列：并发 3（`queue_max_concurrency=3`），前端 4s 轮询 `ai_tasks`。
- `ai_tasks` 表用 `skill_name` 列（不是 `skill`）。
- 每个 skill 提交后返回 `stream_url`（`/api/ai/tasks/{task_id}/stream`），SSE 事件：`meta / phase / progress / delta / result / done / error / heartbeat`。
- 通用提交兜底路由：`POST /api/ai/skills/submit/{task_key}`（DB 动态新增 skill 用）。

## 8. 认证（JWT）

- 密码哈希：`pbkdf2_sha256`（passlib）；JWT：HS256（`secret_key`，默认 `change-me`，token 有效期 1440 分钟）。
- 依赖：`get_current_user`（必登录，失败 401）、`get_current_user_optional`（可选登录）。
- 端点（前缀 `/api/auth`）：
  - `POST /api/auth/register` → `{access_token, token_type}`
  - `POST /api/auth/login` → `{access_token, token_type}`
  - `GET /api/auth/me` → 当前用户
- 前端调用需带 `Authorization: Bearer <token>`。

## 9. REST API 总表（非 AI 部分）

> 前缀见各 router；`/api/scripts` 前缀同时挂载 characters、episodes 两个子资源。

**auth**（`/api/auth`）：`POST /register`、`POST /login`、`GET /me`

**scripts**（`/api/scripts`）：
- `GET /` 列表、`POST /` 创建、`GET /{script_id}`、`PATCH /{script_id}`、`PUT /{script_id}`、`DELETE /{script_id}`（软删）
- `POST /{script_id}/restore`、`POST /{script_id}/duplicate`、`POST /{script_id}/lock`、`POST /{script_id}/unlock`
- `GET /{script_id}/export`（导出）
- `GET /{script_id}/versions`、`POST /{script_id}/versions`、`GET /{script_id}/versions/{version_id}`、`GET /{script_id}/versions/diff`、`POST /{script_id}/versions/{version_id}/restore`、`DELETE /{script_id}/versions/{version_id}`

**characters**（前缀 `/api/scripts`，挂 `/{script_id}/characters`）：
- `GET /{script_id}/characters`、`POST /{script_id}/characters`、`GET/PUT/DELETE /{script_id}/characters/{character_id}`

**episodes**（前缀 `/api/scripts`，挂 `/{script_id}/episodes`）：
- `GET /{script_id}/episodes`、`POST /{script_id}/episodes`、`GET/PUT/DELETE /{script_id}/episodes/{episode_id}`
- `POST /{script_id}/episodes/{episode_id}/validate`、`.../pass`、`.../unpass`、`GET /{script_id}/episodes/passed/all`

**tags**（`/api/tags`）：`GET /`（列表）、`GET /categories`（分类）

**imports**（`/api/imports`）：`POST /`（上传/解析）、`GET /`（列表）

**ai-providers**（`/api/ai-providers`）：
- `GET /`、`POST /`、`GET /{name}`、`PUT /{name}`、`DELETE /{name}`
- `POST /{name}/activate`、`POST /{name}/bindings`、`POST /{name}/set-default`、`POST /{name}/test`

**ai/tasks**（`/api/ai/tasks`）：
- `GET /`（列表）、`GET /stats`、`GET /{task_id}`、`POST /{task_id}/cancel`、`POST /{task_id}/retry`、`DELETE /{task_id}`

**ai/skills**（`/api/ai/skills`）：
- `GET /`（列表，含启停状态）、`GET /{key}`、`PUT /{key}`（可新建 prompt 版本）、`POST /{key}/activate-version/{version}`

## 10. 数据表（11 张，`Base.metadata.create_all` 自动建）

| 表 | 作用 |
|----|------|
| users | 用户（含 quota_daily 每日配额 200） |
| scripts | 剧本主表（content JSON、status/step/progress、软删 deleted_at） |
| script_versions | 剧本版本（版本号、diff/restore） |
| script_imports | 导入文件记录 |
| tag_dictionaries | 标签字典（category+name 唯一） |
| ai_providers | AI 提供商（mock / LLM，task_bindings JSON） |
| prompt_templates | 提示词模板（task_key+version 唯一） |
| ai_skills | AI 技能（key 主键，api_path 唯一） |
| ai_calls | AI 调用日志（token/latency/error_class） |
| ai_tasks | AI 任务队列（status/priority/attempts/重试） |
| ai_task_events | 任务事件流（task_id+seq 唯一，SSE 消费） |

## 11. 配置项（`config.py` Settings）

- MySQL：`mysql_host / mysql_port / mysql_user / mysql_password / mysql_database`
- 安全：`secret_key`、`access_token_expire_minutes`
- 服务：`api_host / api_port`
- LLM：`default_llm_provider`（mock 默认）、`llm_base_url / llm_api_key / llm_model / llm_timeout`
- 队列：`queue_max_concurrency(3) / queue_poll_interval / queue_max_retries(2) / queue_task_timeout / queue_heartbeat_interval / queue_stale_timeout / queue_user_max_pending(10)`

## 12. 关键文件

| 文件 | 作用 |
|------|------|
| `/workspace/backend/config.py` | 配置 + `database_url` 逻辑 |
| `/workspace/backend/.env` | 环境变量（MySQL / LLM / 端口） |
| `/workspace/backend/main.py` | FastAPI 入口 + `/api/health` + create_all |
| `/workspace/backend/seed.py` | 初始化 tags / ai_providers / prompt_templates / ai_skills |
| `/workspace/backend/api/ai.py` | 11 个 AI SSE 端点 |
| `/workspace/backend/ai/skills_registry.py` | 11 个内置 skill 注册 |
| `/workspace/backend/ai/mock_provider.py` | mock 假数据（含 fix_episode 的 resolved_issue_ids 修复） |
| `/workspace/backend/docs/ai_components.md` | AI 组件详细文档 |
| `/workspace/script-creation/index.html` | 前端主文件（单文件 SPA） |
| `/workspace/script-creation/vite.config.js` | 前端端口 + /api 代理 |

## 13. 常见坑（务必记住）

1. **MySQL 不会自动启动**：沙箱无 systemd，装完/重启后要手动 `mysqld --user=mysql`。
2. **`/health` 会 404**：健康检查是 `/api/health`。
3. **历史坑已修**：`httpx` 曾漏写进 requirements.txt（导致新环境 `ModuleNotFoundError: httpx`），现已补为 `httpx==0.28.1`。
4. **别用 `DATABASE_URL` 覆盖成 SQLite**：项目标准是 MySQL；只有在 MySQL 确实不可用时才临时兜底 SQLite。
5. **fix_episode 结果契约**：mock/LLM 的 fix_episode 必须返回 `resolved_issue_ids`，否则前端无法把问题标记为已解决。
6. **`ai_tasks` 的列名是 `skill_name`**，不是 `skill`。
