# Workflow 01 — 制定研究路线图

**触发**：stage=01-roadmap-pending 或用户说「制定路线图」  
**前置**：topic.yaml 已存在  
**产出**：`prism/topics/{slug}/{variant}/roadmap.yaml`

---

## Step 1：读取 topic

```bash
python -c "
import json
from prism.scripts.topic import read_topic
print(json.dumps(read_topic('{slug}', '{variant}'), ensure_ascii=False, indent=2))
"
```

确认研究问题、类型、地理范围、深度。

---

## Step 1.5：检查父 topic 可复用资料

如果此 topic 有 `parent_topic`，列出父 topic 已收集的 materials 并标记哪些可复用：

```bash
python -c "
from prism.scripts.topic import read_topic, list_parent_materials
from prism.scripts.manifest import read_manifest
import json

topic = read_topic('{slug}', '{variant}')
parent = topic.get('parent_topic')
if parent:
    print(f'父 topic: {parent}')
    # 列出父 topic materials 目录
    materials = list_parent_materials('{slug}', '{variant}')
    print(f'父 topic materials ({len(materials)} 份):')
    for m in materials:
        print(f'  {m}')
    
    # 读取父 topic 的 manifest 获取 notes
    # 尝试所有 variant
    from prism.scripts.topic import list_variants
    variants = list_variants(parent)
    if variants:
        try:
            manifest = read_manifest(parent, variants[0])
            print()
            print('Manifest 详情:')
            for mat in manifest.get('materials', []):
                print(f'  [{mat[\"id\"]}] {mat[\"filename\"]}')
                print(f'    类型: {mat[\"source_type\"]}')
                print(f'    备注: {mat.get(\"notes\", \"\")}')
        except Exception as e:
            print(f'(无法读取 manifest: {e})')
else:
    print('无 parent_topic，跳过')
"
```

**根据输出判断**：哪些父 topic 资料对此 arena/company 研究有直接价值？在 Step 3 中将这些可复用资料标注为 `✓ 已收集（来自父 topic）`，并在 roadmap 的 `why` 字段中注明"复用父 topic materials/{filename}"。

**关键：用脚本登记 parent_materials 字段**（让 workflow 04 自动复用，不用 dispatch prompt 手填路径）：

```bash
python3 -c "
from prism.scripts.topic import set_parent_materials
items = [
    {'parent_slug': '{父slug}', 'mat_id': 'mat-XXXXXX', 'addresses': ['K1','K2'], 'note': '...'},
    # 只列对本 topic thesis 有价值的父级 mat_id（不要全部塞）
]
set_parent_materials('{slug}', '{variant}', items)
print(f'已登记 {len(items)} 项父级复用')
"
```

mat_id 从父 topic `manifest.yaml` 拿（`prism/topics/{父slug}/{父variant}/manifest.yaml`），filename 不重要，链接通过 mat_id。

---

## Step 1.7：读取 thesis（**强制：路线图必须 thesis-driven**）

在制定路线图前先把 thesis_v0（如有）读进来：

```bash
python3 -c "
from prism.scripts.topic import read_topic
from prism.scripts.outputs import extract_killer_questions, extract_research_questions
t = read_topic('{slug}', '{variant}')
cur = (t.get('thesis') or {}).get('current_version')
if cur is None:
    print('⚠ 无 thesis — 应先回 workflow 00 Step 5.0 写 thesis_v0')
else:
    print(f'当前 thesis: v{cur}')
    print('Killer Questions:', extract_killer_questions('{slug}', '{variant}', cur))
    print('Research Questions:', extract_research_questions('{slug}', '{variant}', cur))
"
```

**如果没有 thesis**：先回 workflow 00 Step 5.0 写 thesis_v0，再回来跑 Step 2。

---

## Step 2：制定学习轨道（L1→L4 问题树）

**硬要求**：
- **L4 狩猎层必须逐条对齐 thesis 的 Killer Question**（K1, K2, ...），每条 L4 question 写 `addresses: [Kn]` 字段
- L3 争议层应反映 thesis 的"最大反方观点"——把反方逻辑展开为 3-5 个可调研的争议点
- L1/L2 是基础知识层，与 thesis 无强对齐

