import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import Base, engine, SessionLocal
import models
from models import TagDictionary, AiProvider, PromptTemplate, AiSkill
from ai.skills_registry import BUILTIN_SKILLS, BUILTIN_PROMPTS
from config import settings


TAG_DATA = {
    "theme": ["重生", "穿越", "逆袭", "甜宠", "悬疑", "复仇", "玄幻", "都市", "古风", "科幻", "末世", "职场", "校园", "豪门", "仙侠"],
    "plot": ["打脸", "虐恋", "爽点", "反转", "伏笔", "黑化", "替身", "逃婚", "失忆", "重生复仇", "真假千金", "系统流"],
    "time": ["古代", "现代", "未来", "架空", "末世", "民国"],
    "emotion": ["虐", "甜", "燃", "治愈", "紧张", "搞笑", "暗黑", "热血", "悬疑"],
    "appearance": ["剑眉星目", "清冷出尘", "英气逼人", "温润如玉", "明艳动人", "柔弱温婉", "邪魅狂狷", "阳光帅气"],
    "artstyle": ["写实电影感", "赛博朋克", "国风水墨", "日系动漫", "港风复古", "欧式油画", "暗黑哥特"],
    "shot": ["长镜头", "蒙太奇", "慢动作", "特写推进", "手持晃动", "空镜留白", "POV视角"],
}


def seed_tags(db):
    for category, names in TAG_DATA.items():
        for idx, name in enumerate(names):
            exists = (
                db.query(TagDictionary)
                .filter(TagDictionary.category == category, TagDictionary.name == name)
                .first()
            )
            if not exists:
                tag = TagDictionary(
                    category=category,
                    name=name,
                    sort_order=idx,
                    is_active=True,
                )
                db.add(tag)
    db.commit()


def seed_ai_provider(db):
    exists = db.query(AiProvider).filter(AiProvider.name == "mock").first()
    if not exists:
        provider = AiProvider(
            name="mock",
            provider="mock",
            model_name="mock-v1",
            base_url="",
            api_key_enc="",
            task_bindings=["*"],
            is_active=True,
            priority=100,
        )
        db.add(provider)
        db.commit()

    # 若 .env 配置了 LLM_API_KEY，则自动注册一个名为 "default-llm" 的真实 provider
    if settings.llm_api_key and settings.llm_base_url and settings.llm_model:
        name = settings.default_llm_provider if settings.default_llm_provider and settings.default_llm_provider != "mock" else "default-llm"
        exists = db.query(AiProvider).filter(AiProvider.name == name).first()
        if exists:
            exists.provider = "openai"
            exists.model_name = settings.llm_model
            exists.base_url = settings.llm_base_url
            exists.api_key_enc = settings.llm_api_key
            exists.task_bindings = ["*"]
            exists.is_active = True
            exists.priority = 10
            db.commit()
        else:
            provider = AiProvider(
                name=name,
                provider="openai",
                model_name=settings.llm_model,
                base_url=settings.llm_base_url,
                api_key_enc=settings.llm_api_key,
                task_bindings=["*"],
                is_active=True,
                priority=10,
            )
            db.add(provider)
            db.commit()


