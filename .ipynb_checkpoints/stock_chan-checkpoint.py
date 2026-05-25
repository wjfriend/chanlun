import akshare as ak
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import pandas_ta as ta  # 技术指标库

# ================== 1. 获取A股日线数据 ==================
def get_stock_data(symbol="000001", start="20230101", end="20241231"):
    """
    获取A股历史数据，symbol: 6位代码，如'000001'（平安银行）
    """
    df = ak.stock_zh_a_hist(symbol, period="daily", start_date=start, end_date=end, adjust="qfq")
    df.rename(columns={"日期":"date", "开盘":"open","收盘":"close","最高":"high","最低":"low","成交量":"volume"}, inplace=True)
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    return df

# ================== 2. 技术指标（MACD, KDJ, RSI, BOLL）==================
def add_indicators(df):
    df['MACD'] = ta.macd(df['close'], fast=12, slow=26, signal=9)['MACD_12_26_9']
    df['MACD_signal'] = ta.macd(df['close'])['MACDs_12_26_9']
    df['MACD_hist'] = ta.macd(df['close'])['MACDh_12_26_9']
    
    df['RSI'] = ta.rsi(df['close'], length=14)
    
    # KDJ
    df['K'], df['D'] = ta.stoch(df['high'], df['low'], df['close'])[:2]
    df['J'] = 3 * df['K'] - 2 * df['D']
    
    # BOLL
    boll = ta.bbands(df['close'], length=20, std=2)
    df['BOLL_upper'] = boll['BBU_20_2.0']
    df['BOLL_mid'] = boll['BBM_20_2.0']
    df['BOLL_lower'] = boll['BBL_20_2.0']
    return df

# ================== 3. 缠论核心：分型、笔、线段、中枢 ==================
def find_pivots(df, left=2, right=2):
    """
    寻找顶底分型
    left: 左边K线数, right: 右边K线数
    """
    highs = df['high'].values
    lows = df['low'].values
    tops = []
    bottoms = []
    for i in range(left, len(df)-right):
        if all(highs[i] >= highs[i-j] for j in range(1, left+1)) and \
           all(highs[i] >= highs[i+j] for j in range(1, right+1)):
            tops.append(i)
        if all(lows[i] <= lows[i-j] for j in range(1, left+1)) and \
           all(lows[i] <= lows[i+j] for j in range(1, right+1)):
            bottoms.append(i)
    return tops, bottoms

def draw_chan_lines(df, tops, bottoms):
    """
    画笔（简化版：顶底交替连接）
    实际笔还需要过滤包含关系等，这里做演示
    """
    points = []
    all_idx = sorted(tops + bottoms)
    types = {i:'top' for i in tops}
    types.update({i:'bottom' for i in bottoms})
    prev = None
    for idx in all_idx:
        if prev is not None:
            if types[prev] != types[idx]:  # 交替
                points.append((prev, idx))
        prev = idx
    return points

