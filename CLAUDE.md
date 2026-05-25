# chanlun - 缠论画线分析选股策略

## Project Overview

缠论是一种基于形态分析的技术分析方法，本项目实现：
- 标准缠论算法：分型→笔→线段→中枢→买卖点
- 交互式Web可视化（K线图、笔、中枢、买卖点）
- 选股策略和回测功能

## Commands

```bash
# 验证项目（lint + typecheck）
make verify

# 完整验证（含测试）
make verify-full

# Lint 检查
make lint

# 类型检查
make typecheck

# 关键测试（快速）
make test-critical

# 完整测试
make test-full

# 本地开发服务器
flask run 或 python app.py
```

## Architecture

```
chanlun/
├── api/              # 参数校验和协议转换（不许查数据库）
├── services/         # 业务逻辑（缠论算法 calc_ma/calc_macd 等）
├── repositories/     # 数据访问层
├── app.py            # Flask 应用入口，路由和数据获取
├── stock_chan.py     # 命令行缠论分析入口
├── static/           # 前端资源
│   ├── style.css
│   ├── main.js
│   ├── lightweight-charts.standalone.production.js  # TradingView lightweight-charts v5.2.0
│   └── lightweight-charts-drawing.umd.js             # lightweight-charts-drawing v0.1.1 (68种画图工具)
├── templates/        # HTML 模板
│   ├── index.html   # 首页（股票代码输入）
│   ├── chart.html   # Plotly 图表页
│   └── tv_chart.html # TradingView 图表页（含 DrawingManager 画图工具）
├── tests/            # 测试文件
├── docs/             # 文档
├── TV_charting_lib/  # 外部依赖（TradingView 图表库源码，参考用）
├── CLAUDE.md         # 本文件
├── requirements.txt  # Python 依赖
└── Makefile          # 构建命令
```

> **注意**: `文件结构如有变动，每次请求完成后自动更新本 Architecture 部分。`

## Constraints

1. **api/ 只做参数校验和协议转换** - 不包含业务逻辑
2. **业务逻辑放 services/** - 缠论算法、技术指标计算
3. **数据库操作放 repositories/** - 数据获取和存储
4. **路由层不许直接查数据库** - 必须通过 repositories

## Testing

```bash
# 运行关键测试
pytest tests/ -m "not slow"

# 运行所有测试
pytest tests/

# 带覆盖率
pytest --cov=. --cov-report=term-missing
```

## Conventions

1. **Python**: PEP 8, 类型注解 required
2. **Git**: 提交信息格式 `type(scope): description`
3. **API**: RESTful, JSON 响应 `{success, data, error}`
4. **命名**:
   - 函数: `snake_case`
   - 类: `PascalCase`
   - 常量: `UPPER_SNAKE_CASE`
5. **缠论术语**: 顶分型/底分型/笔/线段/中枢/123买卖点

### 请求处理

1. **每次一个请求修复一个问题**: 多个独立问题时，分成多个请求依次完成，每次只改一件事，避免一次性大批量修改导致难以追踪和回滚
2. **文件结构变动后自动更新本文件的 Architecture 部分**: 每次请求完成后检查文件结构，如有变化立即更新 CLAUDE.md 中的 Architecture 段，保持文档与实际结构同步
3. **TODO 列表**: 多步骤任务使用 TodoWrite 跟踪进度
4. 每次请求做了哪些改动实现了什么功能写入E:\WW\chanlun实现.txt 带时间戳

## Self-Check

执行 `make verify` 前自查：

1. **语法错误**: `ruff check .`
2. **类型错误**: `pyright`
3. **Import 正确**: 无循环依赖
4. **API 路径**: 已注册、无重复
5. **测试覆盖**: 核心算法有测试
6. **文档更新**: 决策已记录（DECISIONS.md）

## Self-Heal Protocol

`make verify` 失败后自动修复流程（最多 3 轮）：

1. **Round 1**: `ruff check --fix .` 自动修复
2. **Round 2**: 手动检查错误，修复后重跑
3. **Round 3**: 修复后仍失败，输出完整错误日志等待人工介入

## Change Log

| 日期 | 版本 | 变更内容 |
|------|------|----------|
| 2026-05-16 | 0.1.0 | 初始化项目结构，Flask + 缠论算法框架 |
| 2026-05-16 | 0.2.0 | 添加 TradingView 图表页（tv_chart.html），集成 lightweight-charts v5.2.0 和 lightweight-charts-drawing v0.1.1（68种画图工具），支持 BOLL/RSI/OBV/CCI/StochRSI 指标多 pane 显示，完善缠论买卖点渲染 |
| 2026-05-16 | 0.2.1 | 完善 CLAUDE.md：加入请求处理规则（每次一个请求修复一个问题），更新 Architecture 反映实际文件结构 |