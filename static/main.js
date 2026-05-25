/**
 * 缠论画图工具 - 前端主逻辑
 * 支持：笔/线段、中枢（笔/段）、123买卖点、K线样式切换、多指标面板、多周期切换
 */

let klineData = [];
let chanResult = null;
let klineStyle = 'standard';  // 'standard' | 'chan'
let currentPeriod = 'daily';  // 当前K线周期

// ========== 显示开关 ==========
const showState = {
    MA: true, BOLL: true, MACD: true,
    RSI: false, KDJ: false, CCI: false, OBV: false, StochRSI: false,
    bi: true, segment: true,
    bi_zhongshu: true, segment_zhongshu: true,
    buy_1: true, buy_2: true, buy_3: true,
    sell_1: true, sell_2: true, sell_3: true,
};

// ========== 加载数据 ==========
async function loadChanData(code, period = 'daily') {
    currentPeriod = period;
    showLoading(true);
    try {
        // 先加载K线数据（串行，chan分析依赖同一数据源）
        const stockRes = await fetch(`/api/stock/${code}?period=${period}`);
        if (!stockRes.ok) {
            throw new Error(`K线数据请求失败 (${stockRes.status})`);
        }
        const stockJson = await stockRes.json();
        if (!stockJson.success) {
            throw new Error(stockJson.error || 'K线数据加载失败');
        }
        klineData = stockJson.data;

        // 再加载缠论分析
        const chanRes = await fetch(`/api/chan/${code}?period=${period}`);
        if (!chanRes.ok) {
            throw new Error(`缠论分析请求失败 (${chanRes.status})`);
        }
        const chanJson = await chanRes.json();
        if (!chanJson.success) {
            throw new Error(chanJson.error || '缠论分析失败');
        }
        chanResult = chanJson;

        renderChart();
    } catch (err) {
        showError(err.message || '加载失败，请检查股票代码是否正确');
    } finally {
        showLoading(false);
    }
}

function showLoading(show) {
    const el = document.getElementById('loadingOverlay');
    if (el) el.classList.toggle('hidden', !show);
}

function showError(msg) {
    showLoading(false);
    document.getElementById('mainChart').innerHTML = `
        <div class="error-container" style="margin:80px auto;">
            <h2 style="color:#e94560;margin-bottom:16px;">出错了</h2>
            <p style="color:#888;">${msg}</p>
            <br>
            <button class="btn" onclick="window.location.href='/'">返回首页</button>
        </div>`;
}

// ========== 指标显示切换（checkbox勾选）==========
function toggleIndicator(name, checked) {
    showState[name] = checked;
    const label = document.querySelector(`label[for="ind${name}"]`) ||
        document.querySelector(`#ind${name}`)?.closest('label');
    if (label) label.classList.toggle('active', checked);
    renderChart();
}

// ========== 缠论元素切换 ==========
function toggleChanElement(name, checked) {
    showState[name] = checked;
    renderChart();
}

// ========== 买卖点切换 ==========
function toggleSignal(name, checked) {
    showState[name] = checked;
    renderChart();
}

// ========== K线样式切换 ==========
function setKlineStyle(style) {
    klineStyle = style;
    document.getElementById('btnKlineStandard').classList.toggle('active', style === 'standard');
    document.getElementById('btnKlineChan').classList.toggle('active', style === 'chan');
    updateKlineTraces();
}

function updateKlineTraces() {
    if (!klineData.length) return;
    const n = klineData.length;

    if (klineStyle === 'standard') {
        Plotly.restyle('mainChart', {
            high: klineData.map(k => k.high),
            low: klineData.map(k => k.low),
        }, [0]);
    } else {
        // 缠论K线：无影线，high/low = close/open
        const opens = klineData.map(k => k.open);
        const closes = klineData.map(k => k.close);
        const high = opens.map((o, i) => Math.max(o, closes[i]));
        const low = opens.map((o, i) => Math.min(o, closes[i]));
        Plotly.restyle('mainChart', { high, low }, [0]);
    }
}

