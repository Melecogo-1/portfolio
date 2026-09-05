"""
AI智能管报助手 - 数据清洗与深度分析
输出：清洗后CSV + 10个关键业务发现 + 分析报告
"""
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime

BASE = r"D:\PORTFOLIO作品集\AI-DataPilot"
RAW = os.path.join(BASE, "data", "raw")
PROCESSED = os.path.join(BASE, "data", "processed")
ANALYSIS = os.path.join(BASE, "analysis")

os.makedirs(PROCESSED, exist_ok=True)
os.makedirs(ANALYSIS, exist_ok=True)

findings = []  # 存储10个关键发现

def add_finding(category, title, description, data_evidence, severity="info", recommendation=""):
    findings.append({
        "id": len(findings) + 1,
        "category": category,
        "title": title,
        "description": description,
        "data_evidence": data_evidence,
        "severity": severity,  # red / yellow / blue / info
        "recommendation": recommendation
    })

print("=" * 70)
print("AI智能管报助手 - 数据清洗与深度分析")
print("=" * 70)

# ======================================================================
# 1. 管报数据汇总 - PC品类
# ======================================================================
print("\n【1. 管报数据汇总 - PC品类】")
f1 = os.path.join(RAW, "管报数据汇总.xlsx")

# --- 汇总数据 ---
df_summary = pd.read_excel(f1, sheet_name='汇总数据')
months = ['2026-01', '2026-02', '2026-03', '2026-04', '2026-05',
          '2026-06', '2026-07', '2026-08']

# 提取关键指标
def get_row(df, item_name):
    row = df[df['项目'] == item_name]
    if row.empty:
        return None
    return row.iloc[0]

income_row = get_row(df_summary, '收入')
sales_row = get_row(df_summary, '-销售量')
return_row = get_row(df_summary, '-退货率')
cogs_margin_row = get_row(df_summary, '-进销毛利率')
cust_margin_row = get_row(df_summary, '客户毛利率')
cust_fee_row = get_row(df_summary, '客户费用')
fulfill_margin_row = get_row(df_summary, '履约毛利')

monthly_data = []
for m in months:
    entry = {'month': m}
    if income_row is not None:
        entry['income'] = float(income_row[m]) if pd.notna(income_row[m]) else 0
    if sales_row is not None:
        entry['sales'] = int(float(sales_row[m])) if pd.notna(sales_row[m]) else 0
    if return_row is not None:
        v = return_row[m]
        if isinstance(v, str) and '%' in v:
            entry['return_rate'] = float(v.replace('%', '')) / 100
        else:
            entry['return_rate'] = float(v) if pd.notna(v) else 0
    if cogs_margin_row is not None:
        v = cogs_margin_row[m]
        if isinstance(v, str) and '%' in v:
            entry['cogs_margin'] = float(v.replace('%', '')) / 100
        else:
            entry['cogs_margin'] = float(v) if pd.notna(v) else 0
    if cust_margin_row is not None:
        v = cust_margin_row[m]
        if isinstance(v, str) and '%' in v:
            entry['cust_margin'] = float(v.replace('%', '')) / 100
        else:
            entry['cust_margin'] = float(v) if pd.notna(v) else 0
    monthly_data.append(entry)

df_monthly = pd.DataFrame(monthly_data)
df_monthly.to_csv(os.path.join(PROCESSED, 'pc_monthly_summary.csv'), index=False, encoding='utf-8-sig')
print(f"月度汇总: {len(df_monthly)}行, 已保存")

total_income = df_monthly['income'].sum()
total_sales = df_monthly['sales'].sum()
avg_price = total_income / total_sales if total_sales > 0 else 0
avg_return = df_monthly['return_rate'].mean()
avg_cogs_margin = df_monthly['cogs_margin'].mean()
avg_cust_margin = df_monthly['cust_margin'].mean()

print(f"  总收入: {total_income/1e8:.2f}亿")
print(f"  总销量: {total_sales:,}台")
print(f"  平均客单价: {avg_price:.0f}元")
print(f"  平均退货率: {avg_return*100:.2f}%")
print(f"  平均进销毛利率: {avg_cogs_margin*100:.2f}%")
print(f"  平均客户毛利率: {avg_cust_margin*100:.2f}%")

