"""
双色球智能分析系统 - Web版
============================
提供历史数据查询、分析、更新和预测功能的可视化界面。
"""
import os
import sys
from datetime import datetime

from flask import Flask, render_template_string, request, jsonify, make_response

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ssq_analyzer import SSQAnalyzer, RED_BALLS, BLUE_BALLS
from ssq_updater import SSQUpdater

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

DATA_FILE = "ssq_history.csv"

_analyzer_cache = None
_cache_time = 0


def get_analyzer(force_reload=False):
    """获取分析器实例，支持缓存机制。"""
    global _analyzer_cache, _cache_time
    now = datetime.now().timestamp()
    
    if force_reload or _analyzer_cache is None or (now - _cache_time) > 60:
        _analyzer_cache = SSQAnalyzer(DATA_FILE)
        _cache_time = now
    
    return _analyzer_cache


def get_updater():
    return SSQUpdater(DATA_FILE)


def json_response(data):
    """创建带有防缓存头的JSON响应。"""
    resp = make_response(jsonify(data))
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>双色球数据分析系统</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background: #f5f5f5; min-height: 100vh; color: #333; }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        .header { text-align: center; margin-bottom: 30px; padding: 20px; background: white; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
        .header h1 { font-size: 2rem; color: #333; margin-bottom: 8px; font-weight: 600; }
        .header p { font-size: 1rem; color: #666; }
        .stats-bar { display: flex; justify-content: center; gap: 15px; margin-bottom: 25px; flex-wrap: wrap; }
        .stat-card { background: white; padding: 12px 25px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); text-align: center; border-left: 4px solid #e74c3c; }
        .stat-card:nth-child(2) { border-left-color: #3498db; }
        .stat-card:nth-child(3) { border-left-color: #2ecc71; }
        .stat-card .label { font-size: 0.85rem; color: #888; margin-bottom: 4px; }
        .stat-card .value { font-size: 1.5rem; font-weight: 600; color: #333; }
        .tabs { display: flex; justify-content: center; gap: 8px; margin-bottom: 25px; flex-wrap: wrap; }
        .tab { background: white; border: 1px solid #ddd; padding: 10px 22px; border-radius: 6px; cursor: pointer; font-size: 0.95rem; transition: all 0.2s; color: #666; }
        .tab:hover { background: #f8f9fa; border-color: #ccc; }
        .tab.active { background: #e74c3c; color: white; border-color: #e74c3c; }
        .content { background: white; border-radius: 12px; box-shadow: 0 2px 15px rgba(0,0,0,0.05); padding: 25px; min-height: 500px; }
        .section { display: none; }
        .section.active { display: block; }
        .btn { background: #e74c3c; color: white; border: none; padding: 10px 25px; border-radius: 6px; cursor: pointer; font-size: 0.95rem; font-weight: 500; transition: all 0.2s; display: inline-flex; align-items: center; gap: 6px; }
        .btn:hover { background: #c0392b; }
        .btn-secondary { background: #f0f0f0; color: #333; border: 1px solid #ddd; }
        .btn-secondary:hover { background: #e8e8e8; }
        .btn-group { display: flex; gap: 8px; margin-bottom: 18px; flex-wrap: wrap; }
        .ball-grid { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 18px; }
        .ball { width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 1rem; color: white; }
        .ball.red { background: #e74c3c; }
        .ball.blue { background: #3498db; }
        .ball.small { width: 30px; height: 30px; font-size: 0.8rem; }
        .ball.tiny { width: 22px; height: 22px; font-size: 0.65rem; }
        .ball.active { box-shadow: 0 0 0 3px rgba(231, 76, 60, 0.3); }
        .ball.blue.active { box-shadow: 0 0 0 3px rgba(52, 152, 219, 0.3); }
        .ball.inactive { background: #e0e0e0; color: #999; }
        .prediction-section { background: #fafafa; padding: 18px; border-radius: 8px; margin-bottom: 18px; }
        .prediction-title { font-size: 1.15rem; font-weight: 600; color: #333; margin-bottom: 12px; }
        .feature-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-top: 15px; }
        .feature-card { background: #fff; padding: 12px; border-radius: 6px; border-left: 3px solid #e74c3c; }
        .feature-card .title { font-size: 0.85rem; color: #888; margin-bottom: 4px; }
        .feature-card .value { font-size: 1.2rem; font-weight: 600; color: #333; }
        .table-container { overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 0.85rem; }
        th, td { padding: 8px 10px; text-align: center; border-bottom: 1px solid #eee; }
        th { background: #f8f9fa; font-weight: 600; color: #666; font-size: 0.8rem; }
        tr:hover { background: #fafafa; }
        .search-box { display: flex; gap: 8px; margin-bottom: 15px; flex-wrap: wrap; }
        .search-box input { flex: 1; min-width: 180px; padding: 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 0.95rem; }
        .search-box input:focus { outline: none; border-color: #e74c3c; }
        .analysis-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 15px; margin-top: 15px; }
        .analysis-card { background: #fafafa; padding: 15px; border-radius: 8px; }
        .analysis-card h3 { font-size: 1rem; margin-bottom: 12px; color: #333; font-weight: 600; }
        .analysis-list { list-style: none; }
        .analysis-list li { padding: 6px 0; border-bottom: 1px solid #e8e8e8; display: flex; justify-content: space-between; align-items: center; }
        .analysis-list li:last-child { border-bottom: none; }
        .analysis-list .name { font-weight: 500; }
        .analysis-list .count { font-weight: 600; }
        .omission-high { color: #e74c3c; }
        .omission-medium { color: #f39c12; }
        .frequency-high { color: #2ecc71; }
        .frequency-medium { color: #3498db; }
        .frequency-low { color: #95a5a6; }
        .log-area { background: #2c3e50; color: #ecf0f1; padding: 15px; border-radius: 6px; font-family: 'Courier New', monospace; font-size: 0.85rem; height: 180px; overflow-y: auto; margin-top: 15px; }
        .log-area .error { color: #e74c3c; }
        .log-area .warning { color: #f39c12; }
        .log-area .success { color: #2ecc71; }
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); justify-content: center; align-items: center; z-index: 1000; }
        .modal.active { display: flex; }
        .modal-content { background: white; padding: 25px; border-radius: 12px; max-width: 450px; width: 90%; text-align: center; }
        .modal-content h3 { margin-bottom: 15px; color: #333; }
        .modal-content p { margin-bottom: 15px; color: #666; }
        .loading { display: inline-block; width: 18px; height: 18px; border: 2px solid #fff; border-top-color: transparent; border-radius: 50%; animation: spin 0.8s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
        .btn .loading { margin-right: 4px; }
        .history-grid { display: flex; gap: 10px; margin-bottom: 15px; }
        .history-grid .red-grid { flex: 1; }
        .history-grid .blue-grid { width: 200px; }
        .number-grid { display: grid; grid-template-columns: repeat(11, 1fr); gap: 4px; }
        .blue-grid .number-grid { grid-template-columns: repeat(4, 1fr); }
        .number-grid .ball { width: 100%; padding: 6px 0; font-size: 0.85rem; border-radius: 4px; }
        .history-info { margin-bottom: 15px; padding: 10px; background: #fafafa; border-radius: 6px; }
        .history-info span { margin-right: 20px; font-size: 0.95rem; }
        .history-info .period { font-weight: 600; color: #e74c3c; }
        .history-info .date { color: #666; }
        .pagination { display: flex; justify-content: center; gap: 5px; margin-top: 15px; flex-wrap: wrap; }
        .pagination button { padding: 6px 12px; border: 1px solid #ddd; background: white; border-radius: 4px; cursor: pointer; font-size: 0.85rem; }
        .pagination button:hover { background: #f8f9fa; }
        .pagination button.active { background: #e74c3c; color: white; border-color: #e74c3c; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>双色球数据分析系统</h1>
            <p>历史数据查询与统计分析</p>
        </div>
        
        <div class="stats-bar" id="statsBar">
            <div class="stat-card">
                <div class="label">数据总量</div>
                <div class="value" id="totalCount">--</div>
            </div>
            <div class="stat-card">
                <div class="label">最新期号</div>
                <div class="value" id="latestPeriod">--</div>
            </div>
            <div class="stat-card">
                <div class="label">最近更新</div>
                <div class="value" id="lastUpdate">--</div>
            </div>
        </div>

        <div class="tabs">
            <button class="tab active" onclick="showTab('predict')">号码预测</button>
            <button class="tab" onclick="showTab('history')">历史数据</button>
            <button class="tab" onclick="showTab('analysis')">数据分析</button>
            <button class="tab" onclick="showTab('update')">数据更新</button>
        </div>

        <div class="content">
            <div class="section active" id="predict">
                <div class="btn-group">
                    <button class="btn" onclick="doPredict()">
                        <span class="loading" id="predictLoading" style="display:none;"></span>
                        生成预测
                    </button>
                    <button class="btn btn-secondary" onclick="refreshData()">
                        刷新数据
                    </button>
                </div>
                
                <div id="predictionResult"></div>
                
                <div id="customPredictSection" style="margin-top:30px;">
                    <h3 style="font-size:1.15rem;color:#333;margin-bottom:20px;">动态预测</h3>
                    <p style="font-size:0.85rem;color:#666;margin-bottom:15px;">拖动下方滑动条调整算法参数，实时查看预测结果变化</p>
                    
                    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:15px;margin-bottom:20px;">
                        <div>
                            <label style="display:block;font-size:0.85rem;color:#555;margin-bottom:5px;">热号权重: <span id="hotVal">1.0</span></label>
                            <input type="range" id="hotSlider" min="0" max="3" step="0.1" value="1.0" oninput="updateSliderVal('hot', this.value); doCustomPredict()">
                            <div style="font-size:0.75rem;color:#999;margin-top:3px;">0=不考虑热号, 3=强热号偏好</div>
                        </div>
                        <div>
                            <label style="display:block;font-size:0.85rem;color:#555;margin-bottom:5px;">冷号权重: <span id="coldVal">1.0</span></label>
                            <input type="range" id="coldSlider" min="0" max="3" step="0.1" value="1.0" oninput="updateSliderVal('cold', this.value); doCustomPredict()">
                            <div style="font-size:0.75rem;color:#999;margin-top:3px;">0=不考虑冷号, 3=强冷号偏好</div>
                        </div>
                        <div>
                            <label style="display:block;font-size:0.85rem;color:#555;margin-bottom:5px;">遗漏值权重: <span id="omissionVal">1.0</span></label>
                            <input type="range" id="omissionSlider" min="0" max="3" step="0.1" value="1.0" oninput="updateSliderVal('omission', this.value); doCustomPredict()">
                            <div style="font-size:0.75rem;color:#999;margin-top:3px;">0=不考虑遗漏, 3=强遗漏偏好</div>
                        </div>
                        <div>
                            <label style="display:block;font-size:0.85rem;color:#555;margin-bottom:5px;">区间均衡权重: <span id="intervalVal">1.0</span></label>
                            <input type="range" id="intervalSlider" min="0" max="2" step="0.1" value="1.0" oninput="updateSliderVal('interval', this.value); doCustomPredict()">
                            <div style="font-size:0.75rem;color:#999;margin-top:3px;">0=随机区间, 2=严格均衡</div>
                        </div>
                        <div>
                            <label style="display:block;font-size:0.85rem;color:#555;margin-bottom:5px;">奇偶均衡权重: <span id="parityVal">1.0</span></label>
                            <input type="range" id="paritySlider" min="0" max="2" step="0.1" value="1.0" oninput="updateSliderVal('parity', this.value); doCustomPredict()">
                            <div style="font-size:0.75rem;color:#999;margin-top:3px;">0=随机奇偶, 2=严格均衡</div>
                        </div>
                        <div>
                            <label style="display:block;font-size:0.85rem;color:#555;margin-bottom:5px;">大小均衡权重: <span id="sizeVal">1.0</span></label>
                            <input type="range" id="sizeSlider" min="0" max="2" step="0.1" value="1.0" oninput="updateSliderVal('size', this.value); doCustomPredict()">
                            <div style="font-size:0.75rem;color:#999;margin-top:3px;">0=随机大小, 2=严格均衡</div>
                        </div>
                    </div>
                    
                    <button class="btn btn-secondary" onclick="resetSliders()">重置参数</button>
                    <button class="btn" onclick="doCustomPredict()">应用参数</button>
                    
                    <div id="customResult" style="margin-top:20px;"></div>
                </div>
            </div>

            <div class="section" id="history">
                <div class="search-box">
                    <input type="text" id="searchPeriod" placeholder="搜索期号（如2026068）" onkeyup="if(event.key==='Enter') searchHistory()">
                    <button class="btn" onclick="searchHistory()">搜索</button>
                    <button class="btn btn-secondary" onclick="clearSearch()">清空</button>
                </div>
                <div class="btn-group">
                    <button class="btn btn-secondary" onclick="showHistory(10)">最近10期</button>
                    <button class="btn btn-secondary" onclick="showHistory(20)">最近20期</button>
                    <button class="btn btn-secondary" onclick="showHistory(50)">最近50期</button>
                    <button class="btn btn-secondary" onclick="showHistory(0)">全部数据</button>
                </div>
                <div id="historyContent"></div>
            </div>

            <div class="section" id="analysis">
                <div class="btn-group">
                    <button class="btn" onclick="loadAnalysis()">
                        <span class="loading" id="analysisLoading" style="display:none;"></span>
                        加载分析数据
                    </button>
                </div>
                
                <div id="analysisContent"></div>
            </div>

            <div class="section" id="update">
                <div class="btn-group">
                    <button class="btn" onclick="checkUpdate()">
                        <span class="loading" id="checkLoading" style="display:none;"></span>
                        检查更新
                    </button>
                    <button class="btn" onclick="doUpdate()">
                        <span class="loading" id="updateLoading" style="display:none;"></span>
                        执行更新
                    </button>
                    <button class="btn btn-secondary" onclick="forceUpdate()">
                        <span class="loading" id="forceLoading" style="display:none;"></span>
                        强制更新
                    </button>
                </div>
                
                <div class="log-area" id="updateLog">
                    <div class="success">系统就绪，点击按钮检查或更新数据...</div>
                </div>
            </div>
        </div>
    </div>

    <div class="modal" id="confirmModal">
        <div class="modal-content">
            <h3>确认操作</h3>
            <p id="confirmMessage">确定要执行此操作吗？</p>
            <div class="btn-group" style="justify-content: center;">
                <button class="btn btn-secondary" onclick="closeModal()">取消</button>
                <button class="btn" onclick="confirmAction()">确定</button>
            </div>
        </div>
    </div>

    <script>
        function showTab(tabName) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById(tabName).classList.add('active');
            
            if (tabName === 'predict') loadPrediction();
            if (tabName === 'history') showHistory(10);
            if (tabName === 'analysis') loadAnalysis();
            refreshStats();
        }

        function refreshStats() {
            fetch('/api/stats')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('totalCount').textContent = data.total;
                    document.getElementById('latestPeriod').textContent = data.latest_period;
                    document.getElementById('lastUpdate').textContent = data.last_update;
                })
                .catch(e => console.error(e));
        }

        function loadPrediction() {
            fetch('/api/predict?' + Date.now())
                .then(r => r.json())
                .then(data => {
                    if (!data.success) {
                        document.getElementById('predictionResult').innerHTML = 
                            '<div style="text-align:center;color:#e74c3c;padding:50px;">' + data.message + '</div>';
                        return;
                    }
                    
                    function buildPredictionSection(pred) {
                        let redBalls = pred.red_balls.map(b => 
                            `<span class="ball red">${b.toString().padStart(2, '0')}</span>`
                        ).join('');
                        let blueBalls = `<span class="ball blue">${pred.blue_ball.toString().padStart(2, '0')}</span>`;
                        let blueOptions = pred.blue_options.slice(1).map(b => 
                            `<span class="ball blue small">${b.toString().padStart(2, '0')}</span>`
                        ).join('');
                        let features = pred.features;
                        
                        let featureHtml = `
                            <div class="feature-grid">
                                <div class="feature-card">
                                    <div class="title">奇偶分布</div>
                                    <div class="value">${features.parity}</div>
                                </div>
                                <div class="feature-card">
                                    <div class="title">大小分布</div>
                                    <div class="value">${features.size}</div>
                                </div>
                                <div class="feature-card">
                                    <div class="title">区间分布</div>
                                    <div class="value">${features.interval}</div>
                                </div>
                            </div>
                        `;
                        
                        return `
                            <div class="prediction-section" style="margin-bottom:20px;">
                                <div class="prediction-title">${pred.name}</div>
                                <div style="font-size:0.85rem;color:#666;margin-bottom:10px;">${pred.description}</div>
                                <div style="margin-bottom:15px;">
                                    <strong>预测红球：</strong>
                                    <div class="ball-grid">${redBalls}</div>
                                </div>
                                <div>
                                    <strong>预测蓝球：</strong>
                                    <div class="ball-grid" style="margin-bottom:8px;">${blueBalls}</div>
                                    <div style="font-size:0.85rem;color:#666;">
                                        备选蓝球：<div style="display:flex;gap:6px;display:inline-flex;">${blueOptions}</div>
                                    </div>
                                </div>
                                ${featureHtml}
                            </div>
                        `;
                    }
                    
                    document.getElementById('predictionResult').innerHTML = `
                        ${buildPredictionSection(data.prediction_a)}
                        ${buildPredictionSection(data.prediction_b)}
                        
                        <div style="background:#fff3cd;border:1px solid #ffeeba;border-radius:8px;padding:15px;margin-bottom:20px;">
                            <div style="font-size:0.9rem;color:#856404;">
                                <strong>两组预测对比：</strong>红球重叠 ${data.overlap} 个（共6个）
                            </div>
                        </div>
                        
                        <div style="background:#f8f9fa;padding:20px;border-radius:8px;margin-top:20px;">
                            <h3 style="font-size:1.15rem;margin-bottom:15px;color:#333;">预测原理</h3>
                            
                            <div style="margin-bottom:15px;">
                                <h4 style="font-size:1rem;margin-bottom:10px;color:#e74c3c;">算法A：频率统计均衡法</h4>
                                <div style="font-size:0.85rem;color:#666;line-height:1.8;">
                                    <p><strong>核心策略：</strong>采用行业通用的3热+2温+1冷配比原则，结合区间、奇偶、大小均衡筛选，避免极端组合。</p>
                                    <p><strong>冷热温判定标准：</strong></p>
                                    <ul>
                                        <li>热号：近10期出现≥4次，短期高频开出</li>
                                        <li>温号：近10期出现2-3次，冷热过渡均衡</li>
                                        <li>冷号：近10期出现≤1次，长期遗漏未开出</li>
                                    </ul>
                                    <p><strong>配比原则：</strong>3热+2温+1冷（占比约68%），兼顾短期活跃号码与长期遗漏回补。</p>
                                    <p><strong>平衡调整：</strong>确保区间2:2:2或3:2:1、奇偶3:3、大小3:3的均衡形态。</p>
                                </div>
                            </div>
                            
                            <div style="margin-bottom:15px;">
                                <h4 style="font-size:1rem;margin-bottom:10px;color:#3498db;">算法B：多维指标共振法</h4>
                                <div style="font-size:0.85rem;color:#666;line-height:1.8;">
                                    <p><strong>核心策略：</strong>采用余数分类法、尾数关联法、区间回补法等多维度交叉验证。</p>
                                    <p><strong>余数分类法：</strong>按除3余数分为余0、余1、余2三类，每类理论占比约33%，若某类连续偏少则重点关注。</p>
                                    <p><strong>尾数关联法：</strong>统计近5期尾数分布，若某尾数连续未出现则纳入候选。</p>
                                    <p><strong>区间回补法：</strong>若某区间连续3期出号偏少，下期适当增加该区间号码。</p>
                                    <p><strong>多维共振：</strong>当某号码同时满足多个条件时，出现概率显著提升。</p>
                                </div>
                            </div>
                            
                            <div style="margin-top:15px;padding-top:15px;border-top:1px dashed #ddd;font-size:0.8rem;color:#999;text-align:center;">
                                * 彩票开奖结果完全随机，本预测仅供参考，不代表真实开奖结果
                            </div>
                        </div>
                    `;
                });
        }

        function doPredict() {
            let loading = document.getElementById('predictLoading');
            loading.style.display = 'inline-block';
            loadPrediction();
            setTimeout(() => loading.style.display = 'none', 500);
        }

        function showHistory(limit) {
            let url = limit > 0 ? `/api/history?limit=${limit}` : '/api/history';
            fetch(url)
                .then(r => r.json())
                .then(data => {
                    if (!data.success) {
                        document.getElementById('historyContent').innerHTML = 
                            '<div style="text-align:center;color:#e74c3c;padding:50px;">' + data.message + '</div>';
                        return;
                    }
                    
                    let records = data.records;
                    let html = '';
                    
                    records.forEach((rec, index) => {
                        let redSet = new Set(rec.reds);
                        let redHtml = '';
                        for (let i = 1; i <= 33; i++) {
                            let cls = redSet.has(i) ? 'red' : 'inactive';
                            redHtml += `<div class="ball ${cls} tiny">${i.toString().padStart(2, '0')}</div>`;
                        }
                        
                        let blueHtml = '';
                        for (let i = 1; i <= 16; i++) {
                            let cls = i === rec.blue ? 'blue' : 'inactive';
                            blueHtml += `<div class="ball ${cls} tiny">${i.toString().padStart(2, '0')}</div>`;
                        }
                        
                        html += `
                            <div class="history-info">
                                <span class="period">期号: ${rec.period}</span>
                                <span class="date">日期: ${rec.date}</span>
                                <span>红球: ${rec.reds.map(r => r.toString().padStart(2, '0')).join(', ')}</span>
                                <span>蓝球: ${rec.blue.toString().padStart(2, '0')}</span>
                            </div>
                            <div style="display:flex;gap:20px;margin-bottom:15px;">
                                <div>
                                    <div style="font-size:0.8rem;color:#666;margin-bottom:3px;">红球 (1-33)</div>
                                    <div style="display:flex;gap:1px;flex-wrap:wrap;">${redHtml}</div>
                                </div>
                                <div>
                                    <div style="font-size:0.8rem;color:#666;margin-bottom:3px;">蓝球 (1-16)</div>
                                    <div style="display:flex;gap:1px;">${blueHtml}</div>
                                </div>
                            </div>
                            ${index < records.length - 1 ? '<hr style="border:none;border-top:1px dashed #ddd;margin:15px 0;">' : ''}
                        `;
                    });

                    document.getElementById('historyContent').innerHTML = html;
                });
        }

        function searchHistory() {
            let keyword = document.getElementById('searchPeriod').value.trim();
            if (!keyword) return showHistory(10);
            
            fetch(`/api/search?keyword=${keyword}`)
                .then(r => r.json())
                .then(data => {
                    if (!data.success || data.records.length === 0) {
                        document.getElementById('historyContent').innerHTML = 
                            '<div style="text-align:center;color:#e74c3c;padding:50px;">未找到匹配的数据</div>';
                        return;
                    }
                    
                    let records = data.records;
                    let html = '';
                    
                    records.forEach((rec, index) => {
                        let redSet = new Set(rec.reds);
                        let redHtml = '';
                        for (let i = 1; i <= 33; i++) {
                            let cls = redSet.has(i) ? 'red' : 'inactive';
                            redHtml += `<div class="ball ${cls} tiny">${i.toString().padStart(2, '0')}</div>`;
                        }
                        
                        let blueHtml = '';
                        for (let i = 1; i <= 16; i++) {
                            let cls = i === rec.blue ? 'blue' : 'inactive';
                            blueHtml += `<div class="ball ${cls} tiny">${i.toString().padStart(2, '0')}</div>`;
                        }
                        
                        html += `
                            <div class="history-info">
                                <span class="period">期号: ${rec.period}</span>
                                <span class="date">日期: ${rec.date}</span>
                                <span>红球: ${rec.reds.map(r => r.toString().padStart(2, '0')).join(', ')}</span>
                                <span>蓝球: ${rec.blue.toString().padStart(2, '0')}</span>
                            </div>
                            <div style="display:flex;gap:20px;margin-bottom:15px;">
                                <div>
                                    <div style="font-size:0.8rem;color:#666;margin-bottom:3px;">红球 (1-33)</div>
                                    <div style="display:flex;gap:1px;flex-wrap:wrap;">${redHtml}</div>
                                </div>
                                <div>
                                    <div style="font-size:0.8rem;color:#666;margin-bottom:3px;">蓝球 (1-16)</div>
                                    <div style="display:flex;gap:1px;">${blueHtml}</div>
                                </div>
                            </div>
                            ${index < records.length - 1 ? '<hr style="border:none;border-top:1px dashed #ddd;margin:15px 0;">' : ''}
                        `;
                    });

                    document.getElementById('historyContent').innerHTML = html;
                });
        }

        function clearSearch() {
            document.getElementById('searchPeriod').value = '';
            showHistory(10);
        }

        function loadAnalysis() {
            let loading = document.getElementById('analysisLoading');
            loading.style.display = 'inline-block';
            
            fetch('/api/analysis')
                .then(r => r.json())
                .then(data => {
                    loading.style.display = 'none';
                    
                    if (!data.success) {
                        document.getElementById('analysisContent').innerHTML = 
                            '<div style="text-align:center;color:#e74c3c;padding:50px;">' + data.message + '</div>';
                        return;
                    }

                    let hotReds = data.hot_reds.map((b, i) => 
                        `<li><span class="name">红球${b.toString().padStart(2, '0')}</span><span class="count frequency-high">${i + 1}位</span></li>`
                    ).join('');
                    
                    let coldReds = data.cold_reds.map((b, i) => 
                        `<li><span class="name">红球${b.toString().padStart(2, '0')}</span><span class="count frequency-low">${i + 1}位</span></li>`
                    ).join('');
                    
                    let highOmissionReds = data.high_omission_reds.map((b, i) => 
                        `<li><span class="name">红球${b.toString().padStart(2, '0')}</span><span class="count omission-high">遗漏${data.red_omission[b]}期</span></li>`
                    ).join('');
                    
                    let hotBlues = data.hot_blues.map((b, i) => 
                        `<li><span class="name">蓝球${b.toString().padStart(2, '0')}</span><span class="count frequency-high">${i + 1}位</span></li>`
                    ).join('');
                    
                    let coldBlues = data.cold_blues.map((b, i) => 
                        `<li><span class="name">蓝球${b.toString().padStart(2, '0')}</span><span class="count frequency-low">${i + 1}位</span></li>`
                    ).join('');

                    let highOmissionBlues = data.high_omission_blues.map((b, i) => 
                        `<li><span class="name">蓝球${b.toString().padStart(2, '0')}</span><span class="count omission-high">遗漏${data.blue_omission[b]}期</span></li>`
                    ).join('');

                    let intervalHtml = Object.entries(data.interval).map(([name, stats]) => `
                        <div class="analysis-card">
                            <h3>${name} (${stats.range})</h3>
                            <div class="analysis-list">
                                <li><span class="name">平均每期</span><span class="count">${stats.avg}</span></li>
                                <li><span class="name">出现最多</span><span class="count">${stats.mode}</span></li>
                                <li><span class="name">范围</span><span class="count">${stats.min}-${stats.max}</span></li>
                            </div>
                        </div>
                    `).join('');

                    let parityHtml = `
                        <div class="analysis-card">
                            <h3>奇偶分析</h3>
                            <div class="analysis-list">
                                <li><span class="name">平均奇数</span><span class="count">${data.parity.avg}</span></li>
                                <li><span class="name">众数奇数</span><span class="count">${data.parity.mode}</span></li>
                            </div>
                        </div>
                    `;

                    let sizeHtml = `
                        <div class="analysis-card">
                            <h3>大小分析</h3>
                            <div class="analysis-list">
                                <li><span class="name">平均大数</span><span class="count">${data.size.avg}</span></li>
                                <li><span class="name">众数大数</span><span class="count">${data.size.mode}</span></li>
                            </div>
                        </div>
                    `;

                    document.getElementById('analysisContent').innerHTML = `
                        <div class="analysis-grid">
                            <div class="analysis-card">
                                <h3>红球热号 (频率最高)</h3>
                                <ul class="analysis-list">${hotReds}</ul>
                            </div>
                            <div class="analysis-card">
                                <h3>红球冷号 (频率最低)</h3>
                                <ul class="analysis-list">${coldReds}</ul>
                            </div>
                            <div class="analysis-card">
                                <h3>红球高遗漏 (未出现最久)</h3>
                                <ul class="analysis-list">${highOmissionReds}</ul>
                            </div>
                            <div class="analysis-card">
                                <h3>蓝球热号</h3>
                                <ul class="analysis-list">${hotBlues}</ul>
                            </div>
                            <div class="analysis-card">
                                <h3>蓝球冷号</h3>
                                <ul class="analysis-list">${coldBlues}</ul>
                            </div>
                            <div class="analysis-card">
                                <h3>蓝球高遗漏</h3>
                                <ul class="analysis-list">${highOmissionBlues}</ul>
                            </div>
                        </div>
                        <div class="analysis-grid" style="margin-top:20px;">
                            ${intervalHtml}
                            ${parityHtml}
                            ${sizeHtml}
                        </div>
                    `;
                });
        }

        function appendLog(message, type='info') {
            let logArea = document.getElementById('updateLog');
            let colorClass = type === 'error' ? 'error' : type === 'warning' ? 'warning' : type === 'success' ? 'success' : '';
            let time = new Date().toLocaleTimeString();
            logArea.innerHTML += `<div class="${colorClass}">[${time}] ${message}</div>`;
            logArea.scrollTop = logArea.scrollHeight;
        }

        function checkUpdate() {
            let loading = document.getElementById('checkLoading');
            loading.style.display = 'inline-block';
            appendLog('正在检查数据源...');
            
            fetch('/api/check-update')
                .then(r => r.json())
                .then(data => {
                    loading.style.display = 'none';
                    if (data.count > 0) {
                        appendLog(`发现 ${data.count} 条新数据`, 'warning');
                        data.records.forEach(rec => {
                            appendLog(`${rec.period} (${rec.date}): ${rec.reds.join(',')} + ${rec.blue}`, 'success');
                        });
                    } else {
                        appendLog(data.message, 'success');
                    }
                })
                .catch(e => {
                    loading.style.display = 'none';
                    appendLog('检查失败: ' + e.message, 'error');
                });
        }

        function doUpdate() {
            let loading = document.getElementById('updateLoading');
            loading.style.display = 'inline-block';
            appendLog('正在执行更新...');
            
            fetch('/api/update')
                .then(r => r.json())
                .then(data => {
                    loading.style.display = 'none';
                    appendLog(data.message, data.success ? 'success' : 'error');
                    if (data.success) {
                        appendLog(`更新后数据: ${data.total} 条, 最新期号: ${data.latest}`, 'success');
                        refreshStats();
                    }
                })
                .catch(e => {
                    loading.style.display = 'none';
                    appendLog('更新失败: ' + e.message, 'error');
                });
        }

        let confirmCallback = null;
        function forceUpdate() {
            confirmCallback = () => {
                let loading = document.getElementById('forceLoading');
                loading.style.display = 'inline-block';
                appendLog('正在执行强制更新...');
                
                fetch('/api/update?force=true')
                    .then(r => r.json())
                    .then(data => {
                        loading.style.display = 'none';
                        appendLog(data.message, data.success ? 'success' : 'error');
                        if (data.success) {
                            appendLog(`更新后数据: ${data.total} 条, 最新期号: ${data.latest}`, 'success');
                            refreshStats();
                        }
                    })
                    .catch(e => {
                        loading.style.display = 'none';
                        appendLog('更新失败: ' + e.message, 'error');
                    });
                closeModal();
            };
            
            document.getElementById('confirmMessage').textContent = '确定要强制更新吗？这将覆盖本地所有数据！';
            document.getElementById('confirmModal').classList.add('active');
        }

        function showModal(message, callback) {
            confirmCallback = callback;
            document.getElementById('confirmMessage').textContent = message;
            document.getElementById('confirmModal').classList.add('active');
        }

        function closeModal() {
            document.getElementById('confirmModal').classList.remove('active');
            confirmCallback = null;
        }

        function confirmAction() {
            if (confirmCallback) confirmCallback();
        }

        function updateSliderVal(name, value) {
            document.getElementById(name + 'Val').textContent = parseFloat(value).toFixed(1);
        }
        
        function resetSliders() {
            document.getElementById('hotSlider').value = 1.0;
            document.getElementById('coldSlider').value = 1.0;
            document.getElementById('omissionSlider').value = 1.0;
            document.getElementById('intervalSlider').value = 1.0;
            document.getElementById('paritySlider').value = 1.0;
            document.getElementById('sizeSlider').value = 1.0;
            
            updateSliderVal('hot', 1.0);
            updateSliderVal('cold', 1.0);
            updateSliderVal('omission', 1.0);
            updateSliderVal('interval', 1.0);
            updateSliderVal('parity', 1.0);
            updateSliderVal('size', 1.0);
            
            doCustomPredict();
        }
        
        function doCustomPredict() {
            let hot = parseFloat(document.getElementById('hotSlider').value);
            let cold = parseFloat(document.getElementById('coldSlider').value);
            let omission = parseFloat(document.getElementById('omissionSlider').value);
            let interval = parseFloat(document.getElementById('intervalSlider').value);
            let parity = parseFloat(document.getElementById('paritySlider').value);
            let size = parseFloat(document.getElementById('sizeSlider').value);
            
            let url = `/api/predict-custom?hot=${hot}&cold=${cold}&omission=${omission}&interval=${interval}&parity=${parity}&size=${size}&t=${Date.now()}`;
            
            fetch(url)
                .then(r => r.json())
                .then(data => {
                    if (!data.success) {
                        document.getElementById('customResult').innerHTML = 
                            '<div style="text-align:center;color:#e74c3c;padding:50px;">' + data.message + '</div>';
                        return;
                    }
                    
                    let redBalls = data.red_balls.map(b => 
                        `<span class="ball red">${b.toString().padStart(2, '0')}</span>`
                    ).join('');
                    let blueBall = `<span class="ball blue">${data.blue_ball.toString().padStart(2, '0')}</span>`;
                    let blueOptions = data.blue_options.slice(1).map(b => 
                        `<span class="ball blue small">${b.toString().padStart(2, '0')}</span>`
                    ).join('');
                    let features = data.features;
                    
                    document.getElementById('customResult').innerHTML = `
                        <div class="prediction-section">
                            <div class="prediction-title">自定义预测结果</div>
                            <div style="margin-bottom:10px;">
                                <span style="font-size:0.9rem;color:#666;">预测红球：</span>
                                ${redBalls}
                            </div>
                            <div style="margin-bottom:10px;">
                                <span style="font-size:0.9rem;color:#666;">预测蓝球：</span>
                                ${blueBall}
                            </div>
                            <div style="margin-bottom:15px;">
                                <span style="font-size:0.9rem;color:#666;">备选蓝球：</span>
                                ${blueOptions}
                            </div>
                            <div class="feature-grid">
                                <div class="feature-card">
                                    <div class="title">奇偶分布</div>
                                    <div class="value">${features.parity}</div>
                                </div>
                                <div class="feature-card">
                                    <div class="title">大小分布</div>
                                    <div class="value">${features.size}</div>
                                </div>
                                <div class="feature-card">
                                    <div class="title">区间分布</div>
                                    <div class="value">${features.interval}</div>
                                </div>
                            </div>
                        </div>
                    `;
                })
                .catch(e => {
                    console.error(e);
                });
        }
        
        function refreshData() {
            appendLog('正在刷新数据...', 'success');
            refreshStats();
            loadPrediction();
        }

        window.onload = function() {
            refreshStats();
            loadPrediction();
        };
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/stats')
def api_stats():
    analyzer = get_analyzer()
    if not analyzer.is_ready:
        return json_response({"success": False, "message": "数据加载失败"})
    
    total = len(analyzer.history_data)
    latest = analyzer.history_data[-1]["period"] if analyzer.history_data else None
    
    if os.path.exists(DATA_FILE):
        last_update = datetime.fromtimestamp(os.path.getmtime(DATA_FILE))
        last_update_str = last_update.strftime("%m-%d %H:%M")
    else:
        last_update_str = "未知"
    
    return json_response({
        "success": True,
        "total": total,
        "latest_period": latest,
        "last_update": last_update_str
    })


@app.route('/api/predict')
def api_predict():
    analyzer = get_analyzer()
    if not analyzer.is_ready:
        return json_response({"success": False, "message": "数据加载失败，请检查数据文件"})
    
    red_balls_a = analyzer.predict_red_balls()
    blue_ball_a = analyzer.predict_blue_ball()
    blue_options_a = analyzer.predict_blue_options(5)
    features_a = analyzer.analyze_prediction_features(red_balls_a, blue_ball_a)
    
    red_balls_b = analyzer.predict_red_balls_advanced(exclude_balls=red_balls_a)
    blue_ball_b = analyzer.predict_blue_ball_advanced(exclude_ball=blue_ball_a)
    blue_options_b = analyzer.predict_blue_options(5)
    features_b = analyzer.analyze_prediction_features(red_balls_b, blue_ball_b)
    
    overlap = len(set(red_balls_a) & set(red_balls_b))
    
    return json_response({
        "success": True,
        "prediction_a": {
            "name": "算法A：频率统计均衡法",
            "description": "采用行业通用的3热+2温+1冷配比，结合区间、奇偶、大小均衡筛选，避免极端组合",
            "red_balls": red_balls_a,
            "blue_ball": blue_ball_a,
            "blue_options": blue_options_a,
            "features": features_a
        },
        "prediction_b": {
            "name": "算法B：多维指标共振法",
            "description": "采用余数分类法（除3余数）、尾数关联法、区间回补法等多维度交叉验证，优先选择冷号和高遗漏号码",
            "red_balls": red_balls_b,
            "blue_ball": blue_ball_b,
            "blue_options": blue_options_b,
            "features": features_b
        },
        "overlap": overlap
    })


@app.route('/api/predict-custom')
def api_predict_custom():
    analyzer = get_analyzer()
    if not analyzer.is_ready:
        return json_response({"success": False, "message": "数据加载失败，请检查数据文件"})
    
    hot_weight = request.args.get('hot', type=float, default=1.0)
    cold_weight = request.args.get('cold', type=float, default=1.0)
    omission_weight = request.args.get('omission', type=float, default=1.0)
    interval_weight = request.args.get('interval', type=float, default=1.0)
    parity_weight = request.args.get('parity', type=float, default=1.0)
    size_weight = request.args.get('size', type=float, default=1.0)
    recent_penalty = request.args.get('recent', type=float, default=1.0)
    
    result = analyzer.predict_with_params(
        hot_weight=hot_weight,
        cold_weight=cold_weight,
        omission_weight=omission_weight,
        interval_weight=interval_weight,
        parity_weight=parity_weight,
        size_weight=size_weight,
        recent_penalty=recent_penalty
    )
    
    return json_response({
        "success": True,
        "red_balls": result["red_balls"],
        "blue_ball": result["blue_ball"],
        "blue_options": result["blue_options"],
        "features": result["features"],
        "params": {
            "hot_weight": hot_weight,
            "cold_weight": cold_weight,
            "omission_weight": omission_weight,
            "interval_weight": interval_weight,
            "parity_weight": parity_weight,
            "size_weight": size_weight,
            "recent_penalty": recent_penalty
        }
    })


@app.route('/api/history')
def api_history():
    analyzer = get_analyzer()
    if not analyzer.is_ready:
        return json_response({"success": False, "message": "数据加载失败"})
    
    limit = request.args.get('limit', type=int, default=0)
    records = analyzer.history_data[-limit:] if limit > 0 else analyzer.history_data
    
    return json_response({
        "success": True,
        "records": records
    })


@app.route('/api/search')
def api_search():
    analyzer = get_analyzer()
    if not analyzer.is_ready:
        return json_response({"success": False, "message": "数据加载失败"})
    
    keyword = request.args.get('keyword', '')
    if not keyword:
        return json_response({"success": True, "records": []})
    
    records = [
        rec for rec in analyzer.history_data
        if keyword in rec["period"] or keyword in rec["date"]
    ]
    
    return json_response({
        "success": True,
        "records": records
    })


@app.route('/api/analysis')
def api_analysis():
    analyzer = get_analyzer()
    if not analyzer.is_ready:
        return json_response({"success": False, "message": "数据加载失败"})
    
    interval = analyzer.analyze_interval()
    interval_data = {}
    for name, stats in interval.items():
        lo, hi = {'一区': (1, 11), '二区': (12, 22), '三区': (23, 33)}[name]
        interval_data[name] = {
            "range": f"{lo}-{hi}",
            "avg": stats["平均"],
            "mode": stats["众数"],
            "min": stats["最小"],
            "max": stats["最大"]
        }
    
    parity = analyzer.analyze_parity()
    size = analyzer.analyze_size()
    
    return json_response({
        "success": True,
        "hot_reds": analyzer.get_hot_red_balls(5),
        "cold_reds": analyzer.get_cold_red_balls(5),
        "high_omission_reds": analyzer.get_high_omission_red(5),
        "hot_blues": analyzer.get_hot_blue_balls(3),
        "cold_blues": analyzer.get_cold_blue_balls(3),
        "high_omission_blues": analyzer.get_high_omission_blue(3),
        "red_omission": analyzer.red_omission,
        "blue_omission": analyzer.blue_omission,
        "interval": interval_data,
        "parity": {"avg": parity["平均奇数"], "mode": parity["众数奇数"]},
        "size": {"avg": size["平均大数"], "mode": size["众数大数"]}
    })


@app.route('/api/check-update')
def api_check_update():
    updater = get_updater()
    count, records = updater.check_update()
    
    if count > 0:
        return json_response({
            "success": True,
            "count": count,
            "records": records
        })
    return json_response({
        "success": True,
        "count": 0,
        "message": "本地已是最新"
    })


@app.route('/api/update')
def api_update():
    force = request.args.get('force', 'false').lower() == 'true'
    updater = get_updater()
    
    try:
        count, msg = updater.update(force)
        get_analyzer(force_reload=True)
        return json_response({
            "success": count > 0 or '最新' in msg,
            "message": msg,
            "total": len(updater.local_data),
            "latest": updater.get_local_latest()
        })
    except Exception as e:
        return json_response({
            "success": False,
            "message": str(e)
        })


if __name__ == '__main__':
    print("双色球数据分析系统 - Web版")
    print("=================================")
    print(f"数据文件: {DATA_FILE}")
    print("访问地址: http://127.0.0.1:5000")
    print("按 Ctrl+C 停止服务")
    print("=================================")
    app.run(host='127.0.0.1', port=5000, debug=False)
