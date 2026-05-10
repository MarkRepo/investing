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

## 质量检验

产出完成后自问：
- [ ] 有具体数据/时间/主体，不只是泛泛之词
- [ ] 多空观点都有呈现，不只说一边
- [ ] 有明确的「哪里可能是错的」
- [ ] 训练知识和资料来源有区分标注
- [ ] 字数适当（800-2000字为宜，过长反而难用）
