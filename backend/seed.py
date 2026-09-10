import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import Base, engine, SessionLocal
import models
from models import TagDictionary, AiProvider, PromptTemplate


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


PROMPT_DATA = [
    {
        "task_key": "generate_outline",
        "system_prompt": "你是一位资深短剧编剧...",
        "user_prompt_template": "请根据以下配置生成16模块大纲：{config}",
    },
    {
        "task_key": "review_outline",
        "system_prompt": "你是一位剧本审核专家...",
        "user_prompt_template": "请审核以下大纲：{outline}",
    },
    {
        "task_key": "generate_episode",
        "system_prompt": "你是一位分镜编剧...",
        "user_prompt_template": "请根据大纲和上下文生成分集分镜：{context}",
    },
    {
        "task_key": "review_episode",
        "system_prompt": "你是一位剧本审核专家...",
        "user_prompt_template": "请审核此分集：{episode}",
    },
    {
        "task_key": "fix_episode",
        "system_prompt": "你是一位剧本修改专家...",
        "user_prompt_template": "请修复以下问题：{issues}",
    },
    {
        "task_key": "review_characters",
        "system_prompt": "你是一位人物设定专家...",
        "user_prompt_template": "请审核人物小传：{characters}",
    },
    {
        "task_key": "rewrite_segment",
        "system_prompt": "你是一位剧本润色专家...",
        "user_prompt_template": "请按指令改写：{instruction}",
    },
    {
        "task_key": "modify_outline_module",
        "system_prompt": "你是一位大纲修改专家...",
        "user_prompt_template": "请修改该模块：{module}",
    },
    {
        "task_key": "batch_modify_outline",
        "system_prompt": "你是一位大纲修改专家...",
        "user_prompt_template": "请批量修改：{modules}",
    },
    {
        "task_key": "generate_characters",
        "system_prompt": "你是一位人物设计专家...",
        "user_prompt_template": "请补全配角：{outline}",
    },
    {
        "task_key": "parse_import",
        "system_prompt": "你是一位剧本解析专家...",
        "user_prompt_template": "请解析文本：{text}",
    },
]


def seed_prompts(db):
    for item in PROMPT_DATA:
        exists = (
            db.query(PromptTemplate)
            .filter(PromptTemplate.task_key == item["task_key"], PromptTemplate.version == "v1")
            .first()
        )
        if not exists:
            prompt = PromptTemplate(
                task_key=item["task_key"],
                version="v1",
                system_prompt=item["system_prompt"],
                user_prompt_template=item["user_prompt_template"],
                is_active=True,
            )
            db.add(prompt)
    db.commit()


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_tags(db)
        seed_ai_provider(db)
        seed_prompts(db)
        print("✅ 种子数据初始化完成")
    finally:
        db.close()
