// ========== 全局变量 ==========
const API_BASE = '/api';  // 同源相对路径：本地由 Flask 直接提供前端，无需写死 localhost
let charts = {};
let allFindings = [];
let currentRole = 'management';

// ========== 初始化 ==========
document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    initDate();
    loadDashboard();
    loadAnomalies();
    loadReport('management');
    initQuery();
    initAnomalyFilters();
    initRoleSelector();
});

// ========== 标签切换 ==========
function initTabs() {
    const tabs = document.querySelectorAll('.tab');
    const contents = document.querySelectorAll('.tab-content');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const target = tab.dataset.tab;

            tabs.forEach(t => t.classList.remove('active'));
            contents.forEach(c => c.classList.remove('active'));

            tab.classList.add('active');
            document.getElementById(target).classList.add('active');

            // 切换到对应tab时重新渲染图表
            if (target === 'dashboard') {
                setTimeout(() => {
                    Object.values(charts).forEach(chart => chart && chart.resize());
                }, 100);
            }
        });
    });
}

function initDate() {
    const now = new Date();
    document.getElementById('currentDate').textContent =
        `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
}

// ========== API请求 ==========
async function apiGet(endpoint) {
    try {
        const resp = await fetch(`${API_BASE}${endpoint}`);
        return await resp.json();
    } catch (e) {
        console.error('API请求失败:', e);
        return { code: -1, message: e.message };
    }
}

async function apiPost(endpoint, data) {
    try {
        const resp = await fetch(`${API_BASE}${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        return await resp.json();
    } catch (e) {
        console.error('API请求失败:', e);
        return { code: -1, message: e.message };
    }
}

// ========== 仪表盘 ==========
async function loadDashboard() {
    const data = await apiGet('/dashboard');
    if (data.code !== 0) return;

    const d = data.data;
    const pc = d.pc_summary;
    const order = d.order_summary;

    // 更新指标卡片
    document.getElementById('pcIncome').textContent = (pc.total_income / 1e8).toFixed(2) + '亿';
    document.getElementById('pcSales').textContent = pc.total_sales.toLocaleString() + '台';
    document.getElementById('avgPrice').textContent = pc.avg_price.toLocaleString() + '元';
    document.getElementById('orderTotal').textContent = order.total_orders.toLocaleString();
    document.getElementById('dealRate').textContent = (order.deal_rate * 100).toFixed(1) + '%';
    document.getElementById('redCount').textContent = d.findings_count.red;
    document.getElementById('yellowCount').textContent = d.findings_count.yellow;
    document.getElementById('anomalyCount').textContent = d.findings_count.red + d.findings_count.yellow + d.findings_count.blue;

    // 更新AI状态
    const health = await apiGet('/health');
    if (health.code === 0) {
        const badge = document.getElementById('aiStatus');
        if (health.mock_mode) {
            badge.textContent = 'AI模拟模式';
            badge.className = 'status-badge';
        } else {
            badge.textContent = 'AI在线';
            badge.className = 'status-badge active';
        }
    }

    // 渲染图表
    renderMonthlyChart(d.monthly_trend);
    renderBrandChart(d.brand_distribution);
    renderPlatformChart(d.platform_distribution);
    renderCategoryChart();
}

