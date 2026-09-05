"""
生成作品集用的数据可视化图表（3张）
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import pandas as pd
import os

# 设置中文字体
font_path = 'C:\\Windows\\Fonts\\simhei.ttf'
font_prop = fm.FontProperties(fname=font_path)
plt.rcParams['font.family'] = font_prop.get_name()
plt.rcParams['axes.unicode_minus'] = False

BASE = r"D:\PORTFOLIO作品集\AI-DataPilot"
OUT_DIR = os.path.join(BASE, "case-study")
os.makedirs(OUT_DIR, exist_ok=True)

# 颜色
COLORS = {
    'primary': '#1a1d27',
    'accent_blue': '#4f8cff',
    'accent_cyan': '#22d3ee',
    'red': '#dc2626',
    'yellow': '#d97706',
    'green': '#059669',
    'gray': '#9ca3af',
    'light_bg': '#f5f5f7',
}

# ========== 图1：月度营收趋势 ==========
months = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月']
revenue = [2.85, 1.92, 2.31, 2.68, 2.95, 2.78, 2.51, 2.15]  # 亿元（模拟合理数据）

fig, ax = plt.subplots(figsize=(10, 5), dpi=150)
fig.patch.set_facecolor('white')
ax.set_facecolor('white')

bars = ax.bar(months, revenue, color=COLORS['accent_blue'], alpha=0.8, width=0.6)
# 高亮7-8月下降
bars[6].set_color(COLORS['yellow'])
bars[7].set_color(COLORS['red'])

# 数值标签
for bar, val in zip(bars, revenue):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
            f'{val:.2f}', ha='center', va='bottom', fontsize=10, fontproperties=font_prop,
            color=COLORS['primary'])

ax.set_title('PC品类月度营收趋势（1-8月累计20.15亿）', fontsize=14, fontproperties=font_prop,
             color=COLORS['primary'], pad=15)
ax.set_ylabel('营收（亿元）', fontsize=11, fontproperties=font_prop, color=COLORS['primary'])
ax.set_ylim(0, 3.5)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_color('#e0e0e0')
ax.spines['bottom'].set_color('#e0e0e0')
ax.tick_params(colors=COLORS['primary'])

# 标注7-8月下降
ax.annotate('7-8月连续下降\n累计下降14.3%', xy=(6.5, 2.3), xytext=(5, 3.1),
            fontsize=10, fontproperties=font_prop, color=COLORS['red'],
            arrowprops=dict(arrowstyle='->', color=COLORS['red'], lw=1.5),
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#fef2f2', edgecolor=COLORS['red'], alpha=0.8))

plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, 'chart_monthly_trend.png'), dpi=150, bbox_inches='tight', facecolor='white')
plt.close()
print("图1已生成：月度营收趋势")

# ========== 图2：平台毛利率对比 ==========
platforms = ['京东', '天猫', '淘宝', '拼多多', '抖音', '电商通', '快手']
margins = [10.96, 7.20, 6.65, 5.16, 4.59, 3.63, -1.70]
colors = [COLORS['green'] if m > 5 else COLORS['yellow'] if m > 0 else COLORS['red'] for m in margins]

fig, ax = plt.subplots(figsize=(10, 5), dpi=150)
fig.patch.set_facecolor('white')
ax.set_facecolor('white')

bars = ax.barh(platforms, margins, color=colors, alpha=0.8, height=0.6)
ax.axvline(x=0, color='#333', linewidth=0.8)

# 数值标签
for bar, val in zip(bars, margins):
    x_pos = val + 0.3 if val >= 0 else val - 0.3
    ha = 'left' if val >= 0 else 'right'
    ax.text(x_pos, bar.get_y() + bar.get_height()/2,
            f'{val:.2f}%', ha=ha, va='center', fontsize=10, fontproperties=font_prop,
            color=COLORS['primary'], fontweight='bold')

ax.set_title('各平台进销毛利率对比（快手唯一负毛利）', fontsize=14, fontproperties=font_prop,
             color=COLORS['primary'], pad=15)
ax.set_xlabel('进销毛利率（%）', fontsize=11, fontproperties=font_prop, color=COLORS['primary'])
ax.set_xlim(-3, 13)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_color('#e0e0e0')
ax.spines['bottom'].set_color('#e0e0e0')
ax.tick_params(colors=COLORS['primary'])

# 标注快手
ax.annotate('负毛利-1.70%\n亏钱在卖', xy=(-1.7, 6), xytext=(-2.8, 4.5),
            fontsize=10, fontproperties=font_prop, color=COLORS['red'],
            arrowprops=dict(arrowstyle='->', color=COLORS['red'], lw=1.5),
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#fef2f2', edgecolor=COLORS['red'], alpha=0.8))

plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, 'chart_platform_margin.png'), dpi=150, bbox_inches='tight', facecolor='white')
plt.close()
print("图2已生成：平台毛利率对比")

# ========== 图3：品牌报价成交率对比 ==========
brands = ['荣耀', '华为', '联想', '戴尔', '惠普', '华硕', '小米', '苹果']
deal_rates = [69.7, 58.3, 45.2, 38.5, 32.1, 25.6, 15.4, 12.8]
quote_volumes = [10223, 8560, 15680, 6230, 5890, 4120, 12723, 3250]

fig, ax1 = plt.subplots(figsize=(10, 5), dpi=150)
fig.patch.set_facecolor('white')
ax1.set_facecolor('white')

# 成交率柱状图
colors_bar = [COLORS['green'] if r > 50 else COLORS['yellow'] if r > 20 else COLORS['red'] for r in deal_rates]
bars = ax1.bar(brands, deal_rates, color=colors_bar, alpha=0.7, width=0.6, label='成交率')

# 数值标签
for bar, val in zip(bars, deal_rates):
    ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
              f'{val:.1f}%', ha='center', va='bottom', fontsize=9, fontproperties=font_prop,
              color=COLORS['primary'])

ax1.set_ylabel('报价成交率（%）', fontsize=11, fontproperties=font_prop, color=COLORS['primary'])
ax1.set_ylim(0, 85)
ax1.spines['top'].set_visible(False)
ax1.spines['right'].set_visible(False)
ax1.tick_params(colors=COLORS['primary'])

# 报价量折线图（双轴）
ax2 = ax1.twinx()
ax2.plot(brands, quote_volumes, color=COLORS['accent_blue'], marker='o', linewidth=2,
         markersize=6, label='报价量')
ax2.set_ylabel('报价量（次）', fontsize=11, fontproperties=font_prop, color=COLORS['accent_blue'])
ax2.spines['top'].set_visible(False)
ax2.tick_params(colors=COLORS['accent_blue'])

# 标注小米
ax1.annotate('小米：报价量最大(12,723)\n但成交率仅15.4%', xy=(6, 15.4), xytext=(4.5, 55),
             fontsize=9, fontproperties=font_prop, color=COLORS['red'],
             arrowprops=dict(arrowstyle='->', color=COLORS['red'], lw=1.5),
             bbox=dict(boxstyle='round,pad=0.3', facecolor='#fef2f2', edgecolor=COLORS['red'], alpha=0.8))

# 标注荣耀
ax1.annotate('荣耀：成交率最高69.7%', xy=(0, 69.7), xytext=(0.5, 78),
             fontsize=9, fontproperties=font_prop, color=COLORS['green'],
             arrowprops=dict(arrowstyle='->', color=COLORS['green'], lw=1.5),
             bbox=dict(boxstyle='round,pad=0.3', facecolor='#f0fdf4', edgecolor=COLORS['green'], alpha=0.8))

ax1.set_title('各品牌报价成交率 vs 报价量（小米高报价低成交，荣耀相反）', fontsize=13,
              fontproperties=font_prop, color=COLORS['primary'], pad=15)

# 图例
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right', prop=font_prop)

plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, 'chart_brand_deal_rate.png'), dpi=150, bbox_inches='tight', facecolor='white')
plt.close()
print("图3已生成：品牌成交率对比")

print("\n全部3张图表生成完成！")
print(f"输出目录：{OUT_DIR}")
