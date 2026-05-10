# Digest Summary Workflow

**触发词**：研报摘要 / 生成摘要 / digest / 做摘要

独立流程，与 bundle ingest 无关，不依赖 ClaimRegistry，直接从 MinerU 输出生成结构化摘要写入 `/digest`。

---

## 前置条件

已完成 MinerU 转换（Step 1 of bundle workflow），`full-clean.md` 或 `full.md` 可用。

---

## 步骤

### Step 1 — 确认 report_id

命名规范：`{base_id}-{model_suffix}`

- `base_id`：从 `KNOWN_REPORTS`（`app/io/mineru_summaries.py`）查找，或新建（kebab-case 中文音译）
- `model_suffix`：`sonnet46` / `gemini-3.1-pro` / `qwen36plus`

示例：`he-jubian-sonnet46`

### Step 2 — 派发独立 subagent

**必须用独立干净的 subagent**，不在主 agent 对话里做 LLM 提取。

派发参数：
- `model=sonnet`（除非用户指定其他模型）
- System prompt：`docs/prompts/report-summary.md`
- 输入：`full-clean.md`（优先）或 `full.md` 的全文内容
- 任务：生成摘要，写入 `mineru_summaries/{report_id}.md`，更新 `mineru_summaries/registry.json`

Subagent 输出的 frontmatter 必须包含：
```yaml
report_id: {report_id}
title: {标题}
topic: {主题}
source_pdf: {PDF 文件名}
source_dir: {MinerU 输出目录名}
model: {sonnet46 | gemini-3.1-pro | qwen36plus}
generated_at: {ISO 8601}
```

### Step 3 — 验证

确认 `mineru_summaries/{report_id}.md` 已写入，`registry.json` 已追加对应条目。

可访问：`/digest/{report_id}`

---

## 注意

- 不读 ClaimRegistry，不写 claims，不触发 bundle 流程的任何步骤
- 同一研报可用不同模型各生成一份（`report_id` 不同），互不覆盖
- 若 `base_id` 尚未在 `KNOWN_REPORTS` 中，需同时在 `app/io/mineru_summaries.py` 的 `KNOWN_REPORTS` 列表添加基础条目（无 model suffix 的那条），用于 `source_id` → `report_id` 映射