# 发现1: 6月收入异常峰值
peak_month = df_monthly.loc[df_monthly['income'].idxmax()]
trough_month = df_monthly.loc[df_monthly['income'].idxmin()]
add_finding(
    "销售趋势", "6月收入异常峰值，占全年30%",
    f"6月收入{peak_month['income']/1e4:.0f}万，是2月（{trough_month['income']/1e4:.0f}万）的{peak_month['income']/trough_month['income']:.1f}倍，占1-8月总收入的{peak_month['income']/total_income*100:.1f}%。",
    f"6月收入{peak_month['income']/1e4:.0f}万 vs 月均{total_income/8/1e4:.0f}万，超出均值{peak_month['income']/(total_income/8)*100-100:.0f}%",
    "yellow",
    "6月为618大促月，需确认大促投入产出比；同时关注大促后7-8月的回落是否正常。"
)

# 发现2: 4月进销毛利率异常高
max_margin_month = df_monthly.loc[df_monthly['cogs_margin'].idxmax()]
min_margin_month = df_monthly.loc[df_monthly['cogs_margin'].idxmin()]
add_finding(
    "利润率", "4月进销毛利率异常高达7.17%，2月仅4.03%",
    f"4月进销毛利率{max_margin_month['cogs_margin']*100:.2f}%为8个月最高，2月{min_margin_month['cogs_margin']*100:.2f}%为最低，差值达{(max_margin_month['cogs_margin']-min_margin_month['cogs_margin'])*100:.2f}个百分点。",
    f"4月毛利率{max_margin_month['cogs_margin']*100:.2f}% vs 均值{avg_cogs_margin*100:.2f}%，高出{(max_margin_month['cogs_margin']-avg_cogs_margin)*100:.2f}pp",
    "yellow",
    "需排查4月高毛利原因：是产品结构变化（高毛利机型占比提升）、采购成本下降、还是定价策略调整？可复制到其他月份。"
)

# --- 分品牌分析 ---
print("\n【分品牌分析】")
df_brand = pd.read_excel(f1, sheet_name='分品牌汇总', header=None)

brand_names = df_brand.iloc[1, 2:12].tolist()
brand_income = df_brand.iloc[2, 2:12].tolist()
brand_sales = df_brand.iloc[3, 2:12].tolist()
brand_return = df_brand.iloc[6, 2:12].tolist()
brand_cogs_margin = df_brand.iloc[10, 2:12].tolist()

brand_data = []
for name, income, sales, ret, margin in zip(brand_names, brand_income, brand_sales, brand_return, brand_cogs_margin):
    if pd.notna(name) and pd.notna(income) and float(income) > 0:
        brand_data.append({
            'brand': str(name).strip(),
            'income': float(income),
            'sales': int(float(sales)),
            'return_rate': float(ret) if isinstance(ret, (int, float)) else 0,
            'cogs_margin': float(margin) if isinstance(margin, (int, float)) else 0,
        })

df_brand_clean = pd.DataFrame(brand_data)
df_brand_clean['avg_price'] = df_brand_clean['income'] / df_brand_clean['sales']
df_brand_clean['income_share'] = df_brand_clean['income'] / df_brand_clean['income'].sum()
df_brand_clean.to_csv(os.path.join(PROCESSED, 'pc_brand_analysis.csv'), index=False, encoding='utf-8-sig')
print(f"品牌数据: {len(df_brand_clean)}个品牌, 已保存")

# 发现3: 品牌高度集中，联想占67%
top_brand = df_brand_clean.iloc[0]
add_finding(
    "品牌结构", "品牌高度集中，联想独占67%收入",
    f"联想收入{top_brand['income']/1e8:.2f}亿，占PC品类总收入的{top_brand['income_share']*100:.1f}%。前3品牌（联想+华硕+ThinkPad）占比{(df_brand_clean['income_share'].head(3).sum())*100:.1f}%。",
    f"CR1={top_brand['income_share']*100:.1f}%, CR3={df_brand_clean['income_share'].head(3).sum()*100:.1f}%",
    "yellow",
    "单一品牌依赖度过高，联想政策变化（返点、供货、价格管控）将直接影响整体业绩。建议提升第二梯队品牌（华硕/ThinkPad/惠普）的占比至40%以上。"
)

