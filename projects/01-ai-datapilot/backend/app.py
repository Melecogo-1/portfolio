"""
AI智能管报助手 - Flask主应用
"""
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os
import sys

# 添加backend目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_service import DataService
from ai_service import AIService

app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app)

# 初始化服务
data_service = DataService()
ai_service = AIService(data_service)

# ========== 页面路由 ==========
@app.route('/')
def index():
    return send_from_directory('../frontend', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('../frontend', path)

# ========== 数据API ==========
@app.route('/api/dashboard', methods=['GET'])
def get_dashboard():
    """获取仪表盘综合数据"""
    data = data_service.get_dashboard_data()
    return jsonify({'code': 0, 'data': data})

@app.route('/api/monthly', methods=['GET'])
def get_monthly():
    """获取月度趋势数据"""
    data = data_service.get_monthly_summary()
    return jsonify({'code': 0, 'data': data})

@app.route('/api/brands', methods=['GET'])
def get_brands():
    """获取品牌分析数据"""
    data = data_service.get_brand_analysis()
    return jsonify({'code': 0, 'data': data})

@app.route('/api/platforms', methods=['GET'])
def get_platforms():
    """获取平台分析数据"""
    data = data_service.get_platform_analysis()
    return jsonify({'code': 0, 'data': data})

# ========== 订单API ==========
@app.route('/api/orders/overview', methods=['GET'])
def get_order_overview():
    """获取订单概览"""
    data = data_service.get_order_overview()
    return jsonify({'code': 0, 'data': data})

@app.route('/api/orders/categories', methods=['GET'])
def get_order_categories():
    """获取各类别成交率"""
    data = data_service.get_category_deal_rates()
    return jsonify({'code': 0, 'data': data})

@app.route('/api/orders/brands', methods=['GET'])
def get_order_brands():
    """获取品牌成交率排名"""
    top_n = request.args.get('top', 10, type=int)
    data = data_service.get_brand_deal_rates(top_n)
    return jsonify({'code': 0, 'data': data})

@app.route('/api/orders/sources', methods=['GET'])
def get_order_sources():
    """获取成交率最低的订单来源"""
    bottom_n = request.args.get('bottom', 10, type=int)
    data = data_service.get_source_deal_rates(bottom_n)
    return jsonify({'code': 0, 'data': data})

@app.route('/api/orders/status', methods=['GET'])
def get_order_status():
    """获取订单状态分布"""
    data = data_service.get_status_distribution()
    return jsonify({'code': 0, 'data': data})

@app.route('/api/orders/periods', methods=['GET'])
def get_order_periods():
    """获取账期分布"""
    data = data_service.get_period_distribution()
    return jsonify({'code': 0, 'data': data})

# ========== 业务发现API ==========
@app.route('/api/findings', methods=['GET'])
def get_findings():
    """获取业务发现列表"""
    severity = request.args.get('severity')
    data = data_service.get_findings(severity)
    return jsonify({'code': 0, 'data': data})

@app.route('/api/findings/<int:finding_id>', methods=['GET'])
def get_finding(finding_id):
    """获取单个业务发现详情"""
    data = data_service.get_finding_by_id(finding_id)
    if not data:
        return jsonify({'code': 404, 'message': '未找到该发现'}), 404
    return jsonify({'code': 0, 'data': data})

# ========== AI API ==========
@app.route('/api/ai/query', methods=['POST'])
def ai_query():
    """自然语言查数"""
    body = request.get_json()
    question = body.get('question', '')
    if not question:
        return jsonify({'code': 400, 'message': '问题不能为空'}), 400

    result = ai_service.natural_language_query(question)
    return jsonify({'code': 0, 'data': result, 'mock_mode': ai_service.mock_mode})

@app.route('/api/ai/report/<role>', methods=['GET'])
def ai_report(role):
    """生成岗位化日报"""
    valid_roles = ['sales', 'operations', 'finance', 'management']
    if role not in valid_roles:
        return jsonify({'code': 400, 'message': f'无效的岗位，可选: {valid_roles}'}), 400

    result = ai_service.generate_daily_report(role)
    return jsonify({'code': 0, 'data': result, 'mock_mode': ai_service.mock_mode})

@app.route('/api/ai/explain/<int:finding_id>', methods=['GET'])
def ai_explain(finding_id):
    """AI解释异常原因并给建议"""
    result = ai_service.explain_anomaly(finding_id)
    if 'error' in result:
        return jsonify({'code': 404, 'message': result['error']}), 404
    return jsonify({'code': 0, 'data': result, 'mock_mode': ai_service.mock_mode})

# ========== 健康检查 ==========
@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'code': 0,
        'status': 'ok',
        'mock_mode': ai_service.mock_mode,
        'data_loaded': True,
        'findings_count': len(data_service.findings)
    })

if __name__ == '__main__':
    print("=" * 60)
    print("AI智能管报助手 - 启动中...")
    print(f"AI模式: {'模拟模式 (无DeepSeek API Key)' if ai_service.mock_mode else 'DeepSeek API模式'}")
    print(f"业务发现: {len(data_service.findings)}条")
    print("访问 http://localhost:5000 打开应用")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=False)
