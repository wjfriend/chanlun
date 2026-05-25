"""
缠论核心算法服务
实现标准缠论：分型→笔→线段→中枢→123买卖点
"""
from typing import TypedDict


class FenxingDict(TypedDict):
    """分型数据结构"""
    tops: list[int]
    bottoms: list[int]


class BiDict(TypedDict):
    """笔数据结构"""
    start: int
    end: int
    type: str  # "top" | "bottom"


class ZongshuDict(TypedDict):
    """中枢数据结构"""
    start_idx: int
    end_idx: int
    zg: float
    zd: float
    gg: float
    dg: float
    mid_idx: int
    source: str  # "bi" | "segment"


class SignalDict(TypedDict):
    """买卖点数据结构"""
    buy_1: list[int]
    buy_2: list[int]
    buy_3: list[int]
    sell_1: list[int]
    sell_2: list[int]
    sell_3: list[int]


class ChanResult(TypedDict):
    """完整缠论分析结果"""
    fenxing: FenxingDict
    bi: list[BiDict]
    segments: list[dict]
    zhongshu: list[ZongshuDict]
    signals: SignalDict


def process_inclusion(klines: list[dict]) -> list[dict]:
    """
    处理K线包含关系。
    向上走势：取高高（取max）
    向下走势：取低低（取min）
    返回处理后的K线列表（保留完整OHLC，用于分型判断）。
    """
    if not klines:
        return []

    processed = []
    trend = None  # "up" or "down"

    for curr in klines:
        curr_h = curr["high"]
        curr_l = curr["low"]
        curr_o = curr["open"]
        curr_c = curr["close"]

        if not processed:
            processed.append({"open": curr_o, "high": curr_h, "low": curr_l, "close": curr_c})
            continue

        prev = processed[-1]
        prev_h = prev["high"]
        prev_l = prev["low"]

        # 判断包含关系：前一根完全被后一根包含，或后一根完全被前一根包含
        # prev 包含 curr（curr被包在prev内）
        if prev_h >= curr_h and prev_l <= curr_l:
            continue

        # curr 包含 prev（需要融合）
        if curr_h >= prev_h and curr_l <= prev_l:
            # 确定趋势：至少需要2根确定趋势
            if len(processed) >= 2:
                pprev = processed[-2]
                trend = "up" if pprev["high"] > pprev["low"] else "down"
            else:
                trend = "up"

            if trend == "up":
                new_high = max(prev_h, curr_h)
                new_low = max(prev["open"], curr_o)
                new_close = max(prev["close"], curr_c)
            else:
                new_high = min(prev_h, curr_h)
                new_low = min(prev["open"], curr_o)
                new_close = min(prev["close"], curr_c)

            processed[-1] = {"open": min(prev["open"], curr_o), "high": new_high, "low": new_low, "close": new_close}
            continue

        # 无包含关系，直接保留
        processed.append({"open": curr_o, "high": curr_h, "low": curr_l, "close": curr_c})

    return processed


def find_fenxing(processed_klines: list[dict]) -> tuple[list[int], list[int]]:
    """
    识别顶底分型。
    顶分型：中间K线最高（high），两侧次高，同时收盘价也低于两侧
    底分型：中间K线最低（low），两侧次低，同时收盘价也高于两侧
    """
    tops: list[int] = []
    bottoms: list[int] = []

    for i in range(1, len(processed_klines) - 1):
        prev = processed_klines[i - 1]
        curr = processed_klines[i]
        next_k = processed_klines[i + 1]

        # 顶分型：中间K线最高，两侧次高（只看high）
        if curr["high"] > prev["high"] and curr["high"] > next_k["high"]:
            tops.append(i)

        # 底分型：中间K线最低，两侧次低（只看low）
        if curr["low"] < prev["low"] and curr["low"] < next_k["low"]:
            bottoms.append(i)

    return tops, bottoms


