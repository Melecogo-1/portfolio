"""
AI服务 - DeepSeek API集成，洞察生成、自然语言查询、岗位化日报
"""
import requests
import json
import os
from datetime import datetime

class AIService:
    def __init__(self, data_service):
        self.data_service = data_service
        self.api_key = os.environ.get('DEEPSEEK_API_KEY', '')
        self.base_url = 'https://api.deepseek.com/v1/chat/completions'
        self.mock_mode = not bool(self.api_key)  # 没有key时用模拟模式

    def _call_deepseek(self, system_prompt, user_prompt, temperature=0.7):
        """调用DeepSeek API"""
        if self.mock_mode:
            return self._mock_response(system_prompt, user_prompt)

        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        data = {
            'model': 'deepseek-chat',
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt}
            ],
            'temperature': temperature,
            'max_tokens': 2000
        }
        try:
            resp = requests.post(self.base_url, headers=headers, json=data, timeout=30)
            resp.raise_for_status()
            result = resp.json()
            return result['choices'][0]['message']['content']
        except Exception as e:
            # API调用失败（余额不足/网络问题等），自动降级到模拟模式
            print(f"[AI服务] DeepSeek API调用失败，自动降级到模拟模式: {str(e)[:100]}")
            self.mock_mode = True
            return self._mock_response(system_prompt, user_prompt)

    def _mock_response(self, system_prompt, user_prompt):
        """模拟AI响应（无API key时使用）"""
        # 根据用户问题返回预设的模拟回答
        if '亏钱' in user_prompt or '负毛利' in user_prompt:
            return json.dumps({
                'answer': '快手平台毛利率为-1.70%，是唯一亏钱的平台。该平台收入仅26万元，销量96台，客单价2741元（远低于整体均价7084元）。建议：1）立即评估快手渠道的战略价值；2）如果是新渠道试水，设定亏损上限和时间窗口；3）排查是否有补贴/返点未计入。',
                'data_source': 'pc_platform_analysis',
                'confidence': 0.95
            }, ensure_ascii=False)
        elif '成交率' in user_prompt or '转化' in user_prompt:
            return json.dumps({
                'answer': '整体报价成交率为55.8%。品类差异巨大：平板电视98.6%、家电95.2%、笔记本75%成交率较高；相机仅10.9%、耳机19.6%、小家电21.6%成交率极低。品牌方面：小米报价量最大(12723次)但成交率仅15.4%，荣耀成交率高达69.7%。建议低成交率品类优化报价策略，高成交率品类加大资源投入。',
                'data_source': 'orders_cleaned',
                'confidence': 0.92
            }, ensure_ascii=False)
        elif '退货' in user_prompt:
            return json.dumps({
                'answer': '整体退货率3.92%。平台维度：拼多多4.76%最高，淘宝2.63%最低；品牌维度：宏碁5.65%最高，联想3.40%最低。拼多多高退货可能与低价策略+7天无理由退货+下沉市场用户行为有关。建议：拼多多优化商品描述降低预期差，淘宝加大投入提升占比。',
                'data_source': 'pc_monthly_summary + pc_platform_analysis',
                'confidence': 0.90
            }, ensure_ascii=False)
        elif '6月' in user_prompt or '峰值' in user_prompt or '暴涨' in user_prompt:
            return json.dumps({
                'answer': '6月收入5.99亿元，占1-8月总收入的29.7%，是2月（1.09亿）的5.5倍。主要原因是618大促，联想在拼多多的促销活动贡献了主要增量。大促后7月回落至2.80亿，8月进一步降至1.57亿，属于正常的大促后回调。建议关注Q4双11的备货和促销策略。',
                'data_source': 'pc_monthly_summary',
                'confidence': 0.88
            }, ensure_ascii=False)
        elif '品牌' in user_prompt and '集中' in user_prompt:
            return json.dumps({
                'answer': '品牌高度集中，联想独占67.0%收入（13.49亿），前3品牌（联想+华硕+ThinkPad）占比88%。单一品牌依赖度过高，联想政策变化（返点、供货、价格管控）将直接影响整体业绩。建议提升第二梯队品牌（华硕/ThinkPad/惠普）的占比至40%以上，降低单一品牌风险。',
                'data_source': 'pc_brand_analysis',
                'confidence': 0.93
            }, ensure_ascii=False)
        else:
            return json.dumps({
                'answer': '基于数据分析，我发现以下关键信息：1）PC品类1-8月总收入20.15亿元，总销量28.4万台；2）6月618大促贡献全年30%收入；3）联想占67%收入，品牌集中度高；4）快手平台负毛利-1.70%，需关注；5）订单整体报价成交率55.8%，相机类仅10.9%。请问您想了解哪个具体方面？',
                'data_source': 'multiple',
                'confidence': 0.85
            }, ensure_ascii=False)

    # ========== 自然语言查询 ==========
    def natural_language_query(self, question):
        """自然语言查数"""
        system_prompt = """你是一个电商数据分析专家。用户会用自然语言提问，你需要：
1. 理解用户的问题意图
2. 从提供的数据中找到相关信息
3. 给出准确、有数据支撑的回答
4. 如果发现问题，给出可执行的建议
回答格式为JSON，包含answer（回答）、data_source（数据来源）、confidence（置信度0-1）"""

        # 把相关数据摘要传给AI
        data_context = self._build_data_context()
        user_prompt = f"数据摘要:\n{data_context}\n\n用户问题: {question}"

        response = self._call_deepseek(system_prompt, user_prompt, temperature=0.3)

        # 尝试解析JSON
        try:
            result = json.loads(response)
            return result
        except:
            return {'answer': response, 'data_source': 'AI生成', 'confidence': 0.7}

    def _build_data_context(self):
        """构建数据上下文摘要"""
        dashboard = self.data_service.get_dashboard_data()
        pc = dashboard['pc_summary']
        order = dashboard['order_summary']

        context = f"""【PC品类管报 - 2026年1-8月】
总收入: {pc['total_income']/1e8:.2f}亿元
总销量: {pc['total_sales']:,}台
平均客单价: {pc['avg_price']:.0f}元
平均退货率: {pc['avg_return_rate']*100:.2f}%
平均进销毛利率: {pc['avg_cogs_margin']*100:.2f}%
平均客户毛利率: {pc['avg_cust_margin']*100:.2f}%

【品牌分布】
"""
        for b in dashboard['brand_distribution'][:5]:
            context += f"- {b['brand']}: {b['income']/1e8:.2f}亿 ({b['income_share']*100:.1f}%), 退货率{b['return_rate']*100:.2f}%, 毛利率{b['cogs_margin']*100:.2f}%\n"

        context += "\n【平台分布】\n"
        for p in dashboard['platform_distribution']:
            context += f"- {p['platform']}: {p['income']/1e8:.2f}亿 ({p['income_share']*100:.1f}%), 退货率{p['return_rate']*100:.2f}%, 毛利率{p['cogs_margin']*100:.2f}%\n"

        context += f"""
【O2O采购订单】
报价总数: {order['total_orders']:,}
成交数: {order['dealt_orders']:,}
成交率: {order['deal_rate']*100:.1f}%
成交金额: {order['deal_amount']/1e4:.0f}万元
平均成交价: {order['avg_price']:.0f}元
"""
        return context

    # ========== 岗位化日报 ==========
    def generate_daily_report(self, role='management'):
        """生成岗位化日报
        role: sales(销售), operations(运营), finance(财务), management(管理层)
        """
        findings = self.data_service.get_findings()
        dashboard = self.data_service.get_dashboard_data()

        if role == 'sales':
            return self._sales_report(findings, dashboard)
        elif role == 'operations':
            return self._operations_report(findings, dashboard)
        elif role == 'finance':
            return self._finance_report(findings, dashboard)
        else:
            return self._management_report(findings, dashboard)

    def _management_report(self, findings, dashboard):
        """管理层日报 - 3条核心洞察+1个风险+1个机会"""
        red_findings = [f for f in findings if f['severity'] == 'red']
        yellow_findings = [f for f in findings if f['severity'] == 'yellow']

        # 用AI生成管理层洞察
        system_prompt = """你是电商公司的CEO顾问。基于数据，给管理层生成3条核心洞察、1个风险提示、1个机会点。要求简洁、有数据支撑、可执行。"""
        user_prompt = f"关键发现: {json.dumps([f['title'] + ': ' + f['description'][:100] for f in findings[:5]], ensure_ascii=False)}"

        ai_insight = self._call_deepseek(system_prompt, user_prompt, temperature=0.5)

        return {
            'role': '管理层',
            'date': datetime.now().strftime('%Y-%m-%d'),
            'core_insights': [
                f"PC品类1-8月收入{dashboard['pc_summary']['total_income']/1e8:.2f}亿，6月618大促贡献30%，大促后回落正常",
                f"品牌集中度高，联想占67%，前3品牌占88%，存在单一品牌依赖风险",
                f"O2O订单整体成交率{dashboard['order_summary']['deal_rate']*100:.1f}%，品类差异大（家电95% vs 相机11%）"
            ],
            'risk_alerts': [f['title'] for f in red_findings] if red_findings else ['暂无严重风险'],
            'opportunities': [
                "淘宝平台毛利率最高(6.65%)且退货率最低(2.63%)，建议加大投入",
                "荣耀品牌成交率69.7%远高于小米15.4%，可优化品牌资源分配"
            ],
            'ai_summary': ai_insight
        }

    def _sales_report(self, findings, dashboard):
        """销售岗日报 - 品牌/平台排行、TOP SKU、环比"""
        brands = dashboard['brand_distribution']
        platforms = dashboard['platform_distribution']

        return {
            'role': '销售',
            'date': datetime.now().strftime('%Y-%m-%d'),
            'brand_ranking': [
                {'brand': b['brand'], 'income': b['income'], 'share': b['income_share'], 'margin': b['cogs_margin']}
                for b in brands[:5]
            ],
            'platform_ranking': [
                {'platform': p['platform'], 'income': p['income'], 'share': p['income_share'], 'margin': p['cogs_margin']}
                for p in platforms[:5]
            ],
            'key_observations': [
                f"联想占比{brands[0]['income_share']*100:.1f}%，是绝对主力",
                f"拼多多占比{platforms[0]['income_share']*100:.1f}%为第一大平台",
                "淘宝毛利率最高但占比仅17.6%，有提升空间"
            ],
            'action_items': [
                "跟进联想618后的库存和返点政策",
                "评估淘宝渠道的增长机会",
                "关注快手负毛利渠道的去留决策"
            ]
        }

    def _operations_report(self, findings, dashboard):
        """运营岗日报 - 异常预警、退货率、订单状态"""
        red_findings = [f for f in findings if f['severity'] == 'red']
        yellow_findings = [f for f in findings if f['severity'] == 'yellow']

        return {
            'role': '运营',
            'date': datetime.now().strftime('%Y-%m-%d'),
            'anomaly_alerts': [
                {'level': f['severity'], 'title': f['title'], 'description': f['description'][:150]}
                for f in red_findings + yellow_findings[:3]
            ],
            'return_rate_analysis': {
                'overall': dashboard['pc_summary']['avg_return_rate'],
                'highest_platform': '拼多多 (4.76%)',
                'lowest_platform': '淘宝 (2.63%)',
                'highest_brand': '宏碁 (5.65%)'
            },
            'order_status': dashboard['order_summary'],
            'action_items': [
                "排查快手负毛利原因，评估是否暂停",
                "优化拼多多商品描述，降低退货预期差",
                "关注相机类10.9%的低成交率，优化报价策略"
            ]
        }

    def _finance_report(self, findings, dashboard):
        """财务岗日报 - 利润率、账期、资金占用"""
        return {
            'role': '财务',
            'date': datetime.now().strftime('%Y-%m-%d'),
            'profit_analysis': {
                'cogs_margin': dashboard['pc_summary']['avg_cogs_margin'],
                'cust_margin': dashboard['pc_summary']['avg_cust_margin'],
                'highest_margin_platform': '京东 (10.96%)',
                'lowest_margin_platform': '快手 (-1.70%)',
                'monthly_trend': '4月最高7.17%，2月最低4.03%'
            },
            'payment_terms': {
                'T+1': '16534单 (33.7%)',
                'T+3': '14070单 (28.7%)',
                '现款': '4506单 (9.2%)'
            },
            'capital_occupation': {
                'note': '账单中存在税金冻结、国补冻结货款等资金占用项',
                'action': '建议测算冻结资金的时间成本和机会成本'
            },
            'risk_alerts': [
                "快手平台负毛利，需确认是否有未计入的补贴/返点",
                "44%订单为未成交报价，不产生实际收入，管报应区分报价和成交"
            ]
        }

    # ========== 异常分析解释 ==========
    def explain_anomaly(self, finding_id):
        """AI解释异常原因并给建议"""
        finding = self.data_service.get_finding_by_id(finding_id)
        if not finding:
            return {'error': '未找到该异常'}

        system_prompt = """你是电商数据分析专家。针对发现的异常，分析可能的原因，并给出3条可执行的建议。要求：1）原因分析要有逻辑，结合电商行业常识；2）建议要具体、可操作；3）区分短期措施和长期优化。"""
        user_prompt = f"异常: {finding['title']}\n描述: {finding['description']}\n数据证据: {finding['data_evidence']}"

        explanation = self._call_deepseek(system_prompt, user_prompt, temperature=0.6)

        return {
            'finding': finding,
            'ai_analysis': explanation,
            'mock_mode': self.mock_mode
        }
