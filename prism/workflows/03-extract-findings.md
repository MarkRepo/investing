# Workflow 03 — 从资料中提取发现

**触发**：有未处理资料，或说「提取发现」  
**前置**：manifest.yaml 有 processed=false 的条目  
**产出**：在 `prism/topics/{slug}/{variant}/outputs/` 中积累发现笔记（按资料 ID）

> **Web 搜索路径**：见 [[_web_search_routing]]（必读）。本步默认走 adapter；
> 仅事实校验类临时单查走 WebSearch tool。
>
> 入库类 inline web-search 示例：
> ```bash
> python3 -m prism.scripts.web_search search "<query>" \
>     --intent news --output sidecar \
>     --slug <slug> --variant <variant> \
>     --triggered-by 03-extract --addresses K1,K3
> ```
> 旧 helper `register_web_search_batch` 直调路径仍可用，但 adapter 会自动跑 dedup + 黑名单过滤，推荐统一走 adapter。domain_tier 仍由 H2 救回流程判（主 agent 看 dropped_hits 决定救回哪些）。

---

## Step 0a：gap 体检（进 03 第一件事）

```bash
python3 -c "
from prism.scripts.gap_detector import detect_gaps, format_summary
print(format_summary(detect_gaps('{slug}', '{variant}')))
"
```

主 agent 直接读上面 Bash 输出的 report 做决策——**不必再整份贴/复述到对话**（Bash 输出里已有一份，actionable 项也在 web 详情页），对话只回**一句话摘要**。**若本会话刚从 02 Step 5.8 直连推进、其后未新增材料，直接沿用那次结果、不必重跑本块；新会话/隔轮回来则照常重跑本块（从磁盘重算，绝不跳过）。** **双轴都看**（B 轴 = K# 脊柱，A 轴 = 决策链输入合同）：
- `uncovered_ks` 非空 → 该 K# 当前 0 条材料覆盖
- `thin_evidence` 非空 → 该 K# 证据 < 2 条
- `uncovered_ring_inputs` 非空 → 决策链某环必带输入无料覆盖（带 🔴 = 三项真·欠供，最该补）；`api_pending_inputs` 非红
- `expired_web_materials` 非空 → web-search 材料 > 90 天

任一红项非空 → **不要硬干**，按 auto-fetch 规约**有先后**补救（不是平级）：**先**即兴 web-search Step 2.4 / sub-agent 深挖 Step 2.4b 尝试自动抓；**只有** attempt 真跑过且对应 todo 被 `mark_todo_fetch('empty')`（有效尝试确认公开无源）后，`set_user_todos` 让用户补才是合法最后手段（且走 empty 硬闸门）。`error` 必须重试不得降级。判定见 [`_autofetch_protocol.md`](_autofetch_protocol.md)。这是诊断不是 gate——脚本不会拒绝前进，但跳过等于把"论证薄弱"留给 04/05。抽取阶段尤其要借 ring 轴定位"哪些决策环输入还没料喂 §2.2 F"。

---

## Step 0b：父级 findings 健康检查

子 topic（在 01 Step 1.5 写过 `parent_materials`）04 合成时会通过 `list_all_findings` 自动捞父级 findings——**但若父 topic 没跑过 03，父级 `findings_{mat_id}.md` 不存在，会被静默跳过**，导致本 topic 04 时相关 K# 缺论据。

```bash
python3 -c "
from prism.scripts.findings import list_missing_parent_findings
miss = list_missing_parent_findings('{slug}', '{variant}')
if not miss:
    print('✓ 所有 parent_materials 引用的 finding 都已就位（或本 topic 无 parent_materials）')
else:
    print(f'⚠ 有 {len(miss)} 条 parent_materials 引用了未生成的 finding（04 时会被静默跳过）:')
    for m in miss:
        addr = ','.join(m['addresses']) or '-'
        print(f'  - parent={m[\"parent_slug\"]}/{m[\"mat_id\"]} addresses=[{addr}]')
        if m['note']: print(f'    note: {m[\"note\"]}')
"
```