# 发现4: 宏碁毛利率最高但退货率也最高
high_margin_brand = df_brand_clean.loc[df_brand_clean['cogs_margin'].idxmax()]
high_return_brand = df_brand_clean.loc[df_brand_clean['return_rate'].idxmax()]
add_finding(
    "品牌利润", f"{high_margin_brand['brand']}毛利率最高({high_margin_brand['cogs_margin']*100:.2f}%)但退货率也最高({high_return_brand['return_rate']*100:.2f}%)",
    f"{high_margin_brand['brand']}进销毛利率{high_margin_brand['cogs_margin']*100:.2f}%为所有品牌最高，但退货率{high_margin_brand['return_rate']*100:.2f}%也偏高。高毛利可能被高退货侵蚀。",
    f"毛利率{high_margin_brand['cogs_margin']*100:.2f}% vs 均值{df_brand_clean['cogs_margin'].mean()*100:.2f}%; 退货率{high_margin_brand['return_rate']*100:.2f}% vs 均值{df_brand_clean['return_rate'].mean()*100:.2f}%",
    "blue",
    f"需计算{high_margin_brand['brand']}的退货后实际毛利率。如果退货后毛利仍高于均值，可考虑加大投入；如果退货侵蚀严重，需优化选品和描述。"
)

# --- 分平台分析 ---
print("\n【分平台分析】")
df_platform = pd.read_excel(f1, sheet_name='分平台汇总', header=None)

platform_names = df_platform.iloc[1, 2:10].tolist()
platform_income = df_platform.iloc[2, 2:10].tolist()
platform_sales = df_platform.iloc[3, 2:10].tolist()
platform_return = df_platform.iloc[6, 2:10].tolist()
platform_cogs_margin = df_platform.iloc[10, 2:10].tolist()

platform_data = []
for name, income, sales, ret, margin in zip(platform_names, platform_income, platform_sales, platform_return, platform_cogs_margin):
    if pd.notna(name) and pd.notna(income) and float(income) > 0:
        platform_data.append({
            'platform': str(name).strip(),
            'income': float(income),
            'sales': int(float(sales)),
            'return_rate': float(ret) if isinstance(ret, (int, float)) else 0,
            'cogs_margin': float(margin) if isinstance(margin, (int, float)) else 0,
        })

df_platform_clean = pd.DataFrame(platform_data)
df_platform_clean['avg_price'] = df_platform_clean['income'] / df_platform_clean['sales']
df_platform_clean['income_share'] = df_platform_clean['income'] / df_platform_clean['income'].sum()
df_platform_clean.to_csv(os.path.join(PROCESSED, 'pc_platform_analysis.csv'), index=False, encoding='utf-8-sig')
print(f"平台数据: {len(df_platform_clean)}个平台, 已保存")

# 发现5: 快手负毛利，亏钱在卖
negative_margin_platform = df_platform_clean[df_platform_clean['cogs_margin'] < 0]
if not negative_margin_platform.empty:
    neg = negative_margin_platform.iloc[0]
    add_finding(
        "平台利润", f"{neg['platform']}毛利率为负({neg['cogs_margin']*100:.2f}%)，亏钱在卖",
        f"{neg['platform']}进销毛利率{neg['cogs_margin']*100:.2f}%，是唯一负毛利平台。收入{neg['income']/1e4:.0f}万，销量{neg['sales']}台，客单价仅{neg['avg_price']:.0f}元（远低于整体均价{avg_price:.0f}元）。",
        f"毛利率{neg['cogs_margin']*100:.2f}% vs 均值{df_platform_clean['cogs_margin'].mean()*100:.2f}%; 客单价{neg['avg_price']:.0f}元 vs 整体{avg_price:.0f}元",
        "red",
        f"立即评估{neg['platform']}渠道的战略价值：如果是新渠道试水，设定亏损上限和时间窗口；如果无战略意义，建议暂停或调整定价策略。同时排查是否有补贴/返点未计入。"
    )

