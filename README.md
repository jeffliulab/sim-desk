# sim-desk —— ANIMA 的一个独立「世界」

一张虚拟桌面 + 一支笔。它是一个**单独运行的程序**,模拟「真实世界」:有自己的状态、自己的画面、
还有一个给人用的界面(可以手动拖动笔、复位)。ANIMA(大脑)不碰它的内部,只**隔着一套 HTTP 接口**
去观测它、操作它——就像看真实世界一样。

## 它对外提供什么(世界接口)

任何「世界」都实现同一套接口,ANIMA 那边换个 URL 就能接(这也是 sim2sim / 上真机的路径):

```
GET  /capabilities  ->  {name, version, tools:[{name, description, parameters, kind}]}
GET  /perceive      ->  {state:{"pen":[x,y]}, image_b64:"<png base64>"}
POST /invoke {name, args}  ->  {ok, message, data}
POST /reset         ->  {ok:true}     # 世界自己复位,给下面的人类 UI 用
GET  /              ->  世界自己的人类 UI(单页)
```

## 文件

- `world.py` —— `DeskWorld`:世界本体(状态、step、observe、reset)。
- `render.py` —— 用 Pillow 把桌面 + 笔渲染成 PNG。
- `server.py` —— FastAPI,把世界通过上面那套 HTTP 接口暴露出去 + 托管人类 UI。
- `web/index.html` —— 给人用的单页:拖动笔、复位。

## 怎么跑

```bash
pip install -e .            # 或 pip install fastapi uvicorn pillow pydantic
uvicorn server:app --port 8100
```

然后:
- 打开 `http://localhost:8100` —— 世界自己的界面,可以**手动拖动笔**、点「复位」。
- ANIMA(anima-zero)通过 `http://localhost:8100` 连这个世界来观测和操作它。

试一下「世界是独立的」:在这个界面里手动把笔拖到角落,ANIMA 那边下一次 perceive 就会看到笔变了——
证明世界自己独立运行,大脑只是个观测者。
