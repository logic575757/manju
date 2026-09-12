import copy
import random
import time
from typing import Any, Dict, List, Optional, AsyncGenerator

from ai.sse import sse_event, sse_done, sse_error, stream_text_chunks, stream_phases


MOCK_OUTLINE = [
    {
        "id": "m0", "type": "meta", "title": "剧本总览",
        "badge": "总览",
        "summary": "女主重生归来，携子复仇，步步为营夺回家产，最终收获真爱与正义。",
        "aiScore": 88,
        "tone": "爽感十足、节奏紧凑、反转频出",
        "content": "【核心卖点】\n重生复仇+萌宝助攻+豪门商战+甜宠反转，20集每集90秒高密度爽点。\n\n【一句话梗概】\n五年前被陷害坠海身亡的苏晚晴带着天才萌宝重生归来，化名潜入前夫顾言的集团，利用前世记忆步步设局，手撕白莲花堂妹，夺回母亲遗产，揭露顾家罪证，最终与一直默默守护她的冷面律师陆沉渊走到一起。\n\n【情绪曲线】\n开篇压迫(1-3集)→首次反击(4-7集)→甜虐交织(8-13集)→高潮反转(14-18集)→大快人心(19-20集)\n\n【目标用户】\n25-45岁女性观众，偏好豪门复仇、萌宝、甜宠题材。",
        "issues": []
    },
    {
        "id": "m1-1", "type": "section", "title": "世界观与时代背景",
        "badge": "一、基础核心设定 / 世界观",
        "summary": "当代滨海都市，顶级豪门顾家掌控地产帝国，商业斗争激烈。",
        "aiScore": 85,
        "content": "【时代背景】\n当代滨海都市「海城」，一线城市，经济高度发达，以顾氏集团为首的四大豪门掌控地产、金融、娱乐三大产业。\n\n【社会环境】\n表面繁华，暗地里豪门之间暗流涌动。商战残酷，联姻、并购、做空手段层出不穷。\n\n【核心场景】\n1. 顾氏集团总部——88层摩天大楼，权力中心\n2. 顾家老宅——半山别墅，家族博弈场\n3. 苏氏集团旧址——被顾家吞并的女主母家企业\n4. 陆沉渊律师事务所——女主后期的情报基地\n5. 星光幼儿园——萌宝顾念念上学的地方，关键剧情触发点",
        "issues": [
            {"severity": 2, "type": "细节", "text": "四大豪门中另外三家可以在后续剧情中自然带出，目前不需要详细设定。"}
        ]
    },
    {
        "id": "m1-2", "type": "section", "title": "核心规则",
        "badge": "一、基础核心设定 / 核心规则",
        "summary": "重生设定：女主保留前世完整记忆，时间点回到坠海前三天。",
        "aiScore": 90,
        "content": "【重生规则】\n1. 苏晚晴重生回到2024年3月15日，即她「被自杀」坠海前三天\n2. 保留前世全部记忆，包括商业机密、人物隐秘、未来走向\n3. 萌宝顾念念当时3岁，在她重生当晚被忠心老管家偷偷送到身边\n4. 没有系统/金手指，纯粹靠前世信息差和智慧\n\n【叙事规则】\n1. 每集必须有1个钩子（悬念/反转/爽点）\n2. 每3集一个小高潮，每6集一个大反转\n3. 萌宝每集至少出场1次，提供信息或制造萌点\n4. 男女主感情线每2集推进一小步",
        "issues": []
    },
    {
        "id": "m2-1", "type": "section", "title": "女主：苏晚晴",
        "badge": "二、核心人物设定 / 女主",
        "summary": "28岁，前世是苏氏集团千金，被丈夫和堂妹联手害死。重生后冷静腹黑。",
        "aiScore": 92,
        "content": "【人物定位】\n表面温婉贤淑，实则心思缜密、步步为营的复仇者。重生后不再恋爱脑，目标明确：保护儿子、夺回一切、让仇人付出代价。\n\n【前史】\n父亲早逝后继承苏氏集团，被顾言的温柔追求打动嫁入顾家，却在婚后被堂妹苏梦瑶和丈夫联手架空，母亲遗产被侵吞，最终被推下海，伪装成自杀。\n\n【人物弧光】\n复仇机器→逐渐打开心扉→学会信任→放下执念，收获真爱\n\n【标志性动作】\n转动手腕上的旧银镯（母亲遗物），思考时的习惯。",
        "issues": []
    },
    {
        "id": "m2-2", "type": "section", "title": "男主：陆沉渊",
        "badge": "二、核心人物设定 / 男主",
        "summary": "32岁，海城顶尖律所合伙人，冷面律师，前世暗中调查苏晚晴死因。",
        "aiScore": 87,
        "content": "【人物定位】\n外冷内热的实力派律师，海城胜率最高的商业诉讼律师，表面只为钱办案，实则坚守正义底线。\n\n【与女主的关系】\n前世受苏晚晴母亲临终嘱托暗中保护苏晚晴，却未能阻止悲剧。重生时间线里，他在女主最孤立无援时出现，成为她复仇路上的盟友，逐渐从合作走向相爱。\n\n【人物秘密】\n陆家曾是海城第一豪门，被顾家联手其他家族陷害导致家破人亡，他隐姓埋名成为律师也是为了调查真相。\n\n【标志性台词】\n「证据不会说谎，人会。」",
        "issues": [
            {"severity": 1, "type": "伏笔", "text": "陆家被害的真相可以和女主母亲的死因挂钩，形成双线复仇。"}
        ]
    },
    {
        "id": "m2-3", "type": "section", "title": "反派与配角",
        "badge": "二、核心人物设定 / 反派配角",
        "summary": "渣男前夫顾言、白莲花堂妹苏梦瑶、萌宝顾念念、忠心管家福伯。",
        "aiScore": 84,
        "content": "【顾言——渣男前夫】\n30岁，顾氏集团少东家，表面温文尔雅，实则心狠手辣、控制欲极强。娶苏晚晴只为侵吞苏氏，对苏梦瑶也非真心。\n\n【苏梦瑶——白莲花堂妹】\n26岁，苏晚晴父亲兄长的私生女，寄居苏家，表面柔弱善良，实则嫉妒心极强，处处模仿苏晚晴。最终坐上顾太太位置却发现自己也是棋子。\n\n【顾念念——萌宝】\n3岁半，苏晚晴和顾言的儿子，智商超群的天才儿童，是女主最大软肋也是最强助攻，多次童言无忌点破真相。\n\n【福伯——忠仆】\n65岁，苏家老管家，唯一知道女主重生秘密的人，负责照顾念念和传递消息。",
        "issues": []
    },
    {
        "id": "m3-1", "type": "section", "title": "核心冲突与主线",
        "badge": "三、情节架构 / 核心冲突",
        "summary": "三条主线并行：复仇线夺回苏氏、感情线与陆沉渊相知、萌宝线守护儿子。",
        "aiScore": 89,
        "content": "【主线A：复仇夺产】\n苏晚晴化名「苏晴」进入顾氏集团，从基层做起，利用前世记忆：\n1. 提前截胡顾言的关键项目\n2. 揭露苏梦瑶的真面目\n3. 一步步收集顾氏吞并苏氏的非法证据\n4. 最终联合陆沉渊发起商业反击，夺回苏氏\n\n【主线B：感情发展】\n1. 初遇——陆沉渊受女主母亲遗嘱之托找到她\n2. 合作——建立利益同盟，他提供法律支持\n3. 试探——多次在险境中互相救助\n4. 信任——女主坦白重生秘密\n5. 相爱——联手翻盘后走到一起\n\n【主线C：萌宝守护】\n顾念念是连接所有人物的关键：顾言不知道他的存在，苏梦瑶多次想加害，陆沉渊暗中保护，最终父子相认（但顾言已失去一切）。",
        "issues": []
    },
    {
        "id": "m3-2", "type": "section", "title": "节奏结构",
        "badge": "三、情节架构 / 节奏结构",
        "summary": "20集分为4卷：重生归来、初露锋芒、甜虐交织、终极翻盘。",
        "aiScore": 91,
        "content": "【第一卷：重生归来（1-5集）——钩子密度高】\n- 开篇重生，回到坠海前3天\n- 联系福伯救下萌宝\n- 化名潜入顾氏\n- 首次出手，破坏顾言和苏梦瑶的定情宴会\n- 钩子：苏晚晴在顾氏电梯中与顾言擦肩而过，他没有认出她\n\n【第二卷：初露锋芒（6-10集）——爽点密集】\n- 职场中多次展现过人能力，引起顾言注意\n- 与陆沉渊建立合作\n- 苏梦瑶开始怀疑苏晴身份\n- 第一次商战胜利，截胡南城地块\n- 钩子：顾念念幼儿园活动上，顾言作为嘉宾出席\n\n【第三卷：甜虐交织（11-15集）——情感升温】\n- 顾言开始对「苏晴」产生兴趣，试图靠近\n- 陆沉渊吃醋，与女主关系微妙变化\n- 苏梦瑶设局陷害女主\n- 女主身份险些暴露\n- 陆沉渊为救女主受伤\n- 钩子：女主发现母亲的死并非意外\n\n【第四卷：终极翻盘（16-20集）——高潮爆发】\n- 女主主动暴露身份\n- 法庭对决，陆沉渊拿出关键证据\n- 苏梦瑶反水，交出顾言罪证\n- 顾氏崩塌，顾言入狱\n- 苏晚晴夺回苏氏，与陆沉渊在一起",
        "issues": []
    },
    {
        "id": "m4-1", "type": "section", "title": "第一卷·重生归来（第1-5集）",
        "badge": "四、分集大纲 / 第一卷",
        "summary": "重生开局，救下萌宝，化名潜入，首场惊艳亮相打破顾言布局。",
        "aiScore": 86,
        "content": "",
        "episodes": [
            {"range": "第1集", "hook": "重生归来·血仇立誓", "summary": "苏晚晴从冰冷海水中惊醒，发现自己回到坠海前三天。她疯狂联系福伯，得知儿子念念还活着，立誓这一世要让仇人付出血的代价。"},
            {"range": "第2集", "hook": "萌宝相认·母子连心", "summary": "福伯秘密带念念来见苏晚晴，3岁的念念一眼认出妈妈。苏晚晴抱着儿子痛哭，决心以新身份潜入顾氏集团。"},
            {"range": "第3集", "hook": "化名入职·步步为营", "summary": "苏晚晴通过面试进入顾氏集团市场部，成为一名普通策划。第一天上班就在电梯里与顾言相遇，他完全没认出换了气质的她。"},
            {"range": "第4集", "hook": "宴会风云·初露锋芒", "summary": "顾氏举办商业酒会，苏晚晴巧妙提醒合作方王总合同陷阱，引起全场关注。苏梦瑶注意到这个气质出众的新员工。"},
            {"range": "第5集", "hook": "律师登场·暗流涌动", "summary": "顾言因合同问题被告，对方代理律师正是陆沉渊。苏晚晴和陆沉渊在法院走廊第一次对视，陆沉渊的眼神让她感到莫名熟悉。"}
        ],
        "issues": []
    },
    {
        "id": "m4-2", "type": "section", "title": "第二卷·初露锋芒（第6-10集）",
        "badge": "四、分集大纲 / 第二卷",
        "summary": "职场崭露头角，与陆沉渊结盟，商战首胜，萌宝险被发现。",
        "aiScore": 88,
        "content": "",
        "episodes": [
            {"range": "第6集", "hook": "秘密同盟·利益交换", "summary": "陆沉渊主动约见苏晚晴，出示她母亲的遗嘱，表明自己受委托保护她。两人达成秘密同盟。"},
            {"range": "第7集", "hook": "南城地块·前世情报", "summary": "顾氏内部竞标南城地块，苏晚晴利用前世记忆提出精准方案，引起顾言注意，被破格提拔。"},
            {"range": "第8集", "hook": "白莲疑心·试探身份", "summary": "苏梦瑶以嫂子身份来公司「探班」，对苏晴百般试探。苏晚晴将计就计，故意露出破绽引她上钩。"},
            {"range": "第9集", "hook": "商战胜局·一鸣惊人", "summary": "南城地块竞标会上，苏晚晴的方案完胜对手公司，顾言对她刮目相看，庆功宴上主动邀她跳舞。"},
            {"range": "第10集", "hook": "幼儿园惊魂·父子擦肩", "summary": "幼儿园亲子日，顾言作为投资人出席，顾念念上台表演，顾言莫名觉得这个孩子眼熟，关键时刻陆沉渊出现替苏晚晴解围。"}
        ],
        "issues": [
            {"sever": 1, "type": "节奏", "text": "第8集和第9集之间可以加一个苏梦瑶的反派小动作，保持紧张感。"}
        ]
    },
    {
        "id": "m4-3", "type": "section", "title": "第三卷·甜虐交织（第11-15集）",
        "badge": "四、分集大纲 / 第三卷",
        "summary": "感情线升温，身份危机，生死相护，母亲死因真相浮出水面。",
        "aiScore": 85,
        "content": "",
        "episodes": [
            {"range": "第11集", "hook": "顾言追求·危险靠近", "summary": "顾言开始对苏晴产生浓厚兴趣，送花、邀约不断。苏晚晴将计就计利用他获取情报，但内心对陆沉渊的感情在萌芽。"},
            {"range": "第12集", "hook": "雨夜告白·沉渊吃醋", "summary": "陆沉渊看到苏晚晴上了顾言的车，雨夜在她家楼下等了一整夜。第二天带着药出现，冷着脸给她处理伤口。"},
            {"range": "第13集", "hook": "梦瑶设局·身份险露", "summary": "苏梦瑶拿到苏晴的头发去做DNA比对，福伯冒险潜入换掉样本。苏晚晴决定加快复仇节奏。"},
            {"range": "第14集", "hook": "车祸相救·沉渊受伤", "summary": "苏梦瑶买凶制造车祸，陆沉渊为保护苏晚晴身受重伤。病床前苏晚晴终于坦白自己重生的秘密。"},
            {"range": "第15集", "hook": "母亲遗信·真相初现", "summary": "陆沉渊交给苏晚晴一封她母亲的遗信，揭露母亲的死可能与顾老爷子有关，更大的阴谋浮出水面。"}
        ],
        "issues": []
    },
    {
        "id": "m4-4", "type": "section", "title": "第四卷·终极翻盘（第16-20集）",
        "badge": "四、分集大纲 / 第四卷",
        "summary": "身份公开，法庭对决，反派反水，大仇得报，圆满结局。",
        "aiScore": 93,
        "content": "",
        "episodes": [
            {"range": "第16集", "hook": "公开身份·全场震动", "summary": "顾氏集团股东大会上，苏晚晴以苏晚晴的真实身份现身，出示自己是苏氏合法继承人的证据，全场哗然。"},
            {"range": "第17集", "hook": "法庭交锋·证据为王", "summary": "陆沉渊代理苏晚晴起诉顾氏侵吞资产，法庭上顾言百般狡辩，关键证据链却一环扣一环地闭合。"},
            {"range": "第18集", "hook": "白莲反水·罪证曝光", "summary": "苏梦瑶发现自己也是顾言的棋子，万念俱灰下交出顾言指使她的录音和伪造遗嘱的证据。"},
            {"range": "第19集", "hook": "顾氏崩塌·恶人落网", "summary": "顾言被捕，顾老爷子中风入院，顾氏集团股价崩盘。苏晚晴正式夺回苏氏集团，更名重建。"},
            {"range": "第20集", "hook": "涅槃重生·携手余生", "summary": "半年后，苏晚晴带着念念在海边别墅生活，陆沉渊拿出戒指向她求婚。念念大喊「我要陆叔叔当我爸爸！」，夕阳下三人相拥。"}
        ],
        "issues": []
    }
]