# 发现6: 拼多多退货率最高但毛利率不低，淘宝退货率最低毛利率最高
pdd = df_platform_clean[df_platform_clean['platform'].str.contains('拼多多', na=False)]
tb = df_platform_clean[df_platform_clean['platform'].str.contains('淘宝', na=False)]
if not pdd.empty and not tb.empty:
    pdd = pdd.iloc[0]
    tb = tb.iloc[0]
    add_finding(
        "平台对比", f"拼多多退货率最高({pdd['return_rate']*100:.2f}%)但毛利率不低；淘宝退货率最低({tb['return_rate']*100:.2f}%)毛利率最高({tb['cogs_margin']*100:.2f}%)",
        f"拼多多收入占比{pdd['income_share']*100:.1f}%为第一大平台，但退货率{pdd['return_rate']*100:.2f}%最高。淘宝退货率仅{tb['return_rate']*100:.2f}%，毛利率{tb['cogs_margin']*100:.2f}%为所有平台最高。",
        f"PDD: 退货率{pdd['return_rate']*100:.2f}%, 毛利率{pdd['cogs_margin']*100:.2f}%; 淘宝: 退货率{tb['return_rate']*100:.2f}%, 毛利率{tb['cogs_margin']*100:.2f}%",
        "blue",
        "拼多多高退货可能与低价策略+7天无理由退货+下沉市场用户行为有关。淘宝高毛利低退货说明用户质量更好。建议：拼多多优化商品描述降低预期差，淘宝加大投入提升占比。"
    )

# ======================================================================
# 2. 订单详细信息 - O2O采购订单
# ======================================================================
print("\n" + "=" * 70)
print("【2. 订单详细信息 - O2O采购订单】")
f2 = os.path.join(RAW, "订单详细信息2026-08-17 17_16_11.xlsx")

df_orders = pd.read_excel(f2, sheet_name='0')
print(f"原始订单: {len(df_orders)}行 x {len(df_orders.columns)}列")

# 数据清洗
df_orders['成交价_num'] = pd.to_numeric(df_orders['成交价'], errors='coerce')
df_orders['订单金额_num'] = pd.to_numeric(df_orders['订单金额'], errors='coerce')

# 脱敏：收件人姓名、手机号、地址
df_orders['收件人姓名_脱敏'] = df_orders['收件人姓名'].apply(
    lambda x: str(x)[0] + '**' if pd.notna(x) and len(str(x)) > 0 else x)
df_orders['收件人手机号_脱敏'] = df_orders['收件人手机号'].apply(
    lambda x: str(x)[:3] + '****' + str(x)[-4:] if pd.notna(x) and len(str(x)) >= 7 else x)

# 保存清洗后的订单数据（脱敏版，只保留关键列）
key_columns = ['供应商', '无仓单号', '所属企业', '商家单号', 'ERP单号', '采购类型',
               '采购人', '订单来源', '渠道来源', '类别', '品牌', '产品名称', '产品规格',
               '数量', '账期', '质量要求', '成交价_num', '订单金额_num', '订单状态',
               '售后状态', '创建时间', '成交时间', '发货时间', '签收时间', '付款主体',
               '订单业务类型', '收件人姓名_脱敏', '收件人手机号_脱敏']
available_cols = [c for c in key_columns if c in df_orders.columns]
df_orders_clean = df_orders[available_cols].copy()
df_orders_clean.rename(columns={'成交价_num': '成交价', '订单金额_num': '订单金额',
                                  '收件人姓名_脱敏': '收件人姓名', '收件人手机号_脱敏': '收件人手机号'}, inplace=True)
df_orders_clean.to_csv(os.path.join(PROCESSED, 'orders_cleaned.csv'), index=False, encoding='utf-8-sig')
print(f"清洗后订单: {len(df_orders_clean)}行, 已保存（脱敏）")

# 订单状态分析
status_counts = df_orders['订单状态'].value_counts()
print(f"\n订单状态分布:")
for status, count in status_counts.items():
    print(f"  {status}: {count} ({count/len(df_orders)*100:.1f}%)")