// ========== 渲染主图表 ==========
function renderChart() {
    if (!klineData.length) return;

    subplotIdx = 2;  // 重置副图索引 (y=K线, y2=vol, y3+=indicator)

    const traces = [];
    const shapes = [];
    const annotations = [];

    // ---------- 1. K线 ----------
    const dates = klineData.map(k => k.date);
    const opens = klineData.map(k => k.open);
    const closes = klineData.map(k => k.close);
    const highs = klineData.map(k => k.high);
    const lows = klineData.map(k => k.low);

    // 缠论K线：无影线
    let klineHighs = highs, klineLows = lows;
    if (klineStyle === 'chan') {
        klineHighs = opens.map((o, i) => Math.max(o, closes[i]));
        klineLows = opens.map((o, i) => Math.min(o, closes[i]));
    }

    traces.push({
        x: dates,
        open: opens,
        high: klineHighs,
        low: klineLows,
        close: closes,
        type: 'ohlc',
        name: 'K线',
        increasing: { line: { color: '#e94560', width: 1 } },
        decreasing: { line: { color: '#26a69a', width: 1 } },
        xaxis: 'x',
        yaxis: 'y',
    });

    // ---------- 1.5 成交量（与K线共享y轴，放在底部区域）----------
    const volumes = klineData.map(k => k.volume || 0);
    const volColors = klineData.map((k, i) =>
        closes[i] >= opens[i] ? 'rgba(233,69,96,0.3)' : 'rgba(38,166,154,0.3)'
    );
    traces.push({
        x: dates, y: volumes,
        type: 'bar',
        name: 'Vol',
        marker: { color: volColors },
        xaxis: 'x',
        yaxis: 'y',
        showlegend: false,
        opacity: 0.8,
    });

    // ---------- 2. MA均线 ----------
    if (showState.MA) {
        addMATraces(traces, dates);
    }

    // ---------- 3. BOLL布林带 ----------
    if (showState.BOLL) {
        addBOLLTraces(traces, dates);
    }

    // ---------- 4. 笔 ----------
    if (showState.bi && chanResult?.bi) {
        addBiTraces(traces, dates);
    }

    // ---------- 5. 线段 ----------
    if (showState.segment && chanResult?.segments?.length) {
        addSegmentTraces(traces, dates);
    }

    // ---------- 6. 中枢 ----------
    if (chanResult?.zhongshu?.length) {
        addZhongshuShapes(shapes, annotations, dates);
    }

    // ---------- 7. 买卖点标记 ----------
    if (chanResult?.signals) {
        addSignalTraces(traces, dates, highs, lows);
    }

    // ---------- 8. 副图指标 ----------
    const rowCount = calcRowCount();
    const subplotRows = [];

    if (showState.MACD) subplotRows.push({ type: 'MACD', row: 1 });
    if (showState.RSI) subplotRows.push({ type: 'RSI', row: 2 });
    if (showState.KDJ) subplotRows.push({ type: 'KDJ', row: 3 });
    if (showState.CCI) subplotRows.push({ type: 'CCI', row: 4 });
    if (showState.OBV) subplotRows.push({ type: 'OBV', row: 5 });
    if (showState.StochRSI) subplotRows.push({ type: 'StochRSI', row: 6 });

    // 添加指标traces
    if (showState.MACD) addMACDTraces(traces, dates);
    if (showState.RSI) addRSITraces(traces, dates);
    if (showState.KDJ) addKDJTraces(traces, dates);
    if (showState.CCI) addCCITraces(traces, dates);
    if (showState.OBV) addOBVTraces(traces, dates);
    if (showState.StochRSI) addStochRSITraces(traces, dates);

    // ---------- 布局 ----------
    const totalRows = 1 + subplotRows.length;  // 主图(K线+成交量) + 指标
    const layout = buildLayout(totalRows, subplotRows, shapes, annotations);

    // 配置：启用滚轮缩放、拖拽平移
    const config = {
        responsive: true,
        displayModeBar: true,
        modeBarButtonsToRemove: ['lasso2d', 'select2d'],
        scrollZoom: true,     // 滚轮缩放
        dragMode: 'pan',      // 默认拖拽模式
    };

    Plotly.react('mainChart', traces, layout, config);
}

