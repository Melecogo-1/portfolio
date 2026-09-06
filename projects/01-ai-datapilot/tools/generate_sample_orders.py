# -*- coding: utf-8 -*-
"""
生成脱敏采样版 orders_cleaned.csv，供公开仓库离线跑通 AI-DataPilot。

说明（重要 / 数据合规）：
- 真实订单明细涉及企业经营数据，不进入公开仓库。
- 本脚本只依据仓库内已有的 *聚合结果*（pc_brand_analysis.csv /
  pc_platform_analysis.csv 中的品牌、平台、客单价）与简历中可公开的成交率，
  用固定随机种子重建一份【结构一致、数值合理、不含任何真实客户/个人信息】的采样数据。
- 因此：仪表盘顶部的 PC 营收 / 销量（20.15 亿、28.4 万台）来自真实聚合表，保持不变；
  订单概览、成交率、状态/账期分布等由本采样计算，量级与真实分布接近，但不是全量值。
  全量口径（4.9 万报价单 / 15.6 万账单）见 case-study 静态案例页与简历。
- 重新运行本脚本会得到同一份采样（种子固定，结果可复现）。
"""
import os
import numpy as np
import pandas as pd

SEED = 20260906
rng = np.random.default_rng(SEED)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED = os.path.join(BASE, "data", "processed")

# 真实聚合表里的品牌与客单价（pc_brand_analysis.csv）
brand_df = pd.read_csv(os.path.join(PROCESSED, "pc_brand_analysis.csv"))
BRANDS = [(r["brand"], float(r["avg_price"])) for _, r in brand_df.iterrows()]

# 真实平台、客单价，以及可公开的成交率（快手 15.4% 来自 case-study）
PLATFORMS = [
    ("拼多多", 6352.0, 0.58),
    ("抖音",   7232.0, 0.62),
    ("淘宝",   8920.0, 0.66),
    ("天猫",   7732.0, 0.69),
    ("电商通", 7028.0, 0.55),
    ("京东",   7755.0, 0.60),
    ("快手",   2741.0, 0.154),
]
PLATFORM_NAMES = [p[0] for p in PLATFORMS]
PLATFORM_W = [0.43, 0.245, 0.176, 0.095, 0.042, 0.011, 0.0013]
PLATFORM_W = np.array(PLATFORM_W) / sum(PLATFORM_W)

CATEGORIES = ["笔记本电脑", "游戏本", "轻薄本", "台式整机", "一体机", "显示器", "电脑配件"]
PERIODS = [f"2026-{m:02d}" for m in range(1, 9)]
# 成交价为空（未成交）时的订单状态构成，对应 case-study 的 44.2% 空值拆解
UNDEALT_STATUS = [("撤销", 0.45), ("报价中", 0.30), ("新建采购", 0.15), ("待发布", 0.10)]
BILL_TYPES = ["销售订单", "采购订单", "退换订单"]

# 分层配额：每个来源保底 230 行（通过 data_service 的来源 >200 小样本阈值），
# 剩余名额再按真实平台权重分配，避免快手等小平台被滤掉、讲不清亏损下钻。
N = 2800
_BASE_EACH = 230
_extra = N - _BASE_EACH * len(PLATFORM_W)
_quota = [_BASE_EACH + int(round(_extra * w)) for w in PLATFORM_W]
_quota[0] += N - sum(_quota)
plat_seq = []
for _i, _q in enumerate(_quota):
    plat_seq += [_i] * _q
rng.shuffle(plat_seq)
rows = []
for i in range(N):
    brand, b_price = BRANDS[rng.integers(0, len(BRANDS))]
    plat_idx = plat_seq[i]
    platform, _, deal_prob = PLATFORMS[plat_idx]
    category = CATEGORIES[rng.integers(0, len(CATEGORIES))]
    period = PERIODS[rng.integers(0, len(PERIODS))]

    quoted = round(float(b_price) * float(rng.uniform(0.82, 1.18)), 2)  # 报价/订单金额
    is_dealt = rng.random() < deal_prob
    if is_dealt:
        status = "已成交"
        deal_price = round(float(b_price) * float(rng.uniform(0.85, 1.15)), 2)
    else:
        status = UNDEALT_STATUS[int(rng.choice(len(UNDEALT_STATUS),
                                  p=[x[1] for x in UNDEALT_STATUS]))][0]
        deal_price = None  # 未成交：成交价留空，与真实口径一致

    rows.append({
        "品牌": brand,
        "类别": category,
        "订单来源": platform,
        "订单状态": status,
        "账期": period,
        "成交价": deal_price,
        "订单金额": quoted,
        "账单金额": quoted if status == "已成交" else round(quoted * float(rng.uniform(0.0, 0.3)), 2),
        "账单二级类型": BILL_TYPES[rng.integers(0, len(BILL_TYPES))],
        "项目": "PC 经营采购",
        # 脱敏列：公开采样中不出现任何真实收件人信息
        "收件人姓名": f"顾客{i:04d}",
        "收件人姓名_脱敏": f"顾客{i:04d}",
        "收件人手机号": "1**********",
        "收件人手机号_脱敏": "1**********",
    })

out = pd.DataFrame(rows)
out_path = os.path.join(PROCESSED, "orders_cleaned.csv")
out.to_csv(out_path, index=False, encoding="utf-8-sig")

dealt = out["成交价"].notna().mean()
print(f"written: {out_path}")
print(f"rows={len(out)}  deal_rate={dealt:.3f}  brands={out['品牌'].nunique()}  sources={out['订单来源'].nunique()}")
print(out.groupby("订单来源").size().to_dict())
print(out.groupby("品牌").size().to_dict())
