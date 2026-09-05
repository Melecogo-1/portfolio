# 03 · 一源多服务部署 + 内容溯源

一份 Render Blueprint（`render.yaml`）把四个独立 Web 服务编排在同一个部署根下，服务之间用环境变量互相发现；本目录同时包含其中独立实现的**素材内容溯源服务**。

- **技术栈**：Render Blueprint（IaC）· Python 标准库 `ThreadingHTTPServer` · gunicorn · Pillow · SQLite
- **周期**：2026.02 – 2026.05，独立完成

## 一份蓝图编四个服务

| 服务 | 运行时 | 启动方式 | 源码位置 |
| --- | --- | --- | --- |
| creative-scout-portfolio 主站 | Python，**零第三方依赖** | `python backend/server.py` | `../04-creative-engine-lab` |
| provenance-lab 溯源 | 标准库 + Pillow | `python backend/server.py` | 本目录 `provenance-lab/` |
| dream-weaver 叙事 | Flask | `gunicorn app:app` | `../02-dream-weaver` |
| silent-asylum 游戏 | Flask | `gunicorn app:app` | `../05-silent-asylum` |

主站与溯源刻意用标准库实现，主站零第三方依赖，缩小部署面；两个 Flask 服务用 gunicorn 起。服务地址通过 `DREAM_WEAVER_URL`、`SILENT_ASYLUM_URL`、`PROVENANCE_LAB_URL` 等环境变量注入，代码里不写死地址。

## 幂等自举

空库启动时用 `CREATE TABLE IF NOT EXISTS` 建表、`PRAGMA table_info` 查列、缺列时 `ALTER TABLE` 补齐；实例清空磁盘后可自动重建演示数据与种子版本，不依赖手工初始化。

## 内容溯源（provenance-lab）

- SHA-256 内容哈希去重，避免同一素材重复入库；
- 8×8=64 位感知哈希 + 汉明距离衡量相似版本，对缩放 / 压缩等轻微改动保持鲁棒；
- `parent_id` 维护素材谱系，写入时做三重校验：父版本必须存在、禁止自环、删除父版本前先处理子版本；
- 三张示例图取自 Wikimedia / NOAA / USGS 的公共领域素材，并在前端标注来源与许可。

## 运行

```bash
# 本地单独跑溯源服务（端口 8010，PORT 环境变量可覆盖）
cd provenance-lab
pip install -r requirements.txt
python backend/server.py

# 线上：在 Render 导入根目录 render.yaml 即可按蓝图拉起四个服务
```
