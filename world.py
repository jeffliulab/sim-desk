"""sim-desk 的世界本体:一张桌面 + 一支笔。

它就是一个独立运行的「真实世界」替身:维护自己的状态(pen 的位置)、能渲染自己的画面、
能被外部动作(step)改变、也能自己复位(reset)。ANIMA 不碰它的内部,只通过 server.py 的
HTTP 接口来「看(observe)」和「动(step)」它。
"""
from __future__ import annotations

from render import render_desk

_XY = {
    "type": "object",
    "properties": {
        "x": {"type": "number", "description": "0..1,从左到右"},
        "y": {"type": "number", "description": "0..1,从上到下"},
    },
    "required": ["x", "y"],
}

# 这个世界对外声明的高层动作原语(语言可读,不是关节角)
_TOOLS = [
    {"name": "move_pen", "description": "把笔移动到桌面上的目标位置。", "parameters": _XY, "kind": "tool"},
    {
        "name": "move_object",
        "description": "把桌上的笔整理 / 移动到目标位置(多步:移动后核对到位)。",
        "parameters": _XY,
        "kind": "skill",
    },
]


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


class DeskWorld:
    def __init__(self) -> None:
        self.pen = [0.5, 0.5]  # 笔在桌面上的归一化坐标

    def capabilities(self) -> dict:
        return {"name": "sim-desk", "version": "0.1", "tools": _TOOLS}

    def observe(self) -> tuple[dict, bytes]:
        """看:返回 (结构化 ground truth, 渲染图 PNG)。"""
        return {"pen": list(self.pen)}, render_desk(self.pen)

    def step(self, name: str, **args) -> dict:
        """动:执行一个高层动作,返回 {ok, message, data}。"""
        if name in ("move_pen", "move_object"):
            self.pen = [_clamp(args["x"]), _clamp(args["y"])]
            verb = "整理" if name == "move_object" else "移动"
            return {
                "ok": True,
                "message": f"已把笔{verb}到 ({self.pen[0]:.2f}, {self.pen[1]:.2f})。",
                "data": {"pen": list(self.pen)},
            }
        return {"ok": False, "message": f"未知能力:{name}", "data": {}}

    def reset(self) -> None:
        """世界自己的复位——和任何会话无关。"""
        self.pen = [0.5, 0.5]