def build_bi(
    tops: list[int],
    bottoms: list[int],
    min_klines: int = 4,
) -> list[BiDict]:
    """
    构建笔：顶底分型交替，间隔至少min_klines根K线。
    返回格式为BiDict列表。
    """
    # 合并所有分型点
    all_points: list[tuple[int, str]] = [(t, "top") for t in tops] + [(b, "bottom") for b in bottoms]
    all_points.sort(key=lambda x: x[0])

    bi_list: list[BiDict] = []
    prev_idx: int | None = None
    prev_type: str | None = None

    for idx, ptype in all_points:
        if prev_idx is None:
            prev_idx = idx
            prev_type = ptype
            continue

        if ptype != prev_type:  # 顶底交替
            if idx - prev_idx >= min_klines:  # 间隔足够
                bi_list.append({"start": prev_idx, "end": idx, "type": prev_type})
            prev_type = ptype
            prev_idx = idx

    return bi_list


def build_segments(
    bi_list: list[BiDict],
    klines: list[dict],
    min_bi_count: int = 3,
) -> list[dict]:
    """
    将笔合并为线段：至少3笔构成一线段。
    检查方向一致性（上下上或下上下）。
    """
    if len(bi_list) < min_bi_count:
        return []

    segments: list[dict] = []
    i = 0

    while i <= len(bi_list) - min_bi_count:
        seg = bi_list[i : i + min_bi_count]
        # 线段方向：第1笔确定起始方向
        direction = "up" if seg[0]["type"] == "bottom" else "down"

        # 检查方向一致性：第1笔顶底，第2笔底顶，第3笔顶底（up情况）
        valid = True
        for j in range(len(seg) - 1):
            if seg[j]["type"] == seg[j + 1]["type"]:
                valid = False
                break

        if valid:
            segments.append({
                "start_idx": seg[0]["start"],
                "end_idx": seg[-1]["end"],
                "direction": direction,
                "bars": seg,
            })
        i += 1

    return segments


