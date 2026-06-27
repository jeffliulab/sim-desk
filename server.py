"""sim-desk 世界服务。

把 DeskWorld 通过 HTTP 暴露成一个标准「世界」(ANIMA 的 RemoteWorld 来调),
并在 `/` 提供一个给人用的单页 UI——你可以在浏览器里手动拖动笔、复位,模拟「真实世界
被人改变」,再看 ANIMA 那边能不能观测到。

世界接口:
  GET  /capabilities   GET /perceive   POST /invoke   POST /reset
"""
from __future__ import annotations

import base64
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from world import DeskWorld

world = DeskWorld()  # 单个全局世界,自己独立运行

app = FastAPI(title="sim-desk world")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

_HERE = os.path.dirname(os.path.abspath(__file__))


@app.get("/capabilities")  # 世界声明自己有哪些高层动作
def capabilities() -> dict:
    return world.capabilities()


@app.get("/perceive")  # 看:当前 ground truth + 渲染图(base64)
def perceive() -> dict:
    state, image_png = world.observe()
    return {"state": state, "image_b64": base64.b64encode(image_png).decode()}


class InvokeIn(BaseModel):
    name: str
    args: dict = {}


@app.post("/invoke")  # 动:执行一个高层动作
def invoke(inp: InvokeIn) -> dict:
    return world.step(inp.name, **inp.args)


@app.post("/reset")  # 世界自己复位(给下面的人类 UI 用)
def reset() -> dict:
    world.reset()
    return {"ok": True}


@app.get("/")  # 世界自己的人类 UI(单页)
def home() -> FileResponse:
    return FileResponse(os.path.join(_HERE, "web", "index.html"))
