# 05 · Silent Asylum 文字互动游戏

克苏鲁题材的文字生存游戏。内容全部由一份 71KB 的 JSON 声明式驱动，服务端只负责状态流转与一致性校验，前端用原生 JS 渲染。

- **技术栈**：Python · Flask · Session · JSON 数据驱动 · 原生 JavaScript
- **端口**：`8080`（`HOST` / `PORT` 环境变量可覆盖）
- **周期**：2026.01，独立完成

## 做了什么

- `game_data.json` 承载 5 个场景、52 条规则、22 个事件、66 个选项、18 个碎片、7 个标志，以及 3 个正式结局 + 13 个即死结局；新增内容只改数据、不改代码。
- 核心数值为 0–100 的侵蚀度，单次变化量钳在 [-20, +30] 并分五档，避免一次选择导致数值崩坏。
- 在「做出选择」「进入场景」「读取存档」三处都做一致性校验，防止标志位与场景状态对不上。
- 5 个存档槽支持过场自动存档；死亡后提供三种恢复：原地重试、回到最近存档、回到「首间病房」的软重置——软重置只重置场景，保留侵蚀度、碎片与标志。

## 目录结构

```
05-silent-asylum/
├── app.py                  Flask 入口与状态流转
├── game_data.py            数据加载与校验
├── game_data.json          全部游戏内容（场景 / 规则 / 事件 / 结局）
├── tools/generate_data.py  离线内容生成器（程序化产出 JSON）
├── static/ templates/      前端资源与页面
└── requirements.txt
```

## 运行

```bash
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
python app.py
# 打开 http://localhost:8080
```