**任一缺失 → 三选一补救**：
- A. 切到父 topic 跑 workflow 03 把缺失的 finding 补上（最严谨；相关 K# 在父 topic 也会受益）
- B. 编辑 `topic.yaml` 把这些 ref 从 `parent_materials` 中移除（弃用引用；如父 topic 已废弃）
- C. 忽略继续——但在本 topic 04 完成后 critic-review 会更可能命中"该 K# 论证薄弱"

这是诊断不是 gate——脚本不会拒绝前进，但跳过相当于把 [[feedback_addresses_granularity]] 已经踩过的"父级 finding 假覆盖"问题留到 04/05。

---

## Step 0：扫 topic-scope inbox + inline 02 入库（不再 raise，主 agent 同对话补完）

用户手动放的研报/年报通常落在 `prism/topics/{slug}/inbox/`，**不一定全在 manifest 里**。先扫一遍并打印未登记列表：

```bash
python3 << 'EOF'
from pathlib import Path
from prism.scripts.manifest import read_manifest

slug = '{slug}'
variant = '{variant}'
inbox = Path(f'prism/topics/{slug}/inbox')
if not inbox.exists():
    print('无 topic-scope inbox，跳过 inline 02')
else:
    try:
        m = read_manifest(slug, variant)
        known = {x['filename'] for x in m.get('materials', [])}
    except FileNotFoundError:
        known = set()
    new_files = sorted([f for f in inbox.iterdir() if f.is_file() and f.name not in known])
    if not new_files:
        print(f'✓ topic-scope inbox 全部已登记 ({len(known)} 份)')
    else:
        print(f'⚠ topic-scope inbox 有 {len(new_files)} 份未登记文件:')
        for f in new_files:
            print(f'  {f.name}  ({f.stat().st_size/1024:.0f}KB)')
        print()
        print('→ 主 agent 同对话直接跑 inline 02 流程（不再 raise）：')
        print('  1. 对每份文件用 pdftotext -l 3 抽前 3 页判 source_type（参 02 Step 2）')
        print('  2. 主 agent 给出 addresses（按 _web_prescan_shared.md 三态约定）')
        print('  3. 调 add_material 逐份入库（参 02 Step 4）')
        print('  4. 跑 02 Step 4.5 mineru 批转换（vlm 模型，必须）')
        print('  5. 入库完成后继续 03 Step 1（不离开本对话）')
EOF
```

**inline 02 入库脚本模板**（主 agent 按列出的文件填 source_type/addresses 后跑）：

```bash
python3 << 'EOF'
from pathlib import Path
from prism.scripts.manifest import add_material, list_pending_mineru, set_mineru_state
from scripts.mineru_api import convert

slug = '{slug}'
variant = '{variant}'
inbox = Path(f'prism/topics/{slug}/inbox')

# 主 agent 按上面 ls 出的文件逐份填这张表
# (filename, source_type, addresses, notes)
to_add = [
    # ('某机构_某日期_某标题.pdf', 'sell-side-note', ['K1', 'K3'], '中信建投 2026-05 深度'),
    # ('2026_SSE_600519_annual.pdf', 'annual-report', ['scope'], '茅台 2026 年报'),
]
for fname, stype, addrs, notes in to_add:
    src = inbox / fname
    if not src.exists():
        print(f'  ✗ {fname} 不在 inbox')
        continue
    mat_id = add_material(
        slug=slug, filename=fname, source_type=stype, variant=variant,
        notes=notes, source_path=src, addresses=addrs,
    )
    print(f'  ✓ {fname} → {mat_id}')

# 同步跑 mineru 批转换（vlm 模型，禁止改）
mats_dir = Path(f'prism/topics/{slug}/materials')
pending = list_pending_mineru(slug, variant)
print(f'Pending mineru: {len(pending)}')
for m in pending:
    src = mats_dir / m['filename']
    if not src.exists():
        set_mineru_state(slug, variant, m['id'], 'failed')
        continue
    out_dir = mats_dir / (Path(m['filename']).stem + '_vlm')
    if (out_dir / 'full.md').exists():
        set_mineru_state(slug, variant, m['id'], 'done')
        continue
    set_mineru_state(slug, variant, m['id'], 'in_progress')
    try:
        convert(src, out_dir, 'vlm')
        set_mineru_state(slug, variant, m['id'], 'done')
        print(f'  ✓ mineru {m["filename"][:50]}')
    except Exception as e:
        set_mineru_state(slug, variant, m['id'], 'failed')
        print(f'  ❌ mineru {m["filename"][:50]}: {e}')
EOF
```