基于训练知识 + thesis_v0 内容，为这个研究主题制定四层问题：

**L1 定向层**（3-4 个问题）：搞清楚「是什么」
- 这个行业的边界在哪里？怎么定义市场？
- 主要参与者有哪些（上游/中游/下游）？
- 市场规模多大？主要增长驱动是什么？

**L2 历史层**（3-4 个问题）：搞清楚「怎么来的」
- 过去 5-10 年经历了哪几个发展阶段？
- 有没有明显的周期性规律？
- 关键拐点（政策/技术/需求）是什么时候？

**L3 争议层**（4-5 个问题）：搞清楚「分歧在哪」
- 多空双方的核心分歧是什么？
- 市场共识是什么，哪里可能是错的？
- 最容易被忽视的风险是什么？

**L4 狩猎层**（3-5 个问题）：找错误定价
- **每条必须对应一个 thesis Killer Question（K1/K2/...），addresses: [Kn]**
- 如果市场错了，错在哪里？
- 哪个时间节点能验证或证伪？
- 什么样的新信息会改变当前判断？

L4 写完后做 self-check：thesis 的 N 个 K# 是否每个都有对应的 L4 question？没覆盖的要么补 L4，要么回 thesis 标注"本次不验证此 K"。

---

## Step 3：制定资料优先级

**硬要求**：
- **复用 5.3 已写的 user_todos** 作为 tier1 基础——它们已带 priority/info_tier/addresses 字段
- 每份资料填写 `addresses: [Kn, Qn]` 字段，对应 thesis K# 或 L1-L4 question 编号（不能不写）
- 5.3 P0 → 默认进 tier1；P1 → tier2；P2 → tier3
- 如果 5.3 没覆盖但路线图需要的，新增到对应 tier，**也必须写 addresses**

根据研究深度，列出三档资料：

**Tier 1（必读）**：对研究结论影响最大、最难被替代的 3-5 份
**Tier 2（补充）**：有助于验证但非必须的 3-5 份
**Tier 3（可选）**：深度研究时可参考的

每份资料说明：标题方向、类型（研报/年报/政策/数据）、从哪里找、为什么重要、**addresses（对应哪些 K#/L 问题）、info_tier**。

**对 `annual-report` 类型，必须填写 `ticker` 字段**以支持自动下载：
- A 股：`SSE_600519` / `SZSE_300750`
- 美股：`NVDA` / `AAPL`（直接写 ticker）
- 不可自动下载的（韩股/无代码）：留空

---

## Step 4：识别历史类比

列出 2-3 个值得研究的历史类比案例，格式：
- 案例名称（国家+行业+时间段）
- 类比逻辑（哪里像）
- 类比局限（哪里不像）

---

## Step 5：写入 roadmap.yaml

复制 `prism/templates/roadmap.yaml.tmpl`，填入上面分析内容，写入：
`prism/topics/{slug}/{variant}/roadmap.yaml`

---

## Step 5.5：尝试自动下载可获取的资料

> **ticker 规则**：LLM 在 Step 3 写 roadmap 时，对 `annual-report` 类型材料必须填写 `ticker` 字段。
> - A 股：`SSE_600519` / `SZSE_300750`（自动走 cninfo）
> - 美股：`QS` / `NVDA` / `AAPL`（自动走 SEC EDGAR；自动下 10-K + 10-Q）
> - 不可自动下载的（韩股/非上市公司）：留空

**统一入口**：`scripts.fetch_report_prism.fetch(ticker, slug=, variant=)` 会根据 ticker 格式自动路由到 cninfo 或 SEC，并自动登记 manifest + 更新 todo status。

**多年批量**（A 股 / cninfo only — 用于 thesis 需要多年纵向对照的场景）：

```python
from scripts.fetch_report_prism import fetch_many
fetch_many('SSE_688499', years=[2020, 2021, 2022, 2023, 2024], slug=slug, variant=variant)
# 或 CLI: python -m scripts.fetch_report_prism SSE_688499 --years 2020-2024 --slug ...
```

**文件命名规范**（E7）：年报 / 10-K 落盘后均以 `{report_year}_{ticker}_...` 开头，便于按 report_year 排序、grep 同公司多年材料。旧文件保留原名不动；只对新下载生效。