// ========== 计算需要的行数 ==========
function calcRowCount() {
    let n = 1;  // 主图
    if (showState.MACD) n++;
    if (showState.RSI) n++;
    if (showState.KDJ) n++;
    if (showState.CCI) n++;
    if (showState.OBV) n++;
    if (showState.StochRSI) n++;
    return n;
}

// ========== 构建布局 ==========
function buildLayout(totalRows, subplotRows, shapes, annotations) {
    const rowHeight = 1 / totalRows;

    const domains = subplotRows.map((sp, idx) => {
        const start = 1 - (idx + 2) * rowHeight;
        const end = 1 - (idx + 1) * rowHeight;
        return { yaxis: { domain: [Math.max(0, end), Math.min(1, start)] } };
    });

    const layout = {
        paper_bgcolor: '#1a1a2e',
        plot_bgcolor: '#1a1a2e',
        font: { color: '#e0e0e0', family: 'sans-serif' },
        grid: { rows: totalRows, cols: 1 },
        xaxis: {
            showgrid: true,
            gridcolor: '#2a2a4a',
            rangeslider: { visible: false },
            type: 'date',
            mirror: false,
            zeroline: false,
            showspikes: true,
            spikecolor: '#444',
            spikethickness: 1,
        },
        yaxis: {
            showgrid: true,
            gridcolor: '#2a2a4a',
            domain: [0, 1],
            mirror: false,
            zeroline: false,
            side: 'left',
            showspikes: true,
            spikecolor: '#444',
            spikethickness: 1,
        },
        legend: {
            orientation: 'h',
            x: 0,
            y: 1.12,
            bgcolor: 'rgba(0,0,0,0)',
        },
        annotations: [],
        shapes: [],
        margin: { t: 50, b: 50, l: 60, r: 20 },
        showlegend: true,
    };

    // 添加每个副图的yaxis
    subplotRows.forEach((sp, idx) => {
        const rowNum = idx + 2;
        const yaxisName = `yaxis${rowNum > 1 ? rowNum : ''}`;
        layout[yaxisName] = {
            showgrid: true, gridcolor: '#2a2a4a',
            domain: domains[idx].yaxis.domain,
            mirror: false, zeroline: false,
            side: 'left',
        };

        // xaxis共享
        if (!layout.xaxis2) {
            layout.xaxis2 = {
                showgrid: true, gridcolor: '#2a2a4a',
                type: 'date', mirror: false, zeroline: false,
                anchor: `y${rowNum}`,
            };
        }
    });

    layout.annotations = annotations;
    layout.shapes = shapes;
    return layout;
}

// ========== MA均线 ==========
function addMATraces(traces, dates) {
    const maConfigs = [
        { key: 'MA5', color: '#f39c12', dash: 'solid', name: 'MA5' },
        { key: 'MA10', color: '#e74c3c', dash: 'solid', name: 'MA10' },
        { key: 'MA20', color: '#3498db', dash: 'solid', name: 'MA20' },
        { key: 'MA60', color: '#9b59b6', dash: 'solid', name: 'MA60' },
    ];
    maConfigs.forEach(cfg => {
        const vals = klineData.map(k => k[cfg.key] || 0);
        traces.push({
            x: dates, y: vals,
            type: 'scatter', mode: 'lines',
            name: cfg.name,
            line: { color: cfg.color, width: 1.2, dash: cfg.dash },
            xaxis: 'x', yaxis: 'y',
        });
    });
}