inline 入库 + mineru 全跑完后直接进 Step 1，**不再退场让用户切到 02 再回来**。

---

## Step 1：读取未处理资料清单

```bash
python3 -c "
from prism.scripts.manifest import list_unprocessed
items = list_unprocessed('{slug}', '{variant}')
for i in items:
    print(f'{i[\"id\"]} | {i[\"filename\"]} | {i[\"source_type\"]}')
"
```

> **Role α web-search 自动豁免**：`list_unprocessed` 默认 `exclude_triggered_by=
> ('00-prescan-baseline','00-prescan','01-prescan')`，因此 workflow 00/01 prescan
> 入库的 web-search hit **不会出现在本清单**——它们在 baseline §六 + roadmap
> 起草阶段已被消化进 thesis/roadmap，再走 03 抽 finding 会让 snippet 被当作
> 二次 "事实" 引用走形。如果需要对 Role α 强制抽 finding（罕见），显式传
> `exclude_triggered_by=()`，或手动 Read 对应 `inbox/web-search/*.md`。
>
> Role β（02-step0）与 Role γ（03/04/05 即兴）正常出现。Role γ 的 mat 由
> `register_web_search_batch(inline_finding=True)` 自动产 finding，多数时候
> 也不会出现在 unprocessed 队列里（已被自动 mark_processed）。

---

## Step 1.5：跳过已切片的 SEC parent htm（强制）

SEC 10-K/10-Q 下载时（`fetch_report_prism.fetch_sec`）已自动切片成 `sec/{stem}/item_*.md`，
每节作为 `source_type=sec-section` 的子条目登记，带 `parent_mat` 指回原 htm。

**parent htm 本身不再需要读**——所有有用内容都在 sec-section 子条目里，强行读全文等于退回切片前的"全 htm 60-100k token"成本。

```bash
python3 -c "
from prism.scripts.manifest import read_manifest, mark_processed
slug, variant = '{slug}', '{variant}'
mats = read_manifest(slug, variant)['materials']
parents_with_children = {m['parent_mat'] for m in mats if m.get('parent_mat')}
skipped = 0
for m in mats:
    if m['id'] in parents_with_children and not m['processed'] and m['filename'].lower().endswith(('.htm', '.html')):
        mark_processed(slug, m['id'], variant)
        skipped += 1
print(f'已自动跳过 {skipped} 份 SEC parent htm（其 sec-section 子条目仍在 unprocessed 队列）')
"
```

执行后回到 Step 1 重新拉 unprocessed 清单 —— 你应该看到的是 `sec-section` 子条目，不是 `*.htm` 父文件。

---

## Step 2：对每份资料，执行以下提取

每次处理一份资料：

### Subagent dispatch 规约（如果走 subagent）

**架构铁律：subagent 只产内容，主 agent 落盘**

经 2026-05-22 4/4 测试（含原文嵌入硬规约的 retry），subagent Write findings_{mat_id}.md 时**总会幻觉出"Write 被拦截"错误**（实际不存在 hook），且声称的"Bash heredoc 绕过"/「.write_test 写入成功」也常常是幻觉。详见 [[subagent-write-hallucination]]。

**所以**：subagent **不再负责写 findings 文件**——只负责产出 markdown 内容到 final message。主 agent 接收后用 Write 工具落盘。

dispatch subagent 时：

- `subagent_type`: **必须 `general-purpose`**
- `model`: **不传**，跟随主 agent
- prompt 末尾必须原文加入：
  > "**重要：你不要调用 Write/Edit 工具写文件，也不要用 Bash heredoc 写文件。** 你的全部 markdown 产出必须以 ```markdown\n...\n``` 代码块形式整体放在 final message 中。主 agent 会接收后落盘。final message 格式：(1) 1-2 句 key signals 摘要；(2) 一个完整的 markdown 代码块，包含 frontmatter + 全部 findings。"

