#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成剧本创作平台架构 TodoList Excel"""

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

wb = Workbook()

# ========== 通用样式 ==========
header_font = Font(name="Microsoft YaHei", size=11, bold=True, color="FFFFFF")
header_fill = PatternFill("solid", fgColor="2C5B6F")
section_font = Font(name="Microsoft YaHei", size=11, bold=True, color="FFFFFF")
section_fill = PatternFill("solid", fgColor="7C3AED")
done_fill = PatternFill("solid", fgColor="D1FAE5")
todo_fill = PatternFill("solid", fgColor="FEF3C7")
p0_fill = PatternFill("solid", fgColor="FEE2E2")
p1_fill = PatternFill("solid", fgColor="FFEDD5")
p2_fill = PatternFill("solid", fgColor="DBEAFE")
p3_fill = PatternFill("solid", fgColor="F3F4F6")
cell_font = Font(name="Microsoft YaHei", size=10)
wrap = Alignment(wrap_text=True, vertical="center", horizontal="left")
center = Alignment(wrap_text=True, vertical="center", horizontal="center")
thin = Side(border_style="thin", color="D1D5DB")
border = Border(left=thin, right=thin, top=thin, bottom=thin)


def style_header_row(ws, row, cols):
    for c in range(1, cols + 1):
        cell = ws.cell(row=row, column=c)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center
        cell.border = border


def style_section_row(ws, row, cols, text):
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=cols)
    cell = ws.cell(row=row, column=1, value=text)
    cell.font = section_font
    cell.fill = section_fill
    cell.alignment = Alignment(vertical="center", horizontal="left", indent=1)
    cell.border = border
    ws.row_dimensions[row].height = 26


def add_data_row(ws, row, data, fill=None):
    for c, val in enumerate(data, 1):
        cell = ws.cell(row=row, column=c, value=val)
        cell.font = cell_font
        cell.alignment = wrap if c > 1 else center
        cell.border = border
        if fill:
            cell.fill = fill


# ============================================================
# Sheet 1: 完整 TodoList
# ============================================================
ws1 = wb.active
ws1.title = "架构TodoList"

headers = ["#", "事项", "类型", "优先级", "状态", "所属环节", "说明"]
widths = [5, 38, 14, 10, 10, 22, 60]
for i, (h, w) in enumerate(zip(headers, widths), 1):
    ws1.cell(row=1, column=i, value=h)
    ws1.column_dimensions[get_column_letter(i)].width = w
style_header_row(ws1, 1, len(headers))
ws1.row_dimensions[1].height = 28

