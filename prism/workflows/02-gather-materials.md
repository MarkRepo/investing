# Workflow 02 — 登记资料到 Manifest

**触发**：用户上传了新资料，或说「登记资料」  
**前置**：topic.yaml 和 manifest.yaml 已存在  
**产出**：更新 `prism/topics/{slug}/manifest.yaml`

---

## ⚠️ 前置自检：是否从 workflow 01 顺序推进而来？

workflow 01 已演进到自动化收料阶段（`auto_download_annual_reports` + `01-prescan` 全自动入库），如果你**刚从 01 推进过来**，下面 Step 0-4 大概率全跳过——脚本会自己判：

```bash
python3 << 'EOF'
from prism.scripts.web_prescan import should_run_step0
from prism.scripts.manifest import list_pending_mineru, material_count

slug = '{slug}'
variant = '{variant}'

step0 = should_run_step0(slug, variant)
mineru = list_pending_mineru(slug, variant)
counts = material_count(slug, variant)

print(f"Step 0 (web 增量扫): {'跳过' if not step0['should_run'] else '需跑 recency_days='+str(step0['recency_days'])} — {step0['reason']}")
print(f"Step 4.5 (mineru): {'跳过' if not mineru else f'有 {len(mineru)} 待办'}")
print(f"manifest 现状: total={counts['total']} unprocessed={counts['unprocessed']}")
print()
print("inbox 残料检查（如果非空可能有未登记新文件，需要跑 Step 1-4）:")
import subprocess, os
for d in [f'prism/topics/{slug}/inbox/manual', 'prism/inbox/manual', 'prism/inbox/auto']:
    if os.path.isdir(d):
        files = [f for f in os.listdir(d) if not f.startswith('.')]
        print(f"  {d}: {len(files)} 个文件")
EOF
```

**主 agent 行为约束**：
- 看到 `inbox/web-search/` 里有大量 `.md` 文件 **不要怀疑**——那是 workflow 01 的 prescan 自己写的，已经通过 `register_web_search_batch` 全部登记进 manifest 了
- 看到 `materials/` 里有 23 份 `.PDF` **不要怀疑**——那是 `auto_download_annual_reports` 抓的，已经通过 `add_material` 登记完
- 看到 Step 0-4 脚本都判"跳过 / 0 待办" **不要硬找事做**（如重跑 prescan / 反复 read_manifest / 再 add_material 一遍）
- **Step 5.7 / 5.8 / 6 是 workflow 02 的真正价值兑现点**，不能因为前面"没事做"就连带跳过

**只有以下情况才需要从 Step 0 跑起**：
- 用户在两次 workflow 之间手放新 PDF 到 `prism/topics/{slug}/inbox/` 或全局 `prism/inbox/manual/`
- 上次 prescan 距今 > 7 天（脚本自判）
- workflow 01 因故没跑 auto-download

---

## Step 0：web-search 智能增量扫描（**修 S1：脚本判 recency**）

先调脚本判断是否要跑、跑就用多少 recency_days；不再由 LLM 拍脑袋默认 30。

```bash
python3 -c "
from prism.scripts.web_prescan import should_run_step0
r = should_run_step0('{slug}', '{variant}')
print(f'should_run={r[\"should_run\"]}, recency_days={r[\"recency_days\"]}')
print(f'reason: {r[\"reason\"]}')
"
```

决策表（脚本内置，仅供参考）：

| 最近 prescan 距今 | 决策 |
|---|---|
| ≤ 7 天（任何 triggered_by） | **跳过 Step 0**，直接进 Step 1 |
| 无任何 prescan 历史 | recency_days=90 兜底 |
| 仅有 01/00-prescan，无 02-step0 历史 | recency_days=30 |
| 02-step0 距今 7-14 天 | recency_days=7 增量 |
| 02-step0 距今 14-60 天 | recency_days=30 默认 |
| 02-step0 距今 > 60 天 | recency_days=90 兜底 |

`should_run=True` → 按脚本给的 recency_days 调用 `_web_prescan_shared.md`（`triggered_by='02-step0'`）。
`should_run=False` → 直接进入 Step 1（理由 echo 到对话即可）。

跑完 Step 0 后再进入 Step 1，把 web-search 已经搞定的 todo 从用户视野里摘掉。

---

## Step 1：检查所有来源的新资料

按优先级检查三个来源：

```bash
# 1. Topic 专属 inbox（最高优先级，所有文件自动归属本 topic）
ls prism/topics/{slug}/inbox/   # 如果不存在，创建之

# 2. 全局 manual inbox（需要甄别是否属于本 topic）
ls prism/inbox/manual/

# 3. 全局 auto inbox（自动下载的资料，需要甄别）
ls prism/inbox/auto/
```

**规则**：`prism/topics/{slug}/inbox/` 下的所有文件**默认属于本 topic，无需甄别直接全部登记**。全局 inbox 的文件仍需判断相关性。