// ========== BOLL布林带 ==========
function addBOLLTraces(traces, dates) {
    traces.push({
        x: dates,
        y: klineData.map(k => k.BOLL_upper || 0),
        type: 'scatter', mode: 'lines',
        name: 'BOLL上轨',
        line: { color: 'rgba(155,89,182,0.5)', width: 1 },
        xaxis: 'x', yaxis: 'y',
    });
    traces.push({
        x: dates,
        y: klineData.map(k => k.BOLL_mid || 0),
        type: 'scatter', mode: 'lines',
        name: 'BOLL中轨',
        line: { color: 'rgba(155,89,182,0.8)', width: 1.5 },
        xaxis: 'x', yaxis: 'y',
    });
    traces.push({
        x: dates,
        y: klineData.map(k => k.BOLL_lower || 0),
        type: 'scatter', mode: 'lines',
        name: 'BOLL下轨',
        line: { color: 'rgba(155,89,182,0.5)', width: 1 },
        fill: 'tonexty',
        fillcolor: 'rgba(155,89,182,0.05)',
        xaxis: 'x', yaxis: 'y',
    });
}

// ========== 笔（红色向上，绿色向下）==========
function addBiTraces(traces, dates) {
    // 向上笔：红色 (#e94560)，向下笔：绿色 (#26a69a)
    const upColor = '#e94560', downColor = '#26a69a';
    chanResult.bi.forEach((bi, i) => {
        const start = bi.start, end = bi.end;
        if (start >= dates.length || end >= dates.length) return;
        // bi.type = 'bottom' 表示向上笔，'top' 表示向下笔
        const isUp = bi.type === 'bottom';
        const color = isUp ? upColor : downColor;
        traces.push({
            x: [dates[start], dates[end]],
            y: [klineData[start]?.close || 0, klineData[end]?.close || 0],
            type: 'scatter', mode: 'lines',
            name: i === 0 ? (isUp ? '↑笔' : '↓笔') : '',
            line: { color, width: 2 },
            xaxis: 'x', yaxis: 'y',
            showlegend: i === 0,
        });
    });
}

// ========== 线段（蓝色向上，紫色向下）==========
function addSegmentTraces(traces, dates) {
    const upColor = '#2979ff', downColor = '#7c4dff';
    chanResult.segments.forEach((seg, i) => {
        const start = seg.start_idx, end = seg.end_idx;
        if (start >= dates.length || end >= dates.length) return;
        const isUp = seg.direction === 'up';
        const color = isUp ? upColor : downColor;
        traces.push({
            x: [dates[start], dates[end]],
            y: [klineData[start]?.close || 0, klineData[end]?.close || 0],
            type: 'scatter', mode: 'lines',
            name: i === 0 ? (isUp ? '↑线段' : '↓线段') : '',
            line: { color, width: 4 },
            xaxis: 'x', yaxis: 'y',
            showlegend: i === 0,
        });
    });
}

// ========== 中枢（笔中枢细框/线段中枢粗框）==========
function addZhongshuShapes(shapes, annotations, dates) {
    chanResult.zhongshu.forEach((zs, i) => {
        if (zs.start_idx >= dates.length || zs.end_idx >= dates.length) return;
        const isSegment = zs.source === 'segment';
        const x0 = dates[zs.start_idx];
        const x1 = dates[zs.end_idx];
        const y0 = zs.zd;
        const y1 = zs.zg;

        shapes.push({
            type: 'rect',
            xref: 'x', yref: 'y',
            x0, x1, y0, y1,
            fillcolor: isSegment ? 'rgba(0,200,255,0.15)' : 'rgba(255,215,0,0.12)',
            line: {
                color: isSegment ? 'rgba(0,200,255,0.7)' : 'rgba(255,215,0,0.4)',
                width: isSegment ? 2 : 1,
            },
            layer: 'below',
        });

        // 中枢标签
        annotations.push({
            x: dates[zs.mid_idx] || x0,
            y: (y0 + y1) / 2,
            text: isSegment ? '段中枢' : '笔中枢',
            showarrow: false,
            font: { color: isSegment ? '#00c8ff' : '#ffd700', size: 11 },
            xref: 'x', yref: 'y',
        });
    });
}

