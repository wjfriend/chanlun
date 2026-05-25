"""
缠论交互式画图工具 - Flask后端
路由层：参数校验、协议转换（不许查数据库）
业务逻辑 → services/
数据访问 → repositories/
"""
import json
from datetime import datetime, timedelta

import pandas as pd
import requests

import akshare as ak
from flask import Flask, jsonify, render_template, request

from services.chan import (
    calc_boll,
    calc_cci,
    calc_kdj,
    calc_ma,
    calc_macd,
    calc_obv,
    calc_rsi,
    calc_stoch_rsi,
    full_analysis,
)

app = Flask(__name__)

# ==================== 数据获取（repositories层）====================

# AkShare 支持的周期映射
PERIOD_MAP = {
    "daily": "daily",
    "weekly": "weekly",
    "monthly": "monthly",
    "quarterly": "quarterly",
    "yearly": "yearly",
    "1": "1", "5": "5", "15": "15", "30": "30", "60": "60", "120": "120",
}


def _fetch_tencent(symbol: str, start: str, end: str, period: str = "daily") -> pd.DataFrame | None:
    """从腾讯财经获取K线数据（仅支持日线）。"""
    try:
        # 转换代码格式：000001 → sz000001, 600519 → sh600519
        if symbol.startswith(("0", "3")):
            market = "sz"
        else:
            market = "sh"
        secid = f"{market}{symbol}"

        # period: day, week, month
        period_map = {"daily": "day", "weekly": "week", "monthly": "month"}
        qfq_period = period_map.get(period, "day")

        url = (
            f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
            f"?_var=kline_dayfqnone&param={secid},{qfq_period},,,800,qfq"
        )
        r = requests.get(url, timeout=10)
        text = r.text
        json_str = text[text.index("{"):]
        data = json.loads(json_str)
        days = data["data"][secid].get("qfqday") or data["data"][secid].get("day") or []

        rows = []
        for k in days:
            date_str = k[0]
            if start and date_str < start:
                continue
            if end and date_str > end:
                continue
            rows.append({
                "date": pd.to_datetime(date_str),
                "open": float(k[1]),
                "close": float(k[2]),
                "high": float(k[3]),
                "low": float(k[4]),
                "volume": float(k[5]),
            })

        df = pd.DataFrame(rows)
        if df.empty:
            return None
        df.set_index("date", inplace=True)
        return df
    except Exception:
        return None


def _fetch_eastmoney_minute(symbol: str, start: str, end: str, period: str = "5") -> pd.DataFrame | None:
    """从东方财富获取分钟K线数据（使用curl_cffi）。"""
    try:
        from curl_cffi import requests as curl_requests

        # 转换代码格式
        if symbol.startswith(("0", "3")):
            market = "0"
        else:
            market = "1"
        secid = f"{market}.{symbol}"

        fields = "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13"
        fields2 = "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"

        # period: 1, 5, 15, 30, 60 分钟
        klt_map = {"1": "1", "5": "5", "15": "15", "30": "30", "60": "60", "120": "60"}
        klt = klt_map.get(period, "5")

        url = (
            f"https://push2his.eastmoney.com/api/qt/stock/kline/get"
            f"?secid={secid}&fields1={fields}&fields2={fields2}"
            f"&klt={klt}&fqt=1&beg={start}000000&end={end}235959"
        )

        r = curl_requests.get(url, impersonate="chrome120", timeout=10)
        json_data = r.json()

        if json_data.get("data", {}).get("klines") is None:
            return None

        klines = json_data["data"]["klines"]
        rows = []
        for k in klines:
            parts = k.split(",")
            if len(parts) < 6:
                continue
            rows.append({
                "date": pd.to_datetime(parts[0]),
                "open": float(parts[1]),
                "close": float(parts[2]),
                "high": float(parts[3]),
                "low": float(parts[4]),
                "volume": float(parts[5]),
            })

        df = pd.DataFrame(rows)
        if df.empty:
            return None
        df.set_index("date", inplace=True)
        return df
    except Exception:
        return None


