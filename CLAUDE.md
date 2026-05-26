# chanlun 项目协作规范

## 角色分工

| 角色 | 职责 |
|------|------|
| **Claude Code** | 写代码、修复 bug、功能实现 |
| **克洛伊 (Chloe)** | 验证、测试、审核、进度汇报 |

Claude Code 已有完整项目规范（本文件），按其规范执行即可。

## 协作流程

1. 克洛伊把需求拆成**小任务**（每次一个独立问题）发给 Claude Code
2. Claude Code 完成代码修改
3. 克洛伊验证：运行测试、`make verify`、启动服务人工确认
4. 验证通过后：
   - 更新 `实现.txt` 记录本次改动
   - Git commit（分成小段，不要等全部完成才提交）
5. 验证失败：反馈给 Claude Code 继续修改

## 任务拆分原则

- 每个任务的改动**不超过 3-5 个文件**
- 每个 commit **只做一个类型的改动**（如：只修分型算法、只修中枢渲染）
- 这样方便回滚，也方便查看进度

## 进度汇报

- 每 **15 分钟**自动检查 Claude Code 进度
- 推送格式：
  ```
  📊 进度报告 [时间]
  任务：xxx
  状态：进行中/已完成/阻塞
  最近改动：xxx
  测试结果：pass/fail
  ```

## 进程监控

- 每 15 分钟检查项目文件是否有更新（LastWriteTime）
- 如果 **10 分钟无文件更新且进程还在运行**：
  - 查看进程是否卡死
  - 必要时 `kill` 重启 Claude Code

## 版本推送

- 每个**大功能修复验证通过**后立即 git commit + push
- Commit 格式：`fix(scope): description` / `feat(scope): description`

## 变更记录

每次完成任务后更新 `E:\WW\chanlun\实现.txt`，格式：

```
### [时间] 完成 xxx
- 修改文件：xxx
- 验证方式：xxx
- 测试结果：pass/fail
```

---

*本文档由克洛伊维护*


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

## 约束

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