主 agent 收到 subagent final message 后：
1. 提取 markdown 代码块内容
2. 用 Write 工具写到 `prism/topics/{slug}/{variant}/outputs/findings_{mat_id}.md`
3. 用 `ls -la` 验证文件 mtime + 大小

### 2.1 预处理：根据文件类型准备内容

**判断文件类型**（从 filename 和 source_type 推断）：

#### A. 年报 / 半年报（source_type = annual-report）

```bash
# 1. 找到文件位置
python3 -c "
from prism.scripts.manifest import get_material_path
path = get_material_path('{slug}', '{filename}')
print(path if path else 'FILE_NOT_FOUND')
"
# 2. 用章节提取器处理 PDF，只保留分析相关章节（管理层讨论/主营业务等，跳过财务报表）
#    已存在则跳过——_extracted.md 是确定性 pymupdf 产物（零 LLM、与 variant 无关），
#    落 slug 级 materials/ 可跨 variant 直接复用（与研报 _vlm/ 同为「机械转换层」，对称见 Step B）
test -f "prism/topics/{slug}/materials/{filename_stem}_extracted.md" \
  && echo "已存在，跳过提取（复用 slug 级转换产物）" \
  || python3 -m scripts.annual_report_extractor \
       "{material_path}" \
       --out "prism/topics/{slug}/materials/{filename_stem}_extracted.md"
```

提取完成后，读取 `_extracted.md` 作为分析内容（而非原始 PDF）。

> 🔁 **跨 variant 复用（机械转换层）**：年报 `_extracted.md`（pymupdf）与研报 `_vlm/`（mineru）都是**不调本研究模型的确定性产物**，同一份 PDF 换模型重研字节级一致 → 一律落 slug 级 `materials/`、命中即跳过。**只有 `findings_mat-*.md`（LLM 按本 variant thesis 的 K# 解读）才按 variant 隔离**。详见各 topic `_process_log` P1。

> ⚠️ **materials/ 是 slug 级共享目录**（`prism/topics/{slug}/materials/`，跨 variant 共用），**不是** `{slug}/{variant}/materials/`（该目录不存在，写进去 extractor/mineru 直接 FileNotFoundError）。所有 `_extracted.md` / `_vlm/` 产物都落 slug 级。

**段落级过滤**：故意不做。年报章节抽取后通常 50-80K tokens，单份 LLM 可以一口气消化，由 LLM 根据 thesis K# 自行识别相关段落比 keyword grep 准确得多——避免「凝聚态/麒麟」等非字面变体被漏掉。

```bash
# 2. 从财务 API 补充财务数据（不从 PDF 解析财务数字）
python3 -c "
from prism.scripts.financial_data import get_financial_context
print(get_financial_context('{slug}', '{variant}'))
"
```

将财务数据作为独立上下文附在发现笔记末尾，不计入 token 主正文。

#### B. 研报 / 行业报告（source_type = sell-side-note 或 industry-research）

> ⚠️ **必须用 vlm 模型**——CLI `--model vlm` 不能改成 pipeline/默认。研报/行业报告中表格、公式、多栏排版是核心数据，pipeline 会丢失。详见 [[feedback_mineru_required]]。

> 🔑 **env 变量名是 `MINERU_TOKEN`（在 `.env`），不是 `MINERU_API_KEY`**。缺了 `mineru_api` 会 raise `MINERU_TOKEN not set — add it to .env`。

