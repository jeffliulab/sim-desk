"""把虚拟桌面和笔渲染成一张 PNG —— sim-desk 这个世界自己的「画面」。"""
from __future__ import annotations

import io

from PIL import Image, ImageDraw


def render_desk(pen: list[float], w: int = 640, h: int = 480, fmt: str = "PNG") -> bytes:
    img = Image.new("RGB", (w, h), (222, 205, 170))  # 木色桌面
    d = ImageDraw.Draw(img)
    d.rectangle([10, 10, w - 10, h - 10], outline=(120, 90, 60), width=4)
    px, py = int(pen[0] * w), int(pen[1] * h)
    d.line([px - 28, py + 28, px + 28, py - 28], fill=(40, 40, 40), width=8)  # 笔杆
    d.polygon(
        [(px + 28, py - 28), (px + 18, py - 16), (px + 16, py - 18)],
        fill=(210, 170, 70),  # 笔尖
    )
    buf = io.BytesIO()
    img.save(buf, format=fmt)  # PNG 给 /perceive(大脑用);JPEG 给 /stream(实时视频)
    return buf.getvalue()
