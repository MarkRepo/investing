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

```bash
python -c "
import yaml
import re
import sys
from pathlib import Path
from datetime import date

# Read roadmap
roadmap_path = Path('prism/topics/{slug}/{variant}/roadmap.yaml')
roadmap = yaml.safe_load(roadmap_path.read_text())

downloaded = []
failed = []

# Try to download annual reports
for tier in ['tier1', 'tier2', 'tier3']:
    for mat in roadmap.get('material_priority', {}).get(tier, []):
        if mat.get('type') == 'annual-report':
            # Try to extract company name/ticker from title
            title = mat.get('title', '')
            # Look for patterns like "XXXX(600519)2024年报" or similar
            ticker_match = re.search(r'(\d{6})', title)
            if ticker_match:
                ticker = ticker_match.group(1)
                # Determine market: 6/9/5 → SSE, else SZSE
                if ticker.startswith(('6', '9', '5')):
                    market_ticker = f'SSE_{ticker}'
                else:
                    market_ticker = f'SZSE_{ticker}'
                # Try to extract year - first remove the ticker part to avoid matching 600519 as year
                title_without_ticker = re.sub(r'\d{6}', '', title)
                # Look for 2020-2029 range first
                year_match = re.search(r'(202\d)', title_without_ticker)
                if not year_match:
                    year_match = re.search(r'(201\d)', title_without_ticker)
                year = int(year_match.group(1)) if year_match else (date.today().year - 1)
                # Try to download
                try:
                    import subprocess
                    result = subprocess.run(
                        [sys.executable, '-m', 'scripts.fetch_report_prism', market_ticker, '--year', str(year), '--slug', '{slug}'],
                        capture_output=True, text=True, timeout=120
                    )
                    if result.returncode == 0:
                        downloaded.append(f'{title} ✓')
                    else:
                        failed.append(f'{title} ✗')
                except Exception as e:
                    failed.append(f'{title} ✗')

print('DOWNLOADED:')
for item in downloaded:
    print(f'  {item}')
print('FAILED:')
for item in failed:
    print(f'  {item}')
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
materials_dir = Path('prism/topics/{slug}/materials')
downloaded_filenames = set()
if manual_dir.exists():
    downloaded_filenames.update(p.name for p in manual_dir.iterdir() if p.is_file())
if materials_dir.exists():
    downloaded_filenames.update(p.name for p in materials_dir.iterdir() if p.is_file())

# Build user_todos from tier1 (skip already downloaded)
def is_downloaded(title):
    safe_title = re.sub(r'[<>:\"/\\\\|?*]', '_', title)[:80]
    for fname in downloaded_filenames:
        if safe_title in fname or title[:30] in fname:
            return True
    return False

todos = ['Tier1 必读资料：']
for i, mat in enumerate(roadmap['material_priority']['tier1'], 1):
    if not is_downloaded(mat['title']):
        todos.append(f'  {i}. {mat[\"title\"]}')
    else:
        todos.append(f'  {i}. {mat[\"title\"]} ✓ (已下载)')

# Add tier2 as optional if depth is deep
if roadmap.get('material_priority', {}).get('tier2'):
    todos.append('')
    todos.append('Tier2 补充资料（可选）：')
    for i, mat in enumerate(roadmap['material_priority']['tier2'], 1):
        if not is_downloaded(mat['title']):
            todos.append(f'  {i}. {mat[\"title\"]}')
        else:
            todos.append(f'  {i}. {mat[\"title\"]} ✓ (已下载)')

# Set topic state
set_stage('{slug}', '02-gathering')
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
