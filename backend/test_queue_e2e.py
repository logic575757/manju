import asyncio, json, sys, time
import httpx

BASE = "http://127.0.0.1:8000"


async def main():
    async with httpx.AsyncClient(base_url=BASE, timeout=60.0) as c:
        r = await c.post("/api/auth/login", json={"username": "demo", "password": "demo123456"})
        if r.status_code != 200:
            r2 = await c.post("/api/auth/register", json={
                "username": "demo", "password": "demo123456", "email": "demo@test.com", "display_name": "Demo"
            })
            print("register:", r2.status_code, r2.text[:200])
            token = r2.json()["access_token"]
        else:
            token = r.json()["access_token"]
        c.headers["Authorization"] = f"Bearer {token}"

        me = await c.get("/api/auth/me")
        print("me:", me.status_code, me.json())

        scripts = await c.get("/api/scripts")
        print("scripts list:", scripts.status_code, scripts.text[:200])
        scripts_data = scripts.json()
        if isinstance(scripts_data, list) and scripts_data:
            sid = scripts_data[0]["id"]
        elif isinstance(scripts_data, dict) and scripts_data.get("items"):
            sid = scripts_data["items"][0]["id"]
        else:
            cr = await c.post("/api/scripts", json={"title": "测试短剧", "path_type": "short_drama", "description": "e2e", "config": {}})
            print("create script:", cr.status_code, cr.text[:200])
            sid = cr.json()["id"]
        print("script_id =", sid)

        print("\n=== Submitting outline/generate (short, episodes=1) ===")
        t0 = time.time()
        sub = await c.post("/api/ai/outline/generate", json={
            "script_id": sid,
            "title": "霸道总裁爱上我",
            "theme": ["甜宠", "逆袭"],
            "episodes": 1,
            "episode_duration": 90,
            "male_lead": "顾晏辰",
            "female_lead": "苏晚",
            "logline": "普通女孩意外进入顶级公司，与冷面总裁从互怼到相恋。",
        })
        print("submit:", sub.status_code, sub.text[:500])
        subj = sub.json()
        tid = subj["task_id"]
        print(f"task_id={tid} position={subj.get('position')} est_wait={subj.get('estimated_wait_sec')}s")

        print("\n=== Streaming from /api/ai/tasks/{tid}/stream ===")
        phases = 0
        deltas = 0
        final_status = None
        last_t = time.time()
        async with c.stream("GET", f"/api/ai/tasks/{tid}/stream", timeout=None) as resp:
            print("stream status:", resp.status_code)
            buf = ""
            async for chunk in resp.aiter_text():
                buf += chunk
                while "\n\n" in buf:
                    event_raw, buf = buf.split("\n\n", 1)
                    lines = event_raw.splitlines()
                    ev_name = ""
                    data = ""
                    for ln in lines:
                        if ln.startswith("event:"):
                            ev_name = ln[6:].strip()
                        elif ln.startswith("data:"):
                            data += ln[5:].lstrip()
                    if ev_name in ("meta", "phase", "progress", "heartbeat", "result", "done", "error", "delta"):
                        try:
                            dj = json.loads(data) if data and data[0] in "{[" else data
                        except Exception:
                            dj = data
                        now = time.time()
                        dt = now - last_t
                        last_t = now
                        if ev_name == "delta":
                            deltas += 1
                            if deltas <= 3 or deltas % 200 == 0:
                                snippet = (dj.get("delta") if isinstance(dj, dict) else str(dj))[:60]
                                print(f"  [{dt:5.2f}s] delta#{deltas}: {snippet!r}")
                        elif ev_name == "phase":
                            phases += 1
                            print(f"  [{dt:5.2f}s] PHASE: {dj}")
                        elif ev_name == "meta":
                            print(f"  [{dt:5.2f}s] META: {dj}")
                        elif ev_name == "progress":
                            print(f"  [{dt:5.2f}s] PROGRESS: {dj}")
                        elif ev_name == "heartbeat":
                            print(f"  [{dt:5.2f}s] HEARTBEAT: status={dj.get('status')} phase={dj.get('phase')} progress={dj.get('progress')}")
                        elif ev_name == "result":
                            print(f"  [{dt:5.2f}s] RESULT: keys={list(dj.keys()) if isinstance(dj,dict) else type(dj).__name__}")
                            if isinstance(dj, dict) and "outline" in dj:
                                print(f"         outline count = {len(dj['outline'])}")
                        elif ev_name == "done":
                            final_status = "success"
                            print(f"  [{dt:5.2f}s] DONE: {dj}")
                        elif ev_name == "error":
                            final_status = "error"
                            print(f"  [{dt:5.2f}s] ERROR: {dj}")
        total = time.time() - t0
        print(f"\n=== E2E summary ===")
        print(f"total wall time: {total:.1f}s | phases={phases} delta_chunks={deltas} final={final_status}")

        detail = await c.get(f"/api/ai/tasks/{tid}", params={"include_events": "false"})
        print("task detail:", json.dumps(detail.json(), ensure_ascii=False, indent=2)[:1500])


if __name__ == "__main__":
    asyncio.run(main())
