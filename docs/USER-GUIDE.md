# 用户指南

## 快速开始

### 启动 Web 服务

```bash
cd /path/to/investing
uvicorn main:app --reload
# 访问 http://localhost:8000
```

### 目录结构速览

```
companies/          # 公司档案（每个公司一个目录）
industries/         # 行业档案
arenas/             # 竞技场档案
claims/             # Claim 注册表（JSONL 文件）
data/financials.db  # SQLite 财务数据库
watchlist/          # 观察池
portfolio/          # 持仓、规则、触发器
journal/            # 决策日志
scripts/            # CLI 工具脚本
```

## 日常使用流程

### 1. 研究新标的

**步骤**：创建公司 → 填写 V0 论点 → 设置估值场景 → 加入观察池

1. 在 `/companies` 页面创建新公司（或使用 ingest 流程自动创建）
2. 编辑 `v0.md`（7 节模板：买入逻辑、差异化观点、估值锚、买入区间、卖出触发、什么不算推翻、当前状态）
3. 设置 `valuation.md`（三场景估值：bull / base / bear + 概率）
4. 加入对应阶段的 watchlist：`watchlist/researching.md`

### 2. Ingest 研究报告

这是向系统导入外部研究（行业报告、年报等）的标准流程。

**输入**：一份 PDF 研究报告

**执行步骤**（在 Claude 对话中完成）：

1. 运行 `preprocess_report.py` 提取 PDF 章节结构
2. Claude 执行 review-bundle，从报告中提取 claim candidates、insight blocks、atomic facts
3. （可选）运行 `ingest_qa` 检查质量
4. 运行 `ingest_match.py` 匹配已有 claims
5. 审查匹配结果，填写决策（new / attach / split / skip）
6. 运行 `ingest_apply.py` 应用决策到 ClaimRegistry
7. 对每个受影响的 scope 运行 `narrative_propose.py` 生成叙事提案
8. 审查提案，填写决策（approve / edit / reject / defer）
9. 运行 `narrative_apply.py` 写入叙事档案
10. 运行 `narrative_flags.py` 扫描一致性标记

**注意事项**：
- 行业报告必须同时挖 industry 和 arena 两层 claim，否则会严重低估叙事覆盖
- 对多战场行业报告（如宠物 / 美妆 / 新能源），要显式列出所有可能涉及的 arena slugs
- ingest 遇到失败时正向修复（改模版 / 正则 / 白名单），不手工抽取

### 3. 执行交易

**步骤**：检查触发器 → 执行 → 记录决策日志

1. 查看 `/triggers` 是否有价格触发
2. 查看 `/catalysts` 是否有即将到期的催化事件
3. 查看 `/regime` 确认当前宏观环境
4. 执行交易
5. 在 `journal/decisions/{YYYY}-Q{n}/` 创建决策文件
6. 更新 `portfolio/positions.md`
7. 拍快照保存 V0 状态到 `v0_snapshot_path`

### 4. 季度审查

每季度末执行：

1. 查看 `/discipline` 确认是否有未评审的决策
2. 查看 `/review` 填写季度审查
3. 更新 `/regime` 宏观判定
4. 查看 `/performance` 收益归因
5. 检查 `/qa` 质量缺口
6. 对决策文件补充 `pnl_3m` / `result_quality` / `result_luck_factor` 等事后指标

### 5. 日常监控

首页仪表盘 `/` 聚合了以下信息：

- **待审查**：pending reviews
- **触发的触发器**：价格触及止损/止盈线
- **即将到期的催化**：未来 7 天内的催化事件
- **逾期研究**：watchlist 中超过研究期限的标的
- **审查缺口**：未评审的决策
- **大波动**：当日涨跌幅超过 15% 的持仓
- **行情错误**：未解决的行情抓取失败
- **QA 缺口**：按 scope 分组的 open warnings

## 常用 CLI 命令

### 行情数据

```bash
# 日线行情回填（最近 3 年）
python -m scripts.fetch_quotes_eod --markets SSE,SZSE,US --backfill-years 3

# A 股财务数据
python -m scripts.fetch_financials_cn --ticker 603011 --market SSE

# 美股财务数据
python -m scripts.fetch_financials_us --ticker AAPL --market US
```

### 叙事管理

```bash
# 生成行业叙事提案
python -m scripts.narrative_propose \
  --registry-base . \
  --base . \
  --source-id "行研-机构-2025-06-abc12345" \
  --scope industry --ref cn-pet-industry \
  --out /tmp/proposals.json

# 应用叙事提案
python -m scripts.narrative_apply \
  --registry-base . --base . \
  --proposal /tmp/proposals.json \
  --today 2026-05-02

# 扫描叙事标记
python -m scripts.narrative_flags \
  --registry-base . --base . \
  --scope industry --ref cn-pet-industry
```

### 质量检查

```bash
# ingest 质量告警
python -m scripts.ingest_qa warn \
  --merged /tmp/ingest-merged.json \
  --preprocess /tmp/ingest-sections.json \
  --arena cn-pet-food

# ingest 认知缺口
python -m scripts.ingest_qa gap --company SSE_603011

# Claim 完整性检查
# 在 /claim-audit 页面查看
```

## Web 页面导航

| 页面 | URL | 用途 |
|---|---|---|
| 仪表盘 | `/` | 总览，日常入口 |
| 公司详情 | `/companies/{slug}` | 查看公司论点、叙事、财务 |
| 行业详情 | `/industries/{slug}` | 查看 11 维行业叙事 |
| 竞技场详情 | `/arenas/{slug}` | 查看竞技场定义 + 参与者矩阵 |
| 投资视角 | `/lens` | 综合判断视图（主观） |
| 持仓表 | `/portfolio` | 当前持仓 + 规则校验 |
| 观察池 | `/watchlist` | 待研究的标的 |
| 决策日志 | `/journal` | 历史决策 |
| 价格触发 | `/triggers` | 止盈/止损状态 |
| 宏观判定 | `/regime` | 当前宏观环境 |
| 纪律审查 | `/discipline` | 未评审的决策 |
| 收益归因 | `/performance` | 持仓 PnL |
| 质量缺口 | `/qa` | Open warnings |
| 搜索 | `/search` | 全文搜索 |

## 文件编辑

所有档案文件（Markdown）都可以直接用编辑器修改：

- **公司 V0 论点**：`companies/{MARKET}_{TICKER}/v0.md`
- **行业叙事**：`industries/{slug}/{dimension}.md`
- **竞技场叙事**：`arenas/{slug}/{dimension}.md`
- **持仓表**：`portfolio/positions.md`
- **观察池**：`watchlist/{stage}.md`

修改后刷新 Web 页面即可看到更新。

## 注意事项

1. **Claim 不可直接编辑**：通过 CLI 脚本的 `ingest_apply` 操作（创建/附加/拆分）
2. **Git 版本控制**：所有文件变更通过 git 管理，修改前建议先 commit
3. **强制重 ingest 是危险的**：会先备份再清除已有数据，仅在确认需要时使用
4. **LLM 判断在对话中完成**：Python 脚本不调 LLM API，review-bundle 等步骤在 Claude 对话中执行
5. **A 股行情源**：使用 AkShare（新浪财经接口），不依赖 eastmoney