MOCK_CHARACTERS = [
    {
        "id": "c1", "name": "苏晚晴", "gender": "女", "age": 28,
        "role": "女主角", "tags": ["重生", "复仇", "腹黑", "母爱", "商战女王"],
        "appearance": {
            "gender": "女", "age": 28, "height": 168,
            "faceShape": "鹅蛋脸", "eyeShape": "桃花眼", "noseShape": "精致翘鼻",
            "lipShape": "M字唇", "skinTone": "冷白皮", "bodyShape": "高挑清瘦",
            "mark": ["右锁骨处一颗小红痣", "左手腕旧银镯（不离身）"]
        },
        "personality": "重生前温婉善良、恋爱脑，重生后冷静果决、心思缜密，面对仇人时腹黑狠辣，面对儿子时温柔似水，对盟友重情重义。",
        "background": "苏氏集团唯一继承人，母亲陆婉如出身陆家，在她18岁时车祸去世（实为被害）。父亲早逝后独自掌管家业，被顾言追求嫁入顾家，婚后被架空侵吞，五年前被推下海伪装自杀。重生后化名「苏晴」潜入顾氏。",
        "tagline": "这一世，我要让你们欠我的，千倍百倍地还回来。",
        "arc": "从满心仇恨的复仇机器→在陆沉渊和念念的温暖下重新学会信任和爱→复仇成功后放下执念，成为独立自强的女企业家，收获真爱",
        "relations": "顾言（前夫/仇人）、陆沉渊（盟友→爱人）、苏梦瑶（堂妹/仇人）、顾念念（儿子）、福伯（忠仆/长辈）",
        "motivation": "保护儿子顾念念安全成长；夺回母亲和父亲留下的苏氏集团；让顾言、苏梦瑶以及所有参与谋害她和母亲的人受到法律制裁",
        "description": "重生归来的复仇女王，携子翻盘，步步为营。"
    },
    {
        "id": "c2", "name": "陆沉渊", "gender": "男", "age": 32,
        "role": "男主角", "tags": ["冷面律师", "隐忍守护", "世家遗孤", "外冷内热"],
        "appearance": {
            "gender": "男", "age": 32, "height": 185,
            "faceShape": "长脸", "eyeShape": "丹凤眼", "noseShape": "高挺直鼻",
            "lipShape": "薄唇", "skinTone": "自然偏白", "bodyShape": "宽肩挺拔",
            "mark": ["左手虎口一道旧疤", "常年佩戴一枚低调的铂金尾戒"]
        },
        "personality": "表面冷峻寡言、理性克制，办案时犀利精准、滴水不漏。内心重情重义，对认定的人甘愿付出一切，有极强的正义感和隐忍力。",
        "background": "原海城第一豪门陆家的遗孤，陆家十年前被顾老爷子联手其他家族陷害破产，父母双亡。他隐姓埋名苦读法律，成为海城顶尖商业诉讼律师，胜率99%。受苏晚晴母亲陆婉如临终嘱托（陆婉如也是陆家人），一直在暗中保护苏晚晴。",
        "tagline": "证据不会说谎，人会。",
        "arc": "从冷眼旁观的复仇者→被苏晚晴的坚韧打动→从受托保护变为真心相爱→放下家族仇恨，选择和苏晚晴一起以法律手段讨回公道",
        "relations": "苏晚晴（守护对象→爱人）、顾言（宿敌/陆家仇人之子）、顾念念（视如己出）、陆婉如（姑姑/恩人之托）",
        "motivation": "兑现对姑姑陆婉如的承诺保护苏晚晴母子；查明陆家被害真相；用法律而非暴力的方式让罪人伏法",
        "description": "冷面律师默默守护，是女主复仇路上最坚实的后盾。"
    },
    {
        "id": "c3", "name": "顾言", "gender": "男", "age": 30,
        "role": "反派·渣男前夫", "tags": ["伪君子", "控制狂", "豪门贵公子", "贪心不足"],
        "appearance": {
            "gender": "男", "age": 30, "height": 182,
            "faceShape": "方脸", "eyeShape": "狭长眼", "noseShape": "希腊鼻",
            "lipShape": "薄唇", "skinTone": "自然偏白", "bodyShape": "匀称健美",
            "mark": ["左手腕佩戴百达翡丽腕表（标配）"]
        },
        "personality": "表面温文尔雅、风度翩翩，实则心狠手辣、极度自私，把所有人都当成棋子。对苏晚晴有扭曲的占有欲，失去后才「发现」自己爱她，但本质上只爱自己。",
        "background": "顾氏集团独子，从小被当作接班人培养，习惯了要什么就能得到什么。娶苏晚晴完全是父亲安排的吞并苏氏的一步棋，对苏梦瑶也只是利用。在苏晚晴「死后」偶尔会梦到她，但从未真正忏悔。",
        "tagline": "晚晴，你为什么从来不肯乖乖听话呢？",
        "arc": "自信满满→对苏晴产生兴趣→发现苏晴就是苏晚晴时震惊愤怒→众叛亲离→锒铛入狱时终于忏悔但为时已晚",
        "relations": "苏晚晴（前妻/猎物→失控的棋子）、苏梦瑶（利用对象）、顾老爷子（父亲/幕后黑手）、顾念念（不知情的儿子）",
        "motivation": "掌控顾氏集团成为商业帝国之王；占有苏晚晴（无论是生是死，她都必须是他的）；维护顾家的地位和秘密",
        "description": "温文尔雅的外表下藏着蛇蝎心肠，典型的控制型渣男。"
    },
    {
        "id": "c4", "name": "苏梦瑶", "gender": "女", "age": 26,
        "role": "反派·白莲花堂妹", "tags": ["白莲花", "嫉妒", "伪装", "绿茶"],
        "appearance": {
            "gender": "女", "age": 26, "height": 163,
            "faceShape": "心形脸", "eyeShape": "杏眼", "noseShape": "精致肉鼻",
            "lipShape": "樱桃小嘴", "skinTone": "暖白皮", "bodyShape": "娇小玲珑",
            "mark": ["右耳后有一颗小痣", "喜欢佩戴珍珠耳坠（模仿苏晚晴）"]
        },
        "personality": "表面柔弱乖巧、人畜无害，说话柔声细语，实则内心阴暗、嫉妒心极强。长期活在苏晚晴的阴影下导致心理扭曲，以模仿苏晚晴、夺走她的一切为乐。",
        "background": "苏晚晴大伯的私生女，被苏家收留后一直以亲戚小姐自居，苏晚晴待她如亲妹妹，她却嫉妒苏晚晴拥有的一切。与顾言暗通款曲，是害死苏晚晴的直接凶手之一。坐上顾太太位置后发现自己也只是顾言的棋子。",
        "tagline": "姐姐，你有的东西，我也一样要有。",
        "arc": "伪装善良→频频针对苏晴→怀疑苏晴身份→手段越来越狠毒→发现自己被顾言利用→绝望反水交出证据→最终精神崩溃",
        "relations": "苏晚晴（堂姐/嫉妒对象）、顾言（情人/利用者）、顾老爷子（巴结对象）",
        "motivation": "取代苏晚晴拥有一切（顾太太的位置、财富、顾言的关注）；证明自己不比苏晚晴差；掩盖自己私生女的出身自卑",
        "description": "伪装柔弱的白莲花，嫉妒心扭曲，最终害人害己。"
    },
    {
        "id": "c5", "name": "顾念念", "gender": "男", "age": 3,
        "role": "萌宝·关键配角", "tags": ["天才萌宝", "神助攻", "母子情深"],
        "appearance": {
            "gender": "男", "age": 3, "height": 98,
            "faceShape": "圆脸", "eyeShape": "圆眼", "noseShape": "小巧翘鼻",
            "lipShape": "饱满唇", "skinTone": "冷白皮", "bodyShape": "娇小玲珑",
            "mark": ["左脸颊一个小梨涡", "笑起来眼睛弯弯像月牙"]
        },
        "personality": "人小鬼大、聪明机灵，比同龄人早熟。表面软萌可爱，实则观察力惊人，多次童言无忌点破大人的伪装。非常黏妈妈，对陆沉渊天然亲近，对顾言有莫名的敌意。",
        "background": "苏晚晴和顾言的儿子，苏晚晴被害时他才刚出生不久，被福伯偷偷藏起来抚养。重生后苏晚晴第一时间接回他，他是苏晚晴最大的软肋和最坚强的理由。",
        "tagline": "妈妈不哭，念念保护你！",
        "arc": "始终是妈妈的贴心小棉袄→从怕生到逐渐接纳陆沉渊→幼儿园亲子活动上无意识触发关键剧情→结局大喊要陆叔叔当爸爸",
        "relations": "苏晚晴（妈妈）、陆沉渊（陆叔叔→后爸）、顾言（亲生父亲/不知情）、福伯（福爷爷）",
        "motivation": "保护妈妈不被坏人欺负；吃好吃的；和陆叔叔一起玩",
        "description": "天才萌宝，女主复仇路上的最强助攻和最暖小太阳。"
    },
    {
        "id": "c6", "name": "福伯", "gender": "男", "age": 65,
        "role": "关键配角·忠仆", "tags": ["忠心耿耿", "老管家", "隐藏高手"],
        "appearance": {
            "gender": "男", "age": 65, "height": 172,
            "faceShape": "长脸", "eyeShape": "狭长眼", "noseShape": "高挺直鼻",
            "lipShape": "薄唇", "skinTone": "小麦色", "bodyShape": "骨感挺拔",
            "mark": ["满头银发一丝不苟", "常年手持一把黑色长柄雨伞"]
        },
        "personality": "沉稳内敛、忠心不二，话不多但每句都关键。身手矫健（退伍军人出身），做事滴水不漏，把苏晚晴当亲孙女看待。",
        "background": "苏家三十多年的老管家，年轻时是侦察兵退伍，被苏晚晴父亲收留后忠心耿耿。苏晚晴母亲去世前将女儿托付给他，五年前他冒着风险偷偷救下顾念念并秘密抚养，是女主重生后唯一知晓全部秘密的人。",
        "tagline": "大小姐，老奴在。",
        "arc": "始终是女主最可靠的后方支持→多次冒险传递情报→在苏梦瑶DNA调查中偷换样本→最终看着苏晚晴重建苏氏，安心退休",
        "relations": "苏晚晴（主仆/祖孙）、顾念念（照顾对象）、陆沉渊（从警惕到信任的盟友）",
        "motivation": "守护苏晚晴母子安全；报答苏家两代人的恩情；兑现对苏母的承诺",
        "description": "忠心耿耿的老管家，苏晚晴最坚实的后盾。"
    }
]


