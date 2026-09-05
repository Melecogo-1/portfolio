"""
数据服务 - 加载清洗后的数据，提供查询接口
"""
import pandas as pd
import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED = os.path.join(BASE, "data", "processed")

class DataService:
    def __init__(self):
        self._load_data()

    def _load_data(self):
        """加载所有清洗后的数据"""
        self.monthly = pd.read_csv(os.path.join(PROCESSED, "pc_monthly_summary.csv"))
        self.brand = pd.read_csv(os.path.join(PROCESSED, "pc_brand_analysis.csv"))
        self.platform = pd.read_csv(os.path.join(PROCESSED, "pc_platform_analysis.csv"))
        self.orders = pd.read_csv(os.path.join(PROCESSED, "orders_cleaned.csv"), low_memory=False)
        self.findings = json.load(open(os.path.join(PROCESSED, "business_findings.json"), encoding="utf-8"))

        # 预计算订单统计
        self._compute_order_stats()

    def _compute_order_stats(self):
        """预计算订单相关统计"""
        df = self.orders
        df['成交价_num'] = pd.to_numeric(df['成交价'], errors='coerce')

        # 整体统计
        self.order_total = len(df)
        self.order_dealt = df['成交价_num'].notna().sum()
        self.deal_rate = self.order_dealt / self.order_total if self.order_total > 0 else 0
        self.deal_amount = df['成交价_num'].sum()
        self.avg_price = df['成交价_num'].mean()

        # 各类别成交率
        self.cat_deal = df.groupby('类别').apply(
            lambda x: pd.Series({
                'total': len(x),
                'dealt': x['成交价_num'].notna().sum(),
                'deal_rate': x['成交价_num'].notna().sum() / len(x),
                'avg_price': x['成交价_num'].mean()
            }), include_groups=False).reset_index()

        # 各品牌成交率
        self.brand_deal = df.groupby('品牌').apply(
            lambda x: pd.Series({
                'total': len(x),
                'dealt': x['成交价_num'].notna().sum(),
                'deal_rate': x['成交价_num'].notna().sum() / len(x),
                'avg_price': x['成交价_num'].mean()
            }), include_groups=False).reset_index()
        self.brand_deal = self.brand_deal[self.brand_deal['total'] > 100]

        # 各订单来源成交率
        self.source_deal = df.groupby('订单来源').apply(
            lambda x: pd.Series({
                'total': len(x),
                'dealt': x['成交价_num'].notna().sum(),
                'deal_rate': x['成交价_num'].notna().sum() / len(x)
            }), include_groups=False).reset_index()
        self.source_deal = self.source_deal[self.source_deal['total'] > 200]

        # 订单状态分布
        self.status_dist = df['订单状态'].value_counts().reset_index()
        self.status_dist.columns = ['status', 'count']

        # 账期分布
        self.period_dist = df.groupby('账期').apply(
            lambda x: pd.Series({
                'count': len(x),
                'avg_price': x['成交价_num'].mean(),
                'total_amount': pd.to_numeric(x['订单金额'], errors='coerce').sum()
            }), include_groups=False).reset_index()

    # ========== PC管报数据 ==========
    def get_monthly_summary(self):
        """获取月度汇总数据"""
        return self.monthly.to_dict('records')

    def get_brand_analysis(self):
        """获取品牌分析数据"""
        return self.brand.to_dict('records')

    def get_platform_analysis(self):
        """获取平台分析数据"""
        return self.platform.to_dict('records')

    # ========== 订单数据 ==========
    def get_order_overview(self):
        """获取订单概览"""
        return {
            'total_orders': int(self.order_total),
            'dealt_orders': int(self.order_dealt),
            'deal_rate': round(float(self.deal_rate), 4),
            'deal_amount': round(float(self.deal_amount), 2),
            'avg_price': round(float(self.avg_price), 2)
        }

    def get_category_deal_rates(self):
        """获取各类别成交率"""
        return self.cat_deal.to_dict('records')

    def get_brand_deal_rates(self, top_n=10):
        """获取品牌成交率排名"""
        df = self.brand_deal.sort_values('deal_rate', ascending=False).head(top_n)
        return df.to_dict('records')

    def get_source_deal_rates(self, bottom_n=10):
        """获取成交率最低的订单来源"""
        df = self.source_deal.sort_values('deal_rate').head(bottom_n)
        return df.to_dict('records')

    def get_status_distribution(self):
        """获取订单状态分布"""
        return self.status_dist.to_dict('records')

    def get_period_distribution(self):
        """获取账期分布"""
        return self.period_dist.to_dict('records')

    # ========== 业务发现 ==========
    def get_findings(self, severity=None):
        """获取业务发现，可按严重级别筛选"""
        if severity:
            return [f for f in self.findings if f['severity'] == severity]
        return self.findings

    def get_finding_by_id(self, finding_id):
        """按ID获取单个发现"""
        for f in self.findings:
            if f['id'] == finding_id:
                return f
        return None

    # ========== 综合数据 ==========
    def get_dashboard_data(self):
        """获取仪表盘综合数据"""
        return {
            'pc_summary': {
                'total_income': round(float(self.monthly['income'].sum()), 2),
                'total_sales': int(self.monthly['sales'].sum()),
                'avg_price': round(float(self.monthly['income'].sum() / self.monthly['sales'].sum()), 2),
                'avg_return_rate': round(float(self.monthly['return_rate'].mean()), 4),
                'avg_cogs_margin': round(float(self.monthly['cogs_margin'].mean()), 4),
                'avg_cust_margin': round(float(self.monthly['cust_margin'].mean()), 4)
            },
            'order_summary': self.get_order_overview(),
            'monthly_trend': self.get_monthly_summary(),
            'brand_distribution': self.get_brand_analysis(),
            'platform_distribution': self.get_platform_analysis(),
            'findings_count': {
                'red': len([f for f in self.findings if f['severity'] == 'red']),
                'yellow': len([f for f in self.findings if f['severity'] == 'yellow']),
                'blue': len([f for f in self.findings if f['severity'] == 'blue']),
                'info': len([f for f in self.findings if f['severity'] == 'info'])
            }
        }
