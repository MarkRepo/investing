# Plan 2026-05-26 — web-search 工作流针对性补强（方案 Y）

> 状态：approved，未实施
> 来源：2026-05-26 cn-commercial-space 推进过程中浮出的 7 个 web-search 流程缺陷复盘
> 关联：[[feedback_prescan_domain_tier]] / [[feedback_addresses_granularity]] / [[feedback_web_search_hit_limits]] / [[feedback_thesis_after_prescan]]

## 1. Context — 为什么要做

4 轮对话浮出 7 个 web-search 流程缺陷，串起来发现是**一个根因 + 多个症状**。

### 根因（A1 角色混杂）

web-search 在 prism 工作流里承担 **3 种本质不同的角色**，但当前架构用同一个 `source_type='web-search'`、同一个 manifest 队列、同一个 03 处理路径一锅煮：

| Role | 触发位置 | triggered_by | 目的 | 当前处理 |
|---|---|---|---|---|
| **α 背景校准** | workflow 00 / 01 prescan | `00-prescan-baseline` / `00-prescan` / `01-prescan` | 服务 baseline_knowledge §六 + roadmap 写作 | hit 信息**已被消化一次**，但仍进 03 unprocessed 队列重复抽 finding |
| **β 研究材料** | workflow 02 step0 | `02-step0` | 与卖方研报/年报并列，作为正式研究材料 | 正常进 03 → 04（符合预期）|
| **γ 即兴补料** | workflow 03 / 04 / 05 inline | `03-extract` / `04-synth` / `05-critic` | 在合成中遇到具体缺口时点状补 | 入库但无 finding 文件，被产出 referenced 后悬挂 |

### 衍生症状

- **B1**（已实测）：04 用聚合 mat_id（`ws-aggregate-K#`）登记 `referenced_mat_ids`，导致 `list_affected_outputs` 把 84 条真 mat 全判 new → cn-commercial-space 9/9 产出误标 stale → 死循环
- **B2**：03/04/05 即兴 web-search 入库的 mat 没有 finding 文件，但已被产出 referenced → 05-critic 找不到论据
- **C1**：mid band 的 `待用户确认` 是死标签（全 codebase 0 处消费方）—— 本方案**暂不修**（留待 dashboard 重构）
- **C2**：主 agent 救回的非白名单 host 不沉淀，每个 topic 重学一遍
- **D1**：manifest 上 web-search mat 不记录 `triggered_by`，无法按来源分流
- **D2**：mat 状态只有 `processed: bool`，缺细粒度状态 —— 本方案**暂不修**（属方案 Z 重构）

### 修复后达到的状态

1. 3 种角色按 `triggered_by` 自动分流，不再混煮
2. 04 stale 判定能正确识别聚合 mat_id（`ws-aggregate-K#` 自动展开）
3. 即兴 web-search 强制产 inline finding，消除黑洞
4. 救回知识沉淀到 per-repo `_runtime_whitelist.yaml`，跨 topic 复用
5. cn-commercial-space 现有 9 份产出回到 `fresh`

**预计耗时**：3-4 小时。

---

## 2. 实施步骤（按依赖顺序）

### Step 1 — D1：`search_meta` 加 `triggered_by` 字段

**文件**：`prism/scripts/manifest.py` `make_search_meta`（约 235 行）

**改动**：
- 新增 `triggered_by: str | None = None` 参数
- 写入返回 dict（None 时落 `'unknown'`）
- 向后兼容：老 mat 读时统一 `.get('triggered_by', 'unknown')`

**调用方调整**（2 处）：
- `prism/scripts/web_prescan.py` `register_web_search_result`（约 559 行）→ 加 `triggered_by` 参数，传给 `make_search_meta`
- `prism/scripts/manifest.py` `refresh_web_search_meta`（约 310 行）→ 加 `triggered_by`，重扫时刷新

**`register_web_search_batch` 已有 `triggered_by` 参数**（参 `web_prescan.py:578`），现在让它真正传到 mat 上（之前只写 search log）。

---