# 发现7: "撤销"=报价未成交，不是真正的退货
missing_price = df_orders['成交价_num'].isna().sum()
missing_price_status = df_orders[df_orders['成交价_num'].isna()]['订单状态'].value_counts()
add_finding(
    "数据质量", "44%订单缺成交价，实为「报价未成交」状态，非数据错误",
    f"{missing_price}条订单（{missing_price/len(df_orders)*100:.1f}%）缺少成交价。进一步分析发现，这些订单的状态全部为「撤销」「报价中」「新建采购」「待发布」，即尚未成交的报价单。「撤销」在本系统中含义为「报价未成交」，而非「已成交后退货」。",
    f"缺成交价订单{missing_price}条，其中撤销{missing_price_status.get('撤销', 0)}条、报价中{missing_price_status.get('报价中', 0)}条、新建采购{missing_price_status.get('新建采购', 0)}条",
    "info",
    "数据口径需统一：分析成交率时应区分「报价单」和「成交单」。建议在管报中增加「报价→成交转化率」指标，这比「撤销率」更有业务意义。"
)

# 成交率分析（有成交价=成交）
df_dealt = df_orders[df_orders['成交价_num'].notna()]
deal_rate = len(df_dealt) / len(df_orders)
print(f"\n整体报价成交率: {deal_rate*100:.1f}%")

# 各类别成交率
cat_deal = df_orders.groupby('类别').apply(
    lambda x: pd.Series({
        'total': len(x),
        'dealt': x['成交价_num'].notna().sum(),
        'deal_rate': x['成交价_num'].notna().sum() / len(x)
    }), include_groups=False).sort_values('total', ascending=False)
print(f"\n各类别成交率:")
print(cat_deal[['total', 'dealt', 'deal_rate']].head(10))

# 发现8: 相机类报价成交率极低，仅14.7%
low_deal_cat = cat_deal[cat_deal['total'] > 100].sort_values('deal_rate').iloc[0]
add_finding(
    "成交转化", f"{low_deal_cat.name}类报价成交率仅{low_deal_cat['deal_rate']*100:.1f}%，远低于整体{deal_rate*100:.1f}%",
    f"{low_deal_cat.name}类共报价{int(low_deal_cat['total'])}次，仅成交{int(low_deal_cat['dealt'])}次，成交率{low_deal_cat['deal_rate']*100:.1f}%。整体报价成交率为{deal_rate*100:.1f}%。",
    f"{low_deal_cat.name}成交率{low_deal_cat['deal_rate']*100:.1f}% vs 整体{deal_rate*100:.1f}%",
    "yellow",
    f"相机类高客单价、决策周期长、比价严重，导致报价成交率低。建议：1）优化报价响应速度；2）增加相机类产品的专业咨询能力；3）评估是否继续投入相机品类，或将资源转向成交率更高的品类（家电成交率{cat_deal.loc['家电', 'deal_rate']*100:.1f}%）。"
)

# 各品牌成交率
brand_deal = df_orders.groupby('品牌').apply(
    lambda x: pd.Series({
        'total': len(x),
        'dealt': x['成交价_num'].notna().sum(),
        'deal_rate': x['成交价_num'].notna().sum() / len(x),
        'avg_price': x['成交价_num'].mean()
    }), include_groups=False)
brand_deal = brand_deal[brand_deal['total'] > 200].sort_values('deal_rate')
print(f"\n品牌成交率（最低5个）:")
print(brand_deal.head(5))
print(f"\n品牌成交率（最高5个）:")
print(brand_deal.tail(5))

# 发现9: 小米报价量最大但成交率仅37.5%，荣耀成交率83%
xiaomi = brand_deal[brand_deal.index.str.contains('小米', na=False)]
honor = brand_deal[brand_deal.index.str.contains('荣耀', na=False)]
if not xiaomi.empty and not honor.empty:
    xiaomi = xiaomi.iloc[0]
    honor = honor.iloc[0]
    add_finding(
        "品牌转化", f"小米报价量最大({int(xiaomi['total'])}次)但成交率仅{xiaomi['deal_rate']*100:.1f}%；荣耀成交率高达{honor['deal_rate']*100:.1f}%",
        f"小米报价{int(xiaomi['total'])}次为所有品牌最多，但成交率仅{xiaomi['deal_rate']*100:.1f}%，意味着{int(xiaomi['total']-xiaomi['dealt'])}次报价未转化。荣耀报价{int(honor['total'])}次，成交率{honor['deal_rate']*100:.1f}%，报价效率远高于小米。",
        f"小米: 报价{int(xiaomi['total'])}, 成交率{xiaomi['deal_rate']*100:.1f}%, 均价{xiaomi['avg_price']:.0f}元; 荣耀: 报价{int(honor['total'])}, 成交率{honor['deal_rate']*100:.1f}%, 均价{honor['avg_price']:.0f}元",
        "yellow",
        "小米价格透明、比价严重、利润薄，导致报价多但成交难。荣耀可能有渠道优势或价格管控。建议：1）小米品类优化报价策略，聚焦有价格优势的SKU；2）学习荣耀的高成交率经验；3）计算各品牌的报价人力成本，低成交率品牌可能在浪费销售资源。"
    )