```bash
# 1. 找到文件位置
python3 -c "
from prism.scripts.manifest import get_material_path
path = get_material_path('{slug}', '{filename}')
print(path if path else 'FILE_NOT_FOUND')
"
# 2. 检查是否已转换（避免重复消耗 API 配额）
test -f "prism/topics/{slug}/materials/{filename_stem}_vlm/full.md" \
  && echo "已存在，跳过转换" \
  || .venv/bin/python -m scripts.mineru_api \
       "{material_path}" \
       --out "prism/topics/{slug}/materials/{filename_stem}_vlm" \
       --model vlm

# 3. 转换成功后翻 mineru_state 为 done（避免 manifest 长期显示 "needs"）
python3 -c "
from pathlib import Path
from prism.scripts.manifest import set_mineru_state
md = Path('prism/topics/{slug}/materials/{filename_stem}_vlm/full.md')
if md.exists() and md.stat().st_size > 0:
    set_mineru_state('{slug}', '{variant}', '{mat_id}', 'done')
    print('mineru_state → done')
else:
    set_mineru_state('{slug}', '{variant}', '{mat_id}', 'failed')
    print()
    print('=' * 60)
    print('⛔ mineru 转换失败 — 跳过这份资料、不要硬抽 finding')
    print('=' * 60)
    print(f'mat_id: {mat_id}')
    print(f'filename: {filename}')
    print()
    print('原因：full.md 缺失或为空——研报/行业报告无 OCR 内容，强行读 PDF')
    print('会丢失所有表格、公式、图片数据，finding 质量会严重劣化。')
    print()
    print('补救：')
    print('  1. 立即跳到下一份资料继续 03（不阻塞）')
    print('  2. 完成本轮 03 后回 workflow 02 Step 4.5 用 list_pending_mineru')
    print('     批量重试 failed 的；或单独跑 scripts.mineru_api 排查 API 配额/网络')
    print('  3. 修好后回 03 重跑该 mat（unprocessed 队列里它仍在）')
    print('=' * 60)
"
```

转换完成后，读取 `prism/topics/{slug}/materials/{filename_stem}_vlm/full.md` 作为分析内容。

**Mineru 失败时主 agent 必须**：（1）在对话里向用户报告失败 mat_id + 上面三条补救路径；（2）跳过该资料，不要用 pymupdf/直读 PDF 偷工（参 [[feedback_mineru_required.md]]）；（3）继续处理下一份 unprocessed。

> 转换规则参见 `.claude/skills/mineru/SKILL.md`。
> 02 Step 4.5 已批量预转换，03 这一段是"用户跳过 02 直接 03"或"02 失败漏修"时的兜底救场——不是 02 的替代品。

#### C. 已是 markdown / 文本文件

直接读取，无需预处理。

```bash
# 找到文件位置
python3 -c "
from prism.scripts.manifest import get_material_path
path = get_material_path('{slug}', '{filename}')
print(path if path else 'FILE_NOT_FOUND')
"
# 读取
cat "{material_path}"
```

#### D. SEC 章节（source_type = sec-section）

`item_1_business.md` / `item_1a_risk.md` / `item_7_mda.md` / `item_7a_quant_risk.md` / `item_8_financial.md`（10-K）
或 `item_1_financial.md` / `item_2_mda.md` / `item_3_quant_risk.md` / `item_1a_risk.md`（10-Q）。

每个 section md 是 `sec_section_split` 切好的纯文本，直接读：

```bash
python3 -c "
from prism.scripts.manifest import get_material_path
path = get_material_path('{slug}', '{filename}')
print(path if path else 'FILE_NOT_FOUND')
"
cat "{material_path}"
```

**抽 finding 时按 manifest 的 `addresses` 标签聚焦**：
- `item_1_business` → `[scope, K3, K5]` —— 业务全景、护城河、增长驱动
- `item_1a_risk` / `item_1a_risk` (10-Q) → `[risk, K1, K6]` —— 风险因素、催化剂触发
- `item_7_mda` / `item_2_mda` → `[K2, K4, K5]` —— 周期定位、财务逻辑、隐含预期
- `item_7a_quant_risk` / `item_3_quant_risk` → `[risk, K2]` —— 量化风险敞口
- `item_8_financial` / `item_1_financial` → `[valuation, K1]` —— 估值反推、关键数据点

不要在 risk section 里硬抽估值数据，也不要在 financial section 里写定性叙事——选错 section = 浪费 LLM context。

