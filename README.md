# sim-desk —— ANIMA 的一个独立「世界」

一张虚拟桌面 + 一支笔 + 一块可涂画的画布。它是一个**单独运行的程序**,模拟「真实世界」:有自己的状态、
自己的画面、还有一个给人用的界面(可切换「笔/橡皮」作画、复位)。ANIMA(大脑)不碰它的内部,只**隔着一套
HTTP 接口**去观测它、操作它——就像看真实世界一样。

它对外声明 **3 个工具**:`move_pen`(把笔移到某点)、`draw`(把某矩形区域 x1,x2,y1,y2 涂黑)、
`erase`(把某矩形区域擦回空白)。

## 它对外提供什么(它实现的就是 AWI)

任何「世界」都实现同一套 **AWI(Anima World Interface)**,ANIMA 那边换个 URL 就能接(这也是 sim2sim /
上真机的路径):

```
# AWI 四个端点(脑↔世界)
GET  /capabilities  ->  {name, version, tools:[{name, description, parameters, kind}]}
GET  /perceive      ->  {state:{"pen":[x,y], "drawn":N}, image_b64:"<png base64>"}
POST /invoke {name, args}  ->  {ok, message, data}
POST /reset         ->  {ok:true}     # 世界自己复位,给下面的人类 UI 用

# 给人看的
GET  /stream        ->  实时画面(MJPEG;摄像头 / MuJoCo 以后同理)
GET  /awi-events    ->  AWI 实时流量(SSE,谁在调我的接口)
GET  /awi-stats     ->  调用统计
GET  /              ->  世界自己的人类 UI(实时画面 + AWI 状态条 + terminal)

# 运维
GET  /health        ->  {ok:true}    # 轻量在线探活(给 ANIMA 判断在线/离线;故意不记入 AWI 流量,免得刷屏)
```

## 文件

- `world.py` —— `DeskWorld`:世界本体(笔位置 + 画布状态、3 个工具的 step、observe、reset)。
- `render.py` —— 用 Pillow 把桌面 + 画布(涂黑的格子)+ 笔渲染成 PNG。
- `server.py` —— FastAPI,把世界通过上面那套 HTTP 接口暴露出去 + 托管人类 UI。
- `web/index.html` —— 给人用的单页:下方切换「笔 / 橡皮 / 移动」三个工具——笔、橡皮**拖出一个矩形选区**(带虚线框)
  涂黑 / 擦除;移动拖动 = 移笔;另有「复位」。

## 怎么跑

```bash
pip install -e .            # 或 pip install fastapi uvicorn pillow pydantic
uvicorn server:app --port 8100
```

然后:
- 打开 `http://localhost:8100` —— 世界自己的界面,选「笔/橡皮」拖出选区作画/擦除、选「移动」拖动移笔、点「复位」。
- ANIMA(anima-zero)通过 `http://localhost:8100` 连这个世界来观测和操作它。

试一下「世界是独立的」:在这个界面里手动画几笔,ANIMA 那边下一次 perceive 就会看到画面变了——
证明世界自己独立运行,大脑只是个观测者。