---

## Step 2：对每份新资料，判断 source_type

按文件名和内容判断类型。**若文件名无语义信息（如 H3_AP*、纯数字、report.pdf、s_* 随机串），须用 pdftotext 抽取前 3 页确认标题和主题：**

```bash
pdftotext -l 3 "<file>" - | head -30
```

类型判断：
- `sell-side-note`：卖方研报（某机构某日期某标题）
- `annual-report`：年报 / 半年报 / 10-K / 20-F
- `industry-research`：第三方行业研究报告
- `web-article`：网页抓取的新闻/文章
- `manual-note`：用户自己写的笔记
- `policy`：政策文件/监管文件

---

## Step 3：读当前 manifest

```bash
python -c "
import json
from prism.scripts.manifest import read_manifest
print(json.dumps(read_manifest('{slug}', '{variant}'), ensure_ascii=False, indent=2))
"
```

检查哪些文件已经在 manifest 里，避免重复登记。

---

## Step 4：逐一登记新资料

对每份新文件执行：

```bash
# 登记 + 自动复制到 materials/ + 必填 addresses（指向 K#）+ 选填 rings（决策链输入合同）
python -c "
from pathlib import Path
from prism.scripts.manifest import add_material
mat_id = add_material(
    slug='{slug}',
    filename='{filename}',
    source_type='{source_type}',
    notes='{notes}',
    source_path=Path('{material_full_path}'),
    variant='{variant}',
    addresses={addresses_list},  # 例如 ['K1', 'K3']
    rings={rings_list},          # 例如 ['mgmt-capital-alloc','financial-arc']，见 _input_contract.md
)
print(f'已登记：{filename} → {mat_id}')
"
```

**关于 addresses（强制三态）** — 全局约定见 `_web_prescan_shared.md` 关键纪律 3：
- 必填，**禁止 `[]`**
- K# 来自 thesis_v{N}.md（Q# 已降级，新 topic 不再用）
- 无具体 K# 时按背景资料填 `['background']`；与 topic scope 相关但非背景填 `['scope']`

**关于 rings（决策链输入合同标签 · 选填但强烈建议）** — 与 addresses **解耦**（addresses=thesis 脊柱 K#，rings=输入脊柱）：
- 这份料服务哪几个决策环输入？按 `_input_contract.md` 本 type 的 code 填（如年报 → `['mgmt-capital-alloc','financial-arc','biz-moat-unit-econ']`；卖方一致预期 → `['consensus']`；行业镜鉴复盘 → `['industry-mirror']`）。
- 财报/公告类**自动下载**的料已由 fetcher 按 report_type 默认打了 rings（见 `fetch_report_prism`），手动登记的料需自己标。
- 喂 gap **ring 轴**（A 轴）覆盖统计；不确定填哪个就先不填，03 抽取时按实际内容在 finding frontmatter 补。

**关于 dedup**：`add_material` 已内建按 filename 去重——重复调用会合并 addresses/notes 而非新增条目，安全幂等。

> 注意：文件会自动复制到 prism/topics/{slug}/materials/，原 inbox 文件保留。

---

## Step 4.5：自动触发 mineru 转换（**新增——sell-side/industry PDF 必做**）

> ⚠️ **必须用 vlm 模型**——pipeline/pymupdf 会丢表格/公式/多栏排版，研报和行业报告的关键数据多在表格里。**禁止改 `convert(src, out_dir, 'vlm')` 的第三参**。详见 [[feedback_mineru_required]]。

`add_material` 登记时已自动给 sell-side-note / industry-research / policy 类型的 PDF 标 `mineru_state=needs`。
登记完成后立即跑 mineru 转换，避免 workflow 03 卡在转换上。

```bash
python3 << 'EOF'
from pathlib import Path
from prism.scripts.manifest import list_pending_mineru, set_mineru_state
from scripts.mineru_api import convert

slug = '{slug}'
variant = '{variant}'
mats_dir = Path(f'prism/topics/{slug}/materials')

pending = list_pending_mineru(slug, variant)
print(f'Pending mineru: {len(pending)}')
for m in pending:
    src = mats_dir / m['filename']
    if not src.exists():
        set_mineru_state(slug, variant, m['id'], 'failed')
        continue
    out_dir = mats_dir / (src.stem + '_vlm')
    if (out_dir / 'full.md').exists():
        set_mineru_state(slug, variant, m['id'], 'done')
        continue
    set_mineru_state(slug, variant, m['id'], 'in_progress')
    try:
        convert(src, out_dir, 'vlm')
        set_mineru_state(slug, variant, m['id'], 'done')
        print(f'  ✓ {m["filename"][:50]}')
    except Exception as e:
        set_mineru_state(slug, variant, m['id'], 'failed')
        print(f'  ❌ {m["filename"][:50]}: {e}')
EOF
```

