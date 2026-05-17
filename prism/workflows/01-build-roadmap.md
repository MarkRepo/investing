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

---

## Step 2：制定学习轨道（L1→L4 问题树）

基于训练知识，为这个研究主题制定四层问题：

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
- 如果市场错了，错在哪里？
- 哪个时间节点能验证或证伪？
- 什么样的新信息会改变当前判断？

---

## Step 3：制定资料优先级

根据研究深度，列出三档资料：

**Tier 1（必读）**：对研究结论影响最大、最难被替代的 3-5 份
**Tier 2（补充）**：有助于验证但非必须的 3-5 份  
**Tier 3（可选）**：深度研究时可参考的

每份资料说明：标题方向、类型（研报/年报/政策/数据）、从哪里找、为什么重要。

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
> - A 股：`SSE_600519` / `SZSE_300750`
> - 美股：`NVDA` / `AAPL`
> - 不可自动下载的（韩股/非上市公司）：留空

```bash
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

## Step 6：更新 topic 状态

从刚生成的 roadmap.yaml 读取资料，把**已成功下载的**从 user_todos 里移除：

```bash
python -c "
import yaml
import re
from pathlib import Path
from prism.scripts.topic import set_stage, set_next_actions, set_user_todos

# Read roadmap
roadmap_path = Path('prism/topics/{slug}/{variant}/roadmap.yaml')
roadmap = yaml.safe_load(roadmap_path.read_text())

# Check what's already downloaded
manual_dir = Path('prism/inbox/manual')
auto_dir = Path('prism/inbox/auto')
materials_dir = Path('prism/topics/{slug}/materials')
downloaded_filenames = set()
if manual_dir.exists():
    downloaded_filenames.update(p.name for p in manual_dir.iterdir() if p.is_file())
if auto_dir.exists():
    downloaded_filenames.update(p.name for p in auto_dir.iterdir() if p.is_file())
if materials_dir.exists():
    downloaded_filenames.update(p.name for p in materials_dir.iterdir() if p.is_file())

# Build user_todos from tier1 (skip already downloaded)
def is_downloaded(mat):
    title = mat['title']
    ticker = mat.get('ticker', '').strip()
    # Match by ticker in filenames (e.g. NVDA in 2026-02-25_NVDA_10-K_2026-01-25.htm)
    if ticker:
        ticker_key = ticker.replace('SSE_', '').replace('SZSE_', '').upper()
        for fname in downloaded_filenames:
            if ticker_key in fname.upper() or ticker in fname:
                return True
    # Fallback: match by title substring
    safe_title = re.sub(r'[<>:\"/\\\\|?*]', '_', title)[:80]
    for fname in downloaded_filenames:
        if safe_title[:20] in fname or title[:20] in fname:
            return True
    return False

todos = ['Tier1 必读资料：']
for i, mat in enumerate(roadmap['material_priority']['tier1'], 1):
    if not is_downloaded(mat):
        todos.append(f'  {i}. {mat[\"title\"]}')
    else:
        todos.append(f'  {i}. {mat[\"title\"]} ✓ (已下载)')

# Add tier2 as optional if depth is deep
if roadmap.get('material_priority', {}).get('tier2'):
    todos.append('')
    todos.append('Tier2 补充资料（可选）：')
    for i, mat in enumerate(roadmap['material_priority']['tier2'], 1):
        if not is_downloaded(mat):
            todos.append(f'  {i}. {mat[\"title\"]}')
        else:
            todos.append(f'  {i}. {mat[\"title\"]} ✓ (已下载)')

# Set topic state
set_stage('{slug}', '02-gather-materials')
set_next_actions('{slug}', [
    '收集剩余资料后运行 workflow 02-gather-materials 登记资料',
    '有资料可以处理时运行 workflow 03-extract-findings',
])
set_user_todos('{slug}', todos)
"
```

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
