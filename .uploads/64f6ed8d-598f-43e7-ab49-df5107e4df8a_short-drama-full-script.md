---
name: short-drama-full-script
description: 给定故事文本，直接重构为抖音竖屏短剧分镜剧本（JSON格式，SB/C/B三级嵌套结构），可直接走API入库和前端渲染。
tags: [短剧, 剧本, 重构, 分镜, 抖音, JSON]
version: 2.0.0
---

# 短剧剧本重构

## 概述

将用户提供的原始故事直接重构为抖音竖屏短剧分镜剧本。输出完整的多集JSON分镜剧本，每集90秒，可直接走API入库和前端渲染。

## 适用题材

- 缅北/诈骗/犯罪
- 都市复仇/豪门/霸总
- 重生/穿越
- 古装权谋
- 恐怖/惊悚/密室
- 悬疑/推理
- 逆袭/爽文/打脸

## 工作流程

### 第一步：提取核心要素

从原始故事中提取：
1. 核心冲突
2. 关键人物（最多5个）
3. 高潮节点（2-3个重大反转）
4. 结局方向

### 第二步：时间线重组

默认使用倒叙/插叙：
- 开篇用高潮/最抓人的场景切入
- 闪回交代前提
- 回到主时间线推进
- 结尾留钩子

如原始时间线更适合正叙则不强制倒叙。

### 第三步：分镜设计（SB/C/B三级结构）

- **SB**（Storyboard Block，分镜段落）：一个完整叙事段落，每集约5-7个SB
- **C**（Shot，镜头）：SB内的独立镜头，一个SB含1-2个C
- **B**（Beat，行为单元）：C内的最小行为单元，一个C含1-2个B

### 第四步：风控规避

| 风控项 | 处理方式 |
|--------|---------|
| 暴力 | 正常拍不回避，不飙血 |
| 枪支 | 不展示枪支画面，用画外枪声代替 |
| 性暗示 | 局部身体（锁骨汗、大腿淤青、吊带肩带滑落）+画外污言碎语暗示 |
| 血腥 | 只展示后果（沾血道具/淤青），不展示伤口特写 |
| 全裸 | 大腿以下局部+锁骨以上局部+画外音 |

### 第五步：结尾钩子

每集末尾必须有悬念。最后一个SB的最后一个C的最后一个B落点必须是钩子。

## 输出格式（JSON）

```json
{
  "episode": 1,
  "title": "豪门婚宴上的羞辱",
  "theme": "复仇",
  "duration": 90,
  "storyboard_blocks": [
    {
      "sb": "SB1",
      "scene": "正门",
      "location": "顾家酒店·正门",
      "summary": "航拍切入交代环境",
      "shots": [
        {
          "c": "C1",
          "shot_type": "大远景",
          "composition": "中心对称",
          "camera_movement": "固定",
          "cut_reason": "",
          "beats": [
            {
              "b": "B1",
              "type": "narrator",
              "dialogue_tag": "",
              "duration": 8,
              "location_detail": "顾家酒店·正门 夜外",
              "visual": "霓虹灯牌"顾氏集团"在雨夜中闪烁，豪车队伍缓缓驶入酒店大门",
              "characters": [],
              "action": "",
              "dialogue": "",
              "emotion": "压抑、盛大",
              "sound": "雨声、引擎低鸣"
            }
          ]
        }
      ]
    }
  ]
}
```

### 字段说明

| 层级 | 字段 | 类型 | 说明 |
|------|------|------|------|
| 集 | episode | int | 集号 |
| 集 | title | string | 本集标题 |
| 集 | theme | string | 核心主题标签 |
| 集 | duration | int | 总时长秒数 |
| 集 | storyboard_blocks | array | SB数组 |
| SB | sb | string | SB编号（SB1, SB2...） |
| SB | scene | string | 场景简称 |
| SB | location | string | 地点全称 |
| SB | summary | string | SB一句话概要 |
| SB | shots | array | 镜头数组 |
| C | c | string | 镜头编号（C1, C2...） |
| C | shot_type | string | 大远景/远景/全景/中景/近景/特写/大特写 |
| C | composition | string | 构图方式（中心对称/三分法/对角线/框架式/引导线） |
| C | camera_movement | string | 固定/推/拉/摇/移/跟/甩/升/降 |
| C | cut_reason | string | 切镜原因 |
| C | beats | array | 行为单元数组 |
| B | b | string | B编号（B1, B2...） |
| B | type | string | lip/narrator/voicover/os |
| B | dialogue_tag | string | 台词标签，无则空 |
| B | duration | int | 该行为秒数 |
| B | location_detail | string | 具体地点+日夜内外（如"正门 夜外"） |
| B | visual | string | 镜头画面描述 |
| B | characters | array | 画面中出现的人物名称数组 |
| B | action | string | 人物具体动作 |
| B | dialogue | string | 台词/旁白文字，无则空 |
| B | emotion | string | 情绪标签 |
| B | sound | string | 环境音+动作音，无则空 |

### type枚举说明

| 值 | 含义 | 使用场景 |
|----|------|---------|
| lip | 对口型台词 | 角色正面对镜头或对话对象说出的台词 |
| narrator | 旁白 | 第三方叙述/上帝视角解说 |
| voicover | 内心独白 | 角色内心OS，嘴唇不动观众能听到 |
| os | 画外音 | 画面外传来的人声 |

## 输出原则

- 直接输出完整JSON，不包裹在markdown代码块外
- 一行一个JSON对象，不要pretty print（节省token）
- 不返回中间推理、不返回修改标注、不返回问题清单
- 多集时输出JSON数组，每集一个对象