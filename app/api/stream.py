from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import asyncio
from typing import Dict
from app.services.stream_service import StreamHandle

router = APIRouter()

_STREAMS: Dict[str, StreamHandle] = {}
_LOOP = None

class StartStreamPayload(BaseModel):
    name: str
    url: str
    interval: float = 3.0

@router.post("/start_stream")
async def start_stream(p: StartStreamPayload):
    global _LOOP
    if p.name in _STREAMS:
        raise HTTPException(status_code=400, detail="stream name already exists")
    if not p.url.startswith("http"):
        raise HTTPException(status_code=400, detail="url must start with http(s)")
    if _LOOP is None:
        _LOOP = asyncio.get_event_loop()
    handle = StreamHandle(name=p.name, url=p.url, interval=max(0.5, float(p.interval)))
    _STREAMS[p.name] = handle
    handle.start(_LOOP)
    return {"status": "started", "name": p.name, "url": p.url, "interval": p.interval}

class StopStreamPayload(BaseModel):
    name: str

@router.post("/stop_stream")
async def stop_stream(p: StopStreamPayload):
    if p.name not in _STREAMS:
        raise HTTPException(status_code=404, detail="stream not found")
    handle = _STREAMS.pop(p.name)
    await handle.stop()
    return {"status": "stopped", "name": p.name}

@router.get("/streams")
async def list_streams():
    return [{"name": n, "url": h.url, "interval": h.interval} for n, h in _STREAMS.items()]