def find_zhongshu(
    bi_list: list[BiDict],
    klines: list[dict],
    min_overlap_bis: int = 3,
) -> list[ZongshuDict]:
    """
    识别线段中枢：连续min_overlap_bis笔有重叠区间。
    也可识别笔中枢（仅需3笔叠加）。
    """
    if len(bi_list) < min_overlap_bis:
        return []

    zhongshu_list: list[ZongshuDict] = []

    for i in range(len(bi_list) - min_overlap_bis + 1):
        group = bi_list[i : i + min_overlap_bis]

        # 计算每笔的价格区间
        ranges: list[tuple[float, float]] = []
        for bi in group:
            start, end = bi["start"], bi["end"]
            highs = [klines[j]["high"] for j in range(max(0, start), min(len(klines), end + 1))]
            lows = [klines[j]["low"] for j in range(max(0, start), min(len(klines), end + 1))]
            ranges.append((min(lows), max(highs)))

        # 计算重叠区间
        overlap_high = max(r[0] for r in ranges)
        overlap_low = min(r[1] for r in ranges)

        if overlap_low < overlap_high:  # 有重叠
            mid = group[len(group) // 2]
            zhongshu_list.append({
                "start_idx": group[0]["start"],
                "end_idx": group[-1]["end"],
                "zg": float(overlap_high),
                "zd": float(overlap_low),
                "gg": float(max(r[1] for r in ranges)),
                "dg": float(min(r[0] for r in ranges)),
                "mid_idx": (mid["start"] + mid["end"]) // 2,
                "source": "bi",
            })

    return zhongshu_list


def find_signals(
    bi_list: list[BiDict],
    zhongshu_list: list[ZongshuDict],
    klines: list[dict],
    macd: list[float] | None = None,
) -> SignalDict:
    """
    识别123买卖点。
    1买：底背驰（价格新低但MACD未新低）
    2买：回调不破1买低点
    3买：突破中枢后回踩不破中枢上轨
    1卖/2卖/3卖：对称逻辑
    """
    signals: SignalDict = {
        "buy_1": [],
        "buy_2": [],
        "buy_3": [],
        "sell_1": [],
        "sell_2": [],
        "sell_3": [],
    }

    if not klines:
        return signals

    prices = [k["close"] for k in klines]
    if macd is None:
        macd = [0] * len(klines)

    # ---- 1买/1卖：基于顶底分型 + MACD背驰 ----
    for i in range(5, len(klines) - 5):
        # 1买：价格创局部新低，但MACD没有创新低（底背驰）
        window_prices = prices[i - 5 : i]
        window_macd = macd[i - 5 : i]

        is_local_low = prices[i] <= min(window_prices)
        macd_not_new_low = macd[i] >= min(window_macd)
        if is_local_low and macd_not_new_low:
            signals["buy_1"].append(i)

        # 1卖：价格创局部新高，但MACD没有创新高（顶背驰）
        window_prices_high = prices[i - 5 : i]
        window_macd_high = macd[i - 5 : i]

        is_local_high = prices[i] >= max(window_prices_high)
        macd_not_new_high = macd[i] <= max(window_macd_high)
        if is_local_high and macd_not_new_high:
            signals["sell_1"].append(i)

    # ---- 2买：1买后向上运行，回调不破1买低点 ----
    for buy1_idx in signals["buy_1"]:
        # 在1买后寻找回调低点
        for j in range(buy1_idx + 1, min(buy1_idx + 20, len(klines))):
            if prices[j] < prices[buy1_idx]:
                signals["buy_2"].append(j)
                break

    # ---- 2卖：1卖后向下运行，反弹不破1卖高点 ----
    for sell1_idx in signals["sell_1"]:
        for j in range(sell1_idx + 1, min(sell1_idx + 20, len(klines))):
            if prices[j] > prices[sell1_idx]:
                signals["sell_2"].append(j)
                break

    # ---- 3买：突破中枢后，回踩不破中枢上轨 ----
    for zs in zhongshu_list:
        zg = zs["zg"]
        zd = zs["zd"]
        zs_end = zs["end_idx"]

        for i in range(zs_end, min(zs_end + 15, len(klines))):
            if prices[i] > zg:  # 突破中枢上轨
                # 检查后续回踩
                for j in range(i + 1, min(i + 15, len(klines))):
                    if prices[j] < zg and prices[j] > zd:
                        # 回踩确认，构成3买
                        signals["buy_3"].append(j)
                        break
                break

    # ---- 3卖：跌破中枢后，反弹不破中枢下轨 ----
    for zs in zhongshu_list:
        zd = zs["zd"]
        zg = zs["zg"]
        zs_end = zs["end_idx"]

        for i in range(zs_end, min(zs_end + 15, len(klines))):
            if prices[i] < zd:  # 跌破中枢下轨
                for j in range(i + 1, min(i + 15, len(klines))):
                    if prices[j] > zd and prices[j] < zg:
                        signals["sell_3"].append(j)
                        break
                break

    return signals


def full_analysis(klines: list[dict], macd: list[float] | None = None) -> ChanResult:
    """
    缠论完整分析流程。
    1. 处理包含关系
    2. 识别分型
    3. 构建笔
    4. 构建线段
    5. 识别中枢（线段中枢 = 3线段重叠，笔中枢 = 3笔重叠）
    6. 识别123买卖点
    """
    # 1. 包含关系处理
    processed = process_inclusion(klines)

    # 2. 分型识别
    tops, bottoms = find_fenxing(processed)

    # 3. 笔构建
    bi_list = build_bi(tops, bottoms, min_klines=4)

    # 4. 线段构建
    segments = build_segments(bi_list, processed, min_bi_count=3)

    # 5a. 笔中枢（3笔重叠）
    bi_zhongshu = find_zhongshu(bi_list, processed, min_overlap_bis=3)

    # 5b. 线段中枢（3线段重叠）- 基于线段构建
    segment_zhongshu = find_zhongshu_from_segments(segments, processed)

    # 合并两种中枢
    all_zhongshu = bi_zhongshu + segment_zhongshu

    # 6. 买卖点
    signals = find_signals(bi_list, all_zhongshu, processed, macd)

    return {
        "fenxing": {"tops": tops, "bottoms": bottoms},
        "bi": bi_list,
        "segments": segments,
        "zhongshu": all_zhongshu,
        "signals": signals,
    }


def find_zhongshu_from_segments(segments: list[dict], klines: list[dict]) -> list[ZongshuDict]:
    """从线段列表中识别线段中枢（连续3线段有重叠）。"""
    if len(segments) < 3:
        return []

    zhongshu_list: list[ZongshuDict] = []

    for i in range(len(segments) - 2):
        group = segments[i : i + 3]

        ranges: list[tuple[float, float]] = []
        for seg in group:
            start, end = seg["start_idx"], seg["end_idx"]
            highs = [klines[j]["high"] for j in range(max(0, start), min(len(klines), end + 1))]
            lows = [klines[j]["low"] for j in range(max(0, start), min(len(klines), end + 1))]
            ranges.append((min(lows), max(highs)))

        overlap_high = max(r[0] for r in ranges)
        overlap_low = min(r[1] for r in ranges)

        if overlap_low < overlap_high:
            mid = group[1]
            zhongshu_list.append({
                "start_idx": group[0]["start_idx"],
                "end_idx": group[-1]["end_idx"],
                "zg": float(overlap_high),
                "zd": float(overlap_low),
                "gg": float(max(r[1] for r in ranges)),
                "dg": float(min(r[0] for r in ranges)),
                "mid_idx": (mid["start_idx"] + mid["end_idx"]) // 2,
                "source": "segment",
            })

    return zhongshu_list


# ---- 技术指标 ----

def calc_macd(closes: list[float], fast: int = 12, slow: int = 26, signal: int = 9) -> tuple[list[float], list[float], list[float]]:
    """计算MACD指标。"""
    if len(closes) < slow:
        return [], [], []

    ema_fast = _ema(closes, fast)
    ema_slow = _ema(closes, slow)
    macd = [f - s for f, s in zip(ema_fast, ema_slow, strict=True)]
    sig = _ema(macd, signal)
    hist = [m - s for m, s in zip(macd, sig, strict=True)]

    return macd, sig, hist


def calc_ma(closes: list[float], periods: list[int] = None) -> dict[int, list[float]]:
    """计算MA均线。"""
    if periods is None:
        periods = [5, 10, 20, 60]
    result = {}
    for p in periods:
        result[p] = _sma(closes, p)
    return result


def calc_boll(closes: list[float], length: int = 20, std_dev: float = 2.0) -> tuple[list[float], list[float], list[float]]:
    """计算布林带。"""
    if len(closes) < length:
        return [], [], []

    mid = _sma(closes, length)
    upper: list[float] = []
    lower: list[float] = []

    for i in range(len(closes)):
        if i < length - 1:
            upper.append(0.0)
            lower.append(0.0)
        else:
            window = closes[i - length + 1 : i + 1]
            std = (sum((x - mid[i]) ** 2 for x in window) / length) ** 0.5
            upper.append(mid[i] + std_dev * std)
            lower.append(mid[i] - std_dev * std)

    return upper[:len(closes)], mid[:len(closes)], lower[:len(closes)]


def calc_rsi(closes: list[float], length: int = 14) -> list[float]:
    """计算RSI指标。"""
    if len(closes) < length + 1:
        return [50.0] * len(closes)

    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]

    avg_gain = sum(gains[:length]) / length
    avg_loss = sum(losses[:length]) / length

    rsi = [50.0] * length
    for i in range(length, len(closes)):
        avg_gain = (avg_gain * (length - 1) + gains[i - 1]) / length
        avg_loss = (avg_loss * (length - 1) + losses[i - 1]) / length
        if avg_loss == 0:
            rsi.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi.append(100 - 100 / (1 + rs))

    return rsi