_APPEARANCE_REASON_LABELS = {
    "height": "身高", "faceShape": "脸型", "eyeShape": "眼型",
    "noseShape": "鼻型", "lipShape": "唇型", "skinTone": "肤色",
    "bodyShape": "体型", "mark": "标志特征",
}


def _attach_appearance_reasons(characters):
    for c in characters:
        app = c.get("appearance")
        if not isinstance(app, dict):
            continue
        reasons = {}
        for key, label in _APPEARANCE_REASON_LABELS.items():
            val = app.get(key)
            if key == "mark":
                val_txt = "、".join(val) if isinstance(val, list) and val else "无明显标志"
            else:
                val_txt = str(val) if val not in (None, "") else "待定"
            reasons[key] = f"{label}「{val_txt}」契合该角色身份与气质，能强化其视觉记忆点，便于工业化分镜统一还原。"
        app["reasons"] = reasons
    return characters


def _b(dur, loc, visual, character, action, dialog, dialog_tag, emotion):
    return {
        "duration": dur, "location": loc, "visual": visual,
        "character": character, "action": action, "dialog": dialog,
        "dialogTag": dialog_tag, "emotion": emotion,
    }


def _c(shot_type, cam_move, behaviors, cut_reason):
    return {"shotType": shot_type, "camMove": cam_move, "behaviors": behaviors, "cutReason": cut_reason}


