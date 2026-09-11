import asyncio, json, time
import httpx

BASE = "http://127.0.0.1:8000"


async def sse_collect(c, url, timeout=120.0):
    phases, deltas, result, done, error = [], 0, None, None, None
    async with c.stream("GET", url, timeout=timeout) as resp:
        if resp.status_code != 200:
            return None, None, None, None, f"HTTP {resp.status_code}"
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


async def submit(c, path, payload, label, timeout):
    t0 = time.time()
    r = await c.post(path, json=payload)
    print(f"\n[{label}] {path} -> {r.status_code}")
    if r.status_code != 200:
        print(f"  ERROR: {r.text[:300]}")
        return None
    sj = r.json()
    tid = sj["task_id"]
    print(f"  task_id={tid}")
    phases, deltas, result, done, err = await sse_collect(c, f"/api/ai/tasks/{tid}/stream", timeout=timeout)
    dt = time.time() - t0
    if err:
        print(f"  FAIL {dt:.1f}s phases={len(phases)} deltas={deltas} err={err}")
        return None
    rk = list(result.keys()) if isinstance(result, dict) else type(result).__name__
    print(f"  OK   {dt:.1f}s phases={len(phases)} deltas={deltas} keys={rk}")
    if isinstance(result, dict):
        for k, v in result.items():
            if isinstance(v, list):
                print(f"       - {k}: list len={len(v)}")
            elif isinstance(v, dict):
                print(f"       - {k}: dict keys={list(v.keys())[:6]}")
            else:
                print(f"       - {k}: {type(v).__name__} {str(v)[:60]!r}")
    return result


async def main():
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
            cr = await c.post("/api/scripts", json={"title": "冒烟测试剧", "path_type": "ai", "config": {}})
            sid = cr.json()["id"]
        print(f"script_id={sid}")

        MOCK_OUTLINE = [
            {"id": "m0", "type": "overview", "title": "测试大纲总览", "summary": "测试", "content": "测试内容", "issues": []},
            {"id": "m1", "type": "section", "title": "世界观", "summary": "现代都市", "content": "海城故事", "issues": []},
            {"id": "m2", "type": "section", "title": "女主", "summary": "苏晚", "content": "复仇女主", "issues": []},
        ]

        print("\n===== review_outline (轻量验证通路) =====")
        rv = await submit(c, "/api/ai/outline/review",
                          {"script_id": sid, "outline": MOCK_OUTLINE},
                          "review_outline", timeout=180)

        print("\n===== review_characters =====")
        await submit(c, "/api/ai/characters/review",
                     {"script_id": sid, "characters": [{"id":"c1","name":"苏晚","role":"女主","background":"苏家千金","arc":"从柔弱到坚强"}]},
                     "review_characters", timeout=180)

        print("\n===== rewrite_segment =====")
        await submit(c, "/api/ai/episode/rewrite-segment",
                     {"script_id": sid, "segment_text": "女主走进房间看到了男主", "instruction": "改成更有冲突感的版本"},
                     "rewrite_segment", timeout=150)

        print("\n===== DONE =====")


if __name__ == "__main__":
    asyncio.run(main())
