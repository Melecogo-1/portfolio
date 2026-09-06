# -*- coding: utf-8 -*-
"""
生成脱敏采样版 orders_cleaned.csv，供公开仓库离线跑通 AI-DataPilot。

数据合规（重要）：
- 真实订单明细含企业经营信息，不进入公开仓库。
- 本脚本只依据仓库内已有 *聚合结果*（pc_brand_analysis.csv 的品牌/客单价）
  与案例页、自然语言查数中已公开的结论（整体成交率 55.8%、各品类/品牌成交率、
  账期结构、快手 15.4% 等），用固定随机种子重建一份【结构一致、分布趋势一致、
  不含任何真实客户信息】的采样，保证：看板订单模块、无 Key 时的规则化自然语言回答、
  静态案例页三者口径互相自洽，不会出现“看板一个数、问答另一个数”。
- 顶部 PC 营收 / 销量（20.15 亿、28.4 万台）来自真实聚合表 pc_*.csv，与本采样无关。
- 采样是脱敏重建，不是全量；全量口径（4.9 万报价单 / 15.6 万账单）见 case-study。
- 固定种子，重复运行结果一致、可复现。
"""
import os
import numpy as np
import pandas as pd

SEED = 20260906
rng = np.random.default_rng(SEED)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED = os.path.join(BASE, "data", "processed")

# ---- 平台：真实客单价 + 公开成交率（快手 15.4% 来自案例页），保底配额过 >200 阈值 ----
PLATFORMS = [
    ("拼多多", 0.55), ("抖音", 0.62), ("淘宝", 0.66),
    ("天猫", 0.69), ("电商通", 0.55), ("京东", 0.60), ("快手", 0.154),
]
PLATFORM_W = np.array([0.43, 0.245, 0.176, 0.095, 0.042, 0.011, 0.0013])
PLATFORM_W /= PLATFORM_W.sum()

# ---- 品类：成交率对齐案例页/问答（电视 98.6%、家电 95.2%、笔记本 75%、相机 10.9%…）----
# (品类, 成交率, 抽样权重, 品牌池key)
CATEGORIES = [
    ("笔记本电脑", 0.75, 0.18, "computing"),
    ("手机",       0.60, 0.16, "mobile"),
    ("平板电视",   0.986, 0.10, "appliance"),
    ("大家电",     0.952, 0.10, "appliance"),
    ("平板电脑",   0.58, 0.08, "computing"),
    ("智能穿戴",   0.50, 0.07, "mobile"),
    ("显示器",     0.62, 0.07, "computing"),
    ("电脑配件",   0.45, 0.08, "computing"),
    ("小家电",     0.216, 0.06, "appliance"),
    ("耳机",       0.196, 0.06, "mobile"),
    ("相机",       0.109, 0.04, "camera"),
]
CAT_NAME = [c[0] for c in CATEGORIES]
CAT_RATE = {c[0]: c[1] for c in CATEGORIES}
CAT_POOL = {c[0]: c[3] for c in CATEGORIES}
CAT_W = np.array([c[2] for c in CATEGORIES]); CAT_W /= CAT_W.sum()

# ---- 品牌池：computing 用真实 PC 品牌/客单价；其余给出合理脱敏客单价与成交率 ----
pc = pd.read_csv(os.path.join(PROCESSED, "pc_brand_analysis.csv"))
BRAND_POOL = {
    "computing": [(r["brand"], float(r["avg_price"]), 0.55) for _, r in pc.iterrows()],
    "mobile": [("小米", 2200.0, 0.154), ("荣耀", 2500.0, 0.697), ("华为", 3500.0, 0.60),
               ("苹果", 6500.0, 0.65), ("OPPO", 2400.0, 0.55), ("vivo", 2300.0, 0.55)],
    "appliance": [("美的", 3200.0, 0.72), ("海尔", 3600.0, 0.70), ("格力", 4100.0, 0.71),
                  ("海信", 2900.0, 0.68), ("TCL", 2700.0, 0.66)],
    "camera": [("佳能", 5200.0, 0.13), ("尼康", 5600.0, 0.12), ("索尼", 6100.0, 0.16)],
}