def _fetch_sina_minute(symbol: str, period: str = "30") -> pd.DataFrame | None:
    """从新浪财经获取分钟K线数据。"""
    try:
        import time

        # 转换代码格式：000001 → sz000001, 600519 → sh600519
        if symbol.startswith(("0", "3")):
            sym = f"sz{symbol}"
        else:
            sym = f"sh{symbol}"

        # scale: 5/15/30/60 分钟
        scale = period if period in ("5", "15", "30", "60") else "30"
        url = (
            f"https://money.finance.sina.com.cn/quotes_service/api/json_v2.php"
            f"/CN_MarketData.getKLineData"
            f"?symbol={sym}&scale={scale}&ma=no&datalen=800&_={int(time.time())}"
        )
        headers = {
            "Referer": "https://finance.sina.com.cn",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()
        if not data:
            return None

        rows = []
        for k in data:
            rows.append({
                "date": pd.to_datetime(k["day"]),
                "open": float(k["open"]),
                "high": float(k["high"]),
                "low": float(k["low"]),
                "close": float(k["close"]),
                "volume": float(k.get("volume") or k.get("volum", 0)),
            })

        df = pd.DataFrame(rows)
        if df.empty:
            return None
        df.set_index("date", inplace=True)
        return df
    except Exception:
        return None


def get_stock_data(symbol: str, start: str | None = None, end: str | None = None, period: str = "daily") -> pd.DataFrame:
    """获取A股 K线数据，分钟线优先新浪财经（日/周/月线用腾讯财经）。"""
    if start is None:
        if period in ("1", "5", "15", "30", "60", "120"):
            start = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
        else:
            start = (datetime.now() - timedelta(days=730)).strftime("%Y%m%d")
    if end is None:
        end = datetime.now().strftime("%Y%m%d")

    # 分钟级别：优先新浪财经，失败则尝试东方财富
    if period in ("1", "5", "15", "30", "60", "120"):
        df = _fetch_sina_minute(symbol, period)
        if df is not None:
            return df
        # 新浪失败则尝试东方财富（可能需要 curl_cffi）
        df2 = _fetch_eastmoney_minute(symbol, start, end, period)
        if df2 is not None:
            return df2
        raise ValueError(f"分钟数据获取失败（period={period}）")

    # 日/周/月线：使用腾讯
    df = _fetch_tencent(symbol, start, end, period)
    if df is not None:
        return df
    raise ValueError(f"无法获取股票数据（symbol={symbol}）")


# ==================== API 端点（api层：只做校验和协议转换）====================

@app.route("/")
def index():
    """首页：股票代码输入."""
    return render_template("index.html")


@app.route("/chart")
def chart():
    """图表页面."""
    return render_template("chart.html")


@app.route("/tv_chart")
def tv_chart():
    """TradingView图表页面."""
    return render_template("tv_chart.html")


def _validate_code(code: str) -> str | None:
    """校验股票代码格式."""
    code = code.strip()
    if not code:
        return "股票代码不能为空"
    if not code.isdigit():
        return "股票代码必须是数字"
    if len(code) != 6:
        return "股票代码必须是6位数字"
    return None


@app.route("/api/stock/<code>")
def get_stock(code: str):
    """获取K线数据 + 所有技术指标."""
    err = _validate_code(code)
    if err:
        return jsonify({"success": False, "error": err}), 400

    start = request.args.get("start", None)
    end = request.args.get("end", None)
    period = request.args.get("period", "daily")

    try:
        df = get_stock_data(code, start, end, period)

        closes = df["close"].tolist()
        highs = df["high"].tolist()
        lows = df["low"].tolist()
        volumes = df["volume"].tolist()

        # MACD
        macd_vals, macd_sig, macd_hist = calc_macd(closes)

        # MA
        ma_data = calc_ma(closes)

        # BOLL
        boll_upper, boll_mid, boll_lower = calc_boll(closes)

        # RSI
        rsi_vals = calc_rsi(closes)

        # KDJ
        k_vals, d_vals, j_vals = calc_kdj(highs, lows, closes)

        # OBV
        obv_vals = calc_obv(closes, volumes)

        # CCI
        cci_vals = calc_cci(highs, lows, closes)

        # Stochastic RSI
        stoch_rsi_k, stoch_rsi_d = calc_stoch_rsi(closes)

        kline_data = []
        for idx, (_, row) in enumerate(df.iterrows()):
            kline_data.append({
                "date": row.name.strftime("%Y-%m-%d") if hasattr(row.name, "strftime") else str(row.name)[:10],
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row["volume"]),
                "MACD": macd_vals[idx] if idx < len(macd_vals) else 0.0,
                "MACD_signal": macd_sig[idx] if idx < len(macd_sig) else 0.0,
                "MACD_hist": macd_hist[idx] if idx < len(macd_hist) else 0.0,
                "MA5": ma_data[5][idx] if idx < len(ma_data[5]) else 0.0,
                "MA10": ma_data[10][idx] if idx < len(ma_data[10]) else 0.0,
                "MA20": ma_data[20][idx] if idx < len(ma_data[20]) else 0.0,
                "MA60": ma_data[60][idx] if idx < len(ma_data[60]) else 0.0,
                "BOLL_upper": boll_upper[idx] if idx < len(boll_upper) else 0.0,
                "BOLL_mid": boll_mid[idx] if idx < len(boll_mid) else 0.0,
                "BOLL_lower": boll_lower[idx] if idx < len(boll_lower) else 0.0,
                "RSI": rsi_vals[idx] if idx < len(rsi_vals) else 50.0,
                "K": k_vals[idx] if idx < len(k_vals) else 50.0,
                "D": d_vals[idx] if idx < len(d_vals) else 50.0,
                "J": j_vals[idx] if idx < len(j_vals) else 50.0,
                "OBV": obv_vals[idx] if idx < len(obv_vals) else 0.0,
                "CCI": cci_vals[idx] if idx < len(cci_vals) else 0.0,
                "StochRSI_K": stoch_rsi_k[idx] if idx < len(stoch_rsi_k) else 50.0,
                "StochRSI_D": stoch_rsi_d[idx] if idx < len(stoch_rsi_d) else 50.0,
            })

        return jsonify({"success": True, "data": kline_data, "symbol": code})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/chan/<code>")