```bash
python3 << 'EOF'
import yaml
from pathlib import Path
from scripts.fetch_report_prism import fetch

slug = '{slug}'
variant = '{variant}'
roadmap = yaml.safe_load(Path(f'prism/topics/{slug}/{variant}/roadmap.yaml').read_text())

downloaded, failed = [], []
for tier in ['tier1', 'tier2', 'tier3']:
    for mat in roadmap.get('material_priority', {}).get(tier, []) or []:
        if mat.get('type') not in ('annual-report', 'prospectus'):
            continue
        tk = (mat.get('ticker') or '').strip()
        title = mat.get('title', '')
        if not tk:
            failed.append(f'{{title[:50]}} (无 ticker)')
            continue
        try:
            result = fetch(tk, slug=slug, variant=variant)
            downloaded.append(f'{{title[:50]}} → {{result}}')
        except Exception as e:
            failed.append(f'{{title[:50]}} ✗ ({{e}})')

print(f'=== DOWNLOADED ({{len(downloaded)}}) ===')
for x in downloaded: print(f'  {{x}}')
print(f'\\n=== FAILED ({{len(failed)}}) ===')
for x in failed: print(f'  {{x}}')
EOF
```

**老的内联下载代码（已废弃）—— 仅作为 fallback 参考**:

```bash
# DEPRECATED — use fetch() from scripts.fetch_report_prism instead
python -c "
import yaml, re, sys, subprocess, json, os, urllib.request
from pathlib import Path
from datetime import date

roadmap_path = Path('prism/topics/{slug}/{variant}/roadmap.yaml')
roadmap = yaml.safe_load(roadmap_path.read_text())

downloaded, failed = [], []
UA = 'investment-wiki research@example.com'
OUT = Path('prism/inbox/auto')
OUT.mkdir(parents=True, exist_ok=True)

def extract_years(title):
    years = set()
    for m in re.finditer(r'(20[12]\d|2030)', title):
        y = int(m.group(1))
        if 2015 <= y <= 2030:
            years.add(y)
    return sorted(years, reverse=True)

# === SEC EDGAR: cache CIK lookup ===
_cik_cache = {{}}
def get_cik(ticker):
    if _cik_cache:
        return _cik_cache.get(ticker.upper())
    try:
        req = urllib.request.Request(
            'https://www.sec.gov/files/company_tickers.json',
            headers={{'User-Agent': UA}}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        for v in data.values():
            _cik_cache[v['ticker'].upper()] = (str(v['cik_str']).zfill(10), v['title'])
    except Exception as e:
        print(f'SEC CIK 获取失败: {{e}}')
        return None
    return _cik_cache.get(ticker.upper())

def download_sec(ticker, cik):
    '''Download latest 10-K and 10-Q for a US ticker.'''
    results = []
    try:
        url = f'https://data.sec.gov/submissions/CIK{{cik}}.json'
        req = urllib.request.Request(url, headers={{'User-Agent': UA}})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        return [(False, f'{{ticker}} SEC filings 获取失败: {{e}}')]

    recent = data.get('filings', {{}}).get('recent', {{}})
    forms = recent.get('form', [])
    dates = recent.get('filingDate', [])
    report_dates = recent.get('reportDate', [])
    acc_numbers = recent.get('accessionNumber', [])
    docs = recent.get('primaryDocument', [])

    targets = {{}}
    for i, form in enumerate(forms):
        if '/A' in form:
            continue
        if form == '10-K' and '10-K' not in targets:
            targets['10-K'] = i
        if form == '10-Q' and '10-Q' not in targets:
            targets['10-Q'] = i
        if len(targets) == 2:
            break

    for form, idx in targets.items():
        acc_dir = acc_numbers[idx].replace('-', '')
        cik_num = str(int(cik))
        doc = docs[idx]
        filing_date = dates[idx]
        report_date = report_dates[idx]
        ext = os.path.splitext(doc)[1] or '.htm'
        fname = f'{{filing_date}}_{{ticker}}_{{form}}_{{report_date}}{{ext}}'
        dest = OUT / fname

        if dest.exists():
            results.append((True, f'{{ticker}} {{form}} ({{report_date}}) — 已存在'))
            continue

        dl_url = f'https://www.sec.gov/Archives/edgar/data/{{cik_num}}/{{acc_dir}}/{{doc}}'
        try:
            req2 = urllib.request.Request(dl_url, headers={{'User-Agent': UA}})
            with urllib.request.urlopen(req2, timeout=120) as resp:
                content = resp.read()
            dest.write_bytes(content)
            size_mb = len(content) / (1024*1024)
            results.append((True, f'{{ticker}} {{form}} ({{report_date}}) ✓ ({{size_mb:.1f}}MB)'))
        except Exception as e:
            results.append((False, f'{{ticker}} {{form}} ({{report_date}}) ✗ ({{e}})'))

    return results

def is_us_ticker(ticker):
    return bool(re.match(r'^[A-Z]{{1,5}}$', ticker))

for tier in ['tier1', 'tier2', 'tier3']:
    for mat in roadmap.get('material_priority', {{}}).get(tier, []) or []:
        mat_type = mat.get('type', '')
        title = mat.get('title', '')
        mat_ticker = mat.get('ticker', '').strip()

        if mat_type not in ('annual-report', 'prospectus'):
            continue
        if not mat_ticker:
            failed.append(f'{{title}} (无 ticker，跳过)')
            continue

        # === US stock (ticker like NVDA) ===
        if is_us_ticker(mat_ticker):
            cik_info = get_cik(mat_ticker)
            if cik_info:
                cik, cname = cik_info
                results = download_sec(mat_ticker, cik)
                for ok, desc in results:
                    (downloaded if ok else failed).append(f'{{title}} — {{desc}}')
            else:
                failed.append(f'{{title}} (SEC CIK 查找失败)')
            continue

        # === A-share (ticker like SSE_688256) ===
        years = extract_years(title)
        if not years:
            years = [date.today().year - 1]

        for year in years:
            try:
                r = subprocess.run(
                    [sys.executable, '-m', 'scripts.fetch_report_prism', mat_ticker,
                     '--year', str(year), '--slug', '{slug}'],
                    capture_output=True, text=True, timeout=120
                )
                if r.returncode == 0:
                    downloaded.append(f'{{title}} ({{year}}年) ✓')
                else:
                    failed.append(f'{{title}} ({{year}}年) ✗')
            except Exception as e:
                failed.append(f'{{title}} ({{year}}年) ✗ ({{e}})')

print('DOWNLOADED:')
for item in downloaded:
    print(f'  {{item}}')
print('FAILED:')
for item in failed:
    print(f'  {{item}}')
"
```

