# Web 搜索路由总则（必读）

> 适用：所有 prism workflow 步骤、所有 subagent dispatch、所有用户对话里的 web 检索。
> 任何与 web 检索相关的实现/修改都必须遵守本文规约。

## 决策一句话

**进文件 → adapter；进上下文 → tool。**

## 三问决策

```
Q1. 结果要不要落 sidecar / 进 register_web_search_batch？
    YES → adapter（强制）
    NO  → 进 Q2

Q2. 是不是批处理（≥3 query 一次性）？或者要可重放？
    YES → adapter（强烈推荐）
    NO  → 进 Q3

Q3. 模型在对话里临时起意要查（探索式、单次、消化即用）？
    YES → WebSearch tool（Anthropic 原生）或 MCP
    NO  → adapter
```

## 步骤映射

| 步骤 | 用途 | 走哪 |
|------|------|------|
| 00 / Step 4.5 web-prescan | baseline 检索落 sidecar | adapter |
| 00 thesis_v0 起草前事实校验 | 模型确认数据点是否过期 | WebSearch tool |
| 02-06 起步 gap_detector 后补窟窿 | 针对 uncovered_K# 显式扩搜 | adapter |
| 03 deep dive 单 thesis 多 query 扩展 | 围绕 thesis 跑 4-8 query | adapter |
| 04 synthesize 期间补查具体事实 | 写 claim 时验证数据 | WebSearch tool |
| 04 bundle review 多 arena 检索 | 每 arena slug 独立 query 集 | adapter |
| 05 critic-rewrite 反方观点检索 | 找异见/反例 | adapter |
| 06 risk-blindspots | 系统性扫风险事件 | adapter |
| 07/09/10 sidecar 字段填充前校验 | 写字段时单次验证 | WebSearch tool |
| 08 living-feed 刷新 | 周期性扫近 N 天新闻 | adapter |
| subagent dispatch 内部检索 | 一律 adapter（脚本 + Bash） | adapter |

## Adapter CLI

```bash
# 直接 search → stdout JSON
python3 -m prism.scripts.web_search search "<query>" \
    --intent <news|semantic|exact|general> \
    --days <N> --max-results 5

# search → 落 raw sidecar 文件（**不 register**——主 agent 后续手动判 tier + 救回）
# 写到 prism/topics/{slug}/inbox/_websearch_raw/{ts}_{qhash}.json
# 主 agent 用 review-digest 看 index 判 tier（勿 Read 整 json）→ register_web_search_batch（见 _web_prescan_shared Step C）
python3 -m prism.scripts.web_search search "<query>" \
    --intent <intent> \
    --output sidecar \
    --slug <slug> --variant <variant> \
    --triggered-by <step>-<thesis> \
    --addresses K1,K3

# WebSearch fallback：吃外部 hits 走 dedup + 黑名单过滤 + 落 sidecar
echo '<json hits array>' | python3 -m prism.scripts.web_search postprocess \
    --source websearch_fallback \
    --query "<original query>" \
    --slug <slug> --variant <variant> \
    --triggered-by <step>-fallback --addresses K1

# key 池状态
python3 -m prism.scripts.web_search status
```

> **domain_tier 由谁判**：adapter 只对黑名单源（twitter/youtube/reddit 等 `LOW_SIGNAL_HOSTS`）打 `'other'` tier。其余源不预判——`register_web_search_batch` 默认走"主 agent LLM 判 tier + H2 救回闭环"流程（参 `_web_prescan_shared.md` Step C）。脚本不维护行业权威源白名单。
>
> **sidecar 模式 ≠ 自动入 manifest**（2026-05-28 修法）：`--output sidecar` 只写 raw hit JSON 到 `prism/topics/{slug}/inbox/_websearch_raw/{ts}_{qhash}.json`，**不**调 `register_web_search_batch`。主 agent 用 `review-digest` 投影判 tier（勿 Read 整 json，见 `_web_prescan_shared.md` Step C）、再手动调 register。之前 sidecar 自动 register 会让 non-WHITELIST hit 全 'other' → low band drop，实质架空 H2 救回。

## 退出码契约

| 退出码 | 含义 | 主 agent 处理 |
|--------|------|---------------|
| 0  | 成功 | 继续 |
| 10 | 部分成功（某些 query 有结果） | 看 stderr 决定补搜 |
| 20 | 全 query 0 hit | 检查 query 写法；可改 WebSearch tool |
| 30 | SOME_DEGRADED（某 provider 已自动降级） | 继续，但记日志 |
| 40 | ALL_PROVIDERS_EXHAUSTED | **走 WebSearch fallback**（见下节） |
| 50 | 配置错（key 缺失等） | 停止，提示用户检查 key |

## 双向 Fallback 规约

### Adapter → WebSearch tool（救急）

退出码 40 时主 agent 必须执行：

1. 读 stderr JSON 拿 `queries_unmet` 和 `fallback_hint`
2. 对每个 unmet query 调 WebSearch tool 单次
3. 把 WebSearch 拿到的 url/title/snippet 整理成 hits JSON
4. 走 `postprocess` 子命令，`--source=websearch_fallback`
5. sidecar 自动标 `source_provider="websearch_fallback"`，dashboard 区分

### WebSearch tool → Adapter（升级）

WebSearch 命中以下任一情况切 adapter：

1. 0 citations
2. citations 全部域名在 LOW_SIGNAL_HOSTS（twitter/youtube/reddit 等）
3. 主 agent 判断"此结果需要进 sidecar"
4. 同一事实需要交叉验证

直接重跑同 query：
```
python3 -m prism.scripts.web_search search "<同 query>" --intent <classified> ...
```

### 防 ping-pong

- **per-query attempt 上限 = 2**：每个 query 在一次 workflow 步骤内最多被 adapter+WebSearch 各试一次
- **postprocess 模式不再触发 fallback**：只做后处理，不发起新检索
- 第二次仍失败 → 标 unmet → 写 sidecar `triggered_by` 后缀加 `-degraded` → 让人决定下一步

## 例外：什么时候允许走 WebSearch tool

只有三类：

1. **prescan 之前的训练知识校准**（[[feedback_thesis_after_prescan]]）—— 单次、不入库
2. **adapter 全 provider 全 key 都炸**—— circuit breaker 全开 → fallback 救急
3. **用户对话里临时问问题**—— 不属于 workflow

其余一律走 adapter。

## 引用

- 多 key 轮换 + 配额持久化：见 `prism/scripts/providers/keypool.py`
- domain_tier 白名单：见 `prism/scripts/providers/_domain.py`
- sidecar schema 纪律：[[feedback_sidecar_schema_compliance]]
- subagent 检索纪律：[[feedback_subagent_write_hallucination]] / [[feedback_subagent_bulk_synthesis]]
- gap_detector 触发：[[feedback_gap_detector_checkpoints]]
