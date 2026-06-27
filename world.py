"""sim-desk 的世界本体:一张桌面 + 一支笔 + 一块可涂画的画布。

它就是一个独立运行的「真实世界」替身:维护自己的状态(笔的位置 pen、画布上涂黑的格子 canvas)、
能渲染自己的画面、能被外部动作(step)改变、也能自己复位(reset)。ANIMA 不碰它的内部,只通过
server.py 的 HTTP 接口来「看(observe)」和「动(step)」它。
"""
from __future__ import annotations

from render import GW, GH, render_desk  # GW×GH = 画布网格(列×行),渲染与本文件共用一套

_XY = {
    "type": "object",
    "properties": {
        "x": {"type": "number", "description": "0..1,从左到右"},
        "y": {"type": "number", "description": "0..1,从上到下"},
    },
    "required": ["x", "y"],
}

_AREA = {
    "type": "object",
    "properties": {
        "x1": {"type": "number", "description": "区域左边界,0..1(从左到右)"},
        "x2": {"type": "number", "description": "区域右边界,0..1"},
        "y1": {"type": "number", "description": "区域上边界,0..1(从上到下)"},
        "y2": {"type": "number", "description": "区域下边界,0..1"},
    },
    "required": ["x1", "x2", "y1", "y2"],
}

# 这个世界对外声明的高层动作原语(语言可读,不是关节角)。
# 给几个正交、互不重叠的工具(move_pen 移光标 / draw 涂黑 / erase 擦白,各司其职);
# 每个 description 都写清「何时该调 / 何时别调 / 不做别的」——这是控制「该不该调」的地方。
_TOOLS = [
    {"name": "move_pen",
     "description": (
         "把笔(光标)移动到桌面上的目标位置 (x, y)——只是移动位置,不会在桌面上留下任何痕迹。"
         "仅当用户明确要求“把笔移到 / 放到某处”时才调用。"
         "要“画 / 涂黑某个区域”请改用 draw;要“擦除某个区域”请改用 erase;用户只是打招呼、提问时不要调用。"
         "本工具只移动笔,不画、不擦。"
     ),
     "parameters": _XY, "kind": "tool"},
    {"name": "draw",
     "description": (
         "把指定矩形区域涂成黑色(在桌面画布上作画)。区域用 x1,x2,y1,y2 四个 0..1 坐标给出"
         "(左、右、上、下边界)。仅当用户明确要求在某区域画、涂黑、填充时才调用本工具。用户只是打招呼、"
         "提问、要移动笔、或要擦除时,不要调用——本工具只涂黑给定区域,不移动笔、也不擦除。"
     ),
     "parameters": _AREA, "kind": "tool"},
    {"name": "erase",
     "description": (
         "把指定矩形区域内已画上的点擦掉、变回空白(橡皮)。区域用 x1,x2,y1,y2 四个 0..1 坐标给出。"
         "仅当用户明确要求擦除、清除、抹掉某区域时才调用本工具。用户只是打招呼、提问、要画图或移动笔时,"
         "不要调用——本工具只擦除给定区域,不画、也不移动笔。"
     ),
     "parameters": _AREA, "kind": "tool"},
]


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


class DeskWorld:
    def __init__(self) -> None:
        self.pen = [0.5, 0.5]                       # 笔在桌面上的归一化坐标
        self.canvas: set[tuple[int, int]] = set()   # 已涂黑的格子集合,元素 (row, col)

    def capabilities(self) -> dict:
        return {"name": "sim-desk", "version": "0.2", "tools": _TOOLS}

    def observe(self) -> tuple[dict, bytes]:
        """看:返回 (结构化 ground truth, 渲染图 PNG)。state 精简(画成什么样看图);drawn=已涂黑格数。"""
        return {"pen": list(self.pen), "drawn": len(self.canvas)}, render_desk(self.pen, self.canvas)

    def _fill_area(self, x1: float, x2: float, y1: float, y2: float, on: bool) -> int:
        """把归一化矩形覆盖到的格子,涂黑(on=True)或擦白(on=False);返回实际变动的格数。"""
        x1, x2 = sorted((_clamp(x1), _clamp(x2)))   # x1>x2 自动交换
        y1, y2 = sorted((_clamp(y1), _clamp(y2)))
        cols = range(min(int(x1 * GW), GW - 1), min(int(x2 * GW), GW - 1) + 1)
        rows = range(min(int(y1 * GH), GH - 1), min(int(y2 * GH), GH - 1) + 1)
        cells = {(r, c) for r in rows for c in cols}
        if on:
            changed = cells - self.canvas
            self.canvas |= cells
        else:
            changed = cells & self.canvas
            self.canvas -= cells
        return len(changed)

    def step(self, name: str, **args) -> dict:
        """动:执行一个高层动作,返回 {ok, message, data}。"""
        if name == "move_pen":
            self.pen = [_clamp(args["x"]), _clamp(args["y"])]
            return {"ok": True, "message": f"已把笔移动到 ({self.pen[0]:.2f}, {self.pen[1]:.2f})。",
                    "data": {"pen": list(self.pen)}}
        if name == "draw":
            n = self._fill_area(args["x1"], args["x2"], args["y1"], args["y2"], True)
            return {"ok": True, "message": f"已在该区域涂黑 {n} 个格子。", "data": {"drawn": len(self.canvas)}}
        if name == "erase":
            n = self._fill_area(args["x1"], args["x2"], args["y1"], args["y2"], False)
            return {"ok": True, "message": f"已擦除该区域 {n} 个格子。", "data": {"drawn": len(self.canvas)}}
        return {"ok": False, "message": f"未知能力:{name}", "data": {}}

    def reset(self) -> None:
        """世界自己的复位——和任何会话无关。"""
        self.pen = [0.5, 0.5]
        self.canvas = set()