# ---- 账期结构对齐财务日报：T+1 33.7% / T+3 28.7% / 现款 9.2%，其余补齐 ----
PERIODS = [("T+1", 0.337), ("T+3", 0.287), ("T+7", 0.20), ("现款", 0.092), ("预付", 0.084)]
UNDEALT = [("撤销", 0.45), ("报价中", 0.30), ("新建采购", 0.15), ("待发布", 0.10)]
BILL_TYPES = ["销售订单", "采购订单", "退换订单"]

N = 3600
# 平台分层配额：每个来源保底 260 行（过来源 >200 阈值），其余按真实权重
base_each, quota = 260, []
extra = N - base_each * len(PLATFORMS)
for i, (_, _) in enumerate(PLATFORMS):
    quota.append(base_each + int(round(extra * PLATFORM_W[i])))
quota[0] += N - sum(quota)
plat_seq = []
for i, q in enumerate(quota):
    plat_seq += [i] * q
rng.shuffle(plat_seq)

rows = []
for i in range(N):
    cat = CAT_NAME[rng.choice(len(CATEGORIES), p=CAT_W)]
    pool = BRAND_POOL[CAT_POOL[cat]]
    brand, b_price, b_rate = pool[rng.integers(0, len(pool))]
    pname, p_rate = PLATFORMS[plat_seq[i]]
    period = PERIODS[int(rng.choice(len(PERIODS), p=[x[1] for x in PERIODS]))][0]

    # 成交概率：品类主导（0.8）+ 品牌边际修正；对快手/小米/荣耀按公开结论做乘性闸门，
    # 让“快手垫底、小米偏低、荣耀偏高”在边际上成立，整体加权落在 55.8% 附近
    p_dealt = 0.90 * CAT_RATE[cat] + 0.10 * b_rate - 0.01
    if pname == "快手":
        p_dealt *= 0.30
    if brand == "小米":
        p_dealt *= 0.32
    elif brand == "荣耀":
        p_dealt = min(0.97, p_dealt * 1.18)
    p_dealt = float(min(0.99, max(0.02, p_dealt)))
    quoted = round(b_price * float(rng.uniform(0.82, 1.18)), 2)
    if rng.random() < p_dealt:
        status, deal_price = "已成交", round(b_price * float(rng.uniform(0.85, 1.15)), 2)
    else:
        status = UNDEALT[int(rng.choice(len(UNDEALT), p=[x[1] for x in UNDEALT]))][0]
        deal_price = None  # 未成交：成交价留空，与“44.2% 成交价为空”口径一致

    rows.append({
        "品牌": brand, "类别": cat, "订单来源": pname, "订单状态": status, "账期": period,
        "成交价": deal_price,
        "订单金额": quoted,
        "账单金额": quoted if status == "已成交" else round(quoted * float(rng.uniform(0, 0.3)), 2),
        "账单二级类型": BILL_TYPES[rng.integers(0, len(BILL_TYPES))],
        "项目": "多品类经营采购",
        "收件人姓名": f"顾客{i:04d}", "收件人姓名_脱敏": f"顾客{i:04d}",
        "收件人手机号": "1**********", "收件人手机号_脱敏": "1**********",
    })

out = pd.DataFrame(rows)
out_path = os.path.join(PROCESSED, "orders_cleaned.csv")
out.to_csv(out_path, index=False, encoding="utf-8-sig")

# ---- 自检：打印各维度成交率，确认与公开结论趋势一致 ----
dealt = out["成交价"].notna()
print(f"written: {out_path}\nrows={N}  整体成交率={dealt.mean():.3f}（目标 .558）")
print("品类成交率:", (out.assign(d=dealt).groupby("类别")["d"].mean().round(3)).to_dict())
print("来源成交率:", (out.assign(d=dealt).groupby("订单来源")["d"].mean().round(3)).to_dict())
bm = out.assign(d=dealt).groupby("品牌")["d"].agg(["mean", "count"])
print("小米/荣耀成交率与样本:", bm.loc["小米"].to_dict() if "小米" in bm.index else None,
      bm.loc["荣耀"].to_dict() if "荣耀" in bm.index else None)
print("账期分布:", (out["账期"].value_counts(normalize=True).round(3)).to_dict())
print("状态分布:", (out["订单状态"].value_counts(normalize=True).round(3)).to_dict())
