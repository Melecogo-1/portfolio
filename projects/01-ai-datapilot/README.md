# 01 · AI-DataPilot 电商经营数据分析平台

面向 PC 渠道经营场景的数据分析平台：导入三张业务 Excel，经清洗脱敏后输出经营仪表盘、品牌 / 平台 / 订单多维分析，并提供受限的自然语言查数与岗位化日报。

- **技术栈**：Python · Flask · flask-cors · pandas · ECharts · 原生 JavaScript · DeepSeek
- **端口**：`5000`（`0.0.0.0:5000`）
- **周期**：2026.06 – 2026.08，独立完成

## 做了什么

- 用 pandas 走完 `sheet → 原始 Excel → 经营看板` 的链路：统一字段命名、对姓名与手机号脱敏、合并 4.9 万张报价单与 15.6 万张账单，覆盖 20.15 亿营收、28.4 万台设备。
- Flask 提供看板、月度、品牌、平台、订单、业务发现等多组只读接口，数据在内存中按口径聚合，不把明细写进独立数据库；前端用 ECharts 做月度双轴、品牌占比、平台对比、品类成交率四张图。
- 自然语言查数采用**受限生成而非 NL2SQL**：按「世界 / NPC / 事件」式的白名单约束模型，只在给定聚合结果范围内作答并标注来源置信度；未配置 DeepSeek Key 时自动回退到关键词规则，两条路径返回结构一致。
- 用样本阈值（品牌样本 >100、来源样本 >200）过滤小样本偏差，逐级下钻定位异常渠道，例如识别出快手渠道毛利率 -1.70%（26 万 / 96 台）、小米成交率 15.4% 与荣耀 69.7% 的结构差异。
- 按业务口径把成交价为空的订单拆分为「撤销 / 报价中 / 新建采购 / 待发布」，判为报价未成交，避免成交额虚高。

## 目录结构

```
01-ai-datapilot/
├── backend/
│   ├── app.py             Flask 入口与全部路由
│   ├── data_service.py    数据加载与口径聚合
│   ├── ai_service.py      LLM 受限生成 + 无 Key 规则降级
│   ├── data_analysis.py   离线清洗脚本（原始 Excel → processed）
│   └── generate_charts.py 离线图表产出
├── frontend/              原生 HTML/CSS/JS 看板
├── data/processed/        仅保留脱敏后的聚合样例（明细见 DATA_NOTE.md）
└── case-study/            分析图表与业务结论文档
```

## 运行

```bash
cd backend
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
python app.py
# 浏览器打开 http://localhost:5000
```

> 自然语言查数需要 `DEEPSEEK_API_KEY`；不配置时走规则降级，看板与图表不受影响。
> 完整明细数据涉及企业经营信息未入仓，仓内只保留聚合样例，复现方式见 `data/DATA_NOTE.md`。
