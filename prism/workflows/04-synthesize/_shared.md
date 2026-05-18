# 产出合成 — 共享前置规范

每份产出工作流开始前必须完成以下检查，违反则停止并告知用户。

## 前置检查

```bash
python -c "
import json
from prism.scripts.topic import read_topic
from prism.scripts.manifest import material_count
t = read_topic('{slug}', '{variant}')
counts = material_count('{slug}')
print('stage:', t['stage'])
print('materials:', json.dumps(counts))
print('question:', t['scope']['question'])
"
```

- **资料量**：至少 3 份已处理资料，否则提示「资料不足，建议先收集更多资料」
- **训练知识依赖**：每份产出明确标注哪些来自训练知识，哪些来自资料

## 写入规范

输出文件路径：`prism/topics/{slug}/{variant}/outputs/{output_key}.md`

每份产出 markdown 必须包含：
1. YAML frontmatter（slug, output_key, version, generated）
2. 正文内容（按各 workflow 规定）
3. 末尾：`## 信息来源` — 列出使用的资料（mat_id + 文件名）和训练知识比例估计

## 更新状态（每份产出完成后必须执行）

```bash
python -c "
from prism.scripts.topic import set_output_status
set_output_status(
    slug='{slug}',
    output_key='{output_key}',
    status='fresh',
    version={new_version},
)
print('状态已更新')
"
```

## 全部产出完成后（收尾）

先更新 01-08 完成状态：

```bash
python -c "
from prism.scripts.topic import read_topic, set_next_actions, set_user_todos
t = read_topic('{slug}', '{variant}')
# 清除 user_todos 中「下一步：生成产出」相关行
todos = [x for x in t.get('user_todos', []) if '生成产出' not in x and '开始 01-08' not in x]
todos.append('全部产出完成（' + str(len(t['outputs_state'])) + ' 份），等待创建子 topic 或进入监控')
set_user_todos('{slug}', todos, '{variant}')
# 确认 next_actions 不再指向生成产出
actions = [x for x in t.get('next_actions', []) if '01-08' not in x and '产出' not in x]
set_next_actions('{slug}', actions, '{variant}')
print('收尾完成')
"
```

**自动触发扩展产出**：根据 topic type 判断是否需要自动生成 09/10：

- **topic_type = industry** → 自动运行 workflow `09-industry-to-arenas`（选拔 arena）
- **topic_type = arena** → 自动运行 workflow `10-peer-matrix`（公司对比矩阵）
- **topic_type = company** → 跳过，01-08 即为完整产出

自动触发时，直接读对应 workflow 文件（`prism/workflows/04-synthesize/09-industry-to-arenas.md` 或 `prism/workflows/04-synthesize/10-peer-matrix.md`），按 Step 执行。完成后将 stage 设为 `done` 并追加到 living feed。

## 质量检验

产出完成后自问：
- [ ] 有具体数据/时间/主体，不只是泛泛之词
- [ ] 多空观点都有呈现，不只说一边
- [ ] 有明确的「哪里可能是错的」
- [ ] 训练知识和资料来源有区分标注
- [ ] 字数适当（800-2000字为宜，过长反而难用）