// ========== 123买卖点 ==========
// 买点：红色向上三角；卖点：绿色向下三角
const SIGNAL_META = {
    buy_1:  { symbol: 'triangle-up',   color: '#e94560', label: '1买', yShift: -0.02 },  // 红色
    buy_2:  { symbol: 'triangle-up',   color: '#ff6b6b', label: '2买', yShift: -0.04 },  // 浅红
    buy_3:  { symbol: 'triangle-up',   color: '#ffb3b3', label: '3买', yShift: -0.06 },  // 更浅红
    sell_1: { symbol: 'triangle-down', color: '#26a69a', label: '1卖', yShift: 0.02 },   // 绿色
    sell_2: { symbol: 'triangle-down', color: '#4db6ac', label: '2卖', yShift: 0.04 },   // 浅绿
    sell_3: { symbol: 'triangle-down', color: '#80cbc4', label: '3卖', yShift: 0.06 },   // 更浅绿
};

function addSignalTraces(traces, dates, highs, lows) {
    const signals = chanResult.signals;
    Object.entries(SIGNAL_META).forEach(([key, meta]) => {
        const indices = signals[key] || [];
        if (!indices.length || !showState[key]) return;

        const x = [], y = [];
        indices.forEach(idx => {
            if (idx < dates.length) {
                x.push(dates[idx]);
                // 使用 close 价格 +/- 百分比偏移
                const ref = klineData[idx]?.close || 0;
                y.push(ref * (1 + meta.yShift));
            }
        });

        traces.push({
            x, y,
            type: 'scatter', mode: 'markers',
            name: meta.label,
            marker: { symbol: meta.symbol, size: 14, color: meta.color },
            xaxis: 'x', yaxis: 'y',
        });
    });
}

// ========== 指标副图工具 ==========
function makeSubplotTrace(x, y, name, color, rowNum, fillColor) {
    const trace = {
        x, y,
        type: 'scatter', mode: 'lines',
        name: name,
        line: { color, width: 1.2 },
        xaxis: 'x',
        yaxis: `y${rowNum > 1 ? rowNum : ''}`,
        showlegend: true,
        fillcolor: fillColor || 'transparent',
    };
    if (fillColor) trace.fill = 'tozeroy';
    return trace;
}

let subplotIdx = 2; // 用于分配yaxis编号 (y=主图, y2=volume, y3+=指标)

// ========== MACD副图 ==========
function addMACDTraces(traces, dates) {
    const r = subplotIdx++;
    const macd = klineData.map(k => k.MACD || 0);
    const sig = klineData.map(k => k.MACD_signal || 0);
    const hist = klineData.map(k => k.MACD_hist || 0);
    const colors = hist.map(h => h >= 0 ? '#e94560' : '#26a69a');

    // MACD柱状图
    traces.push({
        x: dates, y: hist,
        type: 'bar',
        name: 'MACD量',
        marker: { color: colors },
        xaxis: 'x',
        yaxis: `y${r}`,
        showlegend: false,
    });

    // MACD线
    traces.push({
        x: dates, y: macd,
        type: 'scatter', mode: 'lines',
        name: 'MACD',
        line: { color: '#888', width: 1 },
        xaxis: 'x', yaxis: `y${r}`, showlegend: false,
    });

    traces.push({
        x: dates, y: sig,
        type: 'scatter', mode: 'lines',
        name: 'Signal',
        line: { color: '#ffa500', width: 1 },
        xaxis: 'x', yaxis: `y${r}`, showlegend: false,
    });
}

// ========== RSI ==========
function addRSITraces(traces, dates) {
    subplotIdx++;
    const r = subplotIdx++;
    const rsi = klineData.map(k => k.RSI || 50);

    traces.push({
        x: dates, y: rsi,
        type: 'scatter', mode: 'lines',
        name: 'RSI',
        line: { color: '#ff9800', width: 1.2 },
        xaxis: 'x', yaxis: `y${r}`,
        shape: 'hv',  // 阶梯形
    });

    // 超买超卖线
    [70, 50, 30].forEach((val, i) => {
        traces.push({
            x: dates, y: dates.map(() => val),
            type: 'scatter', mode: 'lines',
            name: ['RSI70', 'RSI50', 'RSI30'][i],
            line: { color: 'rgba(255,152,0,0.3)', width: 0.5, dash: 'dot' },
            xaxis: 'x', yaxis: `y${r}`,
            showlegend: false,
        });
    });
}