### Step 2 — A1：`list_unprocessed` 与 `list_affected_outputs` 加 `exclude_triggered_by` 过滤

**文件**：
- `prism/scripts/manifest.py` `list_unprocessed`
- `prism/scripts/outputs.py` `list_affected_outputs`（约 324 行）

**改动**：
- 新增 `exclude_triggered_by: tuple[str, ...] = ('00-prescan-baseline', '00-prescan', '01-prescan')` 参数
- 过滤逻辑：`mat.search_meta.triggered_by in exclude_triggered_by → 跳过`
- 默认排除 3 个 prescan 来源（Role α）；用户显式传 `()` 可强制处理全部

**workflow 文档同步**（`prism/workflows/03-extract-findings.md` 约 154 行）：
- 注明 03 默认只处理 Role β + Role γ 入库的 web-search
- Role α 已在 baseline §六 / roadmap 阶段消化；如需要主 agent 仍可手动 Read `inbox/web-search/*.md`

---

### Step 3 — B1：`list_affected_outputs` 识别聚合 mat_id 自动展开

**文件**：`prism/scripts/outputs.py` `list_affected_outputs`（约 324 行）

**改动**（约 30 行）：
- 引入 `prism.scripts.findings._read_frontmatter` helper（已存在，`findings.py:24-36`）
- 遍历 `referenced_mat_ids`：
  - 形如 `ws-aggregate-*` → 读 `outputs/findings_{mat_id}.md` frontmatter
  - 解析 `aggregated_from` 字段，把虚拟 ID 替换为真 mat_ids
  - 若 finding 不存在或 `aggregated_from` 为空 → **保留虚拟 ID**（视为 unknown，不计入"已纳入"，避免误判 fresh）

**测试覆盖**：`prism/scripts/test_outputs.py`（新建）—— 测三种场景：纯真 mat_id / 含聚合 mat_id 自动展开 / 聚合 finding 不存在 fallback

---

### Step 4 — B2：即兴 web-search 强制产 inline finding

**新增函数**：`prism/scripts/web_prescan.py` 加

```python
def register_inline_finding(
    slug: str, variant: str, mat_id: str,
    content: str, addresses: list[str],
    quality: str = 'medium', bias: str = 'neutral',
) -> Path:
    """写 outputs/findings_{mat_id}.md（最小 frontmatter）+ mark_processed."""
```

**最小 frontmatter**（5 字段）：`mat_id` / `source_type` / `extracted` / `quality` / `bias` / `addresses`

**自动化路径**（推荐）：`register_web_search_batch` 新增 `inline_finding: bool | None = None` 参数：
- `None`（默认）→ 看 `triggered_by ∈ {'03-extract', '04-synth', '05-critic'}` 自动开启
- `True` / `False` → 显式 override

每条 high/mid mat 自动调 `register_inline_finding(content=snippet)`。

**workflow 文档调整**：
- `prism/workflows/03-extract-findings.md` Step 2.4（约 426 行）—— 即兴 register 后自动产 inline finding，**不再依赖下一轮 03**
- `prism/workflows/04-synthesize/_shared.md` 即兴 web-search 段（约 439 行）—— 同步调整
- `prism/workflows/05-critic-review.md` 即兴 web-search 段（约 188 行）—— 同步调整

---

### Step 5 — C2：runtime whitelist 沉淀

**新建文件**：`prism/data/_runtime_whitelist.yaml`（per-repo）

格式（参 `concepts.yaml` 风格）：

```yaml
# 主 agent 救回的非 hardcoded WHITELIST 域名沉淀
# 编辑请通过 promote_to_whitelist API，不要手改
promoted:
  - host: futurephecda.com
    promoted_at: 2026-05-26T12:00:00Z
    reason: 行业垂直媒体，多 topic 验证有效
    evidence_mat_ids: [mat-f82bf3, ...]
```