def _sb(title, cameras):
    return {"title": title, "cameras": cameras}


def _make_episode(ep_num: int, ep_title: str, ep_hook: str, ep_summary: str) -> dict:
    sb_sec = 8
    sbs = []
    if ep_num == 1:
        sbs = [
            _sb("分镜1 · 冰冷海水·重生惊醒", [
                _c("大特写", "手持晃动", [
                    _b(3, "深海 夜", "漆黑海水中，一只手猛然睁开五指，气泡翻涌", "", "", "", "", "窒息、恐惧"),
                    _b(5, "深海 夜", "苏晚晴猛地睁开双眼，瞳孔骤缩，嘴唇发紫，发丝在水中飘散", "苏晚晴", "剧烈挣扎", "", "", "惊恐、不敢置信"),
                ], "从海水大特写开场，第一视角窒息感建立重生悬念"),
                _c("近景", "快速甩镜", [
                    _b(4, "海边礁石 夜", "苏晚晴从海水中爬上岸，剧烈咳嗽，双手撑着沙石", "苏晚晴", "匍匐爬行、咳嗽", "", "", "劫后余生"),
                    _b(4, "海边礁石 夜", "她颤抖着举起右手，看到手腕上母亲留下的旧银镯还在，月光下泛着冷光", "苏晚晴", "颤抖着抚摸银镯", "", "", "震惊、颤抖"),
                ], "切到岸边近景，确认重生事实"),
            ]),
            _sb("分镜2 · 确认时间·血仇立誓", [
                _c("中景", "推镜", [
                    _b(6, "海边礁石 夜", "苏晚晴摸出湿透的手机，颤抖着按亮屏幕——显示2024年3月15日，距离她坠海还有三天", "苏晚晴", "看手机", "", "", "震惊→狂喜→冰冷"),
                ], "手机屏幕特写确认重生时间点"),
                _c("特写推进", "慢推", [
                    _b(4, "海边礁石 夜", "苏晚晴的脸从不敢置信到表情逐渐冰冷，眼中含泪却没有落下", "苏晚晴", "缓缓站起", "", "", "从脆弱到坚定"),
                    _b(4, "海边礁石 夜", "她转头望向远处海城灯火璀璨的方向，顾氏大厦的顶端灯在夜色中格外刺眼", "苏晚晴", "攥紧拳头、指甲掐入掌心",
                       "[OS心声]顾言、苏梦瑶，这一世，我要让你们付出血的代价！", "os", "恨意滔天"),
                ], "表情变化建立复仇动机"),
            ]),
            _sb("分镜3 · 紧急联系·福伯救子", [
                _c("中景", "摇镜", [
                    _b(5, "海边公路 夜", "苏晚晴赤脚跑到公路上拦车，浑身湿透在夜风中发抖", "苏晚晴", "拦车、颤抖", "", "", "紧迫"),
                    _b(3, "出租车内 夜", "她颤抖着拨打福伯的电话，电话响了很久才接通", "苏晚晴", "打电话", "", "", "紧张"),
                ], "紧张节奏推进，联系忠仆"),
                _c("近景", "固定机位", [
                    _b(8, "出租车内 夜", "电话接通，福伯苍老的声音传来，苏晚晴泣不成声",
                       "苏晚晴", "握着电话落泪",
                       "福伯！念念……念念还在吗？带我去见他，马上！", "lip", "急切、哽咽"),
                    _b(4, "出租车内 夜", "电话那头沉默了三秒，福伯颤抖的声音传来：大小姐……你……你还活着？", "", "",
                       "[画外音]大小姐……你还活着？", "voicover", "震惊、老泪纵横"),
                ], "母子情深的第一个泪点"),
            ]),
            _sb("分镜4 · 母子相认·立下誓言", [
                _c("全景", "慢推", [
                    _b(4, "福伯乡下老宅 深夜", "灯光昏黄的小屋，福伯抱着熟睡的小念念在门口等候，看到苏晚晴冲下车，老泪纵横", "福伯、顾念念", "站立等候", "", "", "感人"),
                ], "交代母子见面的场景"),
                _c("近景", "固定机位", [
                    _b(6, "福伯乡下老宅 深夜", "苏晚晴冲进屋，看到床上熟睡的念念，3岁的孩子蜷缩着抱着一只旧小熊", "苏晚晴、顾念念", "快步走近、蹲下", "", "", "激动、克制"),
                    _b(4, "福伯乡下老宅 深夜", "小念念迷迷糊糊睁开眼，看到苏晚晴，愣了一秒，小嘴一瘪", "顾念念", "揉眼睛", "", "", "懵懂"),
                    _b(5, "福伯乡下老宅 深夜", "念念伸出小胳膊搂住苏晚晴的脖子，奶声奶气地叫", "苏晚晴、顾念念", "拥抱",
                       "妈妈……念念梦到妈妈了……", "lip", "母子连心"),
                    _b(3, "福伯乡下老宅 深夜", "苏晚晴紧紧抱着儿子，眼泪无声滑落，但眼神逐渐变得坚定", "苏晚晴", "抱着念念、泪流满面", "", "", "温柔坚定"),
                ], "母子相认的核心情感戏"),
            ]),
            _sb("分镜5 · 复仇序幕·望向灯火", [
                _c("大远景", "航拍·慢推", [
                    _b(5, "福伯乡下老宅外 深夜", "苏晚晴抱着熟睡的念念站在屋前，身后是福伯弯腰等候。远处海城方向，顾氏大厦顶端的灯光刺穿夜幕", "苏晚晴、顾念念、福伯", "站立、远眺", "", "", "史诗感"),
                    _b(3, "福伯乡下老宅外 深夜", "苏晚晴低头看了一眼怀中的念念，在他额头轻轻一吻", "苏晚晴", "亲吻念念额头", "", "", "温柔"),
                ], "航拍远景拉开，建立全剧格局"),
                _c("特写", "固定机位", [
                    _b(4, "福伯乡下老宅外 深夜", "苏晚晴抬起头，目光冰冷地望向顾氏大厦的方向", "苏晚晴", "抬头、目光如刀",
                       "[旁白]三天后，顾氏集团将迎来一个新员工。她的名字，叫苏晴。", "narrator", "悬念、期待"),
                ], "结尾钩子，引导下一集"),
            ]),
        ]
    elif ep_num == 2:
        sbs = [
            _sb("分镜1 · 晨曦誓师·制定计划", [
                _c("全景", "慢推", [
                    _b(5, "福伯乡下老宅 清晨", "晨光透过窗帘，苏晚晴一夜未眠，桌上摊开着她凭记忆写下的顾氏集团人事结构图和关键时间节点", "苏晚晴", "伏案写字", "", "", "冷静、规划"),
                ], "晨光中制定复仇计划，展现女主的谋略"),
                _c("近景", "推镜", [
                    _b(3, "福伯乡下老宅 清晨", "福伯端着粥进来，看到满桌的笔记，面露担忧", "福伯", "端粥进门", "", "", "担忧"),
                    _b(5, "福伯乡下老宅 清晨", "苏晚晴抬头，目光坚定", "苏晚晴", "抬头、握笔",
                       "福伯，我要在三天内以新身份进入顾氏。帮我准备一套身份——「苏晴」，海外归来的市场策划。", "lip", "果决"),
                ], "定下潜入计划"),
            ]),
            _sb("分镜2 · 萌宝助攻·母子约定", [
                _c("中景", "固定机位", [
                    _b(4, "福伯乡下老宅 日", "念念揉着眼睛从房间走出来，看到满桌的纸，好奇地爬上椅子", "顾念念", "揉眼、爬椅子", "", "", "萌"),
                    _b(4, "福伯乡下老宅 日", "苏晚晴赶紧把写满字的纸翻过去，抱起念念", "苏晚晴、顾念念", "抱起念念", "", "", "温柔"),
                    _b(6, "福伯乡下老宅 日", "念念小手捧着苏晚晴的脸，认真地说", "顾念念", "捧着妈妈的脸",
                       "妈妈，念念乖乖的，不闹。妈妈去打坏人对不对？念念等妈妈回来。", "lip", "人小鬼大"),
                ], "萌宝展现超常懂事，催泪"),
                _c("特写", "慢推", [
                    _b(3, "福伯乡下老宅 日", "苏晚晴眼眶泛红，紧紧抱住念念", "苏晚晴、顾念念", "紧紧拥抱", "", "", "感动"),
                    _b(3, "福伯乡下老宅 日", "福伯在一旁默默擦拭眼角", "福伯", "擦眼泪", "", "", "动容"),
                ], "情感落点"),
            ]),
            _sb("分镜3 · 变身准备·褪去旧我", [
                _c("中景", "蒙太奇", [
                    _b(3, "商场 日", "苏晚晴（戴墨镜）在商场挑选职业装，与前世温婉风格截然不同，选择了冷色系干练套装", "苏晚晴", "挑选衣服", "", "", "蜕变"),
                    _b(3, "理发店 日", "长发剪至锁骨，染成深栗色，造型师惊叹她的气质变化", "苏晚晴", "剪发", "", "", "决绝"),
                    _b(2, "眼镜店 日", "戴上一副金丝平光镜，整个人气质从温婉变为精英干练", "苏晚晴", "戴眼镜", "", "", "新身份"),
                ], "蒙太奇快速展现女主形象转变"),
            ]),
            _sb("分镜4 · 顾氏大厦·暗流涌动", [
                _c("大远景", "航拍", [
                    _b(3, "顾氏集团总部 日", "航拍88层顾氏大厦，玻璃幕墙反射阳光，气派非凡", "", "", "", "", "压迫感"),
                ], "交代权力中心"),
                _c("中景", "移镜", [
                    _b(5, "顾氏集团·总裁办公室 日", "顾言坐在大班椅上批阅文件，苏梦瑶穿着名牌套装端着咖啡走进来，亲昵地搭在他肩上", "顾言、苏梦瑶", "办公、亲密", "", "", "虚伪"),
                    _b(4, "顾氏集团·总裁办公室 日", "苏梦瑶娇声说市场部今天有个面试新人，听人事说气质很特别", "苏梦瑶", "搭肩、娇声说话",
                           "阿言，今天市场部面试那个叫苏晴的，听说是海归呢，你要不要去看看？", "lip", "试探"),
                    _b(3, "顾氏集团·总裁办公室 日", "顾言头也不抬，冷淡地说不必，他只看结果", "顾言", "批阅文件",
                           "市场部的人，不必我亲自看。能出业绩就行。", "lip", "冷漠"),
                ], "对比展现仇人日常，为后续戏剧冲突埋伏笔"),
            ]),
            _sb("分镜5 · 面试惊艳·新身份登场", [
                _c("中景", "推镜", [
                    _b(4, "顾氏集团·会议室 日", "苏晚晴一身深色西装套裙走进面试会议室，气场全开，面试官们微微坐直", "苏晚晴", "推门、走进", "", "", "惊艳、自信"),
                ], "新身份首次亮相"),
                _c("近景", "过肩镜头", [
                    _b(5, "顾氏集团·会议室 日", "苏晚晴从容坐下，面对市场总监的提问对答如流，精准分析顾氏当前的品牌策略问题", "苏晚晴", "从容答辩",
                       "顾氏目前在年轻用户群体中的品牌渗透率不足12%，核心原因是传播策略过于保守……", "lip", "专业、自信"),
                    _b(3, "顾氏集团·会议室 日", "面试官们互相交换震惊的眼神，市场总监当场拍板录用", "", "", "", "", "震惊、认可"),
                ], "展现女主的能力，为职场线铺垫"),
                _c("大远景", "拉镜", [
                    _b(3, "顾氏集团·大堂 日", "苏晚晴走出电梯，抬头看了一眼大厅里「顾氏集团」四个烫金大字，嘴角微微上扬", "苏晚晴", "抬头、微笑", "", "", "冷静、期待"),
                    _b(3, "顾氏集团·大堂 日", "她转身走出玻璃大门，阳光落在她身上，画面定格", "", "",
                       "[旁白]苏晚晴已经死了。从今天起，我是苏晴。", "narrator", "爽感钩子"),
                ], "结尾点题，新身份正式登场"),
            ]),
        ]
    else:
        titles = {
            3: ("初入顾氏·电梯擦肩", "苏晚晴化名苏晴第一天上班，在电梯里与顾言面对面相遇，但顾言完全没有认出气场大变的她。"),
            4: ("宴会风云·初露锋芒", "顾氏商业酒会上，苏晚晴巧妙提醒合作方识破合同陷阱，引起全场关注，苏梦瑶开始注意她。"),
            5: ("律师登场·暗流涌动", "顾言因合同纠纷被告，对方代理律师陆沉渊在法庭上犀利碾压。苏晚晴与陆沉渊法院走廊第一次对视。"),
        }
        t, h = titles.get(ep_num, (f"第{ep_num}集", "剧情推进中"))
        sbs = [
            _sb(f"分镜1 · {t}·开场", [
                _c("大远景", "航拍·慢推", [
                    _b(5, "海城城市 日", "航拍海城天际线，阳光洒在顾氏大厦玻璃幕墙上", "", "", "", "", "都市感"),
                ], "航拍城市开场"),
                _c("中景", "移镜", [
                    _b(3, f"第{ep_num}集场景", f"{h}", "苏晚晴", "出场", "", "", "推进剧情"),
                ], "快速交代本集核心"),
            ]),
            _sb("分镜2 · 对手戏·暗潮汹涌", [
                _c("中景", "正反打", [
                    _b(5, "室内场景 日", "关键对手戏场景，人物之间言语交锋，暗流涌动", "苏晚晴/顾言/陆沉渊", "对话交锋",
                       "（对话内容根据具体情境展开）", "lip", "紧张"),
                ], "核心戏剧冲突"),
            ]),
            _sb("分镜3 · 情感线·微妙变化", [
                _c("近景", "固定机位", [
                    _b(4, "室内/外场景", "情感互动场景，人物之间的关系发生微妙变化", "苏晚晴、陆沉渊", "互动", "", "", "温情/紧张"),
                ], "情感推进"),
            ]),
            _sb("分镜4 · 危机或爽点", [
                _c("中景", "快速剪辑", [
                    _b(4, "关键场景", "本集的小高潮，危机化解或爽点释放", "主要角色", "关键行动", "", "", "爽感/紧张"),
                ], "本集高潮点"),
            ]),
            _sb("分镜5 · 钩子结尾·悬念", [
                _c("特写", "慢推", [
                    _b(3, "关键场景 傍晚/夜", "本集结尾留下悬念钩子，镜头定格在人物意味深长的表情上", "关键人物", "意味深长的表情",
                       f"[旁白]{h}……但更大的风暴还在后面。", "narrator", "悬念"),
                ], "结尾钩子引导下集"),
            ]),
        ]

    total_beh = sum(
        len(cam["behaviors"])
        for sb in sbs for cam in sb["cameras"]
    )
    total_cam = sum(len(sb["cameras"]) for sb in sbs)
    total_dur = sum(
        b["duration"]
        for sb in sbs for cam in sb["cameras"] for b in cam["behaviors"]
    )

    return {
        "id": ep_num,
        "title": ep_title,
        "duration": total_dur,
        "sbSec": sb_sec,
        "sbCount": len(sbs),
        "camCount": total_cam,
        "behCount": total_beh,
        "storyboards": sbs,
    }


