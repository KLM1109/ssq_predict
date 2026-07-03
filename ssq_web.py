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
        .container { width: 100%; min-height: 100vh; display: flex; flex-direction: column; }
        .header { display: flex; justify-content: space-between; align-items: center; padding: 15px 25px; background: white; border-bottom: 1px solid #eee; }
        .header-left { display: flex; align-items: center; gap: 15px; }
        .header-left h1 { font-size: 1.5rem; color: #333; font-weight: 600; }
        .header-right { display: flex; gap: 20px; align-items: center; }
        .stat-item { display: flex; flex-direction: column; align-items: flex-end; }
        .stat-item .label { font-size: 0.75rem; color: #888; }
        .stat-item .value { font-size: 1rem; font-weight: 600; color: #333; }
        .stat-item .value.red { color: #e74c3c; }
        .stat-item .value.blue { color: #3498db; }
        .stat-item .value.green { color: #2ecc71; }
        .tabs { display: flex; gap: 0; background: white; border-bottom: 1px solid #eee; }
        .tab { flex: 1; max-width: 150px; background: transparent; border: none; border-bottom: 2px solid transparent; padding: 12px 20px; cursor: pointer; font-size: 0.95rem; transition: all 0.2s; color: #666; }
        .tab:hover { background: #f8f9fa; }
        .tab.active { border-bottom-color: #e74c3c; color: #e74c3c; font-weight: 500; }
        .content { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
        .section { display: none; flex: 1; overflow-y: auto; flex-direction: column; }
        .section.active { display: flex; }
        .section.row-layout { flex-direction: row; }
        .main-content { display: flex; flex: 1; overflow: hidden; }
        .predict-panel { flex: 1; padding: 20px; overflow-y: auto; border-right: 1px solid #eee; }
        .analysis-panel { flex: 1; padding: 20px; overflow-y: auto; }
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
        .feature-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin-top: 12px; }
        .feature-card { background: #fff; padding: 10px; border-radius: 6px; border-left: 3px solid #e74c3c; }
        .feature-card .title { font-size: 0.8rem; color: #888; margin-bottom: 4px; }
        .feature-card .value { font-size: 1.1rem; font-weight: 600; color: #333; }
        .table-container { overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 0.85rem; }
        th, td { padding: 8px 10px; text-align: center; border-bottom: 1px solid #eee; }
        th { background: #f8f9fa; font-weight: 600; color: #666; font-size: 0.8rem; }
        tr:hover { background: #fafafa; }
        .search-box { display: flex; gap: 8px; flex-wrap: wrap; }
        .search-box input { flex: 1; min-width: 180px; padding: 8px 12px; border: 1px solid #ddd; border-radius: 6px; font-size: 0.9rem; }
        .search-box input:focus { outline: none; border-color: #e74c3c; }
        .history-header { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; }
        .history-main { display: flex; gap: 15px; }
        #historyContent { width: 60%; }
        #historyAnalysis { width: 40%; }
        .btn.active { background: #e74c3c; color: white; border-color: #e74c3c; }
        .btn-period-10.active { background: #27ae60; border-color: #27ae60; }
        .btn-period-30.active { background: #3498db; border-color: #3498db; }
        .btn-period-50.active { background: #9b59b6; border-color: #9b59b6; }
        .btn-period-all.active { background: #e74c3c; border-color: #e74c3c; }
        .trend-container { border: 1px solid #ddd; border-radius: 6px; overflow: hidden; }
        .trend-header-row { display: flex; background: #f8f9fa; border-bottom: 1px solid #ddd; }
        .trend-header-row .trend-cell { font-weight: 600; font-size: 0.6rem; color: #666; }
        .trend-row { display: flex; border-bottom: 1px solid #f0f0f0; }
        .trend-row:last-child { border-bottom: none; }
        .trend-period { width: 90px; padding: 6px 8px; text-align: right; font-size: 0.75rem; color: #333; border-right: 1px solid #eee; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .trend-red-area { flex: 33; display: flex; }
        .trend-blue-area { flex: 16; display: flex; border-left: 1px solid #eee; }
        .trend-cell { flex: 1; min-width: 24px; height: 30px; display: flex; align-items: center; justify-content: center; font-size: 0.65rem; border-right: 1px solid #f5f5f5; }
        .trend-cell:last-child { border-right: none; }
        .trend-cell.red { background: #e74c3c; color: white; font-weight: bold; border-radius: 4px; margin: 2px; }
        .trend-cell.blue { background: #3498db; color: white; font-weight: bold; border-radius: 4px; margin: 2px; }
        .trend-stats-container { display: flex; gap: 15px; margin-top: 15px; }
        .trend-stats { flex: 1; padding: 10px; background: #fafafa; border-radius: 6px; }
        .trend-stats h4 { font-size: 0.85rem; margin-bottom: 8px; color: #333; }
        .stats-row { display: flex; align-items: flex-end; gap: 1px; height: 60px; padding: 0 3px; }
        .stats-bar { flex: 1; background: #e74c3c; min-height: 4px; border-radius: 2px 2px 0 0; position: relative; }
        .stats-bar.blue { background: #3498db; }
        .stats-bar span { position: absolute; top: -14px; left: 50%; transform: translateX(-50%); font-size: 0.5rem; color: #333; font-weight: 600; white-space: nowrap; }
        .stats-labels { display: flex; gap: 1px; margin-top: 3px; }
        .stats-label { flex: 1; text-align: center; font-size: 0.5rem; color: #666; }
        .analysis-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 12px; margin-top: 15px; }
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
        .pagination { display: flex; justify-content: center; gap: 5px; margin-top: 15px; flex-wrap: wrap; }
        .pagination button { padding: 6px 12px; border: 1px solid #ddd; background: white; border-radius: 4px; cursor: pointer; font-size: 0.85rem; }
        .pagination button:hover { background: #f8f9fa; }
        .pagination button.active { background: #e74c3c; color: white; border-color: #e74c3c; }
        .slider-section { margin-bottom: 15px; }
        .slider-section label { display: block; font-size: 0.85rem; color: #555; margin-bottom: 5px; }
        .slider-section input[type="range"] { width: 100%; }
        .slider-section .hint { font-size: 0.75rem; color: #999; }
        @media (max-width: 768px) {
            .main-content { flex-direction: column; }
            .predict-panel { border-right: none; border-bottom: 1px solid #eee; }
            .header { flex-direction: column; gap: 10px; align-items: flex-start; }
            .header-right { width: 100%; justify-content: space-between; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="header-left">
                <h1>双色球数据分析系统</h1>
            </div>
            <div class="header-right">
                <div class="stat-item">
                    <span class="label">数据总量</span>
                    <span class="value green" id="totalCount">--</span>
                </div>
                <div class="stat-item">
                    <span class="label">最新期号</span>
                    <span class="value red" id="latestPeriod">--</span>
                </div>
                <div class="stat-item">
                    <span class="label">最近更新</span>
                    <span class="value blue" id="lastUpdate">--</span>
                </div>
            </div>
        </div>

        <div class="tabs">
            <button class="tab active" onclick="showTab('predict')">号码预测</button>
            <button class="tab" onclick="showTab('history')">历史数据</button>
            <button class="tab" onclick="showTab('update')">数据更新</button>
        </div>

        <div class="content">
            <div class="section active row-layout" id="predict">
                <div class="main-content">
                    <div class="predict-panel">
                        <div class="btn-group">
                            <button class="btn" onclick="doPredict()">
                                <span class="loading" id="predictLoading" style="display:none;"></span>
                                生成预测
                            </button>
                            <button class="btn btn-secondary" onclick="refreshData()">
                                刷新数据
                            </button>
                            
                            <button class="btn btn-secondary btn-period-10" onclick="selectPeriod(10)">近10期</button>
                            <button class="btn btn-secondary btn-period-30" onclick="selectPeriod(30)">近30期</button>
                            <button class="btn btn-secondary btn-period-50" onclick="selectPeriod(50)">近50期</button>
                            <button class="btn btn-secondary btn-period-all" onclick="selectPeriod(0)">全部数据</button>
                        </div>
                        
                        <div id="predictionResult"></div>
                    </div>
                    
                    <div class="analysis-panel">
                        <div class="btn-group">
                            <button class="btn btn-secondary btn-period-10" onclick="selectPeriod(10)">近10期</button>
                            <button class="btn btn-secondary btn-period-30" onclick="selectPeriod(30)">近30期</button>
                            <button class="btn btn-secondary btn-period-50" onclick="selectPeriod(50)">近50期</button>
                            <button class="btn btn-secondary btn-period-all" onclick="selectPeriod(0)">全部数据</button>
                        </div>
                        
                        <div id="analysisLoading" style="display:none;color:#3498db;font-size:0.85rem;margin-top:10px;">加载中...</div>
                        <div id="analysisContent"></div>
                    </div>
                </div>
            </div>

            <div class="section" id="history">
                <div class="history-header">
                    <input type="text" id="searchPeriod" placeholder="搜索期号（如2026068）" onkeyup="if(event.key==='Enter') searchHistory()" style="flex:1;min-width:180px;padding:8px 12px;border:1px solid #ddd;border-radius:6px;font-size:0.9rem;">
                    <button class="btn" onclick="searchHistory()">搜索</button>
                    <button class="btn btn-secondary" onclick="clearSearch()">清空</button>
                    <button class="btn btn-secondary" onclick="showHistory(10)">最近10期</button>
                    <button class="btn btn-secondary" onclick="showHistory(20)">最近20期</button>
                    <button class="btn btn-secondary" onclick="showHistory(50)">最近50期</button>
                    <button class="btn btn-secondary" onclick="showHistory(0)">全部数据</button>
                </div>
                <div class="history-main">
                    <div id="historyContent"></div>
                    <div id="historyAnalysis"></div>
                </div>
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
            
            if (tabName === 'predict') {
                loadPrediction();
                loadAnalysis();
            }
            if (tabName === 'history') showHistory(10);
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

        function loadPrediction(limit=0) {
            let url = limit > 0 ? `/api/predict?limit=${limit}&` : '/api/predict?';
            fetch(url + Date.now())
                .then(r => r.json())
                .then(data => {
                    if (!data.success) {
                        document.getElementById('predictionResult').innerHTML = 
                            '<div style="text-align:center;color:#e74c3c;padding:50px;">' + data.message + '</div>';
                        return;
                    }
                    
                    function buildPredictionSection(pred) {
                        let redReasons = pred.red_reasons || {};
                        let redBalls = pred.red_balls.map(b => {
                            let reason = redReasons[b] || '';
                            return `<span class="ball red" title="${reason}">${b.toString().padStart(2, '0')}</span>`;
                        }).join('');
                        let blueBalls = `<span class="ball blue">${pred.blue_ball.toString().padStart(2, '0')}</span>`;
                        let blueOptions = pred.blue_options.slice(1).map(b => 
                            `<span class="ball blue small">${b.toString().padStart(2, '0')}</span>`
                        ).join('');
                        let features = pred.features;
                        
                        let reasonHtml = '';
                        if (redReasons && Object.keys(redReasons).length > 0) {
                            reasonHtml = '<div style="font-size:0.75rem;color:#888;margin-top:8px;">';
                            pred.red_balls.forEach(b => {
                                let reason = redReasons[b] || '综合';
                                reasonHtml += `<span style="margin-right:8px;">${b.toString().padStart(2, '0')}: ${reason}</span>`;
                            });
                            reasonHtml += '</div>';
                        }
                        
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
                                    ${reasonHtml}
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

        function selectPeriod(limit) {
            document.querySelectorAll('.btn-period-10').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.btn-period-30').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.btn-period-50').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.btn-period-all').forEach(b => b.classList.remove('active'));
            
            if (limit === 10) {
                document.querySelectorAll('.btn-period-10').forEach(b => b.classList.add('active'));
            } else if (limit === 30) {
                document.querySelectorAll('.btn-period-30').forEach(b => b.classList.add('active'));
            } else if (limit === 50) {
                document.querySelectorAll('.btn-period-50').forEach(b => b.classList.add('active'));
            } else {
                document.querySelectorAll('.btn-period-all').forEach(b => b.classList.add('active'));
            }
            
            doPredict(limit);
            loadAnalysis(limit);
        }

        function doPredict(limit=0) {
            let loading = document.getElementById('predictLoading');
            loading.style.display = 'inline-block';
            loadPrediction(limit);
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
                    let html = '<div class="trend-container">';
                    
                    html += '<div class="trend-header-row">';
                    html += '<div class="trend-period">期号</div>';
                    html += '<div class="trend-red-area">';
                    for (let i = 1; i <= 33; i++) {
                        html += `<div class="trend-cell">${i.toString().padStart(2, '0')}</div>`;
                    }
                    html += '</div>';
                    html += '<div class="trend-blue-area">';
                    for (let i = 1; i <= 16; i++) {
                        html += `<div class="trend-cell">${i.toString().padStart(2, '0')}</div>`;
                    }
                    html += '</div>';
                    html += '</div>';
                    
                    records.forEach(rec => {
                        let redSet = new Set(rec.reds);
                        html += '<div class="trend-row">';
                        html += `<div class="trend-period">${rec.period}</div>`;
                        html += '<div class="trend-red-area">';
                        for (let i = 1; i <= 33; i++) {
                            let cls = redSet.has(i) ? 'red' : '';
                            html += `<div class="trend-cell ${cls}">${redSet.has(i) ? i.toString().padStart(2, '0') : ''}</div>`;
                        }
                        html += '</div>';
                        html += '<div class="trend-blue-area">';
                        for (let i = 1; i <= 16; i++) {
                            let cls = i === rec.blue ? 'blue' : '';
                            html += `<div class="trend-cell ${cls}">${i === rec.blue ? i.toString().padStart(2, '0') : ''}</div>`;
                        }
                        html += '</div>';
                        html += '</div>';
                    });
                    
                    html += '</div>';
                    
                    let redFreq = new Array(34).fill(0);
                    let blueFreq = new Array(17).fill(0);
                    records.forEach(rec => {
                        rec.reds.forEach(r => redFreq[r]++);
                        blueFreq[rec.blue]++;
                    });
                    
                    html += '<div class="trend-stats-container">';
                    
                    html += '<div class="trend-stats">';
                    html += '<h4>红球出现次数统计</h4>';
                    html += '<div class="stats-row">';
                    for (let i = 1; i <= 33; i++) {
                        let height = Math.max(4, (redFreq[i] / records.length) * 100);
                        html += `<div class="stats-bar" style="height:${height}%;"><span>${redFreq[i]}</span></div>`;
                    }
                    html += '</div>';
                    html += '<div class="stats-labels">';
                    for (let i = 1; i <= 33; i++) {
                        html += `<div class="stats-label">${i}</div>`;
                    }
                    html += '</div>';
                    html += '</div>';
                    
                    html += '<div class="trend-stats">';
                    html += '<h4>蓝球出现次数统计</h4>';
                    html += '<div class="stats-row">';
                    for (let i = 1; i <= 16; i++) {
                        let height = Math.max(4, (blueFreq[i] / records.length) * 100);
                        html += `<div class="stats-bar blue" style="height:${height}%;"><span>${blueFreq[i]}</span></div>`;
                    }
                    html += '</div>';
                    html += '<div class="stats-labels">';
                    for (let i = 1; i <= 16; i++) {
                        html += `<div class="stats-label">${i}</div>`;
                    }
                    html += '</div>';
                    html += '</div>';
                    
                    html += '</div>';

                    document.getElementById('historyContent').innerHTML = html;
                    
                    let analysisUrl = limit > 0 ? `/api/analysis?limit=${limit}` : '/api/analysis';
                    fetch(analysisUrl)
                        .then(r => r.json())
                        .then(analysisData => {
                            if (!analysisData.success) {
                                document.getElementById('historyAnalysis').innerHTML = '';
                                return;
                            }
                            
                            let hotReds = analysisData.hot_reds.map((b, i) => 
                                `<li><span class="name">红球${b.toString().padStart(2, '0')}</span><span class="count frequency-high">${i + 1}位</span></li>`
                            ).join('');
                            
                            let coldReds = analysisData.cold_reds.map((b, i) => 
                                `<li><span class="name">红球${b.toString().padStart(2, '0')}</span><span class="count frequency-low">${i + 1}位</span></li>`
                            ).join('');
                            
                            let hotBlues = analysisData.hot_blues.map((b, i) => 
                                `<li><span class="name">蓝球${b.toString().padStart(2, '0')}</span><span class="count frequency-high">${i + 1}位</span></li>`
                            ).join('');
                            
                            let coldBlues = analysisData.cold_blues.map((b, i) => 
                                `<li><span class="name">蓝球${b.toString().padStart(2, '0')}</span><span class="count frequency-low">${i + 1}位</span></li>`
                            ).join('');
                            
                            let highOmissionReds = analysisData.high_omission_reds.map((b, i) => 
                                `<li><span class="name">红球${b.toString().padStart(2, '0')}</span><span class="count">${analysisData.red_omission[b]}期</span></li>`
                            ).join('');
                            
                            let highOmissionBlues = analysisData.high_omission_blues.map((b, i) => 
                                `<li><span class="name">蓝球${b.toString().padStart(2, '0')}</span><span class="count">${analysisData.blue_omission[b]}期</span></li>`
                            ).join('');
                            
                            let intervalDist = analysisData.interval_distribution;
                            let parityDist = analysisData.parity_distribution;
                            let sizeDist = analysisData.size_distribution;
                            
                            let analysisHtml = `
                                <div class="analysis-grid" style="gap:10px;">
                                    <div class="analysis-card" style="padding:12px;">
                                        <h3 style="font-size:0.9rem;margin-bottom:8px;">热号排行</h3>
                                        <ul class="analysis-list" style="font-size:0.8rem;">${hotReds}</ul>
                                    </div>
                                    <div class="analysis-card" style="padding:12px;">
                                        <h3 style="font-size:0.9rem;margin-bottom:8px;">冷号排行</h3>
                                        <ul class="analysis-list" style="font-size:0.8rem;">${coldReds}</ul>
                                    </div>
                                    <div class="analysis-card" style="padding:12px;">
                                        <h3 style="font-size:0.9rem;margin-bottom:8px;">高遗漏红球</h3>
                                        <ul class="analysis-list" style="font-size:0.8rem;">${highOmissionReds}</ul>
                                    </div>
                                    <div class="analysis-card" style="padding:12px;">
                                        <h3 style="font-size:0.9rem;margin-bottom:8px;">高遗漏蓝球</h3>
                                        <ul class="analysis-list" style="font-size:0.8rem;">${highOmissionBlues}</ul>
                                    </div>
                                    <div class="analysis-card" style="padding:12px;">
                                        <h3 style="font-size:0.9rem;margin-bottom:8px;">区间分布</h3>
                                        <div style="font-size:0.8rem;">一区: ${intervalDist[1]} 二区: ${intervalDist[2]} 三区: ${intervalDist[3]}</div>
                                    </div>
                                    <div class="analysis-card" style="padding:12px;">
                                        <h3 style="font-size:0.9rem;margin-bottom:8px;">奇偶分布</h3>
                                        <div style="font-size:0.8rem;">奇数: ${parityDist['奇数']} 偶数: ${parityDist['偶数']}</div>
                                    </div>
                                    <div class="analysis-card" style="padding:12px;">
                                        <h3 style="font-size:0.9rem;margin-bottom:8px;">大小分布</h3>
                                        <div style="font-size:0.8rem;">大数: ${sizeDist['大数']} 小数: ${sizeDist['小数']}</div>
                                    </div>
                                    <div class="analysis-card" style="padding:12px;">
                                        <h3 style="font-size:0.9rem;margin-bottom:8px;">蓝球冷热</h3>
                                        <div style="font-size:0.8rem;margin-bottom:6px;">热号: ${analysisData.hot_blues.join(', ')}</div>
                                        <div style="font-size:0.8rem;">冷号: ${analysisData.cold_blues.join(', ')}</div>
                                    </div>
                                </div>
                            `;
                            
                            document.getElementById('historyAnalysis').innerHTML = analysisHtml;
                        });
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
                    let html = '<div class="trend-container">';
                    
                    html += '<div class="trend-header-row">';
                    html += '<div class="trend-period">期号</div>';
                    html += '<div class="trend-red-area">';
                    for (let i = 1; i <= 33; i++) {
                        html += `<div class="trend-cell">${i.toString().padStart(2, '0')}</div>`;
                    }
                    html += '</div>';
                    html += '<div class="trend-blue-area">';
                    for (let i = 1; i <= 16; i++) {
                        html += `<div class="trend-cell">${i.toString().padStart(2, '0')}</div>`;
                    }
                    html += '</div>';
                    html += '</div>';
                    
                    records.forEach(rec => {
                        let redSet = new Set(rec.reds);
                        html += '<div class="trend-row">';
                        html += `<div class="trend-period">${rec.period}</div>`;
                        html += '<div class="trend-red-area">';
                        for (let i = 1; i <= 33; i++) {
                            let cls = redSet.has(i) ? 'red' : '';
                            html += `<div class="trend-cell ${cls}">${redSet.has(i) ? i.toString().padStart(2, '0') : ''}</div>`;
                        }
                        html += '</div>';
                        html += '<div class="trend-blue-area">';
                        for (let i = 1; i <= 16; i++) {
                            let cls = i === rec.blue ? 'blue' : '';
                            html += `<div class="trend-cell ${cls}">${i === rec.blue ? i.toString().padStart(2, '0') : ''}</div>`;
                        }
                        html += '</div>';
                        html += '</div>';
                    });
                    
                    html += '</div>';
                    
                    document.getElementById('historyContent').innerHTML = html;
                });
        }

        function clearSearch() {
            document.getElementById('searchPeriod').value = '';
            showHistory(10);
        }

        function loadAnalysis(limit=0) {
            let loading = document.getElementById('analysisLoading');
            loading.style.display = 'inline-block';
            
            let url = limit > 0 ? `/api/analysis?limit=${limit}` : '/api/analysis';
            fetch(url)
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
            loadAnalysis();
        };
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    response = make_response(render_template_string(HTML_TEMPLATE))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


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
    limit = int(request.args.get('limit', 0))
    analyzer = get_analyzer()
    if not analyzer.is_ready:
        return json_response({"success": False, "message": "数据加载失败，请检查数据文件"})
    
    analyzer.calculate_frequency(limit)
    analyzer.calculate_omission(limit)
    
    result_a = analyzer.predict_red_balls()
    red_balls_a = result_a["balls"]
    red_reasons_a = result_a["reasons"]
    blue_ball_a = analyzer.predict_blue_ball()
    blue_options_a = analyzer.predict_blue_options(5)
    features_a = analyzer.analyze_prediction_features(red_balls_a, blue_ball_a)
    
    result_b = analyzer.predict_red_balls_advanced(exclude_balls=red_balls_a)
    red_balls_b = result_b["balls"]
    red_reasons_b = result_b["reasons"]
    blue_ball_b = analyzer.predict_blue_ball_advanced(exclude_ball=blue_ball_a)
    blue_options_b = analyzer.predict_blue_options(5)
    features_b = analyzer.analyze_prediction_features(red_balls_b, blue_ball_b)
    
    overlap = len(set(red_balls_a) & set(red_balls_b))
    
    return json_response({
        "success": True,
        "limit": limit,
        "prediction_a": {
            "name": "算法A：频率统计均衡法",
            "description": "采用行业通用的3热+2温+1冷配比，结合区间、奇偶、大小均衡筛选，避免极端组合",
            "red_balls": red_balls_a,
            "red_reasons": red_reasons_a,
            "blue_ball": blue_ball_a,
            "blue_options": blue_options_a,
            "features": features_a
        },
        "prediction_b": {
            "name": "算法B：多维指标共振法",
            "description": "采用余数分类法（除3余数）、尾数关联法、区间回补法等多维度交叉验证，优先选择冷号和高遗漏号码",
            "red_balls": red_balls_b,
            "red_reasons": red_reasons_b,
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
    limit = int(request.args.get('limit', 0))
    analyzer = get_analyzer()
    if not analyzer.is_ready:
        return json_response({"success": False, "message": "数据加载失败"})
    
    analyzer.calculate_frequency(limit)
    analyzer.calculate_omission(limit)
    
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
