# Workflow 02 — 登记资料到 Manifest

**触发**：用户上传了新资料，或说「登记资料」  
**前置**：topic.yaml 和 manifest.yaml 已存在  
**产出**：更新 `prism/topics/{slug}/manifest.yaml`

---

## Step 1：检查 inbox 有什么新资料

```bash
ls prism/inbox/manual/
ls prism/inbox/auto/
```

列出所有文件，记录文件名。

---

## Step 2：对每份新资料，判断 source_type

按文件名和内容（如有）判断类型：
- `sell-side-note`：卖方研报（某机构某日期某标题）
- `annual-report`：年报 / 半年报 / 10-K / 20-F
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
# 先找到文件完整路径
python -c "
from prism.scripts.manifest import get_material_path
path = get_material_path('{slug}', '{filename}', '{variant}')
print(path if path else 'FILE_NOT_FOUND')
"
# 登记并自动复制到 topic 的 materials 目录
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
)
print(f'已登记：{filename} → {mat_id}')
"
```

> 注意：文件会自动复制到 prism/topics/{slug}/materials/，原 inbox 文件保留。

---

## Step 6：更新 topic 状态

```bash
python -c "
from prism.scripts.topic import set_stage, set_next_actions, set_user_todos
from prism.scripts.manifest import material_count
counts = material_count('{slug}', '{variant}')
set_stage('{slug}', '03-extracting' if counts['unprocessed'] > 0 else '02-gather-materials', '{variant}')
set_next_actions('{slug}', [
    f'已有 {counts[\"unprocessed\"]} 份资料未处理，运行 workflow 03-extract-findings',
])
set_user_todos('{slug}', [
    f'已登记 {counts[\"total\"]} 份资料到 manifest',
    f'待处理：{counts[\"unprocessed\"]} 份（说「prism 推进 {slug}」开始提取发现）',
])
"
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
