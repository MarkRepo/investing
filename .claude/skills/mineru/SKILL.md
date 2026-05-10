---
name: mineru
description: 用 MinerU API 将 PDF 转换为 Markdown。触发词：mineru / 转换PDF / pdf转markdown / 转研报。产出目录包含 full.md（含图表数据）+ images/。
allowed-tools: Bash Read
---

# MinerU PDF 转换

将 PDF 转换为结构化 Markdown，**默认使用 VLM 模型**，图表内容（柱状图、折线图、饼图）会被识别并转为 Markdown 表格。

## 调用方式

```bash
.venv/bin/python -m scripts.mineru_api \
  "{pdf_path}" \
  --out "{out_dir}" \
  --model vlm
```

## 参数规则

| 参数 | 说明 |
|------|------|
| `pdf_path` | PDF 文件的绝对或相对路径 |
| `--out` | **输出目录路径**（不是文件路径）。约定：`{pdf_stem}_vlm/`，与 PDF 同级 |
| `--model` | 默认 `vlm`；纯文字 PDF（无图表）可用 `pipeline`（更快） |

## 产出结构

```
{out_dir}/
  full.md          ← 主要分析内容，含图表数据表格
  images/          ← 图片文件（full.md 里有相对路径引用）
  layout.json
  *_content_list.json
```

**读取内容时始终读 `{out_dir}/full.md`**，不是根目录的 `.md` 文件。

## 判断是否已转换

转换前先检查输出目录是否已存在：

```bash
test -f "{out_dir}/full.md" && echo "已存在" || echo "需要转换"
```

如果已存在，直接读取，**不重复转换**（API 有配额消耗）。

## 何时用 pipeline vs vlm

| 场景 | 模型 |
|------|------|
| 研报 / 行业报告（含图表） | `vlm`（默认） |
| 年报正文（annual_report_extractor 已处理） | 不需要 MinerU |
| 纯文字 PDF（无图表） | `pipeline`（更快） |

## 年报不走此流程

年报使用 `scripts.annual_report_extractor` 处理，不调用 MinerU。

## 使用此 skill 的场景

- `prism/workflows/03-extract-findings.md`：研报预处理
- `ingest` skill：研报 bundle 提取前的 PDF 转换