PROMPT_DATA = [
    {
        "task_key": "generate_outline",
        "system_prompt": "你是一位资深短剧编剧，擅长男频女频爽点节奏、钩子设计和反转结构。请根据用户给出的配置生成短剧大纲。输出必须是严格的 JSON（不要包含任何解释或 markdown），根为对象，包含字段 outline（数组），每个元素结构：{\"id\":\"m1\",\"index\":1,\"title\":\"模块标题\",\"summary\":\"20-50字概要\",\"goal\":\"主角阶段目标\",\"conflict\":\"核心冲突\",\"twist\":\"钩子/反转\",\"ending\":\"落点\"}。通常生成 12-16 个模块，覆盖开篇/起势/发展/高潮/结局完整节奏。",
        "user_prompt_template": "{config}",
    },
    {
        "task_key": "review_outline",
        "system_prompt": "你是一位短剧剧本审核专家。请从以下维度审核大纲：1.节奏与爽点密度 2.钩子设计 3.人物动机合理性 4.逻辑硬伤 5.情感冲突强度 6.分集可行性。输出严格 JSON，根对象包含 issues(数组，每个元素：{moduleId?:string,severity:'high'|'medium'|'low',category:string,suggestion:string}) 与 score(0-100整数)。问题要具体到模块，给出可执行修改建议。",
        "user_prompt_template": "{payload}",
    },
    {
        "task_key": "generate_episode",
        "system_prompt": "你是一位分镜编剧。请根据大纲上下文为指定集数生成分集分镜脚本。输出严格 JSON，根对象包含 episode 对象，结构为：{\"id\":\"eX\",\"index\":1,\"title\":\"本集标题\",\"summary\":\"本集概要60-120字\",\"duration\":90,\"cliffs\":[\"钩子1\"],\"acts\":[{\"id\":\"a1\",\"index\":1,\"title\":\"\",\"summary\":\"\",\"duration\":30,\"beats\":[{\"id\":\"b1\",\"index\":1,\"title\":\"\",\"summary\":\"\",\"goal\":\"\",\"conflict\":\"\",\"twist\":\"\",\"duration\":10,\"camera\":\"景别/运镜\",\"location\":\"场景\",\"charactersInFrame\":[\"c1\"],\"lines\":[{\"id\":\"l1\",\"index\":1,\"characterId\":\"c1\",\"text\":\"台词内容\",\"emotion\":\"情绪\",\"action\":\"动作提示\",\"voiceover\":false,\"duration\":3}]}]}]}。注意：duration单位为秒；每集时长通常60-120秒；lines中每个台词要指定characterId；beats.duration之和等于act.duration，acts之和等于episode.duration；每集结尾留钩子。",
        "user_prompt_template": "{payload}",
    },
    {
        "task_key": "review_episode",
        "system_prompt": "你是一位剧本审核专家。请审核这一分集分镜，重点关注：1.节奏是否紧凑 2.台词是否贴合人设 3.钩子是否够强 4.时长是否合理 5.拍摄可行性 6.人物动机连贯性。输出严格 JSON，根对象包含 issues(数组) 与 score(0-100整数)；issues 元素：{actId?:string,beatId?:string,lineId?:string,severity:'high'|'medium'|'low',category:string,suggestion:string}。",
        "user_prompt_template": "{payload}",
    },
    {
        "task_key": "fix_episode",
        "system_prompt": "你是一位剧本修改专家。请根据审核意见修改分集分镜，保留未被指出的部分不变，只修改有问题的段落。输出严格 JSON，根对象包含 episode（修改后完整的 episode 对象，结构同 generate_episode 的输出）。",
        "user_prompt_template": "{payload}",
    },
    {
        "task_key": "review_characters",
        "system_prompt": "你是一位人物设定专家。请审核这些人物小传，关注：1.人物动机是否清晰 2.人物关系是否有张力 3.人设是否立体有反差 4.是否工具人化 5.台词风格辨识度。输出严格 JSON，根对象包含 issues(数组，每个元素：{characterId?:string,severity:'high'|'medium'|'low',category:string,suggestion:string})。",
        "user_prompt_template": "{payload}",
    },
    {
        "task_key": "rewrite_segment",
        "system_prompt": "你是一位剧本润色专家。请按照用户指令改写指定段落（台词/动作/旁白等），提供多个风格化候选版本。输出严格 JSON，根对象包含 candidates（数组，2-4个字符串候选）。每个候选应保持剧情逻辑不变但语气/风格符合指令。",
        "user_prompt_template": "{payload}",
    },
    {
        "task_key": "modify_outline_module",
        "system_prompt": "你是一位大纲修改专家。请根据用户指令修改指定大纲模块，保持其他模块不变。输出严格 JSON，根对象包含 module（新的模块对象，包含 id/index/title/summary/goal/conflict/twist/ending）。",
        "user_prompt_template": "{payload}",
    },
    {
        "task_key": "batch_modify_outline",
        "system_prompt": "你是一位大纲修改专家。请根据用户的批量修改指令，对指定模块进行修改。输出严格 JSON，根对象包含 modules（数组，每个为修改后的模块完整对象）。只返回需要修改的那些模块。",
        "user_prompt_template": "{payload}",
    },
    {
        "task_key": "generate_characters",
        "system_prompt": "你是一位人物设计专家。请根据已有大纲和主角设定，补全配角/反派/关键功能性角色。输出严格 JSON，根对象包含 characters（数组），每个角色结构：{\"id\":\"cX\",\"name\":\"姓名\",\"role\":\"主角/女主/反派/女配/男配/功能性角色\",\"age\":0,\"appearance\":\"外形描述（30-60字）\",\"personality\":\"性格关键词\",\"background\":\"背景前史\",\"goal\":\"核心诉求\",\"arc\":\"人物弧光（起点→转折→终点）\",\"voice\":\"台词风格\",\"relationships\":[{\"targetId\":\"cX\",\"type\":\"关系类型\",\"description\":\"关系描述\"}]}。生成3-6个角色。",
        "user_prompt_template": "{payload}",
    },
    {
        "task_key": "parse_import",
        "system_prompt": "你是一位剧本解析专家。请从用户提供的原始剧本/故事文本中，提取结构化大纲与人物信息。输出严格 JSON，根对象包含：outline（数组，每个元素{id,index,title,summary,goal,conflict,twist,ending}）、characters（数组，每个元素{id,name,role,age,appearance,personality,background,goal,arc,voice,relationships}）、warnings（数组，字符串，表示识别到的不确定或缺失信息，可空）。若文本中某字段缺失，使用合理推断填充；id 使用 m1..mN、c1..cN。",
        "user_prompt_template": "{text}",
    },
]