function renderMonthlyChart(data) {
    const el = document.getElementById('monthlyChart');
    if (!el) return;

    if (charts.monthly) charts.monthly.dispose();
    charts.monthly = echarts.init(el);

    const months = data.map(d => d.month);
    const income = data.map(d => (d.income / 10000).toFixed(0));
    const sales = data.map(d => d.sales);
    const margin = data.map(d => (d.cogs_margin * 100).toFixed(2));

    charts.monthly.setOption({
        backgroundColor: 'transparent',
        tooltip: {
            trigger: 'axis',
            backgroundColor: '#21242f',
            borderColor: '#2d3140',
            textStyle: { color: '#e8eaf0' }
        },
        legend: {
            data: ['收入(万元)', '销量(台)', '进销毛利率(%)'],
            textStyle: { color: '#9ca3b4' },
            top: 0
        },
        grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
        xAxis: {
            type: 'category',
            data: months,
            axisLine: { lineStyle: { color: '#2d3140' } },
            axisLabel: { color: '#9ca3b4' }
        },
        yAxis: [
            {
                type: 'value',
                name: '收入/销量',
                axisLine: { lineStyle: { color: '#2d3140' } },
                axisLabel: { color: '#9ca3b4' },
                splitLine: { lineStyle: { color: '#2d3140' } }
            },
            {
                type: 'value',
                name: '毛利率(%)',
                axisLine: { lineStyle: { color: '#2d3140' } },
                axisLabel: { color: '#9ca3b4', formatter: '{value}%' },
                splitLine: { show: false }
            }
        ],
        series: [
            {
                name: '收入(万元)',
                type: 'bar',
                data: income,
                itemStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: '#4f8cff' },
                        { offset: 1, color: '#22d3ee' }
                    ]),
                    borderRadius: [4, 4, 0, 0]
                }
            },
            {
                name: '销量(台)',
                type: 'line',
                data: sales,
                smooth: true,
                lineStyle: { color: '#a78bfa', width: 2 },
                itemStyle: { color: '#a78bfa' }
            },
            {
                name: '进销毛利率(%)',
                type: 'line',
                yAxisIndex: 1,
                data: margin,
                smooth: true,
                lineStyle: { color: '#34d399', width: 2, type: 'dashed' },
                itemStyle: { color: '#34d399' }
            }
        ]
    });
}

function renderBrandChart(data) {
    const el = document.getElementById('brandChart');
    if (!el) return;

    if (charts.brand) charts.brand.dispose();
    charts.brand = echarts.init(el);

    const brands = data.slice(0, 6).map(d => d.brand.replace(/（.*?）/g, ''));
    const values = data.slice(0, 6).map(d => (d.income / 1e8).toFixed(2));

    charts.brand.setOption({
        backgroundColor: 'transparent',
        tooltip: {
            trigger: 'item',
            backgroundColor: '#21242f',
            borderColor: '#2d3140',
            textStyle: { color: '#e8eaf0' },
            formatter: '{b}: {c}亿 ({d}%)'
        },
        series: [{
            type: 'pie',
            radius: ['40%', '70%'],
            center: ['50%', '55%'],
            avoidLabelOverlap: false,
            itemStyle: {
                borderRadius: 8,
                borderColor: '#21242f',
                borderWidth: 2
            },
            label: {
                show: true,
                color: '#9ca3b4',
                fontSize: 11,
                formatter: '{b}\n{d}%'
            },
            data: brands.map((b, i) => ({
                name: b,
                value: values[i],
                itemStyle: {
                    color: ['#4f8cff', '#22d3ee', '#34d399', '#fbbf24', '#f87171', '#a78bfa'][i]
                }
            }))
        }]
    });
}

