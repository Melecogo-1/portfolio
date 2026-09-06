# 数据说明（DATA NOTE）

## 数据来源与口径

原始数据为三张业务 Excel：渠道管报、管报数据汇总、订单明细（2026.06 – 2026.08）。`backend/data_analysis.py` 负责离线清洗：统一字段命名、对姓名与手机号脱敏、按业务口径标注订单状态，产出 `data/processed/`。

核心口径：累计营收 20.15 亿、设备 28.4 万台、报价单 4.9 万张、账单 15.6 万张，CR3 集中度 88%。

## 为什么仓内没有明细

原始 Excel 与清洗后的逐行明细（`*_cleaned.csv`）包含客户名称、联系方式等企业经营信息，属于不宜公开的数据，因此**不入公开仓库**，已在 `.gitignore` 中排除。仓内 `data/processed/` 只保留可公开的聚合结果作为产出样例：

- `pc_monthly_summary.csv`：月度汇总
- `pc_platform_analysis.csv`：平台维度汇总
- `pc_brand_analysis.csv`：品牌维度汇总
- `business_findings.json`：自动 / 人工标注的业务发现
- `orders_cleaned.csv`：**脱敏采样，不是真实明细**。由 `tools/generate_sample_orders.py` 依据上面三张聚合表中的真实品牌、平台、客单价，以及可公开的成交率，用固定随机种子重建，共 2800 行、不含任何真实客户或个人信息，仅用于离线跑通订单类图表；其统计结果（如成交率、状态分布）量级接近真实分布，但不等于全量。看板顶部的 PC 营收 / 销量仍来自上面三张真实聚合表，不受采样影响。

## 如何在本地复现完整数据

1. 将三张原始 Excel 放入 `data/raw/`（该目录已被忽略，不会提交）；
2. 运行 `python backend/data_analysis.py` 重新生成 `data/processed/`；
3. 再启动 `python backend/app.py`，`data_service` 即可读到完整明细。
