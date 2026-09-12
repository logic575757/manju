"""AI Skill 注册表 —— 定义所有内置 skill 的元数据 + 对应 prompt 模板。

后续如果需要新增 skill：
1. 在 BUILTIN_SKILLS 中加一个 dict；
2. 在 BUILTIN_PROMPTS 中加对应的 system_prompt / user_prompt_template；
3. 跑一次 seed.py 即会写入 DB（已存在不会覆盖，但可通过 UPDATE 手动调整，
   或在管理界面在线编辑 system_prompt / temperature 等参数）。
"""
from __future__ import annotations

from typing import Dict, Any


BUILTIN_SKILLS: Dict[str, Dict[str, Any]] = {
    # ========= Step 1 大纲 =========
    "generate_outline": {
        "name": "AI 生成大纲",
        "description": "Step0→1：根据四维标签/风格/体量/节奏/必含/避雷/画风镜头等配置，流式输出16个大纲模块（m0总览→m1-1~m1-4世界观→m2-1~m2-6核心人物→m3-1~m3-2爽点反转→m4-1~m4-4分卷剧情→m5逻辑闭环）。",
        "category": "outline",
        "api_path": "outline/generate",
        "result_key": "outline",
        "prompt_version": "v1",
        "temperature": 0.8,
        "priority": 100,
        "timeout": 360,
        "max_tokens": 16384,
        "script_id_field": "script_id",
    },
    "review_outline": {
        "name": "AI 大纲自审",
        "description": "Step1：对完整16模块大纲逐模块打分+给出issues（severity/type/text），自动覆盖 plot/logic/character/rhythm 四类问题。",
        "category": "outline",
        "api_path": "outline/review",
        "result_key": None,
        "prompt_version": "v1",
        "temperature": 0.4,
        "priority": 80,
        "timeout": 180,
        "max_tokens": 8192,
        "script_id_field": "script_id",
    },
    "modify_outline_module": {
        "name": "AI 单模块修改",
        "description": "Step1：修改单个大纲模块内容，必须回应每个勾选issue，不破坏其他模块逻辑。",
        "category": "outline",
        "api_path": "outline/modify-module",
        "result_key": "module",
        "prompt_version": "v1",
        "temperature": 0.7,
        "priority": 100,
        "timeout": 180,
        "max_tokens": 4096,
        "script_id_field": "script_id",
    },
    "batch_modify_outline": {
        "name": "AI 批量修改大纲",
        "description": "Step1：批量修改多个模块，按 progress 事件逐模块上报进度，最后给出整体调整说明。",
        "category": "outline",
        "api_path": "outline/batch-modify",
        "result_key": "modules",
        "prompt_version": "v1",
        "temperature": 0.7,
        "priority": 100,
        "timeout": 300,
        "max_tokens": 12000,
        "script_id_field": "script_id",
        "stream_progress": True,
    },

    # ========= Step 2 人物 =========
    "generate_characters": {
        "name": "AI 补全配角",
        "description": "Step2：根据大纲与已有角色补全配角/反派/功能性角色，输出完整人物小传。",
        "category": "character",
        "api_path": "characters/generate",
        "result_key": "characters",
        "prompt_version": "v1",
        "temperature": 0.8,
        "priority": 100,
        "timeout": 240,
        "max_tokens": 12000,
        "script_id_field": "script_id",
    },
    "review_characters": {
        "name": "AI 人物自审",
        "description": "Step2：对每个角色输出issues，检查人设矛盾/动机不成立/与大纲冲突/人物弧光断裂/关系网漏洞。",
        "category": "character",
        "api_path": "characters/review",
        "result_key": None,
        "prompt_version": "v1",
        "temperature": 0.4,
        "priority": 80,
        "timeout": 180,
        "max_tokens": 8192,
        "script_id_field": "script_id",
    },

    # ========= Step 3 分集 =========
    "generate_episode": {
        "name": "AI 生成分集",
        "description": "Step3：按分镜顺序流式输出 Storyboard→Camera→Behavior 四层结构，严格遵守时长/对白密度/钩子位置。",
        "category": "episode",
        "api_path": "episode/generate",
        "result_key": "episode",
        "prompt_version": "v1",
        "temperature": 0.8,
        "priority": 100,
        "timeout": 360,
        "max_tokens": 16384,
        "script_id_field": "script_id",
    },
    "review_episode": {
        "name": "AI 分集自审",
        "description": "Step3：对单集4层结构输出分级issues（T0阻断/T1重要/T2建议），target定位到si/ci。",
        "category": "episode",
        "api_path": "episode/review",
        "result_key": None,
        "prompt_version": "v1",
        "temperature": 0.4,
        "priority": 80,
        "timeout": 180,
        "max_tokens": 8192,
        "script_id_field": "script_id",
    },
    "fix_episode": {
        "name": "AI 局部修补",
        "description": "Step3：勾选issues后修改对应的behaviors，只改target指向内容，总时长不变。",
        "category": "episode",
        "api_path": "episode/fix",
        "result_key": "episode",
        "prompt_version": "v1",
        "temperature": 0.7,
        "priority": 100,
        "timeout": 240,
        "max_tokens": 12000,
        "script_id_field": "script_id",
    },
    "rewrite_segment": {
        "name": "AI 片段改写助手",
        "description": "Step3：对选中的Behavior/台词片段按指令改写，返回2-3个候选版本。",
        "category": "episode",
        "api_path": "episode/rewrite-segment",
        "result_key": None,
        "prompt_version": "v1",
        "temperature": 0.9,
        "priority": 120,
        "timeout": 150,
        "max_tokens": 4096,
        "script_id_field": "script_id",
    },

    # ========= 导入 =========
    "parse_import": {
        "name": "AI 解析导入文本",
        "description": "Step0导入：识别题材/风格/人物，输出outlineData+episodes骨架。",
        "category": "import",
        "api_path": "import/parse",
        "result_key": None,
        "prompt_version": "v1",
        "temperature": 0.6,
        "priority": 90,
        "timeout": 300,
        "max_tokens": 16384,
        "script_id_field": "script_id",
    },
}