function renderPlatformChart(data) {
    const el = document.getElementById('platformChart');
    if (!el) return;

    if (charts.platform) charts.platform.dispose();
    charts.platform = echarts.init(el);

    const platforms = data.map(d => d.platform);
    const income = data.map(d => (d.income / 1e8).toFixed(2));
    const margin = data.map(d => (d.cogs_margin * 100).toFixed(2));
    const returnRate = data.map(d => (d.return_rate * 100).toFixed(2));

    charts.platform.setOption({
        backgroundColor: 'transparent',
        tooltip: {
            trigger: 'axis',
            backgroundColor: '#21242f',
            borderColor: '#2d3140',
            textStyle: { color: '#e8eaf0' }
        },
        legend: {
            data: ['收入(亿)', '毛利率(%)', '退货率(%)'],
            textStyle: { color: '#9ca3b4' },
            top: 0
        },
        grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
        xAxis: {
            type: 'category',
            data: platforms,
            axisLine: { lineStyle: { color: '#2d3140' } },
            axisLabel: { color: '#9ca3b4', rotate: 30, fontSize: 11 }
        },
        yAxis: {
            type: 'value',
            axisLine: { lineStyle: { color: '#2d3140' } },
            axisLabel: { color: '#9ca3b4' },
            splitLine: { lineStyle: { color: '#2d3140' } }
        },
        series: [
            {
                name: '收入(亿)',
                type: 'bar',
                data: income,
                itemStyle: { color: '#4f8cff', borderRadius: [4, 4, 0, 0] }
            },
            {
                name: '毛利率(%)',
                type: 'line',
                data: margin,
                smooth: true,
                lineStyle: { color: '#34d399', width: 2 },
                itemStyle: { color: '#34d399' }
            },
            {
                name: '退货率(%)',
                type: 'line',
                data: returnRate,
                smooth: true,
                lineStyle: { color: '#f87171', width: 2 },
                itemStyle: { color: '#f87171' }
            }
        ]
    });
}

async function renderCategoryChart() {
    const data = await apiGet('/orders/categories');
    if (data.code !== 0) return;

    const el = document.getElementById('categoryChart');
    if (!el) return;

    if (charts.category) charts.category.dispose();
    charts.category = echarts.init(el);

    const categories = data.data.filter(d => d.total > 50).sort((a, b) => b.deal_rate - a.deal_rate);
    const names = categories.map(d => d.类别);
    const dealRates = categories.map(d => (d.deal_rate * 100).toFixed(1));
    const totals = categories.map(d => d.total);

    charts.category.setOption({
        backgroundColor: 'transparent',
        tooltip: {
            trigger: 'axis',
            backgroundColor: '#21242f',
            borderColor: '#2d3140',
            textStyle: { color: '#e8eaf0' },
            formatter: function(params) {
                let result = params[0].name + '<br/>';
                params.forEach(p => {
                    result += `${p.marker} ${p.seriesName}: ${p.value}${p.seriesName.includes('率') ? '%' : '次'}<br/>`;
                });
                return result;
            }
        },
        legend: {
            data: ['成交率(%)', '报价次数'],
            textStyle: { color: '#9ca3b4' },
            top: 0
        },
        grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
        xAxis: {
            type: 'category',
            data: names,
            axisLine: { lineStyle: { color: '#2d3140' } },
            axisLabel: { color: '#9ca3b4', rotate: 30, fontSize: 11 }
        },
        yAxis: [
            {
                type: 'value',
                name: '成交率(%)',
                axisLine: { lineStyle: { color: '#2d3140' } },
                axisLabel: { color: '#9ca3b4', formatter: '{value}%' },
                splitLine: { lineStyle: { color: '#2d3140' } }
            },
            {
                type: 'value',
                name: '报价次数',
                axisLine: { lineStyle: { color: '#2d3140' } },
                axisLabel: { color: '#9ca3b4' },
                splitLine: { show: false }
            }
        ],
        series: [
            {
                name: '成交率(%)',
                type: 'bar',
                data: dealRates,
                itemStyle: {
                    color: function(params) {
                        const val = parseFloat(params.value);
                        if (val < 30) return '#f87171';
                        if (val < 60) return '#fbbf24';
                        return '#34d399';
                    },
                    borderRadius: [4, 4, 0, 0]
                }
            },
            {
                name: '报价次数',
                type: 'line',
                yAxisIndex: 1,
                data: totals,
                smooth: true,
                lineStyle: { color: '#a78bfa', width: 2 },
                itemStyle: { color: '#a78bfa' }
            }
        ]
    });
}

// ========== 异常猎手 ==========
async function loadAnomalies() {
    const data = await apiGet('/findings');
    if (data.code !== 0) return;

    allFindings = data.data;
    renderAnomalyList(allFindings);
}

