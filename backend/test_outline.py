"""Quick test for generate_outline with larger max_tokens."""
import asyncio, json, time
import httpx

BASE = "http://127.0.0.1:8000"


async def sse_collect(c, url, timeout=400):
    phases, deltas, result, error = [], 0, None, None
    async with c.stream("GET", url, timeout=timeout) as resp:
        if resp.status_code != 200:
            body = await resp.aread()
            return None, None, None, f"HTTP {resp.status_code}: {body[:200].decode(errors='replace')}"
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
                elif ev_name == "error":
                    error = dj
    return phases, deltas, result, error


async def main():
    async with httpx.AsyncClient(base_url=BASE, timeout=420) as c:
        r = await c.post("/api/auth/login", json={"username": "demo", "password": "demo123456"})
        if r.status_code != 200:
            r = await c.post("/api/auth/register", json={
                "username": "demo", "password": "demo123456",
                "email": "demo@test.com", "display_name": "Demo",
            })
        c.headers["Authorization"] = f"Bearer {r.json()['access_token']}"

        scripts = await c.get("/api/scripts")
        sd = scripts.json()
        sid = sd[0]["id"] if isinstance(sd, list) and sd else 0
        print(f"Using script_id={sid}")

        payload = {
            "script_id": sid,
            "style": {
                "theme": ["穿越", "爽文", "复仇"],
                "plot": ["打脸", "逆袭", "权谋"],
                "emotion": ["爽", "燃", "反转"],
                "time": "古代架空",
            },
            "episodes": 20,
            "pregen": {"male": "萧尘", "female": "苏晚晴"},
            "ep_duration": 120,
            "shot_sec": 5,
            "prompt": "特种兵王穿越成废柴皇子，凭借现代军事知识在权谋斗争中逆袭称帝，收获爱情和江山。",
            "must": ["穿越开局", "打脸反派", "权谋博弈"],
            "avoid": ["圣母情节", "拖沓剧情"],
        }
        print("\n=== Testing generate_outline with max_tokens=16384 ===")
        t0 = time.time()
        r = await c.post("/api/ai/outline/generate", json=payload)
        if r.status_code != 200:
            print(f"❌ POST failed: {r.status_code} {r.text[:300]}")
            return
        tid = r.json()["task_id"]
        phases, deltas, result, err = await sse_collect(c, f"/api/ai/tasks/{tid}/stream", timeout=400)
        elapsed = time.time() - t0
        if err:
            print(f"❌ FAILED in {elapsed:.1f}s ({deltas} deltas): {str(err)[:300]}")
            return
        if not result:
            print(f"⚠️  No result in {elapsed:.1f}s ({deltas} deltas)")
            return
        outline = result.get("outline", result)
        if isinstance(outline, list):
            print(f"✅ PASSED in {elapsed:.1f}s ({deltas} deltas): {len(outline)} modules")
            for m in outline[:5]:
                print(f"   - {m.get('id','?'):8s} [{m.get('type','?'):10s}] {m.get('title','')[:40]}")
            if len(outline) > 5:
                print(f"   ... and {len(outline)-5} more modules")
        else:
            print(f"✅ Result keys: {list(result.keys())}")


if __name__ == "__main__":
    asyncio.run(main())
