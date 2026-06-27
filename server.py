"""sim-desk 世界服务。

把 DeskWorld 通过 HTTP 暴露成一个标准「世界」——它实现的就是 **AWI(Anima World Interface)**,
ANIMA 的 RemoteWorld 来调。并在 `/` 提供一个给人用的单页 UI(手动拖笔、复位、看实时画面 + AWI 流量)。

AWI(脑↔世界):GET /capabilities   GET /perceive   POST /invoke   POST /reset
给人看的:    GET /stream(实时画面 MJPEG)  GET /awi-events(AWI 流量 SSE)  GET /awi-stats  GET /
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
import time
from collections import deque

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from render import render_desk
from world import DeskWorld

world = DeskWorld()  # 单个全局世界,自己独立运行

STREAM_FPS = 15  # 实时画面(MJPEG)帧率
SSE_POLL_INTERVAL_S = 0.25  # AWI 流量 SSE 多久查一次新事件;与脑端 presentation/server 对齐
AWI_LOG_MAXLEN = 400  # 保留多少条 AWI 流量历史;与脑端 src/awi_log.py 对齐

# 允许哪些网页源跨域访问;默认只放本机 :3000(脑端网页嵌本世界的 /stream),设 ANIMA_CORS_ORIGINS=* 可全开
_CORS = [o.strip() for o in os.getenv("ANIMA_CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()]

app = FastAPI(title="sim-desk world")
app.add_middleware(
    CORSMiddleware, allow_origins=_CORS, allow_methods=["*"], allow_headers=["*"]
)

_HERE = os.path.dirname(os.path.abspath(__file__))

# ---- AWI 流量记账(给世界网页的状态条 + terminal)----
_LOG: deque = deque(maxlen=AWI_LOG_MAXLEN)
_SEQ = 0
_COUNTS: dict[str, int] = {}


def _log(method: str, summary: str) -> None:
    global _SEQ
    _SEQ += 1
    _COUNTS[method] = _COUNTS.get(method, 0) + 1
    _LOG.append({"id": _SEQ, "ts": time.strftime("%H:%M:%S"), "method": method, "summary": summary})


# ===== AWI 四个端点 =====
@app.get("/capabilities")  # 世界声明自己有哪些高层动作
def capabilities() -> dict:
    caps = world.capabilities()
    _log("capabilities", f"→ 声明 {len(caps['tools'])} 个能力:{[t['name'] for t in caps['tools']]}")
    return caps


@app.get("/perceive")  # 看:当前 ground truth + 渲染图(base64)
def perceive() -> dict:
    state, image_png = world.observe()
    _log("perceive", f"→ state={state}")
    return {"state": state, "image_b64": base64.b64encode(image_png).decode()}


class InvokeIn(BaseModel):
    name: str
    args: dict = {}


@app.post("/invoke")  # 动:执行一个高层动作
def invoke(inp: InvokeIn) -> dict:
    res = world.step(inp.name, **inp.args)
    _log("invoke", f"{inp.name}({inp.args}) → {res['message']}")
    return res


@app.post("/reset")  # 世界自己复位
def reset() -> dict:
    world.reset()
    _log("reset", "世界复位")
    return {"ok": True}


# ===== 给人看的 =====
@app.get("/stream")  # 实时画面(MJPEG):浏览器 <img> 直接嵌,真·视频流(摄像头/MuJoCo 以后同理)
async def stream() -> StreamingResponse:
    async def gen():
        while True:
            jpg = render_desk(world.pen, world.canvas, fmt="JPEG")
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpg + b"\r\n"
            await asyncio.sleep(1 / STREAM_FPS)

    return StreamingResponse(gen(), media_type="multipart/x-mixed-replace; boundary=frame")


@app.get("/awi-events")  # AWI 流量(SSE):给世界网页的 terminal 实时滚动
async def awi_events() -> StreamingResponse:
    async def gen():
        last = 0
        for e in list(_LOG):  # 先补上已有的几条
            last = e["id"]
            yield f"data: {json.dumps(e, ensure_ascii=False)}\n\n"
        while True:
            await asyncio.sleep(SSE_POLL_INTERVAL_S)
            for e in [x for x in list(_LOG) if x["id"] > last]:
                last = e["id"]
                yield f"data: {json.dumps(e, ensure_ascii=False)}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/awi-stats")  # 状态条:总数 + 各方法计数 + 最近一次
def awi_stats() -> dict:
    return {"total": _SEQ, "counts": _COUNTS, "last": _LOG[-1] if _LOG else None}


@app.get("/health")  # 轻量在线探活:给 ANIMA 的 online() 用,故意【不记】AWI 流量,免得刷屏
def health() -> dict:
    return {"ok": True}


@app.get("/")  # 世界自己的人类 UI(单页)
def home() -> FileResponse:
    return FileResponse(os.path.join(_HERE, "web", "index.html"))