tasks = [
    # (section, [id, 事项, 类型, 优先级, 状态, 环节, 说明])
    ("一、用户与账号体系（贯穿全局）", [
        ["1.1", "注册/登录/获取当前用户 API（JWT）", "后端 API", "P0", "已完成", "用户体系", "POST /api/auth/register, POST /api/auth/login, GET /api/auth/me"],
        ["1.2", "users 表（用户基础信息）", "数据库表", "P0", "已完成", "用户体系", "id/username/email/hashed_password/display_name/avatar/is_active"],
        ["1.3", "密码修改、头像上传、昵称修改", "后端 API", "P2", "待做", "用户体系", "非核心功能，后期补充"],
        ["1.4", "微信/手机号一键登录", "第三方", "P3", "待做", "用户体系", "可选，后期接入"],
    ]),
    ("二、剧本列表页（我的剧本）", [
        ["2.1", "剧本列表 API（含搜索+状态筛选）", "后端 API", "P0", "部分完成", "剧本列表", "GET /api/scripts 需加 q=关键词 搜索（title LIKE）"],
        ["2.2", "创建剧本 API（区分 AI/导入路径，保存 config）", "后端 API", "P0", "部分完成", "剧本列表", "需保存初始 config（四维标签/体量/节奏等元信息）"],
        ["2.3", "剧本重命名、归档/恢复 API", "后端 API", "P1", "部分完成", "剧本列表", "PUT 基本字段已做，需加 archive 状态流转"],
        ["2.4", "复制剧本 API（含完整 content 快照）", "后端 API", "P1", "待做", "剧本列表", "POST /api/scripts/{id}/duplicate"],
        ["2.5", "删除剧本（改为软删）", "后端 API", "P1", "部分完成", "剧本列表", "当前硬删，建议改为软删加 deleted_at 字段"],
        ["2.6", "scripts 表扩展字段", "数据库表", "P0", "待做", "剧本列表", "加 cover_url/progress/step/tags/config/deleted_at 字段"],
        ["2.7", "封面图上传 API", "后端+存储", "P2", "待做", "剧本列表", "POST /api/uploads/cover，OSS 或本地静态目录"],
    ]),
    ("三、Step 0 创作入口 — AI 原创路径", [
        ["3.1", "标签词库 API（题材/情节/时空/情绪/画风/镜头/外貌）", "后端 API", "P1", "待做", "Step0 入口", "GET /api/tags?category=xxx，词库从数据库读"],
        ["3.2", "tag_dictionaries 标签词典表", "数据库表", "P1", "待做", "Step0 入口", "id/category/name/weight/sort_order/is_active，支持运营维护"],
        ["3.3", "节奏预设 API（burst/tight/standard）", "后端 API", "P2", "待做", "Step0 入口", "GET /api/presets/pace，可暂留前端"],
        ["3.4", "⭐ AI 大纲生成接口（流式 SSE）", "AI 接口", "P0", "待做", "Step0 入口", "核心能力，入参：四维标签+风格+体量+节奏+必含/避雷+提示词；流式返回16个大纲模块"],
        ["3.5", "⭐ 缝合小说 RAG 向量检索", "AI+向量库", "P2", "待做", "Step0 入口", "Embedding + 向量库（pgvector/Milvus/Chroma），召回相关剧情点"],
        ["3.6", "AI 任务队列表 + 断线续传", "数据库+后端", "P1", "待做", "Step0 入口", "ai_tasks 表记录 pending/streaming/done/failed，SSE 中断可重连"],
        ["3.7", "保存创作配置 config 快照到 scripts 表", "数据库", "P0", "待做", "Step0 入口", "tags/style/pace/must/avoid/novels 等便于复用和审计"],
    ]),
    ("四、Step 0 创作入口 — 导入剧本路径", [
        ["3.8", "文件上传解析 API（txt/docx/pdf）", "后端 API", "P1", "待做", "Step0 导入", "python-docx 解析 docx、pdfplumber 解析 pdf"],
        ["3.9", "⭐ AI 剧本解析接口（流式）", "AI 接口", "P1", "待做", "Step0 导入", "喂入原文+目标集数+情绪基调，返回 outlineData+episodes 骨架"],
        ["3.10", "导入原文存储表 script_imports", "数据库表", "P1", "待做", "Step0 导入", "id/script_id/file_name/file_type/raw_text/created_at"],
        ["3.11", "保存 generated_prompt 到 config 做审计", "数据库", "P2", "待做", "Step0 导入", "便于复盘 AI 生成效果"],
    ]),
    ("五、Step 1 大纲审核与修改", [
        ["4.1", "大纲内容保存 API（PATCH 局部更新）", "后端 API", "P0", "部分完成", "Step1 大纲", "PUT 整包已做，建议加 PATCH 局部更新减流量"],
        ["4.2", "⭐ AI 大纲自审接口（流式）", "AI 接口", "P0", "待做", "Step1 大纲", "入参 outlineData，流式返回每个模块的 issues+aiScore+tone"],
        ["4.3", "⭐ AI 单模块修改接口（流式）", "AI 接口", "P1", "待做", "Step1 大纲", "入参：单模块+勾选 issues+用户 note，流式返回修改后内容"],
        ["4.4", "AI 批量修改接口（流式）", "AI 接口", "P1", "待做", "Step1 大纲", "入参：多模块+globalNote，流式返回批量修改结果"],
        ["4.5", "大纲 UI 临时状态（勾选/备注/队列）", "前端状态", "P1", "待做", "Step1 大纲", "内存+localStorage，无需存后端"],
        ["4.6", "大纲\"重新自审\"按钮对接", "AI 接口", "P1", "待做", "Step1 大纲", "复用 4.2 接口覆盖 issues"],
        ["4.7", "大纲全文手动编辑模式保存", "后端 API", "P1", "待做", "Step1 大纲", "复用 PATCH content"],
        ["4.8", "自动保存（防抖3-5秒）", "后端 API", "P0", "待做", "Step1 大纲", "频繁编辑不打版本，只更新 scripts.content"],
    ]),
    ("六、Step 2 人物小传", [
        ["5.1", "角色 CRUD API", "后端 API", "P0", "待做", "Step2 角色", "POST/GET/PUT/DELETE /api/scripts/{id}/characters/{cid}"],
        ["5.2", "决策：JSON 快照 vs 独立 characters 表", "架构决策", "P0", "待做", "Step2 角色", "推荐初期 JSON，跨剧本复用再拆表"],
        ["5.3", "外貌特征词库", "后端 API", "P1", "待做", "Step2 角色", "复用 tag_dictionaries 的 appearance 分类"],
        ["5.4", "角色参考图上传（多张）", "后端+存储", "P2", "待做", "Step2 角色", "character_references 表或 JSON URL 数组"],
        ["5.5", "⭐ AI 人物逻辑自审接口（流式）", "AI 接口", "P1", "待做", "Step2 角色", "检查动机冲突、人设矛盾、与大纲冲突，返回 issues"],
        ["5.6", "AI 次角色自动补全", "AI 接口", "P2", "待做", "Step2 角色", "根据大纲和主角自动生成配角/反派小传"],
        ["5.7", "角色\"通过\"状态字段 reviewStatus", "前端状态", "P1", "待做", "Step2 角色", "存 JSON content 即可"],
        ["5.8", "用户审核意见保存", "数据库", "P1", "待做", "Step2 角色", "复用 PATCH content"],
    ]),
    ("七、Step 3 分集剧本（核心产出）", [
        ["6.1", "⭐ AI 单集生成接口（流式 SSE）", "AI 接口", "P0", "待做", "Step3 分集", "最核心，4层结构 Episode→Storyboard→Camera→Behavior，遵守节奏规则"],
        ["6.2", "⭐ AI 分集自审接口（流式）", "AI 接口", "P0", "待做", "Step3 分集", "检查 plot/logic/character/continuity/timing，返回 T0/T1/T2 issues"],
        ["6.3", "⭐ AI 局部修复 AI Fix（流式）", "AI 接口", "P0", "待做", "Step3 分集", "按勾选 issues 修改对应 behaviors，保留其他不变"],
        ["6.4", "⭐ AI 局部改写助手（流式）", "AI 接口", "P1", "待做", "Step3 分集", "选中段落+改写指令，返回多个候选版本"],
        ["6.5", "分集 CRUD API", "后端 API", "P1", "待做", "Step3 分集", "POST/GET/PUT/DELETE /api/scripts/{id}/episodes/{eid}"],
        ["6.6", "分集时长校验", "后端/前端", "P2", "待做", "Step3 分集", "前端算+AI生成时后端二次校验"],
        ["6.7", "分集锁定状态（epPassOne/All）", "状态字段", "P0", "待做", "Step3 分集", "episodes[i].locked=true，锁定后AI不再修改"],
        ["6.8", "人物出场悬浮球统计", "前端计算", "P2", "无需", "Step3 分集", "纯前端从 behaviors 统计，无需 API"],
        ["6.9", "用户自定义 issue 添加", "数据库", "P1", "待做", "Step3 分集", "复用 PATCH content"],
    ]),
    ("八、版本管理（贯穿 Step1-3）", [
        ["7.1", "版本快照 CRUD + 恢复 API", "后端 API", "P0", "已完成", "版本管理", "POST/GET/DELETE /api/scripts/{id}/versions + restore"],
        ["7.2", "版本对比 Diff API", "后端 API", "P1", "待做", "版本管理", "JSON 递归 diff，返回字段级修改点"],
        ["7.3", "自动版本策略（切步/定时/AI前）", "后端逻辑", "P1", "待做", "版本管理", "每次切步/30分钟/AI修改前自动打快照"],
        ["7.4", "定稿锁定（is_final/is_locked）", "数据库+后端", "P0", "待做", "版本管理", "加 is_final/is_locked 字段+locked_at，定稿后不可编辑（可解锁）"],
        ["7.5", "定稿导出（docx/pdf/txt/fountain）", "后端 API", "P1", "待做", "版本管理", "python-docx/reportlab 生成专业剧本格式"],
    ]),
    ("九、AI 基础设施（所有 AI 接口的支撑层）", [
        ["8.1", "AI Provider 抽象层（多模型切换）", "后端模块", "P0", "待做", "AI 基建", "封装 OpenAI/Claude/豆包/通义/DeepSeek，统一 chat() 接口"],
        ["8.2", "AI 配置表 ai_providers（key池/模型绑定）", "数据库表", "P0", "待做", "AI 基建", "api_key/model/base_url/is_active，支持运营切换"],
        ["8.3", "Prompt 模板管理（版本化/A/B测试）", "数据库+后端", "P0", "待做", "AI 基建", "prompt_templates 表，每类任务绑定模板版本"],
        ["8.4", "AI 调用日志表 ai_calls", "数据库表", "P0", "待做", "AI 基建", "记录 tokens/latency/status/error，计费+排查必备"],
        ["8.5", "SSE 流式输出基础设施", "后端", "P0", "待做", "AI 基建", "FastAPI StreamingResponse，前端打字机效果"],
        ["8.6", "AI 任务取消（Abort）", "后端", "P1", "待做", "AI 基建", "任务ID + asyncio cancel"],
        ["8.7", "AI 输出结构化校验（JSON Schema）", "后端", "P0", "待做", "AI 基建", "response_format/function calling 强制 JSON，校验后入库"],
        ["8.8", "用户 AI 配额限流", "后端", "P1", "待做", "AI 基建", "按用户/剧本限制每日调用次数或 token"],
    ]),
    ("十、存储与基建", [
        ["9.1", "对象存储（封面/参考图/导入文件）", "存储", "P2", "待做", "基建", "本地 /static/uploads 起步，后切 MinIO/OSS/COS"],
        ["9.2", "向量库（RAG用）", "基础设施", "P2", "待做", "基建", "pgvector轻/Milvus重/Chroma开发"],
        ["9.3", "Redis（缓存/队列/SSE状态）", "基础设施", "P2", "待做", "基建", "并发上来后必要"],
        ["9.4", "Alembic 数据库迁移", "后端工程", "P1", "待做", "基建", "当前 create_all，生产必须加迁移"],
        ["9.5", "Docker Compose 一键启动", "部署", "P1", "待做", "基建", "mysql + redis + backend + frontend"],
        ["9.6", "日志监控告警", "运维", "P3", "待做", "基建", "结构化日志、慢查询、AI异常告警"],
    ]),
    ("十一、前端对接层改造", [
        ["10.1", "前端 API 客户端封装（JWT/错误/401）", "前端改造", "P0", "待做", "前端", "统一 fetch 封装"],
        ["10.2", "登录/注册页面", "前端页面", "P0", "待做", "前端", "目前前端没有"],
        ["10.3", "localStorage → API 数据迁移", "前端改造", "P0", "待做", "前端", "版本、剧本列表、自动保存全部改走后端"],
        ["10.4", "SSE 流式消费（打字机效果）", "前端改造", "P0", "待做", "前端", "EventSource/fetch-stream"],
        ["10.5", "离线/弱网本地缓存同步", "前端", "P3", "待做", "前端", "后期加"],
        ["10.6", "前端路由系统（Vue/React Router）", "前端架构", "P3", "待做", "前端", "可选，目前不影响功能"],
    ]),
]

