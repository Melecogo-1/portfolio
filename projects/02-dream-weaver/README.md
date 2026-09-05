# 02 · Dream Weaver 互动叙事引擎

文字互动叙事后端：玩家用自由文本输入动作，**规则引擎先裁决**可行性与数值后果，LLM 只负责把裁决结果转成符合世界观的叙述，不决定剧情走向。

- **技术栈**：Python · Flask · DeepSeek API · JSON 世界数据 · 多线程
- **端口**：`5002`（`python app.py [port]` 可覆盖）
- **周期**：2026.04 – 2026.06，独立完成，后端约 1435 行

## 做了什么

- 数据外置为 `data/darkwood.json`：4 个地点、4 名 NPC、17 张因果卡、27 张事件卡、5 个结局，内容与服务逻辑解耦。
- 用 9 种谓词实现一套声明式条件 DSL，支持 AND / OR 嵌套，按特异度与 priority 排序匹配事件，避免多条规则同时命中时的歧义。
- 玩家动作经 7 类动作、4 档可行性、4 档风险的白名单分级；模型单步对 NPC 的态度增量被钳制在 [-8, 8]，防止单步跳变。
- 规则与生成分离：关键线索、因果卡、结局、传送都由规则授予，Prompt 明确禁止模型直接发放；规则判不了时才回退模板，模型降级与规则降级两条路径相互独立。
- 把叙述生成移出状态锁的临界区——状态裁决在锁内完成，调用 LLM 的慢过程不持锁，避免一次生成阻塞其他请求。

## 目录结构

```
02-dream-weaver/
├── app.py              Flask 入口：规则引擎 + LLM 适配层
├── data/darkwood.json  世界圣经（地点 / NPC / 因果卡 / 事件卡 / 结局）
├── static/             前端页面与场景图
├── DESIGN.md PLAN.md   设计与规划记录
└── requirements.txt
```

## 运行

```bash
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
python app.py 5002
# 打开 http://localhost:5002
```

> 设 `DEEPSEEK_API_KEY` 与 `DREAM_WEAVER_AI=1` 时走模型叙述；不配置则使用内置模板，规则裁决照常工作。