def calc_kdj(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    n: int = 9,
) -> tuple[list[float], list[float], list[float]]:
    """计算KDJ指标。"""
    if len(closes) < n:
        return [50.0] * len(closes), [50.0] * len(closes), [50.0] * len(closes)

    k = [50.0] * n
    d = [50.0] * n
    j = [50.0] * n

    for i in range(n, len(closes)):
        low_n = min(lows[i - n : i])
        high_n = max(highs[i - n : i])
        rsv = (closes[i] - low_n) / (high_n - low_n) * 100 if high_n > low_n else 50
        k.append(k[-1] * 2 / 3 + rsv / 3)
        d.append(d[-1] * 2 / 3 + k[-1] / 3)
        j.append(3 * k[-1] - 2 * d[-1])

    return k[:len(closes)], d[:len(closes)], j[:len(closes)]


def calc_obv(closes: list[float], volumes: list[float]) -> list[float]:
    """计算OBV能量潮。"""
    if len(closes) < 2:
        return [0.0] * len(closes)

    obv = [0.0]
    for i in range(1, len(closes)):
        if closes[i] > closes[i - 1]:
            obv.append(obv[-1] + volumes[i])
        elif closes[i] < closes[i - 1]:
            obv.append(obv[-1] - volumes[i])
        else:
            obv.append(obv[-1])
    return obv