# 简易中枢识别（价格重叠区间）
def find_centers(df, points, k=3):
    """
    在笔形成的区间中寻找至少3笔重叠的区间
    """
    centers = []
    for i in range(len(points)-2):
        p1_start, p1_end = points[i]
        p2_start, p2_end = points[i+1]
        p3_start, p3_end = points[i+2]
        # 取这三笔的价格区间
        range1 = (min(df.iloc[p1_start]['low'], df.iloc[p1_end]['low']),
                  max(df.iloc[p1_start]['high'], df.iloc[p1_end]['high']))
        range2 = (min(df.iloc[p2_start]['low'], df.iloc[p2_end]['low']),
                  max(df.iloc[p2_start]['high'], df.iloc[p2_end]['high']))
        range3 = (min(df.iloc[p3_start]['low'], df.iloc[p3_end]['low']),
                  max(df.iloc[p3_start]['high'], df.iloc[p3_end]['high']))
        # 重叠部分
        low = max(range1[0], range2[0], range3[0])
        high = min(range1[1], range2[1], range3[1])
        if low < high:
            centers.append((low, high, (p1_end + p3_end)//2))
    return centers

# 123买卖点（简化示例：1买=底背驰，2买=回调不破1买，3买=上涨中枢上轨突破）
def find_trading_signals(df, centers):
    signals = {'buy_1':[], 'buy_2':[], 'buy_3':[], 'sell':[]}
    # 这里只是框架，真实需要结合MACD背驰和中枢位置
    # 演示：假设MACD金叉为1买，死叉为卖点
    for i in range(1, len(df)-1):
        if df['MACD'].iloc[i-1] < df['MACD_signal'].iloc[i-1] and df['MACD'].iloc[i] > df['MACD_signal'].iloc[i]:
            signals['buy_1'].append(i)
        if df['MACD'].iloc[i-1] > df['MACD_signal'].iloc[i-1] and df['MACD'].iloc[i] < df['MACD_signal'].iloc[i]:
            signals['sell'].append(i)
    return signals

# ================== 4. 选股策略（示例：MACD金叉+RSI<30超卖）==================
def select_stocks(stock_list, start, end):
    candidates = []
    for code in stock_list:
        try:
            df = get_stock_data(code, start, end)
            df = add_indicators(df)
            last = df.iloc[-1]
            if last['MACD'] > last['MACD_signal'] and last['RSI'] < 30:
                candidates.append(code)
        except:
            continue
    return candidates

# ================== 5. 简单回测（买入持有）==================
def backtest(df, signals, initial_cash=100000, buy_sell_cost=0.0003):
    cash = initial_cash
    position = 0
    equity = []
    for i in range(len(df)):
        price = df.iloc[i]['close']
        # 买入信号
        if i in signals['buy_1'] and cash > 0:
            shares = cash // (price * (1+buy_sell_cost))
            cash -= shares * price * (1+buy_sell_cost)
            position += shares
        # 卖出信号
        if i in signals['sell'] and position > 0:
            cash += position * price * (1-buy_sell_cost)
            position = 0
        equity.append(cash + position * price)
    df['equity'] = equity
    total_return = (equity[-1] - initial_cash)/initial_cash * 100
    return total_return, equity

# ================== 6. 主程序：绘图 & 运行 ==================
if __name__ == "__main__":
    # 参数
    stock_code = "000001"  # 平安银行，可改成其他
    start_date = "2023-01-01"
    end_date = "2024-12-31"
    
    # 获取数据
    print(f"获取 {stock_code} 数据...")
    df = get_stock_data(stock_code, start_date, end_date)
    df = add_indicators(df)
    
    # 缠论分型
    tops, bottoms = find_pivots(df)
    points = draw_chan_lines(df, tops, bottoms)
    centers = find_centers(df, points)
    signals = find_trading_signals(df, centers)
    
    # 回测
    ret, equity_curve = backtest(df, signals)
    print(f"策略总收益率: {ret:.2f}%")
    
    # 绘图
    fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=True)
    # 子图1：K线 + 缠论笔/中枢
    ax1 = axes[0]
    ax1.plot(df.index, df['close'], label='Close Price', color='black', linewidth=1)
    # 画笔
    for (start_idx, end_idx) in points:
        ax1.plot([df.index[start_idx], df.index[end_idx]], 
                 [df.iloc[start_idx]['close'], df.iloc[end_idx]['close']], 
                 'r-', linewidth=2, label='Bi' if start_idx==points[0][0] else "")
    # 画中枢（矩形）
    for (low, high, mid_idx) in centers:
        x0 = df.index[mid_idx - 5] if mid_idx-5>=0 else df.index[0]
        x1 = df.index[mid_idx + 5] if mid_idx+5<len(df) else df.index[-1]
        rect = Rectangle((x0, low), x1-x0, high-low, alpha=0.3, color='yellow')
        ax1.add_patch(rect)
    # 买卖点
    for i in signals['buy_1']:
        ax1.scatter(df.index[i], df.iloc[i]['low']*0.98, marker='^', color='green', s=100, label='1买' if i==signals['buy_1'][0] else "")
    for i in signals['sell']:
        ax1.scatter(df.index[i], df.iloc[i]['high']*1.02, marker='v', color='red', s=100, label='卖点' if i==signals['sell'][0] else "")
    ax1.set_title(f"{stock_code} 缠论自动画线 + 123买卖点（示例）")
    ax1.legend()
    ax1.grid(True)
    
    # 子图2：MACD
    ax2 = axes[1]
    ax2.bar(df.index, df['MACD_hist'], color=['green' if v>=0 else 'red' for v in df['MACD_hist']], alpha=0.5)
    ax2.plot(df.index, df['MACD'], label='MACD')
    ax2.plot(df.index, df['MACD_signal'], label='Signal')
    ax2.legend()
    ax2.grid(True)
    
    # 子图3：资金曲线
    ax3 = axes[2]
    ax3.plot(df.index, df['equity'], label='Strategy Equity', color='blue')
    ax3.set_ylabel('Equity')
    ax3.legend()
    ax3.grid(True)
    
    plt.tight_layout()
    plt.show()