row = 2
total_count = 0
for section_title, items in tasks:
    style_section_row(ws1, row, len(headers), section_title)
    row += 1
    for item in items:
        total_count += 1
        pr = item[3]
        st = item[4]
        if st == "已完成":
            fill = done_fill
        elif st == "部分完成":
            fill = todo_fill
        elif pr == "P0":
            fill = p0_fill
        elif pr == "P1":
            fill = p1_fill
        elif pr == "P2":
            fill = p2_fill
        else:
            fill = p3_fill
        add_data_row(ws1, row, item, fill)
        ws1.row_dimensions[row].height = 32
        row += 1

ws1.freeze_panes = "A2"
ws1.auto_filter.ref = f"A1:G{row-1}"

# ============================================================
# Sheet 2: 数据库表设计
# ============================================================
ws2 = wb.create_sheet("数据库表设计")
headers2 = ["表名", "字段名", "类型", "约束", "说明"]
widths2 = [26, 26, 20, 22, 50]
for i, (h, w) in enumerate(zip(headers2, widths2), 1):
    ws2.cell(row=1, column=i, value=h)
    ws2.column_dimensions[get_column_letter(i)].width = w
style_header_row(ws2, 1, len(headers2))
ws2.row_dimensions[1].height = 28

tables = [
    ("users（用户表 ✅已建）", [
        ["id", "INT", "PK AUTO_INCREMENT", "用户ID"],
        ["username", "VARCHAR(64)", "UNIQUE NOT NULL INDEX", "用户名"],
        ["email", "VARCHAR(128)", "UNIQUE NULL", "邮箱"],
        ["hashed_password", "VARCHAR(255)", "NOT NULL", "PBKDF2 哈希密码"],
        ["display_name", "VARCHAR(64)", "NULL", "昵称"],
        ["avatar_url", "VARCHAR(512)", "NULL", "头像URL"],
        ["is_active", "BOOLEAN", "DEFAULT true", "是否启用"],
        ["quota_daily", "INT", "DEFAULT 100", "每日AI调用配额"],
        ["created_at", "DATETIME", "NOT NULL", "创建时间"],
        ["updated_at", "DATETIME", "NOT NULL", "更新时间"],
    ]),
    ("scripts（剧本表 ✅已建，需扩展）", [
        ["id", "INT", "PK AUTO_INCREMENT", "剧本ID"],
        ["owner_id", "INT", "FK→users.id NOT NULL INDEX", "所属用户"],
        ["title", "VARCHAR(255)", "NOT NULL", "剧本标题"],
        ["path_type", "VARCHAR(16)", "DEFAULT 'ai'", "ai=AI原创, import=导入"],
        ["description", "TEXT", "NULL", "描述"],
        ["cover_url", "VARCHAR(512)", "NULL 🆕", "封面图"],
        ["status", "VARCHAR(16)", "DEFAULT 'draft'", "draft/final/archived"],
        ["step", "TINYINT", "DEFAULT 0 🆕", "当前步骤 0-3"],
        ["progress", "TINYINT", "DEFAULT 0 🆕", "进度百分比 0-100"],
        ["tags", "JSON", "NULL 🆕", "题材标签数组"],
        ["config", "JSON", "NULL 🆕", "创作配置（四维标签/节奏/体量/prompt快照）"],
        ["current_version_id", "INT", "NULL", "当前版本ID"],
        ["content", "JSON", "NOT NULL", "当前完整内容（outlineData+characters+episodes）"],
        ["locked_at", "DATETIME", "NULL 🆕", "定稿锁定时间"],
        ["deleted_at", "DATETIME", "NULL 🆕", "软删时间"],
        ["created_at", "DATETIME", "NOT NULL", ""],
        ["updated_at", "DATETIME", "NOT NULL", ""],
    ]),
    ("script_versions（版本快照表 ✅已建）", [
        ["id", "INT", "PK AUTO_INCREMENT", "版本ID"],
        ["script_id", "INT", "FK→scripts.id NOT NULL INDEX", "所属剧本"],
        ["version_number", "INT", "NOT NULL", "版本号递增"],
        ["name", "VARCHAR(128)", "NULL", "版本名（如\"大纲完成\"）"],
        ["commit_message", "VARCHAR(512)", "NULL", "提交备注"],
        ["is_final", "BOOLEAN", "DEFAULT false 🆕", "是否定稿版本"],
        ["content", "JSON", "NOT NULL", "完整快照 JSON"],
        ["created_by", "INT", "FK→users.id NULL", "创建者"],
        ["created_at", "DATETIME", "NOT NULL", "创建时间"],
        ["UNIQUE(script_id, version_number)", "", "唯一索引", ""],
    ]),
    ("script_imports（导入原文表 🆕待建）", [
        ["id", "INT", "PK AUTO_INCREMENT", ""],
        ["script_id", "INT", "FK→scripts.id NOT NULL", ""],
        ["file_name", "VARCHAR(255)", "NOT NULL", "原文件名"],
        ["file_type", "VARCHAR(16)", "NOT NULL", "txt/docx/pdf"],
        ["file_size", "INT", "NOT NULL", "字节数"],
        ["file_url", "VARCHAR(512)", "NULL", "存OSS的URL（大文本不直接存DB）"],
        ["raw_text", "LONGTEXT", "NULL", "解析后纯文本"],
        ["created_at", "DATETIME", "NOT NULL", ""],
    ]),
    ("tag_dictionaries（标签词典表 🆕待建）", [
        ["id", "INT", "PK AUTO_INCREMENT", ""],
        ["category", "VARCHAR(32)", "NOT NULL INDEX", "theme/plot/time/emotion/artstyle/shot/appearance"],
        ["name", "VARCHAR(64)", "NOT NULL", "标签名"],
        ["weight", "INT", "DEFAULT 0", "权重（用于排序）"],
        ["sort_order", "INT", "DEFAULT 0", "排序"],
        ["is_active", "BOOLEAN", "DEFAULT true", "是否启用"],
        ["UNIQUE(category, name)", "", "唯一", ""],
    ]),
    ("ai_providers（AI 模型配置表 🆕待建）", [
        ["id", "INT", "PK AUTO_INCREMENT", ""],
        ["name", "VARCHAR(64)", "NOT NULL", "标识名（如doubao-pro/deepseek-chat）"],
        ["provider", "VARCHAR(32)", "NOT NULL", "openai/anthropic/doubao/qwen/deepseek/custom"],
        ["model_name", "VARCHAR(128)", "NOT NULL", "实际模型名"],
        ["base_url", "VARCHAR(255)", "NOT NULL", "API endpoint"],
        ["api_key_enc", "VARCHAR(512)", "NOT NULL", "加密后的API Key"],
        ["task_bindings", "JSON", "NULL", "绑定的任务类型数组"],
        ["is_active", "BOOLEAN", "DEFAULT true", ""],
        ["priority", "INT", "DEFAULT 0", "优先级（用于故障切换）"],
    ]),
    ("prompt_templates（Prompt 模板表 🆕待建）", [
        ["id", "INT", "PK AUTO_INCREMENT", ""],
        ["task_key", "VARCHAR(64)", "NOT NULL INDEX", "generate_outline/review_outline/generate_episode/..."],
        ["version", "VARCHAR(16)", "NOT NULL", "v1/v2/..."],
        ["system_prompt", "TEXT", "NOT NULL", "系统提示词"],
        ["user_prompt_template", "TEXT", "NOT NULL", "用户提示词模板（含{variables}）"],
        ["variables", "JSON", "NULL", "变量定义 schema"],
        ["is_active", "BOOLEAN", "DEFAULT true", ""],
        ["created_at", "DATETIME", "NOT NULL", ""],
        ["UNIQUE(task_key, version)", "", "唯一", ""],
    ]),
    ("ai_calls（AI 调用日志表 🆕待建）", [
        ["id", "BIGINT", "PK AUTO_INCREMENT", ""],
        ["user_id", "INT", "FK→users.id INDEX", ""],
        ["script_id", "INT", "FK→scripts.id NULL INDEX", ""],
        ["version_id", "INT", "FK→script_versions.id NULL", ""],
        ["task_key", "VARCHAR(64)", "NOT NULL INDEX", "generate_outline/ai_fix/..."],
        ["provider_id", "INT", "FK→ai_providers.id", "使用的模型"],
        ["model_name", "VARCHAR(128)", "NOT NULL", ""],
        ["input_tokens", "INT", "NOT NULL DEFAULT 0", ""],
        ["output_tokens", "INT", "NOT NULL DEFAULT 0", ""],
        ["latency_ms", "INT", "NOT NULL DEFAULT 0", "耗时毫秒"],
        ["status", "VARCHAR(16)", "NOT NULL", "success/failed/timeout/cancelled"],
        ["error_msg", "TEXT", "NULL", ""],
        ["request_body", "JSON", "NULL", "请求快照（脱敏后）"],
        ["created_at", "DATETIME", "NOT NULL INDEX", ""],
    ]),
    ("ai_tasks（AI 任务队列表 🆕待建）", [
        ["id", "BIGINT", "PK AUTO_INCREMENT", ""],
        ["task_key", "VARCHAR(64)", "NOT NULL INDEX", ""],
        ["script_id", "INT", "FK→scripts.id NULL", ""],
        ["user_id", "INT", "FK→users.id NOT NULL", ""],
        ["status", "VARCHAR(16)", "NOT NULL INDEX", "pending/streaming/done/failed/cancelled"],
        ["progress", "TINYINT", "DEFAULT 0", "0-100"],
        ["params", "JSON", "NULL", "调用参数"],
        ["result_ref", "VARCHAR(255)", "NULL", "结果存储引用"],
        ["error_msg", "TEXT", "NULL", ""],
        ["started_at", "DATETIME", "NULL", ""],
        ["finished_at", "DATETIME", "NULL", ""],
        ["created_at", "DATETIME", "NOT NULL", ""],
    ]),
    ("character_references（角色参考图表 🆕待建，可选）", [
        ["id", "INT", "PK AUTO_INCREMENT", ""],
        ["script_id", "INT", "FK→scripts.id NOT NULL", ""],
        ["character_id", "VARCHAR(64)", "NOT NULL", "JSON中的角色ID"],
        ["url", "VARCHAR(512)", "NOT NULL", "图片URL"],
        ["sort_order", "INT", "DEFAULT 0", ""],
        ["created_at", "DATETIME", "NOT NULL", ""],
    ]),
]