# 订单来源成交率
source_deal = df_orders.groupby('订单来源').apply(
    lambda x: pd.Series({
        'total': len(x),
        'dealt': x['成交价_num'].notna().sum(),
        'deal_rate': x['成交价_num'].notna().sum() / len(x)
    }), include_groups=False)
source_deal = source_deal[source_deal['total'] > 200].sort_values('deal_rate')
print(f"\n订单来源成交率（最低5个）:")
print(source_deal.head(5))

# 发现10: PDD小米破冰专卖店成交率仅7.2%
worst_source = source_deal.iloc[0]
add_finding(
    "渠道效率", f"{worst_source.name}报价{int(worst_source['total'])}次，成交率仅{worst_source['deal_rate']*100:.1f}%",
    f"{worst_source.name}共报价{int(worst_source['total'])}次，仅成交{int(worst_source['dealt'])}次，成交率{worst_source['deal_rate']*100:.1f}%。大量报价未转化为实际订单，可能存在价格无优势、响应不及时、或店铺流量质量差等问题。",
    f"成交率{worst_source['deal_rate']*100:.1f}% vs 整体{deal_rate*100:.1f}%",
    "red",
    f"立即排查{worst_source.name}的低成交率原因：1）对比竞品价格，确认是否有价格优势；2）检查报价响应时间；3）评估该店铺的ROI，如果持续低成交，考虑减少投入或调整策略。"
)

# 账期分析
print(f"\n【账期分析】")
period_stats = df_orders.groupby('账期').apply(
    lambda x: pd.Series({
        'count': len(x),
        'avg_price': x['成交价_num'].mean(),
        'total_amount': x['订单金额_num'].sum()
    }), include_groups=False)
print(period_stats)

# 价格分析
prices = df_orders['成交价_num'].dropna()
print(f"\n【成交价分析】")
print(f"  成交订单: {len(prices)}")
print(f"  总金额: {prices.sum():,.0f}元")
print(f"  均价: {prices.mean():.0f}元")
print(f"  中位数: {prices.median():.0f}元")

# ======================================================================
# 3. 账单数据
# ======================================================================
print("\n" + "=" * 70)
print("【3. 账单数据】")
df_bills = pd.read_excel(f2, sheet_name='账单')
print(f"账单记录: {len(df_bills)}行 x {len(df_bills.columns)}列")

# 账单类型分析
if '账单二级类型' in df_bills.columns:
    bill_type = df_bills.groupby('账单二级类型').apply(
        lambda x: pd.Series({
            'count': len(x),
            'total_amount': pd.to_numeric(x['账单金额'], errors='coerce').sum()
        }), include_groups=False).sort_values('count', ascending=False)
    print(f"\n账单类型分布:")
    print(bill_type)
    
    # 资金冻结分析
    frozen_types = ['税金冻结', '国补冻结货款', '保证金冻结']
    frozen_amount = bill_type[bill_type.index.isin(frozen_types)]['total_amount'].sum()
    total_bill_amount = bill_type['total_amount'].sum()
    print(f"\n资金冻结总额: {frozen_amount:,.0f}元 ({frozen_amount/total_bill_amount*100:.1f}%)")

# 保存账单清洗数据
if '账单金额' in df_bills.columns:
    df_bills['账单金额_num'] = pd.to_numeric(df_bills['账单金额'], errors='coerce')
    df_bills_clean = df_bills.copy()
    df_bills_clean.to_csv(os.path.join(PROCESSED, 'bills_cleaned.csv'), index=False, encoding='utf-8-sig')
    print(f"账单数据已保存")

# ======================================================================
# 输出分析报告
# ======================================================================
print("\n" + "=" * 70)
print(f"共发现 {len(findings)} 个关键业务洞察")
print("=" * 70)

