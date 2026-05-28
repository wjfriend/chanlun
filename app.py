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


def _fetch_akshare_minute(symbol: str, period: str = "5") -> pd.DataFrame | None:
    """用 akshare stock_zh_a_hist_min_em 获取分钟K线数据。"""
    try:
        df = ak.stock_zh_a_hist_min_em(
            symbol=symbol,
            start_date="1979-09-01 09:32:00",
            end_date="2222-01-01 09:32:00",
            period=period,
            adjust=""
        )
        rows = []
        for _, row in df.iterrows():
            rows.append({
                "date": pd.to_datetime(row["时间"]),
                "open": float(row["开盘"]),
                "close": float(row["收盘"]),
                "high": float(row["最高"]),
                "low": float(row["最低"]),
                "volume": float(row["成交量"]),
            })
        result = pd.DataFrame(rows)
        if result.empty:
            return None
        result.set_index("date", inplace=True)
        return result
    except Exception:
        return None


def _format_kline_date(dt, period: str) -> str:
    """格式化K线日期，分钟数据包含时间。"""
    if period in ("1", "5", "15", "30", "60", "120"):
        return dt.strftime("%Y-%m-%d %H:%M")
    return dt.strftime("%Y-%m-%d")


def get_stock_data(symbol: str, start: str | None = None, end: str | None = None, period: str = "daily") -> pd.DataFrame:
    """获取A股 K线数据，分钟线优先新浪财经（日/周/月线用腾讯财经）。"""
    if start is None:
        if period in ("1", "5", "15", "30", "60", "120"):
            start = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
        else:
            start = (datetime.now() - timedelta(days=730)).strftime("%Y%m%d")
    if end is None:
        end = datetime.now().strftime("%Y%m%d")

    # 分钟级别：优先 akshare，失败则新浪，最后东方财富
    if period in ("1", "5", "15", "30", "60", "120"):
        df = _fetch_akshare_minute(symbol, period)
        if df is not None:
            return df
        df2 = _fetch_sina_minute(symbol, period)
        if df2 is not None:
            return df2
        df3 = _fetch_eastmoney_minute(symbol, start, end, period)
        if df3 is not None:
            return df3
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
                "date": _format_kline_date(row.name, period),
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

        # 构建date->volume映射（来自原始df，用于缠论API响应附带volume）
        # 支持列名"volume"，也支持从df.index取datetime
        date_to_vol = {}
        for i in range(len(df)):
            row = df.iloc[i]
            if "date" in df.columns:
                d = str(row["date"])
            else:
                d = str(df.index[i])
            if "volume" in df.columns:
                date_to_vol[d] = float(row["volume"])
            else:
                date_to_vol[d] = 0.0

        # 构造 list[dict] 传给缠论服务（含date用于processed返回）
        klines: list[dict] = []
        for idx in range(len(df)):
            row = df.iloc[idx]
            # 尝试取date字段（列优先，其次用index）
            row_date = ""
            if "date" in df.columns:
                row_date = str(row["date"])
            elif hasattr(df, "index") and idx < len(df):
                row_date = str(df.index[idx])
            # sina/腾讯的日线数据date格式已经是字符串，直接用
            klines.append({
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "date": row_date,
            })

        # MACD 值（用于背驰判断）
        closes = df["close"].tolist()
        macd_vals, _, _ = calc_macd(closes)

        # 完整缠论分析
        result = full_analysis(klines, macd=macd_vals if macd_vals else None)

        # 为processed_klines附加指标数据（前端子图渲染需要）
        proc = result["processed_klines"]
        proc_closes = [k["close"] for k in proc]
        proc_highs = [k["high"] for k in proc]
        proc_lows = [k["low"] for k in proc]
        proc_volumes = [0] * len(proc)  # processed klines体积不可用，用0

        macd_vals_p, macd_sig_p, macd_hist_p = calc_macd(proc_closes)
        ma_data = calc_ma(proc_closes)
        boll_u, boll_m, boll_l = calc_boll(proc_closes)
        rsi_vals = calc_rsi(proc_closes)
        k_vals, d_vals, j_vals = calc_kdj(proc_highs, proc_lows, proc_closes)
        obv_vals = calc_obv(proc_closes, proc_volumes)
        cci_vals = calc_cci(proc_highs, proc_lows, proc_closes)
        stoch_k, stoch_d = calc_stoch_rsi(proc_closes)

        for i, k in enumerate(proc):
            k["MA5"] = ma_data[5][i] if i < len(ma_data.get(5, [])) else 0
            k["MA10"] = ma_data[10][i] if i < len(ma_data.get(10, [])) else 0
            k["MA20"] = ma_data[20][i] if i < len(ma_data.get(20, [])) else 0
            k["MA60"] = ma_data[60][i] if i < len(ma_data.get(60, [])) else 0
            k["MACD"] = macd_vals_p[i] if i < len(macd_vals_p) else 0
            k["MACD_signal"] = macd_sig_p[i] if i < len(macd_sig_p) else 0
            k["MACD_hist"] = macd_hist_p[i] if i < len(macd_hist_p) else 0
            k["BOLL_upper"] = boll_u[i] if i < len(boll_u) else 0
            k["BOLL_mid"] = boll_m[i] if i < len(boll_m) else 0
            k["BOLL_lower"] = boll_l[i] if i < len(boll_l) else 0
            k["RSI"] = rsi_vals[i] if i < len(rsi_vals) else 50
            k["K"] = k_vals[i] if i < len(k_vals) else 50
            k["D"] = d_vals[i] if i < len(d_vals) else 50
            k["J"] = j_vals[i] if i < len(j_vals) else 50
            k["CCI"] = cci_vals[i] if i < len(cci_vals) else 0
            k["OBV"] = obv_vals[i] if i < len(obv_vals) else 0
            k["StochRSI_K"] = stoch_k[i] if i < len(stoch_k) else 50
            k["StochRSI_D"] = stoch_d[i] if i < len(stoch_d) else 50

        # 序列化 processed_klines（含指标，供前端渲染用）
        proc_data = []
        for k in result["processed_klines"]:
            proc_data.append({
                "date": k.get("date", ""),
                "open": k["open"],
                "high": k["high"],
                "low": k["low"],
                "close": k["close"],
                "volume": date_to_vol.get(k.get("date", ""), 0),
                "MA5": k.get("MA5", 0),
                "MA10": k.get("MA10", 0),
                "MA20": k.get("MA20", 0),
                "MA60": k.get("MA60", 0),
                "MACD": k.get("MACD", 0),
                "MACD_signal": k.get("MACD_signal", 0),
                "MACD_hist": k.get("MACD_hist", 0),
                "BOLL_upper": k.get("BOLL_upper", 0),
                "BOLL_mid": k.get("BOLL_mid", 0),
                "BOLL_lower": k.get("BOLL_lower", 0),
                "RSI": k.get("RSI", 50),
                "K": k.get("K", 50),
                "D": k.get("D", 50),
                "J": k.get("J", 50),
                "CCI": k.get("CCI", 0),
                "OBV": k.get("OBV", 0),
                "StochRSI_K": k.get("StochRSI_K", 50),
                "StochRSI_D": k.get("StochRSI_D", 50),
            })

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
            "klines": proc_data,
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