row = 2
for tbl_name, fields in tables:
    style_section_row(ws2, row, len(headers2), tbl_name)
    row += 1
    for f in fields:
        add_data_row(ws2, row, f)
        ws2.row_dimensions[row].height = 24
        row += 1

ws2.freeze_panes = "A2"

# ============================================================
# Sheet 3: API 路由清单
# ============================================================
ws3 = wb.create_sheet("API路由清单")
headers3 = ["方法", "路径", "功能", "优先级", "状态", "鉴权", "说明"]
widths3 = [8, 52, 24, 10, 10, 8, 42]
for i, (h, w) in enumerate(zip(headers3, widths3), 1):
    ws3.cell(row=1, column=i, value=h)
    ws3.column_dimensions[get_column_letter(i)].width = w
style_header_row(ws3, 1, len(headers3))
ws3.row_dimensions[1].height = 28

apis = [
    ("认证 Auth", [
        ["POST", "/api/auth/register", "用户注册", "P0", "已完成", "否", "返回 JWT + 用户信息"],
        ["POST", "/api/auth/login", "用户登录", "P0", "已完成", "否", "返回 JWT"],
        ["GET", "/api/auth/me", "获取当前用户", "P0", "已完成", "是", ""],
        ["PUT", "/api/auth/password", "修改密码", "P2", "待做", "是", ""],
        ["POST", "/api/auth/avatar", "上传头像", "P2", "待做", "是", "multipart/form-data"],
    ]),
    ("剧本 Scripts", [
        ["GET", "/api/scripts", "剧本列表（搜索+分页+状态筛选）", "P0", "部分完成", "是", "加 q/status 参数"],
        ["POST", "/api/scripts", "创建剧本", "P0", "已完成", "是", "path_type+config"],
        ["GET", "/api/scripts/{id}", "获取剧本详情", "P0", "已完成", "是", "返回完整 content"],
        ["PATCH", "/api/scripts/{id}", "局部更新剧本", "P0", "待做", "是", "只传变更字段"],
        ["DELETE", "/api/scripts/{id}", "删除剧本（软删）", "P1", "部分完成", "是", "改软删"],
        ["POST", "/api/scripts/{id}/duplicate", "复制剧本", "P1", "待做", "是", "完整复制 content"],
        ["POST", "/api/scripts/{id}/archive", "归档/恢复", "P2", "待做", "是", ""],
        ["POST", "/api/scripts/{id}/lock", "定稿锁定", "P0", "待做", "是", "is_final=true"],
    ]),
    ("版本 Versions", [
        ["GET", "/api/scripts/{id}/versions", "版本列表", "P0", "已完成", "是", ""],
        ["POST", "/api/scripts/{id}/versions", "创建版本快照", "P0", "已完成", "是", "可传 name/commit_message"],
        ["GET", "/api/scripts/{id}/versions/{vid}", "获取指定版本", "P0", "已完成", "是", ""],
        ["POST", "/api/scripts/{id}/versions/{vid}/restore", "恢复版本", "P0", "已完成", "是", "content 覆盖回主表"],
        ["DELETE", "/api/scripts/{id}/versions/{vid}", "删除版本", "P1", "已完成", "是", "当前版本不可删"],
        ["GET", "/api/scripts/{id}/versions/diff", "版本对比", "P1", "待做", "是", "v1/v2 参数，返回 JSON diff"],
    ]),
    ("标签与词库 Tags", [
        ["GET", "/api/tags", "标签词库", "P1", "待做", "否", "按 category 过滤"],
        ["POST", "/api/admin/tags", "新增标签（运营）", "P2", "待做", "是(管理员)", ""],
        ["PUT", "/api/admin/tags/{id}", "编辑标签", "P2", "待做", "是(管理员)", ""],
        ["DELETE", "/api/admin/tags/{id}", "删除标签", "P2", "待做", "是(管理员)", ""],
    ]),
    ("导入 Import", [
        ["POST", "/api/scripts/import", "上传并解析剧本文件", "P1", "待做", "是", "multipart，支持 txt/docx/pdf"],
        ["POST", "/api/ai/parse-script", "AI 解析导入文本", "P1", "待做", "是", "SSE 流式，返回 outline+episodes"],
    ]),
    ("角色 Characters", [
        ["GET", "/api/scripts/{id}/characters", "角色列表", "P0", "待做", "是", "可从 content JSON 派生"],
        ["POST", "/api/scripts/{id}/characters", "新增角色", "P0", "待做", "是", ""],
        ["PUT", "/api/scripts/{id}/characters/{cid}", "更新角色", "P0", "待做", "是", ""],
        ["DELETE", "/api/scripts/{id}/characters/{cid}", "删除角色", "P0", "待做", "是", ""],
        ["POST", "/api/scripts/{id}/characters/{cid}/references", "上传参考图", "P2", "待做", "是", ""],
    ]),
    ("分集 Episodes", [
        ["GET", "/api/scripts/{id}/episodes", "分集列表", "P1", "待做", "是", ""],
        ["POST", "/api/scripts/{id}/episodes", "新增分集", "P1", "待做", "是", ""],
        ["PUT", "/api/scripts/{id}/episodes/{eid}", "更新分集", "P1", "待做", "是", ""],
        ["DELETE", "/api/scripts/{id}/episodes/{eid}", "删除分集", "P1", "待做", "是", ""],
        ["POST", "/api/scripts/{id}/episodes/{eid}/pass", "通过当前集", "P0", "待做", "是", "locked=true"],
        ["POST", "/api/scripts/{id}/episodes/{eid}/validate", "时长校验", "P2", "待做", "是", ""],
    ]),
    ("AI 核心接口（均为 SSE 流式）", [
        ["POST", "/api/ai/generate-outline", "AI 生成大纲（Step0→1）", "P0", "待做", "是", "流式返回 16 个大纲模块"],
        ["POST", "/api/ai/review-outline", "AI 大纲自审", "P0", "待做", "是", "返回 issues+aiScore"],
        ["POST", "/api/ai/modify-outline-module", "AI 单模块修改", "P1", "待做", "是", "流式"],
        ["POST", "/api/ai/batch-modify-outline", "AI 批量修改大纲", "P1", "待做", "是", "流式"],
        ["POST", "/api/ai/review-characters", "AI 人物自审", "P1", "待做", "是", "返回人物 issues"],
        ["POST", "/api/ai/generate-characters", "AI 补全配角", "P2", "待做", "是", "流式"],
        ["POST", "/api/ai/generate-episode", "AI 生成单集分镜", "P0", "待做", "是", "流式返回4层结构"],
        ["POST", "/api/ai/review-episode", "AI 分集自审", "P0", "待做", "是", "返回 T0/T1/T2 issues"],
        ["POST", "/api/ai/fix-episode", "AI Fix 局部修复", "P0", "待做", "是", "按 issues 修改对应 behaviors"],
        ["POST", "/api/ai/rewrite-segment", "AI 局部改写助手", "P1", "待做", "是", "返回多候选"],
    ]),
    ("导出 Export", [
        ["GET", "/api/scripts/{id}/export", "导出剧本文件", "P1", "待做", "是", "format=docx|pdf|txt|fountain"],
    ]),
    ("任务与上传", [
        ["GET", "/api/tasks/{taskId}", "查询AI任务状态", "P1", "待做", "是", "SSE重连用"],
        ["POST", "/api/tasks/{taskId}/cancel", "取消AI任务", "P1", "待做", "是", ""],
        ["POST", "/api/uploads/image", "通用图片上传", "P2", "待做", "是", "返回URL"],
        ["GET", "/api/health", "健康检查", "P0", "已完成", "否", ""],
    ]),
]

