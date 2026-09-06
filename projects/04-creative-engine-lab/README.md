# 04 · Creative Engine Lab AIGC 创意素材工具

一个 AIGC 创意素材生成与管理工具。后端**不使用任何 Web 框架**，用 Python 标准库手写 HTTP 服务，配合原生 JS 前端，做到零第三方依赖、断网可用。

- **技术栈**：Python 标准库（`http.server`）· SQLite · 原生 HTML / CSS / JS
- **端口**：`8000`
- **周期**：2026.02，独立完成

> **怎么看**：可交互的创意工具按下方步骤本地启动标准库服务（端口 8000，无需 pip 安装）。`frontend/` 内是一份早期 3D 作品集站快照（含约 15MB 模型，首次加载偏慢）；主线作品集站内嵌了该工具的纯前端复刻，断网即可推演同一套生成逻辑。

## 做了什么

- 用标准库手写 HTTP 路由、MIME 推断、CORS 预检响应，并对请求路径做目录穿越防护，静态文件无法越权访问。
- SQLite 只保留最近 24 条生成历史，超出后滚动淘汰。
- 由用户输入派生随机种子：同一输入得到同一结果，生成过程确定、可复现、可复跑；提供 4 套调色板、4 类原型、10 种材质，按取 4 / 选 3 的规则拼装多版 Prompt。
- 主线 3D 作品集站里内嵌了一个纯前端复刻：用自写的线性同余生成器（乘子 16807）替代后端随机过程，不请求任何接口，离线也能演示同一套生成逻辑。

## 目录结构

```
04-creative-engine-lab/
├── backend/server.py   标准库 HTTP 服务（路由 / MIME / CORS / 路径防护）
├── frontend/           原生前端（含本地 Three.js vendor）
├── data/concepts.db    生成历史样例
└── tools/              素材处理脚本
```

## 运行

```bash
# 纯标准库，无需 pip install
python backend/server.py
# 打开 http://localhost:8000
```