function renderAnomalyList(findings) {
    const container = document.getElementById('anomalyList');
    if (!container) return;

    const severityLabels = {
        red: '🔴 严重',
        yellow: '🟡 警告',
        blue: '🔵 关注',
        info: 'ℹ️ 信息'
    };

    container.innerHTML = findings.map(f => `
        <div class="anomaly-item severity-${f.severity}" onclick="showAnomalyDetail(${f.id})">
            <div class="anomaly-top">
                <div class="anomaly-title">
                    <span class="severity-badge ${f.severity}">${severityLabels[f.severity]}</span>
                    ${f.title}
                </div>
                <span class="anomaly-category">${f.category}</span>
            </div>
            <div class="anomaly-description">${f.description}</div>
            <div class="anomaly-evidence">📊 ${f.data_evidence}</div>
            <div class="anomaly-action">
                <span>点击查看AI分析与建议 →</span>
            </div>
        </div>
    `).join('');
}

function initAnomalyFilters() {
    const buttons = document.querySelectorAll('.filter-btn');
    buttons.forEach(btn => {
        btn.addEventListener('click', () => {
            buttons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            const severity = btn.dataset.severity;
            if (severity === 'all') {
                renderAnomalyList(allFindings);
            } else {
                renderAnomalyList(allFindings.filter(f => f.severity === severity));
            }
        });
    });
}

async function showAnomalyDetail(id) {
    const finding = allFindings.find(f => f.id === id);
    if (!finding) return;

    const severityLabels = {
        red: '🔴 严重',
        yellow: '🟡 警告',
        blue: '🔵 关注',
        info: 'ℹ️ 信息'
    };

    // 获取AI分析
    const aiData = await apiGet(`/ai/explain/${id}`);
    let aiAnalysis = '';
    if (aiData.code === 0 && aiData.data.ai_analysis) {
        aiAnalysis = aiData.data.ai_analysis;
    }

    document.getElementById('modalTitle').textContent = finding.title;
    document.getElementById('modalBody').innerHTML = `
        <div class="modal-section">
            <div class="modal-section-title">异常级别</div>
            <span class="severity-badge ${finding.severity}">${severityLabels[finding.severity]}</span>
            <span style="margin-left: 12px; color: #9ca3b4; font-size: 13px;">分类: ${finding.category}</span>
        </div>
        <div class="modal-section">
            <div class="modal-section-title">问题描述</div>
            <p>${finding.description}</p>
        </div>
        <div class="modal-section">
            <div class="modal-section-title">数据证据</div>
            <div class="modal-evidence">${finding.data_evidence}</div>
        </div>
        <div class="modal-section">
            <div class="modal-section-title">AI分析与建议</div>
            <div class="modal-ai-analysis">
                <p style="white-space: pre-wrap;">${aiAnalysis || 'AI分析生成中...'}</p>
            </div>
        </div>
        <div class="modal-section">
            <div class="modal-section-title">建议行动</div>
            <p>${finding.recommendation}</p>
        </div>
    `;

    document.getElementById('anomalyModal').classList.add('active');
}

function closeModal() {
    document.getElementById('anomalyModal').classList.remove('active');
}

// 点击弹窗外部关闭
document.addEventListener('click', (e) => {
    const modal = document.getElementById('anomalyModal');
    if (e.target === modal) closeModal();
});

// ========== 岗位化日报 ==========
function initRoleSelector() {
    const buttons = document.querySelectorAll('.role-btn');
    buttons.forEach(btn => {
        btn.addEventListener('click', () => {
            buttons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentRole = btn.dataset.role;
            loadReport(currentRole);
        });
    });
}