row = 2
for sec, routes in apis:
    style_section_row(ws3, row, len(headers3), sec)
    row += 1
    for r in routes:
        pr = r[3]
        st = r[4]
        if st == "已完成":
            fill = done_fill
        elif st == "部分完成":
            fill = todo_fill
        elif pr == "P0":
            fill = p0_fill
        elif pr == "P1":
            fill = p1_fill
        elif pr == "P2":
            fill = p2_fill
        else:
            fill = p3_fill
        add_data_row(ws3, row, r, fill)
        ws3.row_dimensions[row].height = 24
        row += 1

ws3.freeze_panes = "A2"
ws3.auto_filter.ref = f"A1:G{row-1}"

# ============================================================
# Sheet 4: 数据结构（剧本 content JSON Schema）
# ============================================================
ws4 = wb.create_sheet("Content数据结构")
headers4 = ["层级", "字段", "类型", "说明"]
widths4 = [10, 28, 24, 70]
for i, (h, w) in enumerate(zip(headers4, widths4), 1):
    ws4.cell(row=1, column=i, value=h)
    ws4.column_dimensions[get_column_letter(i)].width = w
style_header_row(ws4, 1, len(headers4))
ws4.row_dimensions[1].height = 28

schema = [
    ("scripts.content 根对象", [
        ["根", "outlineData", "Array<OutlineModule>", "16 个大纲模块数组"],
        ["根", "characters", "Array<Character>", "角色列表（原型中叫 characterData，统一为 characters）"],
        ["根", "episodes", "Array<Episode>", "分集列表，4 层嵌套"],
        ["根", "outlineState", "Object", "大纲 UI 状态（checkedIssues/userNotes/queuedModules/activeModuleId）"],
        ["根", "episodeIssues", "Object", "按 epId 索引的分集 AI 问题 { [epId]: Issue[] }"],
        ["根", "passedCharacters", "Array<string>", "已通过的角色ID列表"],
        ["根", "passedEpisodes", "Array<number>", "已通过的分集ID列表"],
    ]),
    ("OutlineModule 大纲模块", [
        ["字段", "id", "string", "m0/m1-1~m5"],
        ["字段", "type", "enum", "overview/setting/character/plot/volume/closure"],
        ["字段", "title", "string", "模块名"],
        ["字段", "badge", "string", "徽章文字"],
        ["字段", "summary", "string", "一句话摘要"],
        ["字段", "content", "string", "正文（可就地编辑）"],
        ["字段", "aiScore", "number 1-5", "AI 评分"],
        ["字段", "tone", "string", "情绪基调"],
        ["字段", "issues", "Array<OutlineIssue>", "AI 自审问题"],
        ["字段", "episodes", "Array<VolumeEp>", "仅分卷模块有，range/hook/summary"],
    ]),
    ("OutlineIssue 大纲问题", [
        ["字段", "severity", "1|2|3|4|5", "严重度星级"],
        ["字段", "type", "enum", "plot/logic/character/rhythm"],
        ["字段", "text", "string", "问题描述"],
        ["字段", "resolved", "boolean", "是否已解决（前端勾选标记）🆕"],
    ]),
    ("Character 角色", [
        ["字段", "id", "string", "c1/c2/..."],
        ["字段", "name/gender/age/role", "string", "基础信息"],
        ["字段", "tags", "string[]", "标签"],
        ["字段", "appearance", "Object", "外貌（height/faceShape/eyeShape/noseShape/lipShape/skinTone/bodyShape/mark[]）"],
        ["字段", "personality", "string", "性格"],
        ["字段", "background", "string", "身份背景"],
        ["字段", "tagline", "string", "口头禅"],
        ["字段", "arc", "string", "人物弧光"],
        ["字段", "relations", "string", "关系网"],
        ["字段", "motivation", "string", "核心动机"],
        ["字段", "description", "string", "详细描述"],
        ["字段", "reviewStatus", "enum 🆕", "pending/passed，角色通过状态"],
        ["字段", "issues", "Array<CharIssue>", "AI 自审问题（text/type/resolved）"],
        ["字段", "reviewNotes", "string", "用户审核意见"],
        ["字段", "referenceImages", "string[] 🆕", "参考图 URL"],
    ]),
    ("Episode 分集", [
        ["字段", "id", "number", "集号"],
        ["字段", "title", "string", "集标题"],
        ["字段", "duration", "number", "目标秒数"],
        ["字段", "sbSec", "number", "每分镜秒数"],
        ["字段", "locked", "boolean 🆕", "是否已锁定通过"],
        ["字段", "storyboards", "Array<Storyboard>", "分镜层"],
    ]),
    ("Storyboard 分镜 → Camera 镜头 → Behavior 行为（4 层嵌套）", [
        ["Storyboard", "title", "string", "分镜标题"],
        ["Storyboard", "cameras", "Array<Camera>", "镜头数组"],
        ["Camera", "shotType", "string", "景别（远景/全景/中景/近景/特写）"],
        ["Camera", "camMove", "string", "运镜（推/拉/摇/移/跟/固定）"],
        ["Camera", "cutReason", "string", "剪辑理由"],
        ["Camera", "behaviors", "Array<Behavior>", "行为数组"],
        ["Behavior", "duration", "number", "时长秒"],
        ["Behavior", "location", "string", "场景"],
        ["Behavior", "visual", "string", "画面描述"],
        ["Behavior", "character", "string", "角色"],
        ["Behavior", "action", "string", "动作"],
        ["Behavior", "dialog", "string", "台词"],
        ["Behavior", "dialogTag", "enum", "lip(对白)/voicover(旁白)/os(画外音)/narrator(解说)"],
        ["Behavior", "emotion", "string", "情绪"],
    ]),
    ("EpisodeIssue 分集 AI 问题", [
        ["字段", "id", "string", "问题ID"],
        ["字段", "priority", "T0|T1|T2", "阻断/重要/建议"],
        ["字段", "type", "string", "plot/logic/character/continuity/timing"],
        ["字段", "target", "Object", "{ si: 分镜索引, ci?: 镜头索引 }"],
        ["字段", "text", "string", "问题描述"],
        ["字段", "status", "pending|resolved", ""],
        ["字段", "source", "enum 🆕", "ai/user，区分 AI 自审还是人工添加"],
    ]),
    ("scripts.config 创作配置对象", [
        ["字段", "path", "A|B", "AI原创/导入"],
        ["AI", "style", "string", "风格预设（爽文短剧/悬疑推理/甜宠治愈…）"],
        ["AI", "episodes/pregen", "number", "总集数/预生成集数"],
        ["AI", "epDuration/shotSec", "number", "单集秒数/分镜秒数"],
        ["AI", "tags", "Object", "{ theme[], plot[], time, emotion[] }"],
        ["AI", "pace", "Object", "{preset, hookSec, cliffSec, dialogFreq, dialogLen, silenceSec, hookScope, must[], avoid[]}"],
        ["AI", "artStyle[]/shotPerf[]", "string[]", "画风美术/镜头表演"],
        ["AI", "sewingNovels[]", "string[]", "缝合小说名"],
        ["AI", "prompt", "string", "自由提示词"],
        ["AI", "generatedPrompt", "string 🆕", "最终拼接的完整 prompt（审计用）"],
        ["导入", "text/fileName", "string", "粘贴文本/文件名"],
        ["导入", "episodes/epDuration", "number", "解析集数/单集秒数"],
        ["导入", "tone", "string", "情绪基调（保持原味/爽感化/悬疑化/甜宠化）"],
    ]),
]