def get_chan(code: str):
    """获取缠论完整分析结果（分型→笔→线段→中枢→123买卖点）."""
    err = _validate_code(code)
    if err:
        return jsonify({"success": False, "error": err}), 400

    start = request.args.get("start", None)
    end = request.args.get("end", None)
    period = request.args.get("period", "daily")

    try:
        df = get_stock_data(code, start, end, period)

        # 构造 list[dict] 传给缠论服务
        klines: list[dict] = []
        for idx in range(len(df)):
            row = df.iloc[idx]
            klines.append({
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
            })

        # MACD 值（用于背驰判断）
        closes = df["close"].tolist()
        macd_vals, _, _ = calc_macd(closes)

        # 完整缠论分析
        result = full_analysis(klines, macd=macd_vals if macd_vals else None)

        # 序列化 bi（服务层返回 BiDict）
        bi_data = [
            {
                "start": int(bi["start"]),
                "end": int(bi["end"]),
                "type": bi["type"],
            }
            for bi in result["bi"]
        ]

        # 序列化线段
        seg_data = [
            {
                "start_idx": int(seg["start_idx"]),
                "end_idx": int(seg["end_idx"]),
                "direction": seg["direction"],
            }
            for seg in result["segments"]
        ]

        # 序列化中枢
        zs_data = [
            {
                "start_idx": int(zs["start_idx"]),
                "end_idx": int(zs["end_idx"]),
                "zg": float(zs["zg"]),
                "zd": float(zs["zd"]),
                "gg": float(zs["gg"]),
                "dg": float(zs["dg"]),
                "mid_idx": int(zs["mid_idx"]),
                "source": zs["source"],
            }
            for zs in result["zhongshu"]
        ]

        # 序列化买卖点
        signals_data = {
            "buy_1": [int(v) for v in result["signals"]["buy_1"]],
            "buy_2": [int(v) for v in result["signals"]["buy_2"]],
            "buy_3": [int(v) for v in result["signals"]["buy_3"]],
            "sell_1": [int(v) for v in result["signals"]["sell_1"]],
            "sell_2": [int(v) for v in result["signals"]["sell_2"]],
            "sell_3": [int(v) for v in result["signals"]["sell_3"]],
        }

        # 分型
        fenxing_data = {
            "tops": [int(t) for t in result["fenxing"]["tops"]],
            "bottoms": [int(b) for b in result["fenxing"]["bottoms"]],
        }

        return jsonify({
            "success": True,
            "symbol": code,
            "fenxing": fenxing_data,
            "bi": bi_data,
            "segments": seg_data,
            "zhongshu": zs_data,
            "signals": signals_data,
            "total_klines": len(df),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ==================== 主程序 ====================

if __name__ == "__main__":
    print("=" * 50)
    print("  缠论交互式画图工具")
    print("  访问 http://127.0.0.1:5000")
    print("=" * 50)
    app.run(debug=True, host="0.0.0.0", port=5000)
