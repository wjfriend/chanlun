"""
诊断缠论算法Bug - 用简单已知数据验证各函数行为
"""
import sys
sys.path.insert(0, '.')

from services.chan import process_inclusion, find_fenxing, build_bi, build_segments, find_zhongshu, find_signals, full_analysis, calc_macd

print("=" * 70)
print("测试1: process_inclusion - 包含关系处理")
print("=" * 70)
# 三根K线形成向上的包含关系
klines_up = [
    {"open": 10.0, "high": 10.5, "low": 9.8, "close": 10.2},
    {"open": 10.2, "high": 10.8, "low": 9.9, "close": 10.6},  # prev包含curr
    {"open": 10.6, "high": 11.0, "low": 10.5, "close": 10.8},
]
print("输入:", [(k["open"], k["high"], k["low"], k["close"]) for k in klines_up])
processed = process_inclusion(klines_up)
print("输出:", [(k["open"], k["high"], k["low"], k["close"]) for k in processed])
print(f"期望: 2根K线 | 实际: {len(processed)}根")
print()

# 三根K线形成向下的包含关系
klines_down = [
    {"open": 10.8, "high": 11.0, "low": 10.2, "close": 10.5},
    {"open": 10.5, "high": 10.9, "low": 9.8, "close": 10.2},  # prev包含curr（向上）
    {"open": 10.2, "high": 10.5, "low": 9.6, "close": 9.8},
]
print("输入(向下):", [(k["open"], k["high"], k["low"], k["close"]) for k in klines_down])
processed2 = process_inclusion(klines_down)
print("输出:", [(k["open"], k["high"], k["low"], k["close"]) for k in processed2])
print()

print("=" * 70)
print("测试2: build_bi - 笔的交替连接")
print("=" * 70)
# 顶底分型[1,3,6,9]，间隔都是2（不够4）
tops = [3]
bottoms = [1, 6, 9]
print(f"顶={tops}, 底={bottoms}, 期望间隔>=4")
bi = build_bi(tops, bottoms, min_klines=4)
print(f"笔结果: {bi}")
print(f"期望: 空列表(因为1到3间隔2<4) | 实际: {bi}")
print()

# 现在用够间隔的数据
tops2 = [5]
bottoms2 = [1, 10]
print(f"顶={tops2}, 底={bottoms2}, 间隔1->10=9>=4, 10->5=5>=4")
bi2 = build_bi(tops2 + [], bottoms2, min_klines=4)
print(f"笔: {bi2}")
print()

# 更复杂：多个顶底交替
# 顶: 3, 底: 1, 顶: 6, 底: 10, 顶: 14
# 两顶之间至少需要4根K线
all_points = [(1, "bottom"), (3, "top"), (6, "bottom"), (10, "top"), (14, "bottom")]
# (1, bot) -> (3, top): 间隔2 < 4, 不构成笔
# (3, top) -> (6, bot): 间隔3 < 4, 不构成笔
print(f"交替点: {all_points}, 两两间隔都<4，期望无笔")
bi3 = build_bi([3, 6, 10], [1, 6, 10, 14], min_klines=4)
print(f"笔: {bi3}")
print()

print("=" * 70)
print("测试3: build_segments - 线段方向逻辑")
print("=" * 70)
# 3笔完全同向(都是bottom->top->bottom)，不应该构成线段
bi_list = [
    {"start": 0, "end": 5, "type": "bottom"},
    {"start": 5, "end": 10, "type": "top"},
    {"start": 10, "end": 15, "type": "bottom"},
]
klines = [{"open": 10, "high": 11, "low": 9, "close": 10}] * 20
segs = build_segments(bi_list, klines, min_bi_count=3)
print(f"笔列表: {[(b['start'], b['end'], b['type']) for b in bi_list]}")
print(f"线段结果: {[(s['start_idx'], s['end_idx'], s['direction']) for s in segs]}")
print(f"期望: 有线段(bottom->top->bottom=up) | 实际: {'有线段' if segs else '无线段'}")
print()

# 同type相邻笔
bi_same = [
    {"start": 0, "end": 5, "type": "bottom"},
    {"start": 5, "end": 10, "type": "bottom"},  # 同type，不应该构成线段
    {"start": 10, "end": 15, "type": "top"},
]
segs2 = build_segments(bi_same, klines, min_bi_count=3)
print(f"相邻同type笔: {[(b['start'], b['end'], b['type']) for b in bi_same]}")
print(f"线段结果: {[(s['start_idx'], s['end_idx'], s['direction']) for s in segs2]}")
print(f"期望: 0条线段(因为第1、2笔同type) | 实际: {len(segs2)}条")
print()

print("=" * 70)
print("测试4: find_signals - 买卖点识别")
print("=" * 70)
# 简单数据，测试1买
klines_simple = [
    {"close": 10.0, "open": 10.0, "high": 10.0, "low": 10.0},
] * 30
# 制造一个局部最低点
klines_simple[10] = {"close": 8.0, "open": 8.0, "high": 8.0, "low": 8.0}
klines_simple[15] = {"close": 8.5, "open": 8.5, "high": 8.5, "low": 8.5}

macd = [0.0] * 30
macd[10] = -1.0  # 局部最低，但macd值不是全局最低

bi_list_sig = [
    {"start": 0, "end": 8, "type": "bottom"},
    {"start": 8, "end": 12, "type": "top"},
    {"start": 12, "end": 20, "type": "bottom"},
]
zs_list = []
signals = find_signals(bi_list_sig, zs_list, klines_simple, macd)
print(f"1买: {signals['buy_1']}")
print(f"期望: 包含索引10(局部最低) | 实际: {signals['buy_1']}")
print(f"2买: {signals['buy_2']}")
print()

print("=" * 70)
print("测试5: full_analysis - 完整流程（真实市场数据模式）")
print("=" * 70)
# 生成更多数据的简单测试
import random
random.seed(42)
klines_real = []
base = 10.0
for i in range(50):
    open_p = base + random.uniform(-0.3, 0.3)
    close_p = open_p + random.uniform(-0.5, 0.5)
    high_p = max(open_p, close_p) + random.uniform(0, 0.3)
    low_p = min(open_p, close_p) - random.uniform(0, 0.3)
    klines_real.append({"open": open_p, "high": high_p, "low": low_p, "close": close_p})
    base = close_p

closes = [k["close"] for k in klines_real]
macd_vals, _, _ = calc_macd(closes)
result = full_analysis(klines_real, macd_vals)
print(f"输入K线: {len(klines_real)}根")
print(f"处理后K线: {len(result['processed_klines'])}根")
print(f"分型顶: {result['fenxing']['tops']}")
print(f"分型底: {result['fenxing']['bottoms']}")
print(f"笔数量: {len(result['bi'])}")
print(f"线段数量: {len(result['segments'])}")
print(f"中枢数量: {len(result['zhongshu'])}")
print(f"1买: {result['signals']['buy_1']}")
print(f"1卖: {result['signals']['sell_1']}")