MOCK_REVIEW_ISSUES = [
    {"severity": 2, "type": "节奏", "text": "第2分镜到第3分镜之间转场略显仓促，建议增加一个空镜缓冲情绪。"},
    {"severity": 1, "type": "逻辑", "text": "女主在重生后立即联系福伯的设定合理，但建议补充她如何确认福伯没有被监控的细节。"},
    {"severity": 3, "type": "合规", "text": "部分复仇手段涉及商业窃取，建议调整为通过合法渠道获取信息，避免引导不当价值观。"},
]


class MockProvider:
    name = "mock"
    model_name = "mock-v1"

    _LEGACY_METHODS = {
        "generate_outline": "generate_outline",
        "review_outline": "review_outline",
        "modify_outline_module": "modify_module",
        "batch_modify_outline": "batch_modify",
        "generate_characters": "generate_characters",
        "review_characters": "review_characters",
        "generate_episode": "generate_episode",
        "review_episode": "review_episode",
        "fix_episode": "fix_episode",
        "rewrite_segment": "rewrite_segment",
        "parse_import": "parse_import",
    }

    async def run_skill(
        self,
        task_key: str,
        params: dict,
        skill_meta: dict,
        system_prompt: str,
        user_prompt_template: str,
    ) -> AsyncGenerator[str, None]:
        method_name = self._LEGACY_METHODS.get(task_key)
        if not method_name:
            yield sse_error(f"mock provider 未支持 task_key: {task_key}")
            return
        method = getattr(self, method_name, None)
        if method is None:
            yield sse_error(f"mock provider 缺少方法: {method_name}")
            return
        async for chunk in method(params):
            yield chunk

    async def generate_outline(self, req: dict) -> AsyncGenerator[str, None]:
        yield sse_event("phase", {"phase": "analyzing", "message": "正在分析创作参数..."})
        import asyncio
        await asyncio.sleep(0.3)
        yield sse_event("phase", {"phase": "generating", "message": "正在生成大纲模块..."})
        await asyncio.sleep(0.3)

        outline = copy.deepcopy(MOCK_OUTLINE)
        episodes_count = req.get("episodes", 20)
        if episodes_count != 20:
            for m in outline:
                if m.get("episodes"):
                    sample = m["episodes"][0] if m["episodes"] else None
                    m["episodes"] = [sample] if sample else []

        yield sse_event("result", {"outline": outline})
        yield sse_done({"outline": outline})

    async def review_outline(self, req: dict) -> AsyncGenerator[str, None]:
        import asyncio
        yield sse_event("phase", {"phase": "reviewing", "message": "正在审核大纲..."})
        await asyncio.sleep(0.5)
        outline = req.get("outline", [])
        issues = []
        for i, mod in enumerate(outline):
            if mod.get("type") == "section" and not mod.get("episodes") and i < len(outline) - 2:
                if random.random() > 0.5:
                    issues.append({
                        "moduleId": mod["id"],
                        "severity": random.choice([1, 2]),
                        "type": random.choice(["节奏", "逻辑", "伏笔"]),
                        "text": f"模块「{mod['title']}」内容可以进一步充实，建议增加更多细节描写。",
                    })
        score = random.randint(78, 92)
        yield sse_event("result", {"issues": issues, "score": score})
        yield sse_done({"issues": issues, "score": score})

    async def modify_module(self, req: dict) -> AsyncGenerator[str, None]:
        import asyncio
        yield sse_event("phase", {"phase": "modifying", "message": "正在修改模块..."})
        await asyncio.sleep(0.4)
        module = copy.deepcopy(req.get("module", {}))
        note = req.get("note", "")
        if note and module.get("content"):
            module["content"] += f"\n\n【AI修改补充】{note}相关内容已根据您的要求进行了优化调整，增强了细节描写和情绪张力。"
        module["aiScore"] = min(98, module.get("aiScore", 80) + random.randint(3, 8))
        module["issues"] = []
        yield sse_event("result", {"module": module})
        yield sse_done({"module": module})

    async def batch_modify(self, req: dict) -> AsyncGenerator[str, None]:
        import asyncio
        modules = req.get("modules", [])
        total = len(modules)
        modified = []
        for i, m_item in enumerate(modules):
            yield sse_event("progress", {"current": i + 1, "total": total, "moduleId": m_item.get("moduleId") or m_item.get("id")})
            await asyncio.sleep(0.2)
            mod = m_item.get("module", {}) if isinstance(m_item, dict) else {}
            note = m_item.get("note", "") if isinstance(m_item, dict) else ""
            if not mod and isinstance(m_item, dict) and "id" in m_item:
                mod = copy.deepcopy(m_item)
            if note and mod.get("content"):
                mod["content"] += f"\n\n【批量修改】已根据「{note}」的要求优化。"
            mod["aiScore"] = min(98, mod.get("aiScore", 80) + random.randint(2, 6))
            mod["issues"] = []
            modified.append(mod)
        result = {"modules": modified, "summary": f"已完成 {total} 个模块的批量修改。"}
        yield sse_event("result", result)
        yield sse_done({**result, "modified": total})

    async def review_characters(self, req: dict) -> AsyncGenerator[str, None]:
        import asyncio
        yield sse_event("phase", {"phase": "reviewing", "message": "正在审核人物小传..."})
        await asyncio.sleep(0.5)
        characters = req.get("characters", [])
        issues = []
        for ch in characters:
            if ch.get("role") == "主角" and len(ch.get("background", "")) < 50:
                issues.append({
                    "characterId": ch.get("id"),
                    "type": "背景",
                    "text": f"{ch.get('name')}的背景故事可以更充实，建议补充关键成长经历。",
                })
            if not ch.get("arc"):
                issues.append({
                    "characterId": ch.get("id"),
                    "type": "人物弧光",
                    "text": f"{ch.get('name')}缺少明确的成长弧线，建议补充。",
                })
        yield sse_event("result", {"issues": issues})
        yield sse_done({"issues": issues})

    async def generate_characters(self, req: dict) -> AsyncGenerator[str, None]:
        import asyncio
        yield sse_event("phase", {"phase": "generating", "message": "正在生成人物小传..."})
        await asyncio.sleep(0.5)
        existing = req.get("existing_characters", []) or []
        existing_ids = {c.get("id") for c in existing}
        all_chars = copy.deepcopy(MOCK_CHARACTERS)
        new_chars = [c for c in all_chars if c["id"] not in existing_ids]
        if not new_chars:
            new_chars = copy.deepcopy(MOCK_CHARACTERS[2:4])
            for i, c in enumerate(new_chars):
                c["id"] = f"c{len(existing) + i + 1}"
        new_chars = _attach_appearance_reasons(new_chars)
        yield sse_event("result", {"characters": new_chars})
        yield sse_done({"characters": new_chars})

    async def generate_episode(self, req: dict) -> AsyncGenerator[str, None]:
        import asyncio
        ep_idx = req.get("episode_index", 1)
        yield sse_event("phase", {"phase": "planning", "message": f"正在规划第{ep_idx}集分镜结构..."})
        await asyncio.sleep(0.4)
        yield sse_event("phase", {"phase": "writing", "message": f"正在撰写第{ep_idx}集分镜脚本..."})
        await asyncio.sleep(0.4)

        ep_data = _get_episode_data(ep_idx, req.get("outline", []))
        yield sse_event("result", {"episode": ep_data})
        yield sse_done({"episode": ep_data})

    async def review_episode(self, req: dict) -> AsyncGenerator[str, None]:
        import asyncio
        ep_idx = req.get("episode_index", 1)
        yield sse_event("phase", {"phase": "reviewing", "message": f"正在审核第{ep_idx}集..."})
        await asyncio.sleep(0.5)
        issues = copy.deepcopy(MOCK_REVIEW_ISSUES)
        for i, issue in enumerate(issues):
            sb_idx = random.randint(0, 3)
            issue["target"] = {"si": sb_idx, "ci": random.randint(0, 1)}
            issue["id"] = f"i{ep_idx}_{i}"
            issue["priority"] = random.choice(["T0", "T1", "T2"])
            issue["status"] = "pending"
        score = random.randint(75, 90)
        yield sse_event("result", {"issues": issues, "score": score})
        yield sse_done({"issues": issues, "score": score})

    async def fix_episode(self, req: dict) -> AsyncGenerator[str, None]:
        import asyncio
        ep_idx = req.get("episode_index", 1)
        issues = req.get("issues", [])
        yield sse_event("phase", {"phase": "fixing", "message": f"正在修复第{ep_idx}集的{len(issues)}个问题..."})
        await asyncio.sleep(0.5)
        ep_data = _get_episode_data(ep_idx, req.get("outline", []))
        for issue in issues:
            target = issue.get("target", {})
            si = target.get("si", 0)
            ci = target.get("ci", 0)
            if si < len(ep_data["storyboards"]) and ci < len(ep_data["storyboards"][si]["cameras"]):
                cam = ep_data["storyboards"][si]["cameras"][ci]
                for b in cam["behaviors"]:
                    if b.get("visual"):
                        b["visual"] += "（已根据审核意见优化节奏与情绪铺垫）"
                        break
        resolved_ids = [it.get("id") for it in issues if it.get("id")]
        yield sse_event("result", {"episode": ep_data, "resolved_issue_ids": resolved_ids})
        yield sse_done({"episode": ep_data, "resolved_issue_ids": resolved_ids})

    async def rewrite_segment(self, req: dict) -> AsyncGenerator[str, None]:
        import asyncio
        instruction = req.get("instruction", "")
        candidates_count = req.get("candidates", 2)
        yield sse_event("phase", {"phase": "rewriting", "message": f"正在根据指令「{instruction}」重写..."})
        await asyncio.sleep(0.4)
        behavior = req.get("behavior", {})
        candidates = []
        for i in range(candidates_count):
            b = copy.deepcopy(behavior)
            if b.get("dialog"):
                b["dialog"] = f"【方案{i+1}】（按「{instruction}」优化）{b['dialog']}"
            if b.get("visual"):
                b["visual"] = f"【方案{i+1}】（按「{instruction}」优化画面）{b['visual']}"
            candidates.append(b)
        yield sse_event("result", {"candidates": candidates})
        yield sse_done({"candidates": candidates})

    async def parse_import(self, req: dict) -> AsyncGenerator[str, None]:
        import asyncio
        file_name = req.get("file_name", "")
        yield sse_event("phase", {"phase": "parsing", "message": f"正在解析文件 {file_name}..."})
        await asyncio.sleep(0.6)
        outline = copy.deepcopy(MOCK_OUTLINE)
        characters = copy.deepcopy(MOCK_CHARACTERS[:4])
        characters = _attach_appearance_reasons(characters)
        yield sse_event("result", {"outline": outline, "characters": characters, "warnings": ["已自动推断20集结构，建议人工审核分集边界。"]})
        yield sse_done({"outline": outline, "characters": characters})