**需要跨 section 上下文**（如 MDA 引用了财报某行）→ 同目录其他 section md 都可读，`_meta.yaml` 列出全部 section + 行号区间。

---

### 2.2 提取结构化发现（LLM 推断，在对话里完成）

按以下框架提取：

**A. 核心数据点与事实**（有明确数字/时间/主体的陈述）
- 格式：「[来源] [时间] [主体/指标] [数值/结论]」
- 取舍原则（保留 vs 省略）：
  - **保留**：有具体数字的事实（量、价、时间、占比）；与其他资料有分歧或矛盾的信息；具体公司进展/合同/客户关系；报告独有的测算逻辑（降本路径、市场空间拆分）
  - **省略**：无数据支撑的泛泛判断；行业背景铺垫（常识性知识）；风险提示套话；中间推导步骤（保留起终点即可）；多份资料共同出现的共识数据
- 目标 15-20 条；超过需说明原因

**B. 叙事主线**（报告核心论证链，3 句以内）
- 格式：「因为 X（数据依据）→ 所以研报判断 Y → 对投资意味着 Z」
- 这是报告的主线逻辑，不是观点列表；只写一组核心链条

**C. 反常识/分歧点**（与市场共识或其他资料相悖的内容）
- 格式：「市场预期/常识：xxx，本文表明：xxx」
- 没有则写「无」

**D. 未回答问题**（可选，1-3 条）
- 这份资料没有回答、但对本研究判断重要的问题
- 没有则省略此节

**E. 资料质量评估**
- 数据新鲜度（最新数据截至几时）
- 分析师倾向（偏多/偏空/中性）
- 可信度（高/中/低，原因）
- 与已有发现是否矛盾

**F. 决策链专项勾（O1 · 抽取要喂下游 6 环，不只 K#）**

抽取时**主动扫**以下决策链输入合同类目（见 `_input_contract.md`）——这些是合成层 6 环【必带硬落地】最依赖、且历史上最容易漏抽的维度。命中就抽成独立数据点 + 给该 finding 打对应 `rings`：

- **②定价锚 / 一致预期**（`consensus` / `valuation-anchor`）：卖方目标价、隐含增速/PE、一致预期 EPS/估值倍数、历史估值区间 → 喂环②反推。**别只抽"看多看空"，要抽具体的数字锚**。
- **①管理层 / 资本配置史**（`mgmt-capital-alloc`）：掌舵人任期/track record、回购/分红/并购的历史金额与回报、激励与治理结构 → 喂环①第二梁。年报/proxy 里常有，过去常被当背景略过，现在是一等公民。
- **⑤历史镜鉴**（`historical-mirror` / `industry-mirror` / `arena-mirror`）：相似剧本怎么崩、利润为何没兑现、曾经赢家如何被取代 → 喂环⑤。复盘类材料命中就抽教训一句话。
- **①生意/单位经济**（`biz-moat-unit-econ`）、**④多空/横比**（`bull-bear` / `peer-comparison-financials`）按 type 命中即抽。

> 收料期材料可能已粗标 rings（02 / fetcher）；抽取时按**实际抽到的内容**在 finding frontmatter 精修——抽到了就标，没抽到的别硬标。一份料可同时服务多个 ring。

### 2.3 写入发现笔记

写入 `prism/topics/{slug}/{variant}/outputs/findings_{mat_id}.md`：

```markdown
---
mat_id: {mat_id}
filename: {filename}
source_type: {source_type}
extracted: {timestamp}
quality: high|medium|low
bias: bull|bear|neutral
addresses: [{命中的 K#}]        # thesis 脊柱；frontmatter 优先于 manifest
rings: [{命中的决策链输入合同 code}]   # 见 §2.2 F + _input_contract.md；没命中可省略此字段
conflicts_with: [{冲突 finding 文件名/id}]   # 可选（B6 · observability.md §4.6）：本 finding 与
                                              #   哪些 finding 证据相矛盾；无冲突则省略此字段
conflict_note: {一句话：冲突在哪/暂如何取舍}   # 可选，仅 conflicts_with 非空时填；供被动探针 03.Q3 读
---

## 核心数据点与事实

{bullet list，按取舍原则筛选，目标 15-20 条}

## 叙事主线

因为 {X（数据依据）} → 所以 {研报判断 Y} → 对投资意味着 {Z}

## 反常识/分歧点

{bullet list or "无"}

## 未回答问题

{1-3 条 or 省略此节}

## 质量备注

{notes}
```