async function loadReport(role) {
    const data = await apiGet(`/ai/report/${role}`);
    if (data.code !== 0) return;

    const report = data.data;
    const container = document.getElementById('reportContent');

    let html = `
        <div class="report-section">
            <div class="report-section-title">📅 ${report.role}日报 · ${report.date}</div>
        </div>
    `;

    if (role === 'management') {
        html += `
            <div class="report-section">
                <div class="report-section-title">🎯 核心洞察</div>
                <ul class="report-list">
                    ${report.core_insights.map(i => `<li>${i}</li>`).join('')}
                </ul>
            </div>
            <div class="report-section">
                <div class="report-section-title">⚠️ 风险提示</div>
                ${report.risk_alerts.map(r => `<div class="risk-item">${r}</div>`).join('')}
            </div>
            <div class="report-section">
                <div class="report-section-title">💡 机会点</div>
                ${report.opportunities.map(o => `<div class="opportunity-item">${o}</div>`).join('')}
            </div>
        `;
    } else if (role === 'sales') {
        html += `
            <div class="report-section">
                <div class="report-section-title">🏆 品牌收入排行</div>
                <table class="report-table">
                    <tr><th>品牌</th><th>收入(元)</th><th>占比</th><th>毛利率</th></tr>
                    ${report.brand_ranking.map(b => `
                        <tr>
                            <td><strong>${b.brand}</strong></td>
                            <td>${(b.income / 1e8).toFixed(2)}亿</td>
                            <td>${(b.share * 100).toFixed(1)}%</td>
                            <td>${(b.margin * 100).toFixed(2)}%</td>
                        </tr>
                    `).join('')}
                </table>
            </div>
            <div class="report-section">
                <div class="report-section-title">🛒 平台收入排行</div>
                <table class="report-table">
                    <tr><th>平台</th><th>收入(元)</th><th>占比</th><th>毛利率</th></tr>
                    ${report.platform_ranking.map(p => `
                        <tr>
                            <td><strong>${p.platform}</strong></td>
                            <td>${(p.income / 1e8).toFixed(2)}亿</td>
                            <td>${(p.share * 100).toFixed(1)}%</td>
                            <td>${(p.margin * 100).toFixed(2)}%</td>
                        </tr>
                    `).join('')}
                </table>
            </div>
            <div class="report-section">
                <div class="report-section-title">👀 关键观察</div>
                <ul class="report-list">
                    ${report.key_observations.map(o => `<li>${o}</li>`).join('')}
                </ul>
            </div>
            <div class="report-section">
                <div class="report-section-title">✅ 行动项</div>
                <ul class="report-list">
                    ${report.action_items.map(a => `<li>${a}</li>`).join('')}
                </ul>
            </div>
        `;
    } else if (role === 'operations') {
        html += `
            <div class="report-section">
                <div class="report-section-title">🚨 异常预警</div>
                ${report.anomaly_alerts.map(a => `
                    <div class="risk-item" style="border-left-color: ${a.level === 'red' ? '#f87171' : '#fbbf24'}">
                        <strong>${a.title}</strong><br/>
                        <span style="font-size: 12px; opacity: 0.8;">${a.description}</span>
                    </div>
                `).join('')}
            </div>
            <div class="report-section">
                <div class="report-section-title">📦 退货率分析</div>
                <ul class="report-list">
                    <li>整体退货率: <strong>${(report.return_rate_analysis.overall * 100).toFixed(2)}%</strong></li>
                    <li>最高平台: <strong>${report.return_rate_analysis.highest_platform}</strong></li>
                    <li>最低平台: <strong>${report.return_rate_analysis.lowest_platform}</strong></li>
                    <li>最高品牌: <strong>${report.return_rate_analysis.highest_brand}</strong></li>
                </ul>
            </div>
            <div class="report-section">
                <div class="report-section-title">📊 订单状态概览</div>
                <ul class="report-list">
                    <li>订单总数: <strong>${report.order_status.total_orders.toLocaleString()}</strong></li>
                    <li>成交订单: <strong>${report.order_status.dealt_orders.toLocaleString()}</strong></li>
                    <li>成交率: <strong>${(report.order_status.deal_rate * 100).toFixed(1)}%</strong></li>
                    <li>成交金额: <strong>${(report.order_status.deal_amount / 1e4).toFixed(0)}万元</strong></li>
                </ul>
            </div>
            <div class="report-section">
                <div class="report-section-title">✅ 行动项</div>
                <ul class="report-list">
                    ${report.action_items.map(a => `<li>${a}</li>`).join('')}
                </ul>
            </div>
        `;
    } else if (role === 'finance') {
        html += `
            <div class="report-section">
                <div class="report-section-title">💰 利润率分析</div>
                <ul class="report-list">
                    <li>进销毛利率: <strong>${(report.profit_analysis.cogs_margin * 100).toFixed(2)}%</strong></li>
                    <li>客户毛利率: <strong>${(report.profit_analysis.cust_margin * 100).toFixed(2)}%</strong></li>
                    <li>最高毛利平台: <strong>${report.profit_analysis.highest_margin_platform}</strong></li>
                    <li>最低毛利平台: <strong style="color: #f87171;">${report.profit_analysis.lowest_margin_platform}</strong></li>
                    <li>月度趋势: ${report.profit_analysis.monthly_trend}</li>
                </ul>
            </div>
            <div class="report-section">
                <div class="report-section-title">💳 账期分布</div>
                <ul class="report-list">
                    <li>T+1: <strong>${report.payment_terms['T+1']}</strong></li>
                    <li>T+3: <strong>${report.payment_terms['T+3']}</strong></li>
                    <li>现款: <strong>${report.payment_terms['现款']}</strong></li>
                </ul>
            </div>
            <div class="report-section">
                <div class="report-section-title">🔒 资金占用</div>
                <div class="modal-evidence" style="margin-bottom: 10px;">${report.capital_occupation.note}</div>
                <p style="color: #34d399;">💡 ${report.capital_occupation.action}</p>
            </div>
            <div class="report-section">
                <div class="report-section-title">⚠️ 风险提示</div>
                ${report.risk_alerts.map(r => `<div class="risk-item">${r}</div>`).join('')}
            </div>
        `;
    }

    container.innerHTML = html;
}

