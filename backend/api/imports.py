from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import User, Script, ScriptImport
from ai.service import AiService
from ai.sse import sse_event, sse_done, sse_error

router = APIRouter(prefix="/api/imports", tags=["imports"])


@router.post("")
async def create_import(
    script_id: Optional[int] = Form(None),
    title: str = Form("导入剧本"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    raw_bytes = await file.read()
    try:
        raw_text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        try:
            raw_text = raw_bytes.decode("gbk")
        except UnicodeDecodeError:
            raw_text = raw_bytes.decode("utf-8", errors="ignore")

    if not script_id:
        script = Script(
            owner_id=current.id,
            title=title,
            path_type="import",
            description=f"从文件 {file.filename} 导入",
            content={},
            step=0,
            progress=0,
            status="draft",
            config={"source_file": file.filename},
        )
        db.add(script)
        db.commit()
        db.refresh(script)
        script_id = script.id
    else:
        script = db.query(Script).filter(Script.id == script_id, Script.owner_id == current.id).first()
        if not script:
            raise HTTPException(404, "剧本不存在")

    imp = ScriptImport(
        script_id=script_id,
        file_name=file.filename or "unknown",
        file_type=file.filename.split(".")[-1] if file.filename else "txt",
        file_size=len(raw_bytes),
        raw_text=raw_text[:50000],
    )
    db.add(imp)
    db.commit()
    db.refresh(imp)

    async def parse_stream():
        import asyncio
        svc = AiService(db)
        yield sse_event("import_start", {"import_id": imp.id, "script_id": script_id, "file_name": file.filename})
        await asyncio.sleep(0.2)
        yield sse_event("phase", {"phase": "reading", "message": f"已读取文件 {file.filename}，共{len(raw_bytes)}字节"})
        await asyncio.sleep(0.3)
        async for chunk in svc.stream(
            task_key="parse_import",
            method_name="parse_import",
            params={"text": raw_text[:8000], "file_name": file.filename, "episodes": 20, "ep_duration": 90},
            user_id=current.id,
            script_id=script_id,
        ):
            yield chunk

    return StreamingResponse(
        parse_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("")
def list_imports(
    script_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    script = db.query(Script).filter(Script.id == script_id, Script.owner_id == current.id).first()
    if not script:
        raise HTTPException(404, "剧本不存在")
    imports = (
        db.query(ScriptImport)
        .filter(ScriptImport.script_id == script_id)
        .order_by(ScriptImport.created_at.desc())
        .all()
    )
    return [
        {
            "id": imp.id,
            "file_name": imp.file_name,
            "file_type": imp.file_type,
            "file_size": imp.file_size,
            "created_at": imp.created_at,
        }
        for imp in imports
    ]
