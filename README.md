# 凌煜圣 · 全栈 / 后端（AI 应用方向）

2027 届本科，人工智能专业。主力写 Python 后端与原生前端，独立走完过「数据清洗 → Flask 服务 → LLM 输出约束 → 多服务部署」的完整链路；也用 Three.js 手写了一个零依赖、断网可运行的 3D 作品集站点——就是本仓库的根目录。

- **在线 3D 作品集**：https://melecogo-1.github.io/portfolio/
- **简历 PDF**：[resume/凌煜圣_全栈后端_2027校招简历.pdf](resume/凌煜圣_全栈后端_2027校招简历.pdf)
- **联系方式**：1793838655@qq.com ｜ 17783190642 ｜ 重庆，可全国到岗

---

## 技术栈

| 方向 | 具体技术 |
| --- | --- |
| 后端 | Python、Flask、标准库 `http.server`、RESTful API、规则引擎、多线程与锁粒度、gunicorn |
| 前端 | 原生 HTML / CSS / JavaScript、Three.js（本地 vendor）、ECharts、Canvas，不依赖前端框架 |
| 数据 | pandas 清洗与脱敏、SQLite、聚合分析、Pillow 感知哈希 |
| LLM 应用 | DeepSeek API、Ollama 本地模型、输出白名单 / 数值钳制 / 无 Key 降级、Prompt 工程、ComfyUI |
| 工程化 | Git、Render Blueprint 多服务编排、环境变量服务发现、Linux、Blender 建模与轻量化 |

---

## 项目（均为独立完成）

| # | 项目 | 一句话 | 技术栈 |
| --- | --- | --- | --- |
| 01 | [AI-DataPilot](projects/01-ai-datapilot/) | 电商经营数据分析平台：三张 Excel 进，仪表盘 / 问答 / 岗位化日报出 | Flask · pandas · ECharts · DeepSeek |
| 02 | [Dream Weaver](projects/02-dream-weaver/) | 互动叙事引擎：声明式规则 DSL 裁决自由文本动作，LLM 只负责叙述 | Flask · 规则引擎 · DeepSeek |
| 03 | [一源多服务部署 + 内容溯源](projects/03-multi-service-deploy/) | 一份 Render Blueprint 编排四个服务，另做素材哈希溯源 | Render · 标准库 · 感知哈希 |
| 04 | [Creative Engine Lab](projects/04-creative-engine-lab/) | AIGC 创意素材工具：零第三方依赖的标准库后端，种子确定可复现 | Python 标准库 · SQLite · 原生 JS |
| 05 | [Silent Asylum](projects/05-silent-asylum/) | 文字互动游戏：数值驱动状态流转，多存档与一致性校验 | Flask · Session · 原生 JS |

**01 AI-DataPilot**：用 pandas 统一字段、对姓名与手机号脱敏，聚合 4.9 万报价单 / 15.6 万账单（20.15 亿营收、28.4 万台）；自然语言查数走「世界 / NPC / 事件」白名单做受限生成（非 NL2SQL），模型只在给定范围作答并标注来源置信度，无 Key 时回退到关键词规则。

**02 Dream Weaver**：约 1435 行后端承载 4 地点 / 4 NPC / 17 因果卡 / 27 事件卡 / 5 结局；用 9 种谓词写声明式 DSL（支持 AND/OR 嵌套），按特异度与 priority 排序裁决；模型单步态度增量钳在 [-8, 8]，规则判不了才回退模板，两条降级路径相互独立。

**03 一源多服务**：一份 `render.yaml` 编排出主站、溯源、叙事、游戏四个 Web 服务，靠环境变量做服务发现；主站与溯源用标准库 `ThreadingHTTPServer`（主站零第三方依赖），Flask 服务用 gunicorn。溯源服务用 SHA-256 内容哈希去重、8×8 感知哈希 + 汉明距离算相似度、`parent_id` 做三重谱系校验。

**04 Creative Engine Lab**：不引 Web 框架，用 Python 标准库手写 HTTP 路由、MIME、CORS 与目录穿越防护，SQLite 只留最近 24 条历史；由输入派生随机种子，同一输入结果可复现，断网可用。

**05 Silent Asylum**：71KB JSON 驱动 5 场景 / 52 规则 / 22 事件 / 66 选项 / 3 正式 + 13 即死结局；0–100 侵蚀度单次增量钳在 [-20, +30]，在选择、进入、读档三处做一致性校验，5 个存档槽支持过场自动存与软重置。

---

## 仓库结构

```
portfolio/
├── index.html / app.js / styles.css   3D 作品集站（纯静态，双击 index.html 即可离线打开）
├── assets/  vendor/                   3D 站素材与本地 Three.js（无 CDN、无外部请求）
├── projects/                          五个项目源码，每个目录含独立 README 与运行步骤
└── resume/                            校招简历 PDF
```

## 关于这个 3D 作品集站

仓库根目录本身就是作品之一：一个纯手写单页应用，Three.js 走本地 `vendor/` 加载，**没有任何 CDN、外部 API 或打包步骤**，断网可运行；场景内用一个采集员角色串起时间线，点击轨道节点进入对应项目的详情卡。线上版本由 GitHub Pages 直接托管当前目录，无需后端。

## 本地运行后端项目

Flask / 标准库项目统一流程，端口各项目 README 内有标注：

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py        # 标准库项目为 python backend/server.py
```