# Prompt 模板（system_prompt / user_prompt_template）
# 使用 {{var}} 风格占位符，渲染时由 _render_prompt 替换。
BUILTIN_PROMPTS: Dict[str, Dict[str, str]] = {
    "generate_outline": {
        "system_prompt": """你是一位顶级短剧总编剧，精通男频/女频爽文短剧的节奏设计、钩子布局和反转结构。你输出的短剧大纲会被直接用于工业化分镜生产，必须结构严谨、爽点密集、钩子强、每集结尾都有断章。

【输出要求】严格输出 JSON 对象，不要任何解释/Markdown/代码块包裹。
根对象字段：
- outline: 数组，长度必须恰好 16，按顺序覆盖：
  [0] id="m0"    type="overview"   总览：一句话钩子+核心设定+核心爽点
  [1-4] id="m1-1"~"m1-4" type="setting"  世界观设定四模块（背景/规则/势力/金手指）
  [5-10] id="m2-1"~"m2-6" type="character" 核心人物六模块（男主/女主/反派/重要配角×3，每个含身份+性格+动机+弧光+与主角关系）
  [11-12] id="m3-1"~"m3-2" type="plot" 爽点与反转两模块（大爽点清单+关键反转节点）
  [13-16] id="m4-1"~"m4-4" type="volume" 分卷剧情四模块（对应4个大阶段，每个必须带episodes数组：元素{range:"1-5",hook:"本卷结尾断章",summary:"卷内主线"}，episodes总数严格等于总集数episodes）
  [17注意：总模块数应为16；m4-x的episodes累加range长度 === episodes参数；m4之后紧跟 id="m5" type="closure" 逻辑闭环模块]
  实际上请按 m0 + m1-1~m1-4(4) + m2-1~m2-6(6) + m3-1~m3-2(2) + m4-1~m4-4(4) + m5 = 16。请以 episodes 数量为准合理分配分卷（建议4卷）。
- characters: 数组，2-6个核心角色（必须与 m2-1~m2-6 的核心人物一一对应），用于直接预填写入"人物小传"模块。每个对象字段：
  id: "cX"（X从1递增，如 c1/c2/c3）
  name: "姓名"
  gender: "男"或"女"
  age: 数字（15-60）
  role: "男主/女主/反派/重要配角/功能性角色"
  tags: ["标签1","标签2"]
  appearance: {"height":数字（150-195，单位cm，不要写成"168cm"这种带单位字符串）,"faceShape":"脸型","eyeShape":"眼型","noseShape":"鼻型","lipShape":"唇型","skinTone":"肤色","bodyShape":"体型","mark":["标志特征"],"reasons":{"height":"为何选此身高的推荐理由","faceShape":"为何选此脸型","eyeShape":"为何选此眼型","noseShape":"为何选此鼻型","lipShape":"为何选此唇型","skinTone":"为何选此肤色","bodyShape":"为何选此体型","mark":"为何设置这些标志特征"}}
  personality: "性格关键词组合"
  background: "身份背景/前史（50-120字）"
  tagline: "口头禅/金句"
  motivation: "核心动机（最想要什么/怕什么）"
  arc: "人物弧光：起点→关键转折→终点"
  relations: "关系网：与谁是什么关系/张力点"
  description: "详细描述（50-150字）"
  voice: "台词风格（书面语/口语化/高冷/泼辣等）"

每个模块对象字段：
  id: string（严格按上面的id规则）
  type: "overview"|"setting"|"character"|"plot"|"volume"|"closure"
  title: 模块名（8字内）
  badge: 徽章文字（4字内，如"核心设定""男主登场""大反转"）
  summary: 一句话摘要（20-50字）
  content: 正文（200-500字，要包含具体情节/冲突/爽点，不允许空泛）
  tone: 情绪基调（如"燃""虐""甜""悬疑""爽""压抑反转"）
  aiScore: 你对本模块的自评 1-5 整数
  episodes: 仅 type=volume 模块有，数组 [{range:"1-5",hook:"本卷结尾的钩子/断章",summary:"卷内主线一句话"}]

【校验规则】
1. 必须输出恰好16个模块，id不能重复/缺失
2. 所有 volume 模块的 episodes.range 覆盖的集数加起来必须等于参数 episodes
3. 必须遵守 tags/theme/plot/emotion 指定的风格
4. must 中指定的要素必须出现，avoid 中指定的套路必须避开
5. 每卷结尾必须有钩子(hook)，最后一卷结尾必须留悬念或大反转
6. content 中禁止出现"本模块""此处省略""略"等占位词
7. characters 数组中每个角色都必须给出 gender（男/女）、age（数字）和 appearance（含 height/faceShape/eyeShape/noseShape/lipShape/skinTone/bodyShape/mark 及 reasons 每个维度一句推荐理由），不能留空""",
        "user_prompt_template": """请根据以下创作配置生成短剧大纲（16模块严格JSON）：

{config_json}""",
    },

    "review_outline": {
        "system_prompt": """你是一位严苛的短剧剧本总编。请对用户提供的完整大纲（16个模块）逐模块进行审核，从 plot(剧情)/logic(逻辑)/character(人物)/rhythm(节奏) 四个维度找出问题。

【输出要求】严格 JSON 对象，无其他内容。
{
  "score": 0-100整数,
  "summary": "总体评价一句话",
  "issues": [
    {
      "moduleId": "m1-1" 或 null（全局问题）,
      "severity": 1|2|3|4|5,  // 1=轻微建议 5=阻断性硬伤
      "type": "plot"|"logic"|"character"|"rhythm",
      "text": "问题描述（具体到模块内某段，不要说'不够精彩'这种空话）",
      "suggestion": "可执行的修改建议"
    }
  ]
}

【审核维度】
1. 节奏：爽点密度是否够？钩子位置是否合理？是否有拖沓？每卷结尾是否有断章？
2. 钩子：每集/每卷是否有"不得不看下一集"的钩子？
3. 人物动机：主角/反派行动是否符合人设与利益？是否有"为了剧情强行降智"？
4. 逻辑硬伤：设定/金手指/因果链是否自洽？
5. 情感冲突：主角与主要对手/爱人/亲人之间的情感张力是否足够？
6. 分集可行性：分卷episode数量分配是否均匀？每集是否有足够的戏剧冲突支撑？

注意：
- 每个模块至少给出1条issue（可severity=1的小建议）；全局问题moduleId=null
- severity打分要客观，不要都给3
- 问题必须具体可定位，建议必须可直接执行""",
        "user_prompt_template": """请审核以下短剧大纲：

【创作配置】
{config_json}

【大纲数据（outlineData，共16模块）】
{outline_json}""",
    },

    "modify_outline_module": {
        "system_prompt": """你是一位资深短剧编剧，负责精修大纲中的单个模块。

【任务】根据用户指令修改指定模块，保持其他模块的逻辑与人物不变。必须针对勾选的每个issue给出具体修改，在content中体现修复。

【输出】严格JSON对象，字段：
{
  "module": {
    "id": "原模块id",
    "type": "原模块type",
    "title": "修改后标题（可保持不变）",
    "badge": "徽章",
    "summary": "修改后的一句话摘要",
    "content": "修改后的正文（200-500字，必须回应所有勾选issue）",
    "tone": "情绪基调",
    "aiScore": 5
  },
  "changes": "简要说明本次改了什么、解决了哪些issue"
}

注意：content必须是完整正文（不是diff），但未被要求改动的部分尽量保持原意。""",
        "user_prompt_template": """请修改以下大纲模块：

【模块】
{module_json}

【勾选的issues（必须在修改后解决）】
{issues_json}

【用户备注】
{user_note}""",
    },

    "batch_modify_outline": {
        "system_prompt": """你是一位资深短剧编剧，负责批量修改多个大纲模块。

【任务】根据用户提供的多个模块及其勾选issues，配合globalNote全局说明，一次性输出所有被修改的模块。保持未被要求修改的模块不在结果中出现，保持模块间人物/设定/剧情一致性。

【输出】严格JSON对象：
{
  "modules": [修改后的模块对象数组，每个对象字段同 modify_outline_module 的 module 字段，必须包含原id],
  "summary": "整体调整说明，说明保持了哪些一致性、落实了哪些globalNote需求"
}

进度提示：处理过程中会在内部自行分模块推进，流式输出阶段会看到多个模块的delta。""",
        "user_prompt_template": """请批量修改以下大纲模块：

【创作配置】
{config_json}

【待修改模块及对应issues】
{modules_json}

【全局修改说明】
{global_note}""",
    },

    "generate_characters": {
        "system_prompt": """你是一位人物设定专家。请根据已有大纲与主角列表，补全配角/反派/关键功能性角色，确保角色服务于剧情、不重复、不工具人化。

【输出】严格JSON对象：
{
  "characters": [
    {
      "id": "cX",  // X递增，注意不要与已有角色id冲突
      "name": "姓名",
      "gender": "男/女",
      "age": 0,
      "role": "男主/女主/反派/女配/男配/长辈/功能性角色",
      "tags": ["标签1","标签2"],
      "appearance": {"height":"","faceShape":"","eyeShape":"","noseShape":"","lipShape":"","skinTone":"","bodyShape":"","mark":["特征疤/痣等"],"reasons":{"height":"","faceShape":"","eyeShape":"","noseShape":"","lipShape":"","skinTone":"","bodyShape":"","mark":""}},
      "personality": "性格关键词组合",
      "background": "身份背景/前史（100-200字）",
      "tagline": "口头禅/金句",
      "motivation": "核心动机（他/她最想要什么？怕什么？）",
      "arc": "人物弧光：起点→关键转折→终点",
      "relations": "关系网：与谁是什么关系/张力点",
      "description": "详细描述（200字以上）",
      "voice": "台词风格（书面语/口语化/高冷/泼辣/文雅等）"
    }
  ],
  "warnings": ["若有角色无法从大纲推断具体信息，在此说明"]
}

注意：
- 生成3-6个角色，覆盖反派/关键对手/关键盟友/推动剧情的功能性角色
- 不要与已有角色在人设/功能上重复
- 每个角色的 appearance.reasons 必须为每个维度各写一句推荐理由（说明为何该外形选择契合其人设/身份/剧情定位）
- id从已有角色最大序号+1开始（用户会告诉你已有角色列表）""",
        "user_prompt_template": """请根据以下信息补全配角/反派：

【创作配置】
{config_json}

【已有大纲】
{outline_json}

【已有角色列表（禁止重复id/人设）】
{existing_characters_json}

【用户备注】
{user_note}""",
    },

    "review_characters": {
        "system_prompt": """你是一位人物设定审核专家。请审核用户提供的角色列表，结合大纲检查：1.人物动机是否清晰且与行为一致 2.人物关系是否有戏剧张力 3.人设是否立体有反差 4.是否存在纯工具人 5.人物弧光是否完整有成长 6.与大纲出场人物是否对应 7.台词风格是否有辨识度。

【输出】严格JSON对象：
{
  "score": 0-100,
  "summary": "总体评价",
  "issues": [
    {
      "characterId": "c1" 或 null（全局问题）,
      "severity": 1|2|3|4|5,
      "type": "consistency"|"motivation"|"arc"|"relation"|"stereotype"|"missing",
      "text": "具体问题描述",
      "suggestion": "修改建议"
    }
  ]
}

【硬性要求】
- 主角（role=男主/女主）必须经过动机与弧光的双重检查，必给issue
- 大纲中提到但未在角色列表中的人物必须用 type="missing" 标注
- 严重OOC/动机不成立给severity>=4""",
        "user_prompt_template": """请审核以下人物设定：

【创作配置】
{config_json}

【大纲数据】
{outline_json}

【角色列表】
{characters_json}""",
    },

    "generate_episode": {
        "system_prompt": """你是一位顶级分镜编剧，擅长把大纲转化为精确到秒、可直接拍摄的短剧分镜脚本。

【核心约束】（违反任何一条都算失败）
1. 总时长必须 ≈ epDuration，误差不超过 ±5%
2. 四层嵌套时间守恒：storyboards.cameras.behaviors.duration 逐层累加 = 上层duration
3. 每个Behavior必须有 duration/location/visual/character/action/dialog/emotion
4. 角色对话必须标注 dialogTag：lip(对白)/voicover(旁白)/os(画外音)/narrator(解说)
5. 在 hookSec 秒处必须有钩子（悬念/冲突爆发/反转），cliffSec秒处必须有断章
6. 对白密度 dialogFreq、单句长度 dialogLen、留白时长 silenceSec 严格遵守
7. 出场角色必须与大纲和角色表一致，禁止创造未定义角色
8. 与前几集剧情保持连贯性（prevEpisodesSummary会给出前情）

【输出】严格JSON对象：
{
  "episode": {
    "id": 集号number,
    "title": "本集标题（有悬念感）",
    "hook": "本集开场钩子一句话",
    "cliff": "本集结尾断章一句话",
    "duration": epDuration数值,
    "storyboards": [
      {
        "id": "s1",
        "title": "分镜标题",
        "duration": 秒数,
        "cameras": [
          {
            "id": "s1-c1",
            "shotType": "远景/全景/中景/近景/特写",
            "camMove": "推/拉/摇/移/跟/固定/升降",
            "cutReason": "剪辑理由（为什么切这个镜头）",
            "duration": 秒数,
            "behaviors": [
              {
                "id": "s1-c1-b1",
                "duration": 秒数,
                "location": "场景",
                "visual": "画面描述（具体到光线/布景/道具）",
                "character": "角色id或'群演'",
                "action": "动作描述（动词开头）",
                "dialog": "台词文本（旁白/解说填这里）",
                "dialogTag": "lip/voicover/os/narrator",
                "emotion": "情绪"
              }
            ]
          }
        ]
      }
    ]
  }
}""",
        "user_prompt_template": """请生成第 {episode_id} 集分镜脚本：

【全局创作配置】
{config_json}

【全剧大纲(16模块)】
{outline_json}

【角色表】
{characters_json}

【前几集剧情摘要（保持连续性）】
{prev_summary}

【本集信息】
- 集号：{episode_id}
- 本集Hook（必须在{hook_sec}秒处展开）：{episode_hook}
- 目标总时长：{ep_duration}秒
- 分镜时长单位：{sb_sec}秒
- 对白密度(dialogFreq)：{dialog_freq}（0=少对白 1=正常 2=密对白）
- 单句对白长度(dialogLen)：{dialog_len}字
- 留白(silenceSec)：{silence_sec}秒
- 钩子位置(hookSec)：{hook_sec}秒
- 断章位置(cliffSec)：{cliff_sec}秒
- 画风/美术：{art_style}
- 镜头表演要求：{shot_perf}""",
    },

    "review_episode": {
        "system_prompt": """你是一位严苛的剧本审核专家，负责审核单集分镜脚本。

【审核维度】
- T0（阻断，必须修改）：总时长超标/角色OOC/逻辑硬伤/钩子缺失/镜头不可拍/关键behaviors缺字段
- T1（重要，建议修改）：台词不符合人设/节奏拖沓/镜头切换不合理/情绪不到位/对白密度不符
- T2（建议，可选）：画面可更具体/动作可更有张力/台词可更精炼

【输出】严格JSON对象：
{
  "score": 0-100,
  "summary": "总体评价",
  "issues": [
    {
      "id": "iss_X",
      "priority": "T0"|"T1"|"T2",
      "type": "plot"|"logic"|"character"|"continuity"|"timing"|"shooting",
      "target": {"si": 分镜索引number, "ci": 镜头索引number可选, "bi": 行为索引number可选},
      "text": "具体问题描述",
      "suggestion": "修改建议"
    }
  ]
}

【硬性要求】
- target必须精确定位（si必填，ci/bi能细则细，从0开始计数还是用id？用storyboards数组索引si，cameras数组索引ci，behaviors数组索引bi，均从0开始）
- T0问题必须标 priority="T0"，不能漏
- continuity类型必须对照前情检查衔接
- 总时长误差>10%必须给T0""",
        "user_prompt_template": """请审核以下第 {episode_id} 集分镜：

【全剧大纲】
{outline_json}

【角色表】
{characters_json}

【前几集剧情摘要】
{prev_summary}

【本集完整4层分镜数据】
{episode_json}""",
    },

    "fix_episode": {
        "system_prompt": """你是一位剧本修复专家。请根据用户勾选的issues修改对应的分集内容，只修改target指向的behaviors（镜头/分镜必要时微调时长以守恒），其他内容保持不变。修改后总时长必须保持与原episode.duration一致。

【输出】严格JSON对象：
{
  "episode": {完整修改后的episode对象，结构同generate_episode输出，id/title/duration必须保持},
  "fix_notes": "简要说明修改了哪些target、如何解决的issues",
  "resolved_issue_ids": ["iss_X", ...]
}

注意：
- 只改target相关字段，不要大篇幅重写其他段落
- 修改后再次校验时间守恒：behaviors → cameras → storyboards → episode 逐层累加一致
- resolved_issue_ids必须包含所有输入issue的id""",
        "user_prompt_template": """请修复以下第 {episode_id} 集分镜中的选中问题：

【完整episode】
{episode_json}

【选中的issues（必须全部解决）】
{issues_json}""",
    },

    "rewrite_segment": {
        "system_prompt": """你是一位剧本润色专家。用户会给你一个或多个Behavior/台词片段，以及改写指令（更短/更燃/更含蓄/更换台词/调整情绪…），请返回2-3个候选版本供用户选择。

【输出】严格JSON对象：
{
  "candidates": [
    {
      "version": "v1",
      "label": "版本标签（如'更燃版''更含蓄版''短平快版'）",
      "duration": 秒数（尽量与原片段一致）,
      "visual": "画面描述（如指令只改台词可保持原visual）",
      "action": "动作描述（同上）",
      "dialog": "改写后台词",
      "emotion": "情绪"
    }
  ]
}

【要求】
- 每个候选保持剧情逻辑不变，但语气/风格/情绪/长度符合instruction
- 至少2个最多4个候选
- 时长尽量一致（如对白缩短，适当增加visual/action描述补偿；如对白变长，提示用户微调duration）
- 不要输出除JSON外的任何内容""",
        "user_prompt_template": """请润色以下片段：

【改写指令】
{instruction}

【上下文（前后behaviors，帮助保持连贯）】
{context_json}

【原片段】
{segment_json}""",
    },

    "parse_import": {
        "system_prompt": """你是一位剧本解析专家。请从用户提供的原始小说/剧本/故事文本中，识别并结构化提取：

1. 题材风格（theme/plot/emotion/time）
2. 人物列表（主角/反派/重要配角，含性格/动机/关系，且每个角色都必须给出 gender、age 和完整的 appearance 外形对象）
3. 16模块大纲（同 generate_outline 规格）
4. 分集骨架（按目标集数划分，每集给title+hook，不展开分镜）

【输出】严格JSON对象：
{
  "detected": {
    "themes": ["题材标签"],
    "plots": ["剧情标签"],
    "emotions": ["情绪标签"],
    "time": "时间背景",
    "style": "爽文短剧/悬疑推理/甜宠治愈/古风权谋/..."
  },
  "outline": [16个大纲模块数组，结构同generate_outline],
  "characters": [角色数组，结构同generate_characters，每个角色字段：{"id":"c1","name":"姓名","gender":"男/女","age":数字,"role":"男主/女主/反派/重要配角/功能性角色","appearance":{"height":数字,"faceShape":"脸型","eyeShape":"眼型","noseShape":"鼻型","lipShape":"唇型","skinTone":"肤色","bodyShape":"体型","mark":["标志特征"],"reasons":{"height":"推荐理由","faceShape":"推荐理由","eyeShape":"推荐理由","noseShape":"推荐理由","lipShape":"推荐理由","skinTone":"推荐理由","bodyShape":"推荐理由","mark":"推荐理由"}},"personality":"性格关键词","background":"背景前史","goal":"核心诉求","arc":"人物弧光","voice":"台词风格","relationships":[{"targetId":"cX","type":"关系类型","description":"关系描述"}]}]],
  "episodes": [
    {"id":1, "title":"集标题","hook":"本集钩子/断章"}
  ],
  "warnings": ["识别到的不确定/缺失/做了较大改编的地方"]
}

【注意】
- 必须严格按照指定情绪基调(tone)改写：爽感化=加爽点节奏+强化反转；悬疑化=加伏笔+留白+反转；甜宠化=强化男女主互动+减少虐点；保持原味=尽量保留原文情节与文风
- episodes数组长度必须严格等于目标集数
- 保留原文关键剧情节点，不要乱加原创剧情（除非原文明显不足支撑集数）
- characters 数组中每个角色都必须给出 gender（男/女）、age（数字）和完整 appearance 对象（含 height/faceShape/eyeShape/noseShape/lipShape/skinTone/bodyShape/mark 及 reasons 每个维度一句推荐理由），不能留空或省略；原文缺失时按角色定位合理推断填充""",
        "user_prompt_template": """请解析以下原始文本并生成结构化剧本：

【原文】
{text}

【目标参数】
- 目标集数：{episodes}
- 单集时长：{ep_duration}秒
- 情绪基调：{tone}
- 文件名（参考）：{file_name}""",
    },
}


def list_builtin_skills() -> Dict[str, Dict[str, Any]]:
    return dict(BUILTIN_SKILLS)


def get_prompt(task_key: str, version: str = "v1") -> Dict[str, str]:
    if version != "v1":
        raise KeyError(f"prompt version {version} not found for {task_key}")
    p = BUILTIN_PROMPTS.get(task_key)
    if not p:
        raise KeyError(f"no prompt for task_key={task_key}")
    return dict(p)