row = 2
for sec, fields in schema:
    style_section_row(ws4, row, len(headers4), sec)
    row += 1
    for f in fields:
        add_data_row(ws4, row, f)
        ws4.row_dimensions[row].height = 24
        row += 1

ws4.freeze_panes = "A2"

# ============================================================
# Sheet 5: AI 接口清单（详细）
# ============================================================
ws5 = wb.create_sheet("AI接口清单")
headers5 = ["接口", "触发时机", "输入", "输出（流式）", "绑定Prompt模板", "核心校验"]
widths5 = [28, 20, 32, 36, 24, 28]
for i, (h, w) in enumerate(zip(headers5, widths5), 1):
    ws5.cell(row=1, column=i, value=h)
    ws5.column_dimensions[get_column_letter(i)].width = w
style_header_row(ws5, 1, len(headers5))
ws5.row_dimensions[1].height = 28

ai_tasks = [
    ["/api/ai/generate-outline", "Step0点\"AI生成大纲\"", "四维标签+风格+体量(总集/预生成)+时长+节奏(钩子/断章/对白密度/留白)+必含/避雷+缝合小说列表+画风+镜头表演+自由prompt", "流式依次输出16个大纲模块：m0总览→m1-1~m1-4世界观→m2-1~m2-6核心人物→m3-1~m3-2爽点反转→m4-1~m4-4分卷剧情→m5逻辑闭环；每个模块含title/type/badge/summary/content/tone/aiScore，分卷模块附episodes[]", "generate_outline.v1", "1. 必须输出16个模块不缺漏\n2. 分卷 episodes 数=总集数\n3. JSON 格式严格校验"],
    ["/api/ai/parse-script", "Step0导入点\"解析并生成\"", "原文文本+目标集数+单集时长+情绪基调(保持原味/爽感化/悬疑化/甜宠化)", "流式输出：先输出识别的题材/风格/人物列表，再输出 outlineData（按原作文风改写后的大纲结构），最后输出 episodes 骨架（标题+hook）", "parse_import.v1", "1. 保留原文关键剧情节点\n2. 情绪基调转换到位\n3. 集数严格=目标集数"],
    ["/api/ai/review-outline", "Step1点\"重新自审\"/生成大纲后自动", "完整 outlineData（16模块）+ 创作 config", "流式对每个模块输出：aiScore(1-5)、issues 数组（severity/type/text）、tone 调整建议", "review_outline.v1", "1. 每模块至少1条建设性issue\n2. severity 打分客观\n3. 类型准确(plot/logic/character/rhythm)"],
    ["/api/ai/modify-outline-module", "Step1单模块点\"AI修改\"", "单个模块内容 + 该模块勾选的 issues + 用户 note", "流式输出修改后的模块 content/summary/tone，issues 中标 resolved 的项要在内容中体现修复", "modify_outline_module.v1", "1. 只修改指定模块\n2. 必须回应每个勾选 issue\n3. 不破坏其他模块逻辑"],
    ["/api/ai/batch-modify-outline", "Step1批量队列点\"一键批量修改\"", "多个模块(含选中issues)+globalNote全局说明", "流式依次输出修改后的各模块内容，最后给整体调整说明", "batch_modify_outline.v1", "1. 保持模块间一致性\n2. globalNote 需求要落到具体修改"],
    ["/api/ai/review-characters", "Step2进入/点\"重新自审\"", "完整characterData[]+outlineData+创作config", "流式对每个角色输出issues数组(type:consistency/motivation/arc/relation,text)，检查：人设矛盾、动机不成立、与大纲冲突、人物弧光断裂、关系网漏洞", "review_characters.v1", "1. 主角必须经过动机和弧光检查\n2. 与大纲出场人物对应"],
    ["/api/ai/generate-characters", "Step2点\"自动补全配角\"", "outlineData+已有角色列表", "流式输出推荐新增的配角/反派（完整人物小传字段）", "generate_characters.v1", "1. 不与已有角色重复\n2. 服务于大纲剧情需要"],
    ["/api/ai/generate-episode", "Step3点\"生成内容/重新生成\"", "剧本config+outlineData+characterData+第几集+前N集摘要+当前集hook+sbSec/epDuration节奏约束", "流式按分镜顺序输出：Storyboard(title)→Camera(shotType/camMove/cutReason)→Behavior(duration/location/visual/character/action/dialog/dialogTag/emotion)；严格遵守时长/对白密度/钩子位置", "generate_episode.v1", "1. 总时长≈epDuration±5%\n2. Behavior.duration累加=Camera累加=Storyboard累加=总时长\n3. 对白符合dialogFreq/dialogLen\n4. hookSec位置有钩子/cliffSec位置有断章\n5. 出场角色与大纲一致"],
    ["/api/ai/review-episode", "Step3进入分集后/点\"重新自审\"", "单集完整4层结构+全剧大纲+角色设定+前几集剧情continuity", "流式输出issues：priority(T0阻断/T1重要/T2建议)、type(plot/logic/character/continuity/timing)、target(si分镜索引,ci可选镜头索引)、text描述", "review_episode.v1", "1. T0：时长超标/角色OOC/逻辑硬伤\n2. target 必须精确定位到 si[+ci]\n3. continuity 检查与前集衔接"],
    ["/api/ai/fix-episode", "Step3勾选问题后点\"AI修改选中\"", "单集完整内容+勾选issues数组(T0/T1/T2)", "流式输出修改后的behaviors（按target定位），只修改相关字段，其他内容保持不变；修改后附简短修改说明", "fix_episode.v1", "1. 只改target指向的behavior\n2. 保持总时长不变\n3. 修改后对应issue标resolved"],
    ["/api/ai/rewrite-segment", "Step3局部改写弹窗", "选中的Behavior/台词片段+改写指令(更短/更燃/更含蓄/更换台词/调整情绪…)", "流式返回2-3个候选版本供用户选择", "rewrite_segment.v1", "1. 保留上下文剧情\n2. 符合指令要求\n3. 时长一致（调整visual/dialog字数）"],
]

row = 2
for t in ai_tasks:
    add_data_row(ws5, row, t, p1_fill)
    ws5.row_dimensions[row].height = 100
    row += 1

ws5.freeze_panes = "A2"

# ============================================================
# 保存
# ============================================================
output = "/workspace/剧本创作平台架构TodoList.xlsx"
wb.save(output)
print(f"✅ Excel 已生成: {output}")
print(f"共 {total_count} 个任务项，{len(tables)} 张表设计，{len(ai_tasks)} 个AI接口")