---

## Step 5.7：自动校验 roadmap → thesis 闭环（**未通过不得进 Step 6**）

```bash
python3 -c "
from prism.scripts.outputs import validate_roadmap_thesis_coverage
from prism.scripts.topic import read_topic
t = read_topic('{slug}', '{variant}')
cur = (t.get('thesis') or {}).get('current_version')
if cur is None:
    print('⚠ 无 thesis，跳过校验（强烈建议补 thesis）')
else:
    r = validate_roadmap_thesis_coverage('{slug}', '{variant}', cur)
    print(f'Thesis K#: {r[\"thesis_ks\"]}')
    print(f'L4 covered: {r[\"l4_covered\"]}')
    print(f'Material covered: {r[\"material_covered\"]}')
    if not r['ok']:
        print()
        if r['uncovered_in_l4']:
            print(f'❌ L4 未覆盖: {r[\"uncovered_in_l4\"]} — 补 L4 question 或在 thesis 中标注不验证')
        if r['uncovered_in_material']:
            print(f'❌ Material 未覆盖: {r[\"uncovered_in_material\"]} — 补 tier1/2/3 资料')
        raise SystemExit(1)
    print()
    print('✓ Coverage 通过')
"
```

如果非 0 退出，**回 Step 2/3 修 roadmap**，再回来跑 Step 5.7。

---

## Step 6：增量更新 topic 状态（**禁止覆写 5.3 结构化 todos**）

⚠️ **重要**：5.3 阶段写的 todos 已带 `priority/info_tier/addresses` 字段；不能用 `set_user_todos(slug, list[str])` 全量覆写——会丢字段、破坏 K# coverage 闭环。

