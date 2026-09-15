"""Concurrency test: submit 5 tasks at once, verify only <=concurrency run in parallel."""
import asyncio, json, time
import httpx

BASE = "http://127.0.0.1:8000"


async def submit_and_stream(c: httpx.AsyncClient, sid: int, idx: int, results: dict):
    t0 = time.time()
    sub = await c.post("/api/ai/outline/generate", json={
        "script_id": sid,
        "title": f"并发测试短剧{idx}",
        "theme": ["逆袭"],
        "episodes": 1,
        "episode_duration": 90,
        "male_lead": f"男主{idx}",
        "female_lead": f"女主{idx}",
        "logline": f"测试并发剧情{idx}",
    })
    sj = sub.json()
    tid = sj["task_id"]
    results[idx] = {"tid": tid, "position": sj.get("position"), "submit_ms": int((time.time()-t0)*1000)}
    phases = []
    async with c.stream("GET", f"/api/ai/tasks/{tid}/stream", timeout=None) as resp:
        buf = ""
        async for chunk in resp.aiter_text():
            buf += chunk
            while "\n\n" in buf:
                ev_raw, buf = buf.split("\n\n", 1)
                lines = ev_raw.splitlines()
                ev_name = data = ""
                for ln in lines:
                    if ln.startswith("event:"):
                        ev_name = ln[6:].strip()
                    elif ln.startswith("data:"):
                        data += ln[5:].lstrip()
                if ev_name == "phase":
                    try:
                        dj = json.loads(data)
                        phases.append(dj.get("phase"))
                    except Exception:
                        pass
                elif ev_name == "done":
                    results[idx]["done_ms"] = int((time.time()-t0)*1000)
                    results[idx]["phases"] = phases
                    return
                elif ev_name == "error":
                    results[idx]["error"] = data
                    return


async def main():
    async with httpx.AsyncClient(base_url=BASE, timeout=120.0) as c:
        r = await c.post("/api/auth/login", json={"username": "demo", "password": "demo123456"})
        token = r.json()["access_token"]
        c.headers["Authorization"] = f"Bearer {token}"
        scripts = (await c.get("/api/scripts")).json()
        sid = scripts[0]["id"] if isinstance(scripts, list) else scripts["items"][0]["id"]

        N = 5
        print(f"\n=== Submitting {N} tasks concurrently ===")
        results = {}
        t_start = time.time()
        tasks = [asyncio.create_task(submit_and_stream(c, sid, i, results)) for i in range(N)]

        await asyncio.sleep(3)
        r2 = await c.get("/api/ai/tasks", params={"limit": 20})
        task_list = r2.json()
        items = task_list.get("items", task_list) if isinstance(task_list, dict) else task_list
        running = sum(1 for t in items if t.get("status") == "running")
        queued = sum(1 for t in items if t.get("status") == "queued")
        print(f"[t+3s] running={running} queued={queued}")
        for t in items:
            print(f"  task {t['id']}: status={t['status']} phase={t.get('phase')} attempts={t.get('attempts')} queue_wait_ms={t.get('queue_wait_ms')}")

        await asyncio.gather(*tasks)
        total = time.time() - t_start
        print(f"\n=== All {N} tasks done in {total:.1f}s ===")
        for i in sorted(results):
            r = results[i]
            print(f"  task {i}: tid={r['tid']} pos={r.get('position')} submit_ms={r.get('submit_ms')} done_ms={r.get('done_ms')} err={r.get('error')}")

        stats = await c.get("/api/ai/tasks/stats")
        print("\n=== /stats ===")
        print(json.dumps(stats.json(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