---

### 2.4 训练知识冲突触发即兴 web-search（新增）

提取 finding 时如果遇到以下情况，**主 agent 可以即兴调用 WebSearch 验证一条**（不需要回 02 让用户跑 prescan）：

- 资料中数字与 LLM 训练知识冲突（如资料说 "2024 年市占率 35%"，LLM 训练记忆是 25%）
- 资料引用的事件 LLM 训练时不知道（训练截止后的新事件）
- 资料给出的关键定性结论与 LLM 业内常识不一致

执行方式（保持原 03 主流程不被打断）：

1. 主 agent 在对话里调 `WebSearch` 工具，query 围绕冲突点构造（不超过 2 条）
2. 拿到 hit 后用 Phase 1 加的 helper 一行入库：

```python
from prism.scripts.web_prescan import register_web_search_batch
register_web_search_batch(
    slug='{slug}', variant='{variant}',
    query='冲突点查询词',
    addresses=['{相关 K#}'],
    triggered_by='03-extract',
    hits=[
        {'title': '...', 'url': 'https://...', 'snippet': '...'},
        # 可选: 'confidence': 0.85, 'domain_tier': 'llm-judged-official'
    ],
)
```

3. `triggered_by='03-extract'` 时 `register_web_search_batch` **自动产 inline finding** +
   `mark_processed`。返回值多了 `inline_finding_paths`
   列表，主 agent 可直接 cat 验证。**不会再悬挂到下一轮 03 队列**。
4. 在当前 finding 笔记里**注明**："此处与训练知识 / 资料 X 冲突，已即兴 web-search 入库 mat-xxx 备核"

**纪律**：
- 单份资料 03 处理过程中即兴 web-search 不超过 3 条（避免变成 prescan）
- 若冲突点超过 3 条 → 标记 user_todos，stage 回退 02-gather-materials 走完整 prescan
- 即兴 web-search 必须填 addresses，否则 manifest coverage 算不进
- URL/snippet 必须来自 WebSearch 工具实际返回，不得用训练记忆补 URL
- 显式 `inline_finding=False` 可关闭自动产 finding（罕见，如只想登记 URL 留痕）

### 2.4b 深挖循环升级（可选）

如果 2.4 的"即兴 1-3 条" 不够（如冲突点本身需要多角度验证），主 agent **升级为 dispatch sub-agent 跑深挖循环**：

```
主 agent 判断："1-3 条 query 不足以验证此冲突 → dispatch sub-agent"
  ↓
按 prism/workflows/_subagent_deep_search.md 模版构造 prompt
  ↓
Agent 工具调用（subagent_type='general-purpose', 不传 model）
  ↓
sub-agent 在自己 context 跑 1-3 轮 search → 返回 final message
  ↓
主 agent 解析 hits → register_web_search_batch（triggered_by='03-extract'）
```

**纪律**：
- 一份资料 03 处理过程最多 dispatch 1 次 sub-agent（防"sub-agent 套娃"）
- sub-agent prompt **必须**原文嵌入 _subagent_deep_search.md 的硬规约（防写文件幻觉）

---

## Step 3：标记资料已处理

```bash
python3 -c "
from prism.scripts.manifest import mark_processed
mark_processed('{slug}', '{mat_id}', '{variant}')
print('已标记处理完成')
"
```

对每份处理完的资料执行一次。

---

## Step 3.5：重建 findings 索引（所有 finding 写完后必跑）

下游 workflow 04 依赖 `outputs/_findings_index.md` 做"按需补读"决策。每次新增 finding 后必须重建：

```bash
python3 -c "
from prism.scripts.findings import build_findings_index
print(build_findings_index('{slug}', '{variant}'))
"
```