**正确做法**：
1. 对已下载的 material，**更新对应 todo 的 status 为 `done` 或 `in_progress`**（仅下载部分时 in_progress）
2. **append** roadmap 里新出现、但 5.3 没覆盖的 tier1/tier2 todos（带完整结构）
3. 不删除任何旧 todo

```bash
python3 << 'EOF'
import yaml
from pathlib import Path
from prism.scripts.topic import (
    read_topic, set_stage, set_next_actions, set_user_todos, update_user_todo_status
)

slug = '{slug}'
variant = '{variant}'
roadmap = yaml.safe_load(Path(f'prism/topics/{slug}/{variant}/roadmap.yaml').read_text())

# 1. 收集已下载文件名（manual + auto + materials）
downloaded = set()
for d in ['prism/inbox/manual', 'prism/inbox/auto', f'prism/topics/{slug}/materials']:
    p = Path(d)
    if p.exists():
        downloaded.update(f.name for f in p.iterdir() if f.is_file())

# 2. 对每个 tier1 material 推断状态，更新匹配的 todo
def match_filename(ticker, keywords):
    '''检查 downloaded 里是否有匹配 ticker 或关键词的文件'''
    matches = []
    if ticker:
        tk = ticker.replace('SSE_', '').replace('SZSE_', '').replace('BSE_', '').upper()
        for f in downloaded:
            if tk in f.upper(): matches.append(f)
    for kw in keywords:
        for f in downloaded:
            if kw in f: matches.append(f)
    return matches

# LLM 在这里手动列出 (todo task 子串 → 资料完整性) 的判断
# 例：('宁德时代凝聚态', 'in_progress')  # 年报已到但访谈逐字稿还缺
# 例：('QuantumScape/Solid Power', 'done')  # 10-K + 10-Q 全到

todo_status_updates = [
    # ('todo task substring', 'done' | 'in_progress'),
    # 由 LLM 根据 manifest 判断填写
]
for sub, status in todo_status_updates:
    try:
        update_user_todo_status(slug, variant, sub, status)
        print(f'  ✓ {sub[:40]} → {status}')
    except ValueError as e:
        print(f'  ⚠ {e}')

# 3. Append 新结构化 todos（仅添加 5.3 没覆盖的、roadmap 新冒出来的资料任务）
data = read_topic(slug, variant)
existing_tasks = [t['task'] for t in data['user_todos']]
new_todos = list(data['user_todos'])
APPEND = [
    # 只 append 5.3 todos 完全没提到的新需求，例如：
    # {{'task': '查阅整车厂公告挖一级市场玩家披露', 'priority': 'P0',
    #  'info_tier': 'hard', 'addresses': ['K3','K4'], 'status': 'pending'}},
]
for t in APPEND:
    if not any(t['task'][:25] in et for et in existing_tasks):
        new_todos.append(t)

set_user_todos(slug, new_todos, variant)

set_stage(slug, '02-gather-materials', variant)
set_next_actions(slug, [
    f'已下载 N 份资料，登记 manifest（A股自动；美股需手工 add_material）',
    '运行 workflow 03-extract-findings 处理已收集资料',
    '剩余 P0 todo 补齐后再跑 workflow 03',
], variant)
EOF
```

**注意**：
- `update_user_todo_status` 按 task 字段子串匹配，确保子串唯一
- 旧的 list[str] 风格 todos 在 read 时会被 `_normalize_todo` 自动 upgrade 到 dict，但 priority/info_tier/addresses 会变成默认值——所以最好的实践是从 workflow 00 5.3 起就用结构化 schema

---

## Step 7：汇报

在对话输出：

```
✅ 研究路线图已生成 → prism/topics/{slug}/{variant}/roadmap.yaml

L4 狩猎问题（最重要）：
{list L4 questions}

Tier 1 必读资料：
{list tier 1 items}

你现在需要做的事：
1. 收集上述资料放入 prism/inbox/manual/
2. 具体清单已同步到 Web 页面 "你需要做的事" 区域
3. 完成后说「prism 推进 {slug}」继续

Web 地址：http://localhost:8000/prism/{slug}/{variant}/
```