// ========== 自然语言查数 ==========
function initQuery() {
    const input = document.getElementById('queryInput');
    const sendBtn = document.getElementById('querySendBtn');

    sendBtn.addEventListener('click', sendQuery);
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendQuery();
    });

    // 建议问题点击
    document.querySelectorAll('.suggestion-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            input.value = btn.dataset.question;
            sendQuery();
        });
    });
}

async function sendQuery() {
    const input = document.getElementById('queryInput');
    const question = input.value.trim();
    if (!question) return;

    const sendBtn = document.getElementById('querySendBtn');
    sendBtn.disabled = true;
    sendBtn.textContent = '分析中...';

    // 添加用户消息
    addChatMessage('user', question);
    input.value = '';

    // 调用API
    const data = await apiPost('/ai/query', { question });

    if (data.code === 0) {
        const result = data.data;
        let answer = result.answer || '无法生成回答';
        let source = result.data_source || '未知';
        let confidence = result.confidence || 0;

        let html = answer;
        html += `<div class="data-source">
            📊 数据来源: ${source}
            <span class="confidence">置信度: ${(confidence * 100).toFixed(0)}%</span>
        </div>`;

        addChatMessage('ai', html);
    } else {
        addChatMessage('ai', '抱歉，分析失败，请稍后重试。');
    }

    sendBtn.disabled = false;
    sendBtn.textContent = '发送';
}

function addChatMessage(role, content) {
    const container = document.getElementById('chatContainer');
    const message = document.createElement('div');
    message.className = `chat-message ${role}`;

    const avatar = document.createElement('div');
    avatar.className = 'chat-avatar';
    avatar.textContent = role === 'ai' ? 'AI' : '我';

    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble';
    bubble.innerHTML = content;

    message.appendChild(avatar);
    message.appendChild(bubble);
    container.appendChild(message);
    container.scrollTop = container.scrollHeight;
}

// ========== 窗口大小变化时重绘图表 ==========
window.addEventListener('resize', () => {
    Object.values(charts).forEach(chart => chart && chart.resize());
});
