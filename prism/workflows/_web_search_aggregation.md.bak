# Web-Search 聚合 SOP（K# 级别）

> 适用：04-synthesize 写大产出（K# 论证）时某个 K# 已经收了 **>30 条** web-search hit，
> 单独读 30+ findings 进 context 不现实。需聚合成一份 K# 级 finding。
>
> 复用 cn-commercial-space 2026-05 经验沉淀。

> **Web 搜索路径**：见 [[_web_search_routing]]（必读）。补充检索一律走 adapter（`python3 -m prism.scripts.web_search`）。

## 何时聚合

| 信号 | 处理 |
|---|---|
| 单个 K# 的 finding 数 ≤ 10 | 不要聚合，正常读 |
| 单个 K# 的 finding 数 11-30 | 不一定聚合，可写"分主题摘要"压缩到 5K token 嵌 prompt |
| 单个 K# 的 finding 数 > 30 | **必须聚合**——一次 read 30 份 finding 容易 OOM；同 K# 内容大量重复 |

## 聚合产物

文件：`outputs/findings_ws-aggregate-K#.md`（canonical 命名；老 cn-commercial-space
用了 `findings_mat-ws-K#.md` 也兼容）

**Frontmatter 必填**：

```yaml
---
mat_id: ws-aggregate-K1            # 虚拟 ID，前缀必须 'ws-aggregate-'
filename: web_search_K1_<topic>.md # 仅用于人类索引
source_type: web-search-aggregate
extracted: 2026-05-26
quality: high                       # 视聚合质量：high/medium/low
bias: neutral
addresses: [K1]                     # 单 K# 聚合写单元素
aggregated_from:                    # 强制必填 — 列出所有真 mat_id
  - mat-f2592e
  - mat-342ae0
  - ...
---
```

⚠️ **`aggregated_from` 缺失会触发 [[feedback_addresses_granularity]] 同类陷阱**：
`outputs.list_affected_outputs` 把虚拟 ID 当 unknown，导致所有真 mat 都被标 new →
产出全部 stale → 04 死循环（cn-commercial-space 9/9 实测）。

## 引用约定

写大产出（决策链成稿 case，如 `i_industry_case`）时，`set_output_referenced_mats` 传入 **虚拟 ID**：

```python
from prism.scripts.outputs import set_output_referenced_mats
set_output_referenced_mats(
    slug='...', variant='...',
    output_key='i_industry_case',  # company c_investment_case / arena a_arena_case
    mat_ids=['ws-aggregate-K1', 'ws-aggregate-K2', ..., 'mat-xxxxxx'],
)
```

`list_affected_outputs` 自动展开 `ws-aggregate-*` → 读取 frontmatter 的
`aggregated_from` → 与 manifest processed_ids 比对。

## 聚合写作纪律

1. **不要丢 mat 引用**：聚合内每个事实 bullet 末尾保留 `[mat-xxxxxx]` 标记，便于回溯
2. **不要伪聚合**：把 5 个 finding 拼成一份 ≠ 聚合；聚合是 30+ 同 K# finding 的紧致重述
3. **K1→K3 etc 交叉**：聚合末尾用专门段落标"对 K3 的影响"，便于 04 写 case 环⑤证伪/风险
4. **数据时间窗**：聚合 frontmatter 加 `data_window: 2024-01..2026-05`，05-critic 据此判 stale
5. **聚合后老 finding 不删**：保留 `findings_mat-xxxxxx.md` 单体文件作为底稿，仅在大产出 prompt 里读聚合

## 迁移老数据

老聚合 finding（cn-commercial-space K3/K4/K5/K6/scope）frontmatter 没填 `aggregated_from`，
跑一次性脚本回填：

```bash
python3 -m prism.scripts._migrations.migrate_aggregate_findings <slug> <variant>
```

脚本会 grep 正文里所有 `mat-[a-f0-9]{6}` 模式，与 manifest 比对后写回 frontmatter。
未在 manifest 里的 ID 会被过滤（多半是打错的）并打印让人复核。