def seed_prompts(db):
    for task_key, p in BUILTIN_PROMPTS.items():
        exists = (
            db.query(PromptTemplate)
            .filter(PromptTemplate.task_key == task_key, PromptTemplate.version == "v1")
            .first()
        )
        if not exists:
            prompt = PromptTemplate(
                task_key=task_key,
                version="v1",
                system_prompt=p["system_prompt"],
                user_prompt_template=p["user_prompt_template"],
                is_active=True,
            )
            db.add(prompt)
        else:
            # 内置 v1 prompt：若系统 prompt 明显比库里长（初次升级）则更新到新版本；
            # 用户自定义 prompt 请另存新版本（如 v2），本分支不会覆盖。
            new_sys = p["system_prompt"]
            if exists.system_prompt != new_sys and len(exists.system_prompt) < len(new_sys) - 50:
                exists.system_prompt = new_sys
                exists.user_prompt_template = p["user_prompt_template"]
    db.commit()


def seed_skills(db):
    for key, meta in BUILTIN_SKILLS.items():
        exists = db.query(AiSkill).filter(AiSkill.key == key).first()
        if exists:
            exists.name = meta["name"]
            exists.description = meta.get("description", "")
            exists.category = meta.get("category", "general")
            exists.api_path = meta["api_path"]
            exists.result_key = meta.get("result_key")
            exists.temperature = meta.get("temperature", 0.7)
            exists.priority = meta.get("priority", 100)
            exists.timeout = meta.get("timeout", 120)
            exists.max_tokens = meta.get("max_tokens", 4096)
            exists.stream_progress = meta.get("stream_progress", False)
            exists.auto_review = meta.get("auto_review", False)
            exists.script_id_field = meta.get("script_id_field")
            exists.is_active = True
            exists.is_builtin = True
            continue
        sk = AiSkill(
            key=key,
            name=meta["name"],
            description=meta.get("description", ""),
            category=meta.get("category", "general"),
            api_path=meta["api_path"],
            result_key=meta.get("result_key"),
            prompt_version=meta.get("prompt_version", "v1"),
            temperature=meta.get("temperature", 0.7),
            priority=meta.get("priority", 100),
            timeout=meta.get("timeout", 120),
            max_tokens=meta.get("max_tokens", 4096),
            stream_progress=meta.get("stream_progress", False),
            auto_review=meta.get("auto_review", False),
            script_id_field=meta.get("script_id_field"),
            is_active=True,
            is_builtin=True,
        )
        db.add(sk)
    db.commit()


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_tags(db)
        seed_ai_provider(db)
        seed_prompts(db)
        seed_skills(db)
        print("✅ 种子数据初始化完成")
        if settings.llm_api_key and settings.llm_base_url and settings.llm_model:
            print(f"✅ 已注册默认真实 LLM provider: base_url={settings.llm_base_url} model={settings.llm_model}")
        else:
            print("ℹ️  未配置 LLM_API_KEY/LLM_BASE_URL/LLM_MODEL，AI 将使用 Mock 数据；填入 .env 后重新运行 seed.py 即可切换为真实模型")
    finally:
        db.close()