**幂等保护**：脚本会检查 `{stem}_vlm/full.md` 是否存在，跳过已转换的文件，重复跑安全。

**失败处理**：mineru 失败的会标 `failed`，detail 页会红色显示。可手动修后回设 `needs` 再跑。

---

## Step 5.7：校验 manifest 是否覆盖所有 K#（**新增**）

```bash
python -c "
from prism.scripts.outputs import validate_manifest_coverage
from prism.scripts.topic import read_topic
t = read_topic('{slug}', '{variant}')
cur = (t.get('thesis') or {}).get('current_version')
if cur is not None:
    r = validate_manifest_coverage('{slug}', '{variant}', cur)
    print(f'Manifest 覆盖率: {r[\"coverage_pct\"]}%')
    print(f'已覆盖 K#: {r[\"covered\"]}')
    if r['uncovered']:
        print(f'⚠ 未覆盖 K#: {r[\"uncovered\"]} — 这些 Killer Question 在 roadmap 里规划了但实际没收集到任何材料')
        print('  → 接下来要么补资料、要么在 thesis 里标注\"不验证此 K\"')
"
```

⚠ **重要差异**：roadmap coverage 校验「计划要收什么」，manifest coverage 校验「实际收了什么」。两者背离说明计划落空——detail 页会显示红色 ✗ 提醒。

---

## Step 5.8：gap 体检（升 stage 到 03 前必跑）

```bash
python3 -c "
from prism.scripts.gap_detector import detect_gaps, format_summary
print(format_summary(detect_gaps('{slug}', '{variant}')))
"
```

把 report 输出**完整贴到对话**。**双轴都看**：

**B 轴（K# 脊柱）**：
- `uncovered_ks` 非空 → 该 K# 当前 0 条材料覆盖
- `thin_evidence` 非空 → 该 K# 证据 < 2 条
- `expired_web_materials` 非空 → 有 web-search 材料 > 90 天

**A 轴（决策链输入合同 · ring 轴）**：
- `uncovered_ring_inputs` 非空 → 决策链某环的必带输入无材料覆盖（**带 🔴 = 三项真·欠供之一，最该补**）
- `thin_ring_inputs` 非空 → **hard 项有料但 < min_evidence（🟡 薄输入）**：单条弱料不足以撑起三项真·欠供之一，按 `code(当前/阈值)` 补到阈值或诚实降级
- `api_pending_inputs` → 财务/估值类，合成期自动拉，**非红**，不用管
- `ring_axis_status == 'n/a'` → 旧 topic 未接入拆解/rings，A 轴不适用（忽略）

任一红项非空 → **不要硬升 stage**，先选补救：web-search 增量扫 / sub-agent 深挖 / set_user_todos 让用户补，再决定是否进 03-extracting。这是诊断不是 gate——脚本不会拒绝你升 stage，但跳过等于把"论证薄弱"留给 04/05。`uncovered_ring_inputs` 的 hard 项尤其要在升 stage 前显式处理（收料或诚实标"数据缺失"）。

---

## Step 6：增量更新 topic 状态（**禁止 set_user_todos(list[str]) 覆写**）

⚠ 与 workflow 01 Step 6 同样的纪律：不能用 list[str] 全量覆写 user_todos，会丢 priority/info_tier/addresses。
**自 H2 修后**：`set_user_todos` 在现有 todos 含 addresses 时会 raise；想加进度提示用 `append_user_todos`；想改单条状态用 `update_user_todo_status`。

```bash
python3 << 'EOF'
from prism.scripts.topic import (
    set_stage, set_next_actions, read_topic, update_user_todo_status
)
from prism.scripts.manifest import material_count

slug = '{slug}'
variant = '{variant}'
counts = material_count(slug, variant)

# stage 升级条件：有可处理未处理资料 → 03-extracting（修 F14：排除 Role α prescan web 料）
set_stage(slug, '03-extracting' if counts['unprocessed_actionable'] > 0 else '02-gather-materials', variant)

# next_actions 是给 LLM 看的系统建议（不污染 user_todos）
set_next_actions(slug, [
    f'{counts["unprocessed"]} 份未处理资料 → 运行 workflow 03-extract-findings',
    'detail 页查看「📚 实际收集覆盖」徽章，红色 ✗ 的 K# 优先补料',
], variant)

# 对已通过本次资料登记部分解决的 todo，update_user_todo_status 增量更新
# 例如：登记了 4 份卖方深度 → '下载3份对比卖方深度报告' todo → in_progress 或 done
# update_user_todo_status(slug, variant, '3份对比卖方深度', 'in_progress')
EOF
```

---

## Step 7：汇报

```
✅ manifest 已更新

新登记资料：{list}
当前资料库：共 N 份（已处理 X，未处理 Y）

下一步：
说「prism 推进 {slug}」或「提取发现 {slug}」继续
```