输出新索引文件路径。索引每行 ~80-120 字，22 份 ≈ 3-5K tokens，远低于全文 ~40K，是 04 阶段防 compact + 按需补读的"地图"。

---

## Step 4：完成所有资料后更新状态

**⚠️ 用 `append_user_todos` 不用 `set_user_todos`**——01/02 写的结构化 todos（含 K# addresses）不能被进度提示覆盖。

**⚠️ 进度播报必须传显式 `status`（修：播报污染"待补料"计数）**——`append_user_todos(['纯字符串'])` 会默认落 `status='pending'`，而 web 详情页把每条 pending 当"⚠️ 待你手工补 N 份资料"。**里程碑播报（已完成的事）传 `status='done'`、进行中播报传 `status='in_progress'`**，绝不让播报落进 pending（pending 仅保留给"用户须去取的真实资料"，那些一律带 `addresses`）。

```bash
python3 -c "
from prism.scripts.topic import set_stage, set_next_actions, append_user_todos
from prism.scripts.manifest import material_count
counts = material_count('{slug}', '{variant}')
# advance gate 读 unprocessed_actionable（排除 Role α prescan web 料）：
# 用全量 unprocessed 会让任何跑过 prescan 的 topic 永不升 04
if counts['unprocessed_actionable'] == 0:
    set_stage('{slug}', '04-synthesizing', '{variant}')
    set_next_actions('{slug}', [
        '所有资料已处理完毕，可以生成产出',
        '说「prism 推进 {slug}」走决策链合成（00_primer 领域入门 + {c/i/a}_case 成稿 + sidecar）',
    ], '{variant}')
    append_user_todos('{slug}', [
        {'task': f'资料提取完成：{counts[\"total\"]} 份全部处理完毕', 'status': 'done'},
    ], '{variant}')
else:
    set_next_actions('{slug}', [
        f'还有 {counts[\"unprocessed_actionable\"]} 份可处理资料未处理',
    ], '{variant}')
    append_user_todos('{slug}', [
        {'task': f'资料提取中：{counts[\"processed\"]}/{counts[\"total\"]} 份已处理', 'status': 'in_progress'},
    ], '{variant}')
"
```

---

## Step 5：选择是否更新产出 + 落地状态

**AskUserQuestion**：

```
新资料处理完成！

已处理：{N} 份
关键发现（跨所有资料）：
- {最重要的 3-5 条数据点}

现在要不要立即更新产出？
[ ] 更新产出（重跑决策链合成：00_primer + {c/i/a}_case + sidecar）
[ ] 暂时不更新（等更多资料一起）
```

收到用户选择后**同对话**直接落 stage / next_actions / todos（不再分两步）：

```bash
python3 -c "
from prism.scripts.topic import set_stage, set_next_actions, append_user_todos
from prism.scripts.manifest import material_count
counts = material_count('{slug}', '{variant}')
if counts['unprocessed_actionable'] == 0:   # 排除 Role α
    set_stage('{slug}', '04-synthesizing', '{variant}')
    if {user_chose_update}:
        set_next_actions('{slug}', [
            '正在更新产出...',
        ], '{variant}')
        append_user_todos('{slug}', [
            {'task': '产出更新中...', 'status': 'in_progress'},
        ], '{variant}')
    else:
        set_next_actions('{slug}', [
            '新资料已处理，等待后续再更新产出',
            '需要时说「prism 推进 {slug}」重跑决策链合成',
        ], '{variant}')
        append_user_todos('{slug}', [
            {'task': '新资料已记录，产出暂未更新', 'status': 'done'},
        ], '{variant}')
else:
    set_next_actions('{slug}', [
        f'还有 {counts[\"unprocessed\"]} 份资料未处理',
    ], '{variant}')
    append_user_todos('{slug}', [
        {'task': f'资料提取中：{counts[\"processed\"]}/{counts[\"total\"]} 份已处理', 'status': 'in_progress'},
    ], '{variant}')
"
```

---

## Step 6：汇报

```
✅ 资料提取完成

已处理：{N} 份
关键发现（跨所有资料）：
- {list key findings}

你选择了「{用户选择}」
```