def calc_cci(highs: list[float], lows: list[float], closes: list[float], length: int = 14) -> list[float]:
    """计算CCI顺势指标。"""
    if len(closes) < length:
        return [0.0] * len(closes)

    cci = [0.0] * (length - 1)
    for i in range(length - 1, len(closes)):
        tp = (highs[i] + lows[i] + closes[i]) / 3
        sma = sum(closes[i - length + 1 : i + 1]) / length
        mad = sum(abs(c - sma) for c in closes[i - length + 1 : i + 1]) / length
        cci.append((tp - sma) / (0.015 * mad) if mad != 0 else 0)

    return cci


def calc_stoch_rsi(closes: list[float], length: int = 14, smooth_k: int = 3, smooth_d: int = 3) -> tuple[list[float], list[float]]:
    """计算Stochastic RSI。"""
    if len(closes) < length:
        return [50.0] * len(closes), [50.0] * len(closes)

    rsi = calc_rsi(closes, length)
    stoch_rsi = [50.0] * len(closes)

    for i in range(length, len(closes)):
        window = rsi[i - length + 1 : i + 1]
        min_rsi = min(window)
        max_rsi = max(window)
        if max_rsi > min_rsi:
            stoch_rsi[i] = (rsi[i] - min_rsi) / (max_rsi - min_rsi) * 100

    k = _sma(stoch_rsi[length - 1 :], smooth_k)
    d = _sma(k, smooth_d)

    result_k = [50.0] * (length - 1 + smooth_k - 1) + k
    result_d = [50.0] * (length - 1 + smooth_k - 1 + smooth_d - 1) + d

    return result_k[:len(closes)], result_d[:len(closes)]


# ---- 内部辅助 ----

def _ema(data: list[float], period: int) -> list[float]:
    """计算指数移动平均。"""
    if len(data) < period:
        return data
    k = 2 / (period + 1)
    result = [data[0]]
    for v in data[1:]:
        result.append(result[-1] * (1 - k) + v * k)
    return result


def _sma(data: list[float], period: int) -> list[float]:
    """计算简单移动平均。"""
    if len(data) < period:
        return [0.0] * len(data)
    result: list[float] = []
    for i in range(len(data)):
        if i < period - 1:
            result.append(0.0)
        else:
            result.append(sum(data[i - period + 1 : i + 1]) / period)
    return result