def _get_episode_data(ep_idx: int, outline: list) -> dict:
    ep_titles = {
        1: ("重生归来·血仇立誓", "破旧庄子醒来，立誓护子报仇"),
        2: ("萌宝相认·母子连心", "福伯秘密带念念来见，母子相认"),
        3: ("化名入职·步步为营", "苏晴入职顾氏，电梯里与顾言擦肩"),
        4: ("宴会风云·初露锋芒", "酒会上识破合同陷阱，惊艳全场"),
        5: ("律师登场·暗流涌动", "陆沉渊法庭碾压，走廊第一次对视"),
        6: ("秘密同盟·利益交换", "陆沉渊出示遗嘱，两人结盟"),
        7: ("南城地块·前世情报", "苏晴凭前世记忆提出精准方案"),
        8: ("白莲疑心·试探身份", "苏梦瑶百般试探苏晴"),
        9: ("商战胜局·一鸣惊人", "南城竞标完胜，顾言邀舞"),
        10: ("幼儿园惊魂·父子擦肩", "亲子日顾言出席，陆沉渊解围"),
        11: ("顾言追求·危险靠近", "顾言开始追求苏晴"),
        12: ("雨夜告白·沉渊吃醋", "陆沉渊雨夜等她一整夜"),
        13: ("梦瑶设局·身份险露", "DNA样本被福伯偷换"),
        14: ("车祸相救·沉渊受伤", "陆沉渊为救苏晚晴重伤"),
        15: ("母亲遗信·真相初现", "母亲遗信揭露更大阴谋"),
        16: ("公开身份·全场震动", "股东大会上苏晚晴现身"),
        17: ("法庭交锋·证据为王", "陆沉渊法庭出示关键证据链"),
        18: ("白莲反水·罪证曝光", "苏梦瑶交出录音和伪证证据"),
        19: ("顾氏崩塌·恶人落网", "顾言被捕，苏晚晴夺回苏氏"),
        20: ("涅槃重生·携手余生", "海边求婚，一家三口圆满"),
    }
    title, hook = ep_titles.get(ep_idx, (f"第{ep_idx}集", "剧情推进"))
    return _make_episode(ep_idx, title, hook, hook)


_provider_instance: Optional[MockProvider] = None


def get_provider() -> MockProvider:
    global _provider_instance
    if _provider_instance is None:
        _provider_instance = MockProvider()
    return _provider_instance
