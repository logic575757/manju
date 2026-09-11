import asyncio, json, sys, time
import httpx

BASE = "http://127.0.0.1:8000"


async def sse_collect(c, url, timeout=120.0):
    phases = []
    deltas = 0
    result = None
    done = None
    error = None
    async with c.stream("GET", url, timeout=timeout) as resp:
        if resp.status_code != 200:
            return None, None, None, None, f"HTTP {resp.status_code}: {await resp.aread()}"
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
                    phases.append(dj.get("phase") if isinstance(dj, dict) else str(dj))
                elif ev_name == "result":
                    result = dj
                elif ev_name == "done":
                    done = dj
                elif ev_name == "error":
                    error = dj
    return phases, deltas, result, done, error


async def submit_and_wait(c, path, payload, label, timeout=120):
    t0 = time.time()
    r = await c.post(path, json=payload)
    print(f"\n[{label}] submit {path} -> {r.status_code}")
    if r.status_code != 200:
        print(f"  ERROR body: {r.text[:500]}")
        return None
    sj = r.json()
    tid = sj["task_id"]
    print(f"  task_id={tid} position={sj.get('position')} est={sj.get('estimated_wait_sec')}s")
    phases, deltas, result, done, err = await sse_collect(c, f"/api/ai/tasks/{tid}/stream", timeout=timeout)
    dt = time.time() - t0
    if err:
        print(f"  FAIL after {dt:.1f}s phases={len(phases)} deltas={deltas} error={err}")
        return None
    rk = list(result.keys()) if isinstance(result, dict) else type(result).__name__
    print(f"  OK   after {dt:.1f}s phases={len(phases)} deltas={deltas} result_keys={rk}")
    if isinstance(result, dict):
        for k, v in result.items():
            if isinstance(v, list):
                print(f"       - {k}: list len={len(v)}")
            elif isinstance(v, dict):
                print(f"       - {k}: dict keys={list(v.keys())[:8]}")
            else:
                snippet = str(v)[:80].replace("\n", " ")
                print(f"       - {k}: {type(v).__name__} {snippet!r}")
    return result


async def main():
    async with httpx.AsyncClient(base_url=BASE, timeout=60.0) as c:
        r = await c.post("/api/auth/login", json={"username": "demo", "password": "demo123456"})
        if r.status_code != 200:
            r2 = await c.post("/api/auth/register", json={
                "username": "demo", "password": "demo123456",
                "email": "demo@test.com", "display_name": "Demo",
            })
            token = r2.json()["access_token"]
        else:
            token = r.json()["access_token"]
        c.headers["Authorization"] = f"Bearer {token}"

        scripts = await c.get("/api/scripts")
        sd = scripts.json()
        if isinstance(sd, list) and sd:
            sid = sd[0]["id"]
        elif isinstance(sd, dict) and sd.get("items"):
            sid = sd["items"][0]["id"]
        else:
            cr = await c.post("/api/scripts", json={"title": "Skill联调测试剧", "path_type": "ai", "config": {}})
            sid = cr.json()["id"]
        print(f"using script_id={sid}")

        print("\n========== 1. Skill CRUD smoke test ==========")
        lr = await c.get("/api/ai/skills")
        skills = lr.json()
        print(f"GET /api/ai/skills -> {lr.status_code} count={len(skills)}")
        for s in skills:
            print(f"  - {s['key']:25s} {s['name']:16s} cat={s['category']:10s} path=/{s['api_path']} active={s['is_active']}")

        gr = await c.get("/api/ai/skills/generate_outline")
        gd = gr.json()
        print(f"\nGET generate_outline detail -> versions={len(gd.get('versions', []))} prompt_version={gd.get('prompt_version')} has_active_prompt={gd.get('active_prompt') is not None}")

        print("\n========== 2. generate_outline (mock provider) ==========")
        outline = await submit_and_wait(c, "/api/ai/outline/generate", {
            "script_id": sid,
            "style": "爽文短剧",
            "episodes": 6,
            "pregen": 2,
            "ep_duration": 90,
            "shot_sec": 8,
            "prompt": "霸总甜宠，真假千金反转",
        }, "generate_outline", timeout=360)
        if not outline or not isinstance(outline, dict) or "outline" not in outline:
            print("  !! outline 结果结构异常，后续 review/episode 跳过")
            return
        outline_modules = outline["outline"]
        print(f"  outline modules = {len(outline_modules)}")

        print("\n========== 3. review_outline ==========")
        review = await submit_and_wait(c, "/api/ai/outline/review", {
            "script_id": sid,
            "outline": outline_modules,
        }, "review_outline", timeout=180)
        if review and isinstance(review, dict):
            issues = review.get("issues", [])
            print(f"  review score={review.get('score')} issues={len(issues) if isinstance(issues, list) else 'N/A'}")

        print("\n========== 4. generate_episode (ep1) ==========")
        ep1 = await submit_and_wait(c, "/api/ai/episode/generate", {
            "script_id": sid,
            "episode_index": 1,
            "outline": outline_modules,
            "characters": [{"id": "c1", "name": "顾晏辰", "role": "男主"}, {"id": "c2", "name": "苏晚", "role": "女主"}],
            "episode_hook": "女主意外撞破总裁身份",
            "ep_duration": 90,
            "sb_sec": 8,
        }, "generate_episode", timeout=360)
        if ep1 and isinstance(ep1, dict) and "episode" in ep1:
            ep = ep1["episode"]
            sbs = ep.get("storyboards", [])
            total_behaviors = sum(
                sum(len(cam.get("behaviors", [])) for cam in sb.get("cameras", []))
                for sb in sbs
            )
            print(f"  ep1 storyboards={len(sbs)} behaviors={total_behaviors} duration={ep.get('duration')}")

        print("\n========== 5. generic route submit /api/ai/skills/submit/{key} ==========")
        gen = await submit_and_wait(c, "/api/ai/skills/submit/review_outline", {
            "script_id": sid,
            "outline": outline_modules,
        }, "generic-review", timeout=180)

        print("\n========== ALL DONE ==========")


if __name__ == "__main__":
    asyncio.run(main())
