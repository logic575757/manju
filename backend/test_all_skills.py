import asyncio, json, time, sys
import httpx

BASE = "http://127.0.0.1:8000"


async def sse_collect(c, url, timeout=180.0):
    phases, deltas, result, error = [], 0, None, None
    async with c.stream("GET", url, timeout=timeout) as resp:
        if resp.status_code != 200:
            return None, None, None, f"HTTP {resp.status_code}"
        buf = ""
        async for chunk in resp.aiter_text():
            buf += chunk
            while "\n\n" in buf:
                ev_raw, buf = buf.split("\n\n", 1)
                ev_name, data = "", ""
                for ln in ev_raw.splitlines():
                    if ln.startswith("event:"):
                        ev_name = ln[6:].strip()
                    elif ln.startswith("data:"):
                        data += ln[5:].lstrip()
                if not ev_name:
                    continue
                try:
                    dj = json.loads(data) if data and data[0] in "{[" else data
                except Exception:
                    dj = data
                if ev_name == "delta":
                    deltas += 1
                elif ev_name == "phase":
                    p = dj.get("phase") if isinstance(dj, dict) else str(dj)
                    phases.append(p)
                elif ev_name == "result":
                    result = dj
                elif ev_name == "error":
                    error = dj
    return phases, deltas, result, error


async def submit(c, path, payload, label, timeout):
    t0 = time.time()
    r = await c.post(path, json=payload)
    tag = "✅" if r.status_code == 200 else "❌"
    print(f"\n{tag} [{label}] POST {path} -> {r.status_code}", flush=True)
    if r.status_code != 200:
        print(f"   ERROR: {r.text[:200]}")
        return None
    sj = r.json()
    tid = sj["task_id"]
    phases, deltas, result, err = await sse_collect(c, f"/api/ai/tasks/{tid}/stream", timeout=timeout)
    dt = time.time() - t0
    if err:
        print(f"   ❌ 流式失败 {dt:.1f}s phases={len(phases)} deltas={deltas} err={str(err)[:120]}")
        return None
    rk = list(result.keys()) if isinstance(result, dict) else type(result).__name__
    print(f"   ✅ {dt:.1f}s phases={len(phases)} deltas={deltas} result_keys={rk}")
    if isinstance(result, dict):
        for k, v in result.items():
            if isinstance(v, list):
                print(f"      - {k}: list[{len(v)}]")
            elif isinstance(v, dict):
                print(f"      - {k}: dict keys={list(v.keys())[:6]}")
            else:
                print(f"      - {k}: {type(v).__name__} {str(v)[:50]!r}")
    return result