**改动**：
- `prism/scripts/web_prescan.py` 加 `_load_runtime_whitelist() -> set[str]`（带 lru_cache，文件 mtime 变更失效）
- 修改 `classify_domain`（`web_prescan.py:144-164`）→ runtime whitelist 命中也返回 `'whitelist'`
- 新增 `promote_to_whitelist(host: str, reason: str, evidence_mat_ids: list[str])` API
- **主 agent 显式调用**（不自动）—— 符合 prism "脚本零 LLM" 原则

**workflow 文档**：`_web_prescan_shared.md` Step C 加注 —— 主 agent 救回某 host **2+ 次**后可考虑调 `promote_to_whitelist` 沉淀

---

### Step 6 — cn-commercial-space 迁移（一次性脚本）

**问题**：当前 7 份聚合 finding 中只有 `ws-K1`（11 mat）和 `ws-K2`（28 mat）frontmatter 有 `aggregated_from`；`ws-K3` / `K4` / `K5` / `K6` / `scope` 缺。**但**正文里都有 18-54 个 `mat-[a-f0-9]{6}` 引用，`web_search_log.yaml` 也存在。

**迁移脚本**：`prism/scripts/_migrations/migrate_aggregate_findings.py`（执行后归档）

1. 对每份 `findings_mat-ws-*.md`：
   - 检查 frontmatter 是否有 `aggregated_from`
   - 无 → grep 正文里所有 `mat-[a-f0-9]{6}` 模式
   - 验证这些 mat_id 都在 manifest 里（过滤打错的）
   - 写回 frontmatter（`yaml.dump` + 保留原正文，幂等）
2. 跑 `list_affected_outputs` 验证 9/9 产出回到 `fresh`

**执行后归档**到 `prism/scripts/_migrations/`，不暴露在常用脚本里。

---

### Step 7 — workflow 文档更新

| 文件 | 改动内容 |
|---|---|
| `prism/workflows/_web_prescan_shared.md` | Step C 加 `triggered_by` 字段约定；Step D 加 runtime whitelist promote 提示 |
| `prism/workflows/03-extract-findings.md` | Step 1 注明默认排除 Role α；Step 2.4 即兴改为强制 inline finding |
| `prism/workflows/04-synthesize/_shared.md` | 即兴 web-search 段同步强制 inline finding |
| `prism/workflows/05-critic-review.md` | 即兴 web-search 段同步 |
| **新增** `prism/workflows/_web_search_aggregation.md` | cn-commercial-space 经验沉淀：当某 K# 的 web-search hit > 30 条时按 K# 聚合的 SOP（frontmatter 必填 `aggregated_from`）|

---

### Step 8 — 测试

**新增**：`prism/scripts/test_outputs.py` —— 测 `list_affected_outputs` 三场景（纯真 / 聚合识别 / fallback）+ `exclude_triggered_by` 过滤

**扩展**：`prism/scripts/test_web_prescan_batch.py` —— 测 `triggered_by` 持久化到 search_meta + `register_inline_finding` 端到端 + runtime whitelist promote/lookup

**复用 fixture**：`test_web_prescan_batch.py` 已有 `tmp_topic` fixture（`make_search_meta` 构造 mock manifest）

---

## 3. 关键文件清单

### 代码改动（按修改顺序）

| 文件 | 改动 |
|---|---|
| `prism/scripts/manifest.py` | `make_search_meta` 加 `triggered_by` / `list_unprocessed` 加 `exclude_triggered_by` / `refresh_web_search_meta` 同步 |
| `prism/scripts/web_prescan.py` | `register_web_search_result` 加 `triggered_by` / `register_web_search_batch` 加 `inline_finding` / `classify_domain` 接 runtime whitelist / 新增 `register_inline_finding` / `promote_to_whitelist` / `_load_runtime_whitelist` |
| `prism/scripts/outputs.py` | `list_affected_outputs` 加聚合 mat_id 识别 + `exclude_triggered_by` |
| `prism/scripts/findings.py` | `_read_frontmatter` 已存在，确认 export |
| `prism/data/_runtime_whitelist.yaml` | **新建** |
| `prism/scripts/_migrations/migrate_aggregate_findings.py` | **新建**（一次性） |

### workflow 文档（按修改顺序）