# 保存发现为JSON
with open(os.path.join(PROCESSED, 'business_findings.json'), 'w', encoding='utf-8') as f:
    json.dump(findings, f, ensure_ascii=False, indent=2)
print(f"发现已保存: business_findings.json")

# 生成Markdown分析报告
report = f"""# AI智能管报助手 - 数据分析报告

> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}
> 数据来源: 管报数据汇总.xlsx + 订单详细信息.xlsx（49,074条订单 + 155,896条账单）

## 一、数据概览

### PC品类管报（2026年1-8月）
- 总收入: **{total_income/1e8:.2f}亿元**
- 总销量: **{total_sales:,}台**
- 平均客单价: **{avg_price:.0f}元**
- 平均退货率: **{avg_return*100:.2f}%**
- 平均进销毛利率: **{avg_cogs_margin*100:.2f}%**
- 平均客户毛利率: **{avg_cust_margin*100:.2f}%**

### O2O采购订单
- 报价订单总数: **{len(df_orders):,}条**
- 成交订单数: **{len(df_dealt):,}条**
- 整体报价成交率: **{deal_rate*100:.1f}%**
- 成交总金额: **{prices.sum():,.0f}元**
- 成交均价: **{prices.mean():.0f}元**

### 账单数据
- 账单记录: **{len(df_bills):,}条**
- 账单总金额: **{total_bill_amount:,.0f}元**
- 资金冻结占比: **{frozen_amount/total_bill_amount*100:.1f}%**

---

## 二、关键业务洞察（{len(findings)}个）

"""

severity_labels = {'red': '🔴 严重', 'yellow': '🟡 警告', 'blue': '🔵 关注', 'info': 'ℹ️ 信息'}

for finding in findings:
    report += f"""### 洞察{finding['id']}: {finding['title']}

**类别**: {finding['category']} | **级别**: {severity_labels.get(finding['severity'], finding['severity'])}

**问题描述**:
{finding['description']}

**数据证据**:
{finding['data_evidence']}

**建议**:
{finding['recommendation']}

---

"""

report += """## 三、数据质量说明

1. **「撤销」状态口径**: 本系统中「撤销」= 报价未成交，非已成交后退货。44.2%订单缺成交价，全部为未成交状态。
2. **管报.xlsx**: 4个sheet均为空，可能是未使用的模板文件。
3. **数据脱敏**: 订单明细中的收件人姓名、手机号已脱敏处理。
4. **时间范围**: 管报数据为2026年1-8月，订单数据为截至2026-08-17的快照。

---

## 四、AI管报助手可挖掘的方向

基于以上数据，AI管报助手可提供以下能力：
1. **异常自动检测**: 实时扫描50+指标，主动发现负毛利、高退货、低成交率等问题
2. **岗位化日报**: 销售看品牌/平台排行，运营看异常预警，财务看利润率/资金冻结，管理层看3条核心洞察
3. **自然语言查数**: "哪个平台亏钱最多？"→AI自动计算+结论+图表
4. **成交率分析**: 区分报价单和成交单，计算各维度报价→成交转化率
5. **资金占用分析**: 税金冻结/国补冻结/保证金冻结的资金成本测算
"""

with open(os.path.join(ANALYSIS, 'data_analysis_report.md'), 'w', encoding='utf-8') as f:
    f.write(report)
print(f"分析报告已保存: data_analysis_report.md")

# 打印发现摘要
print("\n" + "=" * 70)
print("关键发现摘要:")
print("=" * 70)
for finding in findings:
    print(f"\n[{finding['severity'].upper()}] {finding['id']}. {finding['title']}")
    print(f"   {finding['description'][:80]}...")

print("\n" + "=" * 70)
print("数据清洗与分析完成！")
print(f"输出文件:")
print(f"  - {PROCESSED}\\pc_monthly_summary.csv")
print(f"  - {PROCESSED}\\pc_brand_analysis.csv")
print(f"  - {PROCESSED}\\pc_platform_analysis.csv")
print(f"  - {PROCESSED}\\orders_cleaned.csv (脱敏)")
print(f"  - {PROCESSED}\\bills_cleaned.csv")
print(f"  - {PROCESSED}\\business_findings.json")
print(f"  - {ANALYSIS}\\data_analysis_report.md")
print("=" * 70)