async def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    async with httpx.AsyncClient(base_url=BASE, timeout=120.0) as c:
        r = await c.post("/api/auth/login", json={"username": "demo", "password": "demo123456"})
        if r.status_code != 200:
            r = await c.post("/api/auth/register", json={
                "username": "demo", "password": "demo123456",
                "email": "demo@test.com", "display_name": "Demo",
            })
        c.headers["Authorization"] = f"Bearer {r.json()['access_token']}"

        scripts = await c.get("/api/scripts")
        sd = scripts.json()
        if isinstance(sd, list) and sd:
            sid = sd[0]["id"]
        elif isinstance(sd, dict) and sd.get("items"):
            sid = sd["items"][0]["id"]
        else:
            cr = await c.post("/api/scripts", json={"title": "Skill 全量联调剧", "path_type": "ai", "config": {}})
            sid = cr.json()["id"]
        print(f"script_id={sid}")

        MOCK_OUTLINE = [
            {"id": "m0", "type": "overview", "title": "霸总甜宠总览", "summary": "假千金鸠占鹊巢，真千金归来复仇", "content": "霸总顾晏辰与真假千金的爱恨", "issues": []},
            {"id": "m1", "type": "section", "title": "世界观", "summary": "现代都市海城", "content": "顶级豪门顾家掌权", "issues": []},
            {"id": "m2", "type": "section", "title": "女主苏晚", "summary": "真千金，隐忍归来", "content": "苏氏集团真千金，5岁被抱错", "issues": []},
        ]
        MOCK_CHARS = [
            {"id": "c1", "name": "顾晏辰", "role": "男主", "background": "顾氏集团总裁", "arc": "冷漠→深情"},
            {"id": "c2", "name": "苏晚", "role": "女主", "background": "真千金", "arc": "隐忍→反击"},
        ]
        MOCK_EP = {
            "index": 1, "title": "第1集 意外相遇",
            "storyboards": [
                {"id": "s1", "index": 1, "summary": "苏晚面试被拒",
                 "cameras": [{"id": "cam1", "shot": "中景", "angle": "平视",
                              "behaviors": [{"id": "b1", "actor": "苏晚", "action": "站在公司门口", "dialog": "我一定会进来的。", "duration": 3}]}]}]
        }
        MOCK_BEHAVIOR = {"id": "b1", "actor": "苏晚", "action": "站在公司门口", "dialog": "我一定会进来的。", "duration": 3}

        cases = [
            # 轻量输出 skills (优先跑)
            ("review_outline", "/api/ai/outline/review",
             {"script_id": sid, "outline": MOCK_OUTLINE}, 180),
            ("review_characters", "/api/ai/characters/review",
             {"script_id": sid, "characters": MOCK_CHARS, "outline": MOCK_OUTLINE}, 180),
            ("rewrite_segment", "/api/ai/episode/rewrite-segment",
             {"script_id": sid, "episode_index": 1, "behavior": MOCK_BEHAVIOR,
              "instruction": "改成更有冲突感、台词更霸气", "candidates": 2}, 150),
            ("review_episode", "/api/ai/episode/review",
             {"script_id": sid, "episode_index": 1, "episode": MOCK_EP,
              "outline": MOCK_OUTLINE, "characters": MOCK_CHARS}, 180),
            ("fix_episode", "/api/ai/episode/fix",
             {"script_id": sid, "episode_index": 1, "episode": MOCK_EP,
              "issues": [{"severity": "T1", "type": "节奏", "text": "开场钩子不够强"}]}, 240),
            ("modify_module", "/api/ai/outline/modify-module",
             {"script_id": sid, "module_id": "m2", "module": MOCK_OUTLINE[2],
              "note": "加强女主反击的爽感"}, 180),
            ("parse_import", "/api/ai/import/parse",
             {"text": "苏晚是被抱错的真千金，五年后归来发现身份被假千金苏梦瑶顶替，霸总顾晏辰一开始认错人，最终被真千金吸引。",
              "file_name": "story.txt", "episodes": 6, "ep_duration": 90}, 300),
            ("batch_modify", "/api/ai/outline/batch-modify",
             {"script_id": sid, "modules": [
                 {"id": "m1", "module": MOCK_OUTLINE[1], "note": "强化豪门压迫感"},
                 {"id": "m2", "module": MOCK_OUTLINE[2], "note": "加强女主反击"},
             ]}, 300),
            ("generate_characters", "/api/ai/characters/generate",
             {"script_id": sid, "outline": MOCK_OUTLINE,
              "existing_characters": MOCK_CHARS}, 240),
            # 重输出 skills
            ("generate_outline", "/api/ai/outline/generate",
             {"script_id": sid, "style": "霸总甜宠", "episodes": 6, "pregen": 2,
              "ep_duration": 90, "shot_sec": 8,
              "prompt": "真假千金反转，霸总认错人，20集以内"}, 360),
            ("generate_episode", "/api/ai/episode/generate",
             {"script_id": sid, "episode_index": 1, "outline": MOCK_OUTLINE,
              "characters": MOCK_CHARS, "episode_hook": "苏晚面试被顾晏辰认出",
              "ep_duration": 90, "sb_sec": 8}, 360),
        ]

        results = {}
        for label, path, payload, tmo in cases:
            if only and only not in label:
                continue
            results[label] = await submit(c, path, payload, label, tmo)

        # generic route 最后用已验证过的轻量请求再验一次
        if not only or "generic" in only:
            await submit(c, "/api/ai/skills/submit/review_outline",
                         {"script_id": sid, "outline": MOCK_OUTLINE}, "generic-review_outline", 180)

        passed = sum(1 for v in results.values() if v is not None)
        total = len(results)
        print(f"\n===== 汇总: {passed}/{total} 通过 =====")
        for k, v in results.items():
            print(f"  {'✅' if v else '❌'} {k}")


if __name__ == "__main__":
    asyncio.run(main())