- `prism/workflows/_web_prescan_shared.md`
- `prism/workflows/03-extract-findings.md`
- `prism/workflows/04-synthesize/_shared.md`
- `prism/workflows/05-critic-review.md`
- `prism/workflows/_web_search_aggregation.md`（**新建**）

### 测试

- `prism/scripts/test_outputs.py`（**新建**）
- `prism/scripts/test_web_prescan_batch.py`（扩展）

---

## 4. 验证（端到端）

### 4.1 单元测试

```bash
pytest prism/scripts/test_outputs.py prism/scripts/test_web_prescan_batch.py prism/scripts/test_whitelist_domains.py -v
```

期望：全绿。

### 4.2 cn-commercial-space 现状验证

```bash
python3 -c "
from prism.scripts.outputs import list_affected_outputs
for k, v in list_affected_outputs('cn-commercial-space', 'claude-opus-4-7').items():
    print(f'{k}: {v[\"reason\"]} (+{len(v[\"new_mat_ids\"])} new)')
"
```

期望：迁移脚本跑完后 9 份产出中 **8 份 `fresh`**（08_living_feed 因无 referenced_mat_ids 仍是 new，符合预期）。

### 4.3 dispatch test（mock topic）

| 步骤 | 操作 | 期望 |
|---|---|---|
| A | `register_web_search_batch(triggered_by='00-prescan')` 入 5 条 hit | mat 入库，search_meta.triggered_by='00-prescan' |
| B | `list_unprocessed()`（默认 exclude） | 返回空 |
| C | `register_web_search_batch(triggered_by='02-step0')` 入 5 条 | mat 入库，triggered_by='02-step0' |
| D | `list_unprocessed()`（默认 exclude） | 返回 5 条 |

### 4.4 inline finding 端到端

| 步骤 | 操作 | 期望 |
|---|---|---|
| A | `register_web_search_batch(triggered_by='04-synth', inline_finding=None)`（自动开启） | 3 条 hit 入库 + 各产出 1 份 `findings_{mat_id}.md` + `processed=True` |
| B | `list_unprocessed()` | 返回空（已自动处理） |

### 4.5 runtime whitelist

| 步骤 | 操作 | 期望 |
|---|---|---|
| A | `promote_to_whitelist('example.com', 'test', ['mat-xxx'])` | `_runtime_whitelist.yaml` 写入 |
| B | `classify_domain('https://news.example.com/foo')` | 返回 `'whitelist'`（endswith 匹配） |

---

## 5. 不在本次方案范围

- **C1 待用户确认 UI**（dashboard chip + approve/reject CLI）→ 留待 dashboard 重构时一并做
- **D2 mat 细粒度状态机**（`raw → ingested → digested → referenced`）→ 方案 Z 内容
- **现有 7 个 topic 全面迁移** → 只迁 cn-commercial-space（其他 topic 受影响极小：老 mat 默认 `triggered_by='unknown'`，不在默认 exclude 集合中，行为与现状一致）

---

## 6. 风险与缓解

| 风险 | 缓解 |
|---|---|
| 老 mat 无 `triggered_by` 被 `exclude_triggered_by` 误漏（'unknown' 不在默认 exclude 里） | 默认 exclude 只列 3 个明确的 prescan 来源；'unknown' 保留默认进 03 行为，向后兼容 |
| `register_inline_finding` 自动写文件覆盖手写 finding | 自动写前先 check `outputs/findings_{mat_id}.md` 是否已存在；存在 → skip 不覆盖（仅追加 log 提示）|
| runtime whitelist 被错误 promote 一直生效 | `promote_to_whitelist` 加 `evidence_mat_ids` 必填，便于事后审计；加 `demote_from_whitelist(host)` 配对 API |
| 迁移脚本误抓正文中"打错的 mat_id" | 脚本里加 `mat_id in manifest_mat_ids_set` 过滤，并打印过滤掉的 ID 让人复核 |
| 多个文档同步改 容易漏 | 用 grep 锚定关键词（`register_web_search_batch` / `inline_finding` / `triggered_by`）做整体回扫 |