// ========== KDJ ==========
function addKDJTraces(traces, dates) {
    subplotIdx++;
    const r = subplotIdx++;

    const k = klineData.map(kn => kn.K || 50);
    const d = klineData.map(kn => kn.D || 50);
    const j = klineData.map(kn => kn.J || 50);

    traces.push({
        x: dates, y: k, type: 'scatter', mode: 'lines',
        name: 'K', line: { color: '#ff6b6b', width: 1.2 },
        xaxis: 'x', yaxis: `y${r}`,
    });
    traces.push({
        x: dates, y: d, type: 'scatter', mode: 'lines',
        name: 'D', line: { color: '#4fc3f7', width: 1.2 },
        xaxis: 'x', yaxis: `y${r}`, showlegend: false,
    });
    traces.push({
        x: dates, y: j, type: 'scatter', mode: 'lines',
        name: 'J', line: { color: '#ce93d8', width: 1 },
        xaxis: 'x', yaxis: `y${r}`, showlegend: false,
    });
}

// ========== CCI ==========
function addCCITraces(traces, dates) {
    subplotIdx++;
    const r = subplotIdx++;
    const cci = klineData.map(k => k.CCI || 0);

    traces.push({
        x: dates, y: cci, type: 'scatter', mode: 'lines',
        name: 'CCI', line: { color: '#26c6da', width: 1.2 },
        xaxis: 'x', yaxis: `y${r}`,
        shape: 'hv',
    });

    // ±100参考线
    [100, -100].forEach((val, i) => {
        traces.push({
            x: dates, y: dates.map(() => val),
            type: 'scatter', mode: 'lines',
            name: ['CCI+100', 'CCI-100'][i],
            line: { color: 'rgba(38,198,218,0.3)', width: 0.5, dash: 'dot' },
            xaxis: 'x', yaxis: `y${r}`, showlegend: false,
        });
    });
}

// ========== OBV ==========
function addOBVTraces(traces, dates) {
    subplotIdx++;
    const r = subplotIdx++;
    const obv = klineData.map(k => k.OBV || 0);

    traces.push({
        x: dates, y: obv, type: 'scatter', mode: 'lines',
        name: 'OBV',
        line: { color: '#66bb6a', width: 1.2 },
        xaxis: 'x', yaxis: `y${r}`,
        fill: 'tozeroy',
        fillcolor: 'rgba(102,187,106,0.1)',
    });
}

// ========== Stochastic RSI ==========
function addStochRSITraces(traces, dates) {
    subplotIdx++;
    const r = subplotIdx++;

    const sk = klineData.map(k => k.StochRSI_K || 50);
    const sd = klineData.map(k => k.StochRSI_D || 50);

    traces.push({
        x: dates, y: sk, type: 'scatter', mode: 'lines',
        name: 'StochRSI_K', line: { color: '#ef5350', width: 1.2 },
        xaxis: 'x', yaxis: `y${r}`,
    });
    traces.push({
        x: dates, y: sd, type: 'scatter', mode: 'lines',
        name: 'StochRSI_D', line: { color: '#42a5f5', width: 1.2 },
        xaxis: 'x', yaxis: `y${r}`, showlegend: false,
    });

    // 20/80参考线
    [80, 20].forEach((val, i) => {
        traces.push({
            x: dates, y: dates.map(() => val),
            type: 'scatter', mode: 'lines',
            name: ['SRSI80', 'SRSI20'][i],
            line: { color: 'rgba(239,83,80,0.3)', width: 0.5, dash: 'dot' },
            xaxis: 'x', yaxis: `y${r}`, showlegend: false,
        });
    });
}

// ========== 切换K线周期 ==========
function changePeriod(period) {
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code') || '000001';
    window.location.href = `/chart?code=${code}&period=${period}`;
}