# 缠论 Bug 诊断报告 (2026-05-26)

## 测试环境
- 项目路径: E:\WW\chanlun
- 测试文件: diagnose_bugs.py (已创建)

## 已确认Bug列表

### Bug 1: build_bi 笔构建缺少顶分型 (严重)
**文件**: services/chan.py, build_bi()
**问题**: 第163行，当分型类型为顶分型时，`type` 被设为 `None`，因为 `ptype` 变量被覆盖为下一个分型
**代码**:
```python
prev_type = ptype  # ← 第159行保存了旧type
ptype = "top" if ptype == "bottom" else "bottom"  # ← 第160行改变了ptype
bi_list.append({"start": prev_idx, "end": idx, "type": prev_type})  # ← 第163行 type=prev_type(旧) ✓
```
**症状**: 所有笔的 type 全是 "bottom"

**修复**: 检查 ptype 是否为 None，添加类型判断：
```python
for idx, ptype in all_points:
    if prev_idx is None:
        prev_idx = idx
        prev_type = ptype  # bottom or top
        continue

    if ptype != prev_type:
        if idx - prev_idx >= min_klines:
            # 注意：prev_type 是正确的，ptype 是新类型
            bi_type = prev_type if prev_type in ("bottom", "top") else ptype
            bi_list.append({"start": prev_idx, "end": idx, "type": bi_type})
        prev_type = ptype  # ← BUG: 这里直接覆盖了，但应该是交替
        prev_idx = idx
```
**正确逻辑**: 
```python
if ptype != prev_type:  # 类型交替
    if idx - prev_idx >= min_klines:
        bi_list.append({"start": prev_idx, "end": idx, "type": prev_type})
    prev_type = ptype  # 交替为新类型
    prev_idx = idx
```

---

### Bug 2: process_inclusion 向下走势融合错误 (严重)
**文件**: services/chan.py, process_inclusion()
**问题**: 向下走势融合时 `new_close` 用 `max` 而不是 `min`，且 `new_open` 计算了但未使用
**错误代码**:
```python
if trend == "up":
    new_high = max(prev_h, curr_h)
    new_low = max(prev_l, curr_l)  # 正确：向上取高值作为区间下界
    new_close = max(prev_c, curr_c)
else:
    new_high = min(prev_h, curr_h)
    new_low = min(prev_l, curr_l)   # 向下取低值
    new_close = max(prev_c, curr_c)  # ← BUG: 应该是 min
    new_open = min(prev_o, curr_o)  # ← 计算了但return里没有用
```
**正确代码**:
```python
if trend == "up":
    new_high = max(prev_h, curr_h)
    new_low = max(prev_l, curr_l)
    new_close = max(prev_c, curr_c)
    new_open = max(prev_o, curr_o)  # 也可以用 max
else:
    new_high = min(prev_h, curr_h)
    new_low = min(prev_l, curr_l)
    new_close = min(prev_c, curr_c)  # 向下：取最低收盘
    new_open = min(prev_o, curr_o)
```

---

### Bug 3: build_bi 笔数量过少 (中等)
**文件**: services/chan.py, build_bi()
**问题**: build_bi 跳过了交替后的第一个分型点（prev_idx/prev_type只更新一次，导致第一个笔的终点变成起点，参与第二次笔构建时方向不对）
**症状**: 只有2笔，线段0条

**分析**: 笔交替逻辑问题
```python
# 当前代码：
for idx, ptype in all_points:
    if prev_idx is None:
        prev_idx = idx; prev_type = ptype; continue
    if ptype != prev_type:
        if idx - prev_idx >= min_klines:
            bi_list.append({"start": prev_idx, "end": idx, "type": prev_type})
        prev_type = ptype  # ← 只更新了一次
        prev_idx = idx
```
问题：当间隔不够时，prev_type 被更新为 ptype，但 prev_idx 也更新了。这意味着交替后，下一个笔的起点是"不够间隔的那个点"，而不是上一个有效笔的终点。

**建议**: 只有在构成笔时才更新 prev_type；否则保留上一个有效分型

---

### Bug 4: build_segments 方向检测不完整 (中等)
**文件**: services/chan.py, build_segments()
**问题**: 只检查相邻笔类型是否相同，但第一笔和第三笔即使类型相同也通过了检测
**示例**: bottom→top→bottom（有效）vs bottom→bottom→top（无效）
- 当前代码对两种情况都正确返回0
- 但问题是：只检查了"相邻是否同type"，没有检查"第一笔和第三笔的顺序是否正确"

**分析**: 当前逻辑实际上正确（只检查相邻），但可以加强

---

### Bug 5: find_signals 1买识别逻辑 (低)
**文件**: services/chan.py, find_signals()
**问题**: 1买/1卖的识别只看"局部最低/最高"，不看MACD背驰
**代码**:
```python
is_local_low = prices[i] <= min(window_prices)
macd_not_new_low = macd[i] >= min(window_macd)
```
这个逻辑是对的（价格新低但MACD没新低=底背驰），但信号过多

---

## 前端渲染问题
**文件**: templates/tv_chart.html
**问题**: addZhongshu() 用 candlestickSeries 绘制矩形框
```javascript
const series = chart.addSeries(window._cs, {...});  // CandlestickSeries
series.setData([{time: t0, open: midPrice, high: wickHigh, low: wickLow, close: midPrice}, ...]);
```
这种方式只能画出上下影线，不适合画矩形（矩形需要专门的矩形绘制工具）

---

## 修复优先级
1. Bug 1 (build_bi顶分型type=None) - 导致所有笔方向错误
2. Bug 2 (向下走势new_close=max错误) - 导致包含关系处理错误
3. Bug 3 (build_bi笔数量少) - 次要逻辑问题
4. 前端中枢渲染 - 需要用矩形工具

## 验证方法
运行 diagnose_bugs.py 可重现问题