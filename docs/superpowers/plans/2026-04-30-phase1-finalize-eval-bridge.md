# Phase 1 收尾 + 评测 + Phase 1.5 桥梁 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在已落地的 Phase 1 review-bundle 骨架基础上，补齐 Phase 1 L2 评测工作流，并落地 Phase 1.5 桥梁字段（claim_candidates、as_of、source_type 分型、schema_fit_review 结构化），为 Phase 2 claim 层做准备。

**依据 spec：**
- `docs/superpowers/specs/2026-04-29-ingest-endgame-design.md`（§7 Phase 1 gap、§8 Phase 1.5 演进）
- `docs/superpowers/specs/2026-04-29-ingest-eval-system-design.md`（§3 Phase 1 评测、§4 Phase 1.5 评测）
- `docs/superpowers/specs/2026-04-29-ingest-v2-phase1-review-bundle-design.md`（bundle 结构、§11 QA 规则）

**Tech Stack:** Python 3, pytest, `scripts/ingest_qa.py`, `docs/prompts/*.md`, JSON 文件。

**不调 LLM API 原则不变**：Python 只做规则校验与聚合；语义评测在 Claude 对话里跑。

---

## 1. Scope 与边界

### 1.1 在本计划范围内

- **Phase 1 收尾**：真实报告 smoke test + 极少量遗漏补漏
- **Phase 1 L2 评测**：evaluation.json schema + L1→L2 聚合 CLI + L2 prompt + USER-GUIDE 章节
- **Phase 1.5 桥梁**：bundle prompt 扩展 + 对应 QA + eval prompt 适配

### 1.2 明确不做（越界即停）

- ❌ 不建 claim registry / ClaimStore / ClaimRepository，不持久化 claim 对象（Phase 2）
- ❌ 不写 archive，不动 `industries/`、`arenas/`、`companies/` 下的任何文件
- ❌ 不引入 event adapter / review queue（Phase 4）
- ❌ 不写 narrative 段落对象（Phase 3）
- ❌ 不做 cross-LLM 交叉评测（Phase 5+）
- ❌ 不从 Python 调 anthropic / openai / 任何 LLM API
- ❌ 不改 `app/io/*`、`scripts/ingest_aggregate.py`、`scripts/preprocess_report.py`（除非 Part A 发现真 bug）
- ❌ 不动 `.claude/skills/ingest/**`（workflow 级变动不在本计划）
- ❌ 不动 `docs/superpowers/archive/` 下任何文档
- ❌ 不新增 async / 缓存 / 数据库 / 后台任务

### 1.3 反延展红线（Sonnet 易踩）

实施时如果产生下列念头，**立即停下**，本计划不做：

| 念头 | 实际应做 |
|---|---|
| "为 claim_candidates 建一个 Python 类 / dataclass" | 只在 JSON 里新增字段；Python 端只做 dict 校验 |
| "source_type 分型写成 Python class per type" | 只在 prompt 里加条件说明，Python 不分支 |
| "eval prompt 要自动跑，调 Claude API" | 永远不调；评测在用户对话里粘贴执行 |
| "加一个 evaluation list/merge 汇总命令" | 只做 `evaluation init` 骨架生成，L2 合并由用户手工编辑 JSON |
| "claim_candidates 跨 bundle 去重" | Phase 2 才做；此处每 bundle 独立 |
| "schema_fit_review.extra_fields_needed 要自动回写 spec" | 不要；只是 LLM 产出的建议，人工判断 |
| "顺便重构 ingest_qa.py" | 不要；按现有风格追加函数即可 |

---

## 2. 前置状态（已完成，不要重做）

- [x] `scripts/preprocess_report.py` 输出 `preprocess_metadata` 单一规范位置，`meta.preprocess_version == "v2-phase1"`
- [x] `scripts/ingest_qa.py` 已含 Phase 1 QA 函数：`check_review_bundle_shape / check_insight_blocks / check_fact_block_links / check_fact_evidence_quotes / check_fact_quote_consistency / check_preprocess_risk_confidence / check_stage_gate_synthesis / check_company_candidates / check_synthesis_discipline`
- [x] `scripts/ingest_qa.py` 已有 `review-bundle` CLI 子命令 (`cmd_review_bundle`)
- [x] `docs/prompts/ingest-review-bundle.md` Phase 1 prompt 存在
- [x] `tests/test_ingest_review_bundle_qa.py` 单元测试

**开工前验证**：

```bash
.venv/bin/python -m pytest tests/test_ingest_review_bundle_qa.py tests/test_preprocess_page_signals.py -q
```

应全绿；若不绿先修回绿再开始本计划。

---

## 3. File Map

**Create:**
- `docs/prompts/ingest-eval-l2.md` — Phase 1 / 1.5 L2 评测 prompt
- `tests/test_ingest_eval_cli.py` — evaluation CLI 单元测试

**Modify:**
- `scripts/ingest_qa.py` — 新增 `evaluation init` 子命令 + Phase 1.5 QA 函数
- `docs/prompts/ingest-review-bundle.md` — Phase 1.5 字段扩展（claim_candidates / as_of / source_type 分型 / schema_fit_review 结构化）
- `tests/test_ingest_review_bundle_qa.py` — Phase 1.5 QA 新测试
- `docs/USER-GUIDE.md` — 评测工作流章节
- `docs/superpowers/specs/2026-04-29-ingest-eval-system-design.md` — §3.5 补足存储约定小节

**Do not modify**（违反即 revert）：
- `scripts/preprocess_report.py`（除非 Part A 发现真 bug）
- `scripts/ingest_aggregate.py`
- `app/io/*`
- `industries/`, `arenas/`, `companies/`
- `.claude/skills/ingest/**`
- `docs/superpowers/archive/**`

---

## Part A: Phase 1 收尾

### Task A1: 真实报告端到端 smoke test

**目的：** 用一份真实 PDF 验证 preprocess → bundle → QA 链路无阻塞。

**Files:**
- 默认不改代码；若发现 bug 才修对应文件

**Steps:**

- [ ] **Step 1: 选一份真实 PDF**

从已有 `companies/*/sources/` 或 `industries/*/sources/` 目录挑一份 `.pdf`。记录绝对路径。若无现成 PDF，请用户提供。**不创造假 PDF**。

- [ ] **Step 2: 运行 preprocess**

```bash
.venv/bin/python scripts/preprocess_report.py <pdf-path> > /tmp/preprocess.json
```

确认输出含：
- `preprocess_metadata.page_count > 0`
- `preprocess_metadata.extracted_pages` 非空
- `sections` 非空
- `meta.preprocess_version == "v2-phase1"`

任一缺失 → 视为 preprocess 真 bug，记录后修 `scripts/preprocess_report.py`；修完补一条 `tests/test_preprocess_page_signals.py` 的覆盖测试；commit 格式 `fix(preprocess): <具体>`。

- [ ] **Step 3: 手工写一份最小合法 bundle.json**

本步骤目的是验证 QA 管道，**不需要真实 Claude 对话**。保存到 `/tmp/bundle.json`：

```json
{
  "bundle_version": "v2-phase1",
  "source_digest": {
    "source_id": "smoke-test-001",
    "source_type": "industry_report",
    "source_date": "2026-04-30",
    "source_quality": "medium",
    "evidence_strength": "medium",
    "limitations": [],
    "coverage_review": {"mode": "full_report_pass", "sections_total": 1, "sections_reviewed": 1, "skipped_sections": 0, "coverage_notes": []}
  },
  "insight_blocks": [
    {"id": "ib-001", "block_type": "market_size", "title": "test", "summary": "test", "evidence_strength": "medium", "reasoning_chain": ["原文观察", "对投资含义推断"]}
  ],
  "atomic_facts": [
    {"fact_id": "fact-001", "linked_block_id": "ib-001", "fact_text": "test", "evidence_quote": "preprocess 里实际存在的一段短文本", "source_page": 1, "confidence": "medium"}
  ],
  "stage_gates": [],
  "company_candidates": [],
  "synthesis": {"one_sentence": "test", "what_we_know": [], "what_is_plausible": [], "cannot_conclude": [], "investment_questions": []},
  "schema_fit_review": {},
  "qa_warnings": [],
  "write_status": "not_applicable_phase1"
}
```

`evidence_quote` **必须**是 preprocess 文本中的真字符串，否则会触发 fidelity warning；随便抄一段 section 文本即可。

- [ ] **Step 4: 运行 review-bundle QA**

```bash
.venv/bin/python scripts/ingest_qa.py review-bundle --bundle /tmp/bundle.json --preprocess /tmp/preprocess.json
```

期望：exit 0（"✓ review bundle QA passed"）或按设计列出 warning 后非 0 退出。**crash 即 bug**。

- [ ] **Step 5: 若有 bug 修复后重跑**

若 Step 4 出现 Python 异常（非 warning 输出），定位到具体 QA 函数修正。修完 Step 4 重跑直到干净。Commit 格式 `fix(ingest-qa): <具体>`。

- [ ] **Step 6: 不生成文档**

本任务不要新建任何 smoke-test 报告文件。结论记入 commit message 或直接跳过。

**验收：** QA CLI 能在真实 preprocess + 手工合法 bundle 上无异常返回；若有 warning 是符合设计的。

---

## Part B: Phase 1 L2 评测工作流

### Task B1: 补足 eval spec 存储约定

**目的：** 明确 evaluation.json 文件名 / 位置 / bundle_ref 格式。不改代码。

**Files:**
- Modify: `docs/superpowers/specs/2026-04-29-ingest-eval-system-design.md`

**Steps:**

- [ ] **Step 1: 在 §3.5 末尾插入 §3.5.1 小节**

追加：

```markdown
### 3.5.1 存储约定

- evaluation 与 bundle、preprocess 同目录存放
- 文件名固定 `evaluation.json`；多次评测时后续记为 `evaluation-{ISO-date}.json`（不覆盖旧版）
- `bundle_ref` 统一存 `source_digest.source_id`，便于跨目录跨 session 引用
- `dimension_ratings.*.trend` 允许值：`stronger | comparable | weaker | insufficient_samples`；首次评测或缺乏对比样本时选 `insufficient_samples`
- `evaluator` 字段由人工填（如 `claude-opus-4-7`、`gpt-5` 等），evaluation init 留空
- `eval_prompt_version` 与 prompt 文件头 `<!-- prompt_version: ... -->` 对齐
```

- [ ] **Step 2: Commit**

`docs(spec): define evaluation record storage convention`

**验收：** spec §3.5 有明确存储约定；§3.5.1 与 prompt 文件内的 prompt_version 标记相互引用。

---

### Task B2: 实现 `evaluation init` CLI

**目的：** 从 bundle + preprocess 聚合 L1 warnings 成一份 evaluation 骨架，留 L2 字段占位。

**Files:**
- Modify: `scripts/ingest_qa.py`
- Create: `tests/test_ingest_eval_cli.py`

**Steps:**

- [ ] **Step 1: 写失败测试**

新建 `tests/test_ingest_eval_cli.py`：

```python
import json
from argparse import Namespace
from pathlib import Path

from scripts import ingest_qa as qa


def _minimal_valid_preprocess():
    return {
        "meta": {"preprocess_version": "v2-phase1"},
        "sections": [{"name": "S1", "text": "原文 A。"}],
        "preprocess_metadata": {"page_count": 1, "extracted_pages": [{"page_num": 1, "text_quality": "ok"}], "extraction_warnings": []},
        "figure_contexts": [],
    }


def _bundle_with_known_warnings():
    return {
        "bundle_version": "v2-phase1",
        "source_digest": {"source_id": "test-001", "source_type": "industry_report", "source_date": "2026-04-30",
                           "source_quality": "medium", "evidence_strength": "medium",
                           "coverage_review": {"mode": "full_report_pass", "sections_total": 1, "sections_reviewed": 1, "skipped_sections": 0, "coverage_notes": []}},
        "insight_blocks": [{"id": "ib-001", "block_type": "x", "title": "t", "summary": "s", "evidence_strength": "medium", "reasoning_chain": ["a", "b"]}],
        # fact 引用不存在 block → 触发 fact-block-link error
        "atomic_facts": [{"fact_id": "fact-001", "linked_block_id": "ib-999", "fact_text": "t", "evidence_quote": "原文 A。", "source_page": 1, "confidence": "medium"}],
        "stage_gates": [],
        "company_candidates": [],
        "synthesis": {"one_sentence": "s", "what_we_know": [], "what_is_plausible": [], "cannot_conclude": [], "investment_questions": []},
        "schema_fit_review": {},
        "qa_warnings": [],
        "write_status": "not_applicable_phase1",
    }


def test_evaluation_init_produces_skeleton_from_qa(tmp_path):
    bundle = _bundle_with_known_warnings()
    preprocess = _minimal_valid_preprocess()
    bpath = tmp_path / "bundle.json"; bpath.write_text(json.dumps(bundle))
    ppath = tmp_path / "preprocess.json"; ppath.write_text(json.dumps(preprocess))
    out = tmp_path / "evaluation.json"

    rc = qa.cmd_evaluation_init(Namespace(bundle=str(bpath), preprocess=str(ppath), out=str(out)))
    assert rc == 0

    data = json.loads(out.read_text())
    assert data["bundle_ref"] == "test-001"
    assert data["method_layers_run"] == ["L1"]
    assert set(data["dimension_ratings"]) == {"coverage_fidelity", "reasoning_quality", "calibration", "narrative"}
    for dim in data["dimension_ratings"].values():
        assert dim["trend"] is None and dim["notes"] == ""
    assert "system_fit" in data and "phase2_readiness" in data
    assert data["eval_prompt_version"] == "phase1-v1"
    assert len(data["defects"]) >= 1
    assert any("fact-block-link" in d["category"] or "broken" in d["category"].lower() for d in data["defects"])


def test_evaluation_init_produces_skeleton_with_no_warnings(tmp_path):
    # 用干净 bundle（无 warning）跑，defects 应为空
    ...  # 按同样模式构造无 warning 的 bundle
```

第二个测试用干净 bundle 验证 defects 为空数组。

- [ ] **Step 2: 运行测试，验证失败**

```bash
.venv/bin/python -m pytest tests/test_ingest_eval_cli.py -q
```

应 ImportError 或 AttributeError（`cmd_evaluation_init` 未定义）。

- [ ] **Step 3: 实现 `cmd_evaluation_init`**

在 `scripts/ingest_qa.py` 的 `cmd_list` 之后追加：

```python
def cmd_evaluation_init(args: argparse.Namespace) -> int:
    from datetime import datetime, timezone
    bundle = json.loads(Path(args.bundle).read_text(encoding="utf-8"))
    preprocess = json.loads(Path(args.preprocess).read_text(encoding="utf-8"))
    warnings = check_ingest_review_bundle(bundle, preprocess)
    source_id = (bundle.get("source_digest") or {}).get("source_id", "")

    evaluation = {
        "bundle_ref": source_id,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "evaluator": "",
        "eval_prompt_version": "phase1-v1",
        "method_layers_run": ["L1"],
        "dimension_ratings": {
            "coverage_fidelity": {"trend": None, "notes": ""},
            "reasoning_quality": {"trend": None, "notes": ""},
            "calibration": {"trend": None, "notes": ""},
            "narrative": {"trend": None, "notes": ""},
        },
        "system_fit": {"notes": ""},
        "phase2_readiness": {"notes": ""},
        "defects": [
            {
                "id": f"d-{i+1:03d}",
                "category": w.get("rule", "unknown"),
                "severity": w.get("severity", "warning"),
                "target_ref": w.get("target", ""),
                "description": w.get("detail", ""),
                "root_cause_hint": None,
                "suggested_fix": "",
            }
            for i, w in enumerate(warnings)
        ],
        "overall_notes": "",
    }
    Path(args.out).write_text(
        json.dumps(evaluation, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"✓ evaluation skeleton written to {args.out}")
    return 0
```

在 `main()`（或现有 subparser 注册块末尾）加：

```python
p_eval = sub.add_parser("evaluation", help="evaluation workflow")
eval_sub = p_eval.add_subparsers(dest="eval_cmd")
p_eval_init = eval_sub.add_parser("init", help="aggregate L1 warnings into evaluation skeleton")
p_eval_init.add_argument("--bundle", required=True)
p_eval_init.add_argument("--preprocess", required=True)
p_eval_init.add_argument("--out", required=True)
p_eval_init.set_defaults(func=cmd_evaluation_init)
```

**注意**：先 `grep -n "add_parser\|sub =" scripts/ingest_qa.py` 看现有 subparser 注册风格，照搬相同 pattern；不要引入新的 CLI 架构。

- [ ] **Step 4: 运行测试验证通过**

- [ ] **Step 5: Commit**

`feat(eval): add evaluation init CLI aggregating Phase 1 L1 warnings`

**验收：** `python scripts/ingest_qa.py evaluation init --bundle ... --preprocess ... --out evaluation.json` 产出符合 schema 的骨架；defects 对应所有 L1 warnings。

**不做：**
- ❌ 不实现 `evaluation update` / `evaluation merge` / `evaluation list`（Phase 2+）
- ❌ 不自动推 root_cause_hint（留空由 L2 填）
- ❌ 不做跨 bundle 对比（trend 为 null 即可）

---

### Task B3: 编写 Phase 1 L2 评测 prompt

**Files:**
- Create: `docs/prompts/ingest-eval-l2.md`

**Steps:**

- [ ] **Step 1: 创建 prompt 文件**

完整内容：

````markdown
<!-- prompt_version: phase1-v1 -->

# Phase 1 Review Bundle L2 评测 Prompt

## 使用

1. 完成 Phase 1 ingest，得到 `bundle.json` + `preprocess.json`
2. 先运行 L1 聚合：
   ```bash
   .venv/bin/python scripts/ingest_qa.py evaluation init \
     --bundle bundle.json --preprocess preprocess.json --out evaluation.json
   ```
3. 在 Claude 对话里贴入本 prompt（作为 system 指令）+ 三份 JSON（bundle、preprocess、evaluation 骨架）
4. Claude 返回 L2 评测 JSON 片段
5. 把片段手工合并进 `evaluation.json`：`dimension_ratings / system_fit / phase2_readiness / overall_notes` 覆盖，`defects` 追加；同时更新 `evaluated_at`、`evaluator`、`method_layers_run = ["L1", "L2"]`

## 系统指令（粘贴到对话）

```text
你是 ingest review bundle 的 L2 评审助手。基于用户提供的 bundle.json 与 preprocess.json（以及已生成的 evaluation 骨架），按下列规则产出 L2 评测结果。

### 评测原则

- **不打绝对分数**。每个维度只输出 trend：`stronger | comparable | weaker | insufficient_samples`。首次评测或缺乏对比样本时填 `insufficient_samples`。
- **主产物是 defects 清单**，trend 与 notes 辅助描述。
- **只基于 bundle + preprocess 可见内容**，不自行补全外部知识。
- **发现问题比给好评重要**。bundle 形式完整不等于推理扎实。
- **不修改 bundle.json**；评测结果独立输出。

### 评测维度

1. **coverage_fidelity**：报告关键论点是否被提炼、提炼是否扭曲原文。关注 insight_blocks 覆盖度 vs. preprocess.sections；atomic_facts 的 evidence_quote 是否忠实。
2. **reasoning_quality**：insight_block.reasoning_chain 是否首尾分别为"可验证观察"与"投资含义推断"；assumptions 是否被识别；counterpoints / risk 维度是否提出；facts 支撑 block 结论是否充分。
3. **calibration**：evidence_strength / confidence 与证据来源匹配度；是否把 chart_heavy / image_heavy / text_quality=low 页的信息误升为 high confidence。
4. **narrative**：synthesis 可读性；blocks 之间的逻辑链是否连贯；what_we_know / what_is_plausible / cannot_conclude 分层是否克制。

### 独立判断（不进维度 trend）

- **system_fit**：本 bundle 字段集是否适配该 source_type？（如医药报告缺 pipeline 信息、行业报告缺 lifecycle 判断等。给具体不适配点）
- **phase2_readiness**：本 bundle 能否为未来 claim layer 提供足够基础？具体风险点？（此字段 Phase 1.5 起会升为必评，Phase 1 允许留 notes 简述）

### 输出格式

只返回一个 JSON 对象（不要 markdown、不要解释、不要代码围栏）：

{
  "dimension_ratings": {
    "coverage_fidelity": {"trend": "stronger|comparable|weaker|insufficient_samples", "notes": "≤200 字"},
    "reasoning_quality": {"trend": "...", "notes": "..."},
    "calibration":       {"trend": "...", "notes": "..."},
    "narrative":         {"trend": "...", "notes": "..."}
  },
  "system_fit":       {"notes": "..."},
  "phase2_readiness": {"notes": "..."},
  "defects": [
    {
      "category":        "coverage_fidelity | reasoning_quality | calibration | narrative | system_fit | phase2_readiness | <L1 rule 名>",
      "severity":        "blocker | major | minor",
      "target_ref":      "<block_id / fact_id / candidate_id / synthesis / bundle>",
      "description":     "具体问题描述",
      "root_cause_hint": "prompt_gap | schema_gap | source_hard_case | preprocess_loss",
      "suggested_fix":   "下次 ingest 如何避免（一句话）"
    }
  ],
  "overall_notes": "总体结论（≤300 字）"
}
```

## 合并规则

用户收到输出后：
- `dimension_ratings` / `system_fit` / `phase2_readiness` / `overall_notes` 直接覆盖 evaluation.json 同名字段
- `defects` **追加**到 evaluation.json 现有 defects 末尾（不要丢 L1 聚合进来的那批）
- 更新 evaluation.json：`evaluated_at` = 合并时刻，`evaluator` = 使用的模型标识，`method_layers_run` = `["L1", "L2"]`
````

- [ ] **Step 2: 提交**

`docs(prompts): add Phase 1 L2 evaluation prompt`

**验收：** prompt 文件含 prompt_version 标记、明确输出 schema、明确合并规则。

**不做：**
- ❌ 不在 prompt 里让 Claude 修改 bundle.json
- ❌ 不要求 Claude 自行运行脚本
- ❌ 不给"打分 1-5"式指令（trend 是相对判断）

---

### Task B4: USER-GUIDE 新增评测工作流章节

**Files:**
- Modify: `docs/USER-GUIDE.md`

**Steps:**

- [ ] **Step 1: 定位插入点**

找到现有的"Phase 1 ingest 不写 archive"附近（line ~280）。确认现有 ingest 步骤链路描述（preprocess → 对话 → bundle → QA）。

- [ ] **Step 2: 在 Phase 1 ingest 小节之后插入新小节**

```markdown
## Phase 1 评测工作流（可选）

评测用于迭代 ingest prompt / QA 规则，不是 ingest 验收门。是否评测、是否在本次 ingest 后跑，由用户决定。

1. 完成 ingest，得到 `bundle.json` + `preprocess.json`
2. 生成 evaluation 骨架（L1 聚合）：

   ```bash
   .venv/bin/python scripts/ingest_qa.py evaluation init \
     --bundle bundle.json --preprocess preprocess.json --out evaluation.json
   ```

3. 在 Claude 对话里贴 `docs/prompts/ingest-eval-l2.md` 作为 system 指令，再贴三份 JSON（bundle / preprocess / evaluation 骨架）
4. Claude 返回 L2 评测 JSON 片段，按 prompt 末尾"合并规则"合并进 `evaluation.json`
5. `evaluation.json` 与 bundle、preprocess 同目录存放；多次评测用 `evaluation-{ISO-date}.json` 避免覆盖

评测的作用是**产出结构化缺陷清单**（`defects[]`），供跨 ingest 对比与 prompt / QA 规则迭代。不产出"合格/不合格"结论。
```

- [ ] **Step 3: 提交**

`docs(user-guide): add Phase 1 evaluation workflow section`

**验收：** 用户按 USER-GUIDE 可自助跑通 L1 聚合 + L2 对话。

---

## Part C: Phase 1.5 桥梁

### Task C1: Prompt 扩展 claim_candidates 与 as_of

**目的：** Bundle 新增 `claim_candidates[]` 数组，每条带 `as_of`。为 Phase 2 claim 层提供素材。

**Files:**
- Modify: `docs/prompts/ingest-review-bundle.md`

**Steps:**

- [ ] **Step 1: Prompt 顶部版本注释更新**

文件顶部加 / 更新：`<!-- prompt_version: phase1.5-v1 -->`（如原无 version 注释就补上）。

- [ ] **Step 2: bundle JSON schema 扩展**

在现有 bundle 顶层 JSON 例子里，**在 `"write_status": ...` 之前**插入一段：

```json
"claim_candidates": [
  {
    "candidate_id": "cc-001",
    "claim_text": "单句命题，不得混合多个命题",
    "scope_type": "industry | arena | company | cross_cutting",
    "scope_ref": "industry_slug / arena_slug / MARKET_TICKER；scope_type=cross_cutting 时留空字符串",
    "claim_type": "thesis | judgment | risk | scenario | gate_assessment",
    "dimension_hint": "与 insight_block.archive_routing_hints.dimension_hint 同值域",
    "supporting_block_ids": ["ib-001"],
    "direction_on_source": "supports | refutes | neutral",
    "confidence": "high | medium_high | medium | medium_low | low",
    "as_of": "YYYY-MM-DD；等于 source_digest.source_date"
  }
],
```

- [ ] **Step 3: 在"规则"章节末尾追加新规则**

```markdown
7. `claim_candidates` 从 `synthesis.what_we_know` / `what_is_plausible` / `investment_questions` 提炼。每条必须：
   - `claim_text` 是**单句命题**（不是主题或名词短语；不混合两个以上论点）
   - `scope_type` 在四值枚举内
   - `supporting_block_ids` 全部来自本 bundle 的 `insight_blocks[].id`
   - `direction_on_source` 记录本研报对该命题的方向（supports / refutes / neutral）
   - `as_of` 等于 `source_digest.source_date`
8. `claim_candidates` 粒度控制：一个 insight_block 通常对应 0-2 条 candidate。不要为每个 atomic_fact 生成 candidate（那是证据，不是命题）。也不要把整份报告合成为 1 条 candidate（过粗无法跨报告比对）。
9. `candidate_id` 稳定格式 `cc-{NNN}`（与 ib / fact id 编号规则对齐）。
```

- [ ] **Step 4: 提交**

`docs(prompts): add claim_candidates + as_of to Phase 1.5 bundle prompt`

**验收：** prompt 能指导 Claude 产出符合 schema 的 claim_candidates 数组。

**不做：**
- ❌ 不引入 `claim_id`（那是 Phase 2 claim registry 的事；此处叫 `candidate_id`）
- ❌ 不做跨 bundle 去重 / 匹配（Phase 2）
- ❌ 不改 `bundle_version`（保持 `v2-phase1`；字段增量不 breaking）

---

### Task C2: QA 校验 claim_candidates

**Files:**
- Modify: `scripts/ingest_qa.py`
- Modify: `tests/test_ingest_review_bundle_qa.py`

**Steps:**

- [ ] **Step 1: 写失败测试**

在 `tests/test_ingest_review_bundle_qa.py` 追加测试（构造最小 bundle，每个只触发单一问题）：

1. `test_claim_candidate_missing_required_field_returns_error` — 缺 claim_text
2. `test_claim_candidate_invalid_scope_type_returns_error` — scope_type = "random"
3. `test_claim_candidate_supporting_block_id_not_in_bundle_returns_error` — 指 "ib-999"
4. `test_claim_candidate_as_of_mismatches_source_date_returns_warning` — as_of ≠ source_date
5. `test_claim_candidate_claim_text_not_atomic_returns_warning` — "A 增长。B 衰退。"（中文句号两句）
6. `test_valid_claim_candidates_pass` — 合法 candidates 不触发任何 rule

模式参考既有测试（如 `test_fact_without_linked_block_returns_error`）。

- [ ] **Step 2: 运行测试验证失败**

- [ ] **Step 3: 实现 `check_claim_candidates`**

在 `scripts/ingest_qa.py` 追加：

```python
_VALID_SCOPE_TYPES = {"industry", "arena", "company", "cross_cutting"}


def check_claim_candidates(bundle: dict) -> list[dict]:
    warnings: list[dict] = []
    candidates = bundle.get("claim_candidates") or []
    if not candidates:
        return warnings  # 允许为空（Phase 1.5 不强制）

    block_ids = {b.get("id") for b in (bundle.get("insight_blocks") or []) if b.get("id")}
    source_date = (bundle.get("source_digest") or {}).get("source_date")

    required_fields = ("candidate_id", "claim_text", "scope_type", "claim_type",
                       "supporting_block_ids", "direction_on_source", "as_of")

    for c in candidates:
        cid = c.get("candidate_id", "?")
        for field in required_fields:
            if not c.get(field):
                warnings.append(_qa_warning(
                    "claim_candidate_missing_field", "error",
                    target=cid, detail=f"missing required field: {field}",
                ))

        scope = c.get("scope_type")
        if scope and scope not in _VALID_SCOPE_TYPES:
            warnings.append(_qa_warning(
                "claim_candidate_invalid_scope_type", "error",
                target=cid, detail=f"scope_type={scope} not in {_VALID_SCOPE_TYPES}",
            ))

        for bid in c.get("supporting_block_ids") or []:
            if bid not in block_ids:
                warnings.append(_qa_warning(
                    "claim_candidate_broken_link", "error",
                    target=cid, detail=f"supporting_block_id={bid} not in insight_blocks",
                ))

        as_of = c.get("as_of")
        if as_of and source_date and as_of != source_date:
            warnings.append(_qa_warning(
                "claim_candidate_as_of_mismatch", "warning",
                target=cid, detail=f"as_of={as_of} != source_date={source_date}",
            ))

        text = (c.get("claim_text") or "").strip()
        if text and _looks_multi_sentence(text):
            warnings.append(_qa_warning(
                "claim_candidate_claim_text_not_atomic", "warning",
                target=cid, detail="claim_text 含多句迹象；应为单句命题",
            ))

    return warnings


def _looks_multi_sentence(text: str) -> bool:
    # 启发：出现中文句号 / 问号 / 分号 / 换行后仍有非空文本
    import re
    parts = re.split(r"[。！？；\n]+", text)
    non_empty = [p for p in parts if p.strip()]
    return len(non_empty) > 1
```

在 `check_ingest_review_bundle` 里追加一行：

```python
warnings.extend(check_claim_candidates(bundle))
```

**注意**：先 `grep -n "def _qa_warning\|def check_ingest_review_bundle" scripts/ingest_qa.py`，按现有签名与风格贴合。

- [ ] **Step 4: 运行测试验证通过**

- [ ] **Step 5: Commit**

`feat(ingest-qa): add Phase 1.5 claim_candidates QA checks`

**验收：** review-bundle CLI 对含 claim_candidates 的 bundle 正确报 warning/error；空 claim_candidates 不触发任何 rule。

**不做：**
- ❌ 不做跨 bundle candidate 去重（Phase 2）
- ❌ 不做 claim_text 语义单句严格判断（启发式 + warning 即可，硬判由 L2 接）
- ❌ 不做 dimension_hint 值域校验（值域与 insight_block 同，且允许自由扩展）

---

### Task C3: Prompt 加 source_type 分型字段要求

**目的：** 降低 source_hard_case 类缺陷。只改 prompt，不改 Python。

**Files:**
- Modify: `docs/prompts/ingest-review-bundle.md`

**Steps:**

- [ ] **Step 1: 在 prompt 的"规则"章节之后追加新章节**

```markdown
## Source-type 分型字段要求

根据 `source_digest.source_type` 应用附加要求。原文有就填、没有就在 `source_digest.limitations` 里说明，**禁止编造**。

### industry_report
- `insight_blocks` 至少一条 `block_type` 涉及 `market_size` / `value_chain` / `lifecycle` / `demand_driver` / `technology` 之一
- 涉及早期行业（生物医药、低空经济、核聚变、BCI、量子、商业航天等）时，`stage_gates` 至少一条，且 `synthesis.cannot_conclude` 非空

### company_report / sell_side_report
- `company_candidates` 至少一条；每条 `exposure_type` 必填
- 若原文提及估值判断，至少一个 insight_block 的 `reasoning_chain` 明确涉及估值假设（折现率、倍数或对标）

### annual_report / quarterly_report
- `insight_blocks` 覆盖 `business_model` / `financial_profile` / `catalysts` 中至少一个
- 管理层指引或前瞻陈述若原文出现，单独作为 `insight_block` 或 `atomic_fact` 记录（不隐藏在通用 summary 里）

### transcript
- 问答涉及 forward-looking 部分，对应 `atomic_facts` 的 `confidence` 不得高于 `medium_high`；对应 `insight_blocks` 的 `evidence_strength` 同样上限 `medium_high`

不属于以上类型时不加额外约束。
```

- [ ] **Step 2: 提交**

`docs(prompts): add source_type branching requirements`

**验收：** prompt 有明确 source_type 条件约束。

**不做：**
- ❌ 不在 Python 加 source_type 硬性 QA（Phase 1.5 只在 prompt 层导引；硬规则等 Phase 2 样本积累后再加）
- ❌ 不新增医药 pipeline 子字段 / 核聚变 stage_gate 子 schema（保持字段集不变，只是用现有字段组合表达）

---

### Task C4: schema_fit_review 结构化 + QA

**目的：** 把 bundle 里的 `schema_fit_review` 从空壳变结构化。按 endgame §7 gap 4。

**决策：** 结构化（不删）。理由：此字段是 schema_evolution 信号入口，Phase 2+ 会用到；现在结构化成本低、未来回炉成本高。

**Files:**
- Modify: `docs/prompts/ingest-review-bundle.md`
- Modify: `scripts/ingest_qa.py`
- Modify: `tests/test_ingest_review_bundle_qa.py`

**Steps:**

- [ ] **Step 1: Prompt 内 schema_fit_review 结构升级**

找到 prompt 现有 `"schema_fit_review": { ... }` 位置，替换为：

```json
"schema_fit_review": {
  "fits_current_schema": true,
  "missing_schema_fields": ["描述原文中重要但 bundle 现有字段无法容纳的信息类型；没有则空数组"],
  "extra_fields_needed": [
    {
      "proposed_field": "建议字段名（短蛇形）",
      "rationale": "为什么需要",
      "example_evidence": "研报中哪一段无处安放（短引文或描述）"
    }
  ],
  "notes": "简述（≤150 字）"
}
```

在相关"规则"章节补充：

```markdown
10. `schema_fit_review.fits_current_schema` 为 false 时，`missing_schema_fields` 和 `extra_fields_needed` 至少一个非空（即给出具体不适配点，不允许 false + 空建议）。
```

- [ ] **Step 2: 写失败测试**

1. `test_schema_fit_review_missing_required_keys_returns_warning` — 缺 fits_current_schema
2. `test_schema_fit_review_fits_false_without_details_returns_warning` — fits=false + missing/extra 都空
3. `test_valid_schema_fit_review_passes_true_case` — fits=true + missing/extra 均空 → 无 warning
4. `test_valid_schema_fit_review_passes_false_case` — fits=false + extra_fields_needed 有 1 条 → 无 warning

- [ ] **Step 3: 实现 `check_schema_fit_review`**

```python
def check_schema_fit_review(bundle: dict) -> list[dict]:
    warnings: list[dict] = []
    sfr = bundle.get("schema_fit_review")
    if sfr is None or sfr == {}:
        warnings.append(_qa_warning(
            "schema_fit_review_incomplete", "warning",
            target="schema_fit_review",
            detail="schema_fit_review 未填写（Phase 1.5 起应至少给出 fits_current_schema 判断）",
        ))
        return warnings

    required = ("fits_current_schema", "missing_schema_fields", "extra_fields_needed", "notes")
    for key in required:
        if key not in sfr:
            warnings.append(_qa_warning(
                "schema_fit_review_incomplete", "warning",
                target="schema_fit_review", detail=f"missing key: {key}",
            ))

    if sfr.get("fits_current_schema") is False:
        missing = sfr.get("missing_schema_fields") or []
        extra = sfr.get("extra_fields_needed") or []
        if not missing and not extra:
            warnings.append(_qa_warning(
                "schema_fit_review_fits_false_without_details", "warning",
                target="schema_fit_review",
                detail="fits_current_schema=false 但未给出 missing_schema_fields 或 extra_fields_needed",
            ))
    return warnings
```

挂进 `check_ingest_review_bundle`。

- [ ] **Step 4: 运行测试验证通过**

- [ ] **Step 5: Commit**

`feat(ingest-qa): structure schema_fit_review with Phase 1.5 QA`

**验收：** schema_fit_review 有明确结构与检查；空对象触发 warning。

**不做：**
- ❌ 不做 schema_fit_review 聚合视图 / 提案汇总（Phase 2+ 的 schema_evolution 再做）
- ❌ 不自动向任何 spec 文件回写建议字段

---

### Task C5: eval prompt 与 init 骨架支持 Phase 1.5 维度

**Files:**
- Modify: `docs/prompts/ingest-eval-l2.md`
- Modify: `scripts/ingest_qa.py`（`cmd_evaluation_init` 骨架）
- Modify: `tests/test_ingest_eval_cli.py`

**Steps:**

- [ ] **Step 1: 更新 eval prompt**

- 顶部 `prompt_version` 改为 `phase1.5-v1`
- "评测维度"节追加：

  ```markdown
  5. **claim_extraction_quality**（Phase 1.5 起）：claim_candidates 粒度是否合适（不过粗不过碎）、claim_text 是否真为单句命题、scope/dimension_hint 归属是否准确、是否可作为跨报告比对单元
  ```

- "独立判断"节升级 phase2_readiness 描述：

  ```markdown
  - **phase2_readiness**（Phase 1.5 起为**必评项**）：本 bundle 进入 Phase 2 claim layer 是否会产生脏数据？具体风险点列明。
  ```

- 输出 JSON schema 在 `dimension_ratings` 对象新增：

  ```json
  "claim_extraction_quality": {"trend": "...", "notes": "..."}
  ```

- [ ] **Step 2: 更新 `cmd_evaluation_init`**

`dimension_ratings` 骨架加：

```python
"claim_extraction_quality": {"trend": None, "notes": ""},
```

`eval_prompt_version` 默认值改为 `"phase1.5-v1"`。

- [ ] **Step 3: 更新测试**

`tests/test_ingest_eval_cli.py`：

- `test_evaluation_init_produces_skeleton_from_qa` 断言 `set(data["dimension_ratings"])` 含 5 维（新加 `claim_extraction_quality`）
- `eval_prompt_version == "phase1.5-v1"`

- [ ] **Step 4: 运行测试验证通过**

```bash
.venv/bin/python -m pytest tests/test_ingest_eval_cli.py tests/test_ingest_review_bundle_qa.py -q
```

- [ ] **Step 5: Commit**

`feat(eval): extend L2 prompt and init skeleton with Phase 1.5 dimensions`

**验收：** eval prompt 与 init 骨架同步覆盖 claim_extraction_quality；phase2_readiness 明确为必评项。

**不做：**
- ❌ 不为每条 claim_candidate 单独打分（维度级评价即可）
- ❌ 不引入 Phase 2 维度（matching_accuracy / claim_lifecycle_discipline）

---

## Part D: 整体验收

### Task D1: Phase 1 + 1.5 完整回归

**Files:**
- 不改代码；仅运行测试与手工 smoke

**Steps:**

- [ ] **Step 1: 运行全部相关测试**

```bash
.venv/bin/python -m pytest \
  tests/test_ingest_review_bundle_qa.py \
  tests/test_preprocess_page_signals.py \
  tests/test_ingest_eval_cli.py \
  -q
```

全绿。若有失败逐一修回，不妥协。

- [ ] **Step 2: 端到端 smoke（含 Phase 1.5 字段）**

按 Task A1 路径，但 Step 3 的手工 bundle 加上最小合法 `claim_candidates[]`（2 条）+ 结构化 `schema_fit_review`。跑：

```bash
.venv/bin/python scripts/ingest_qa.py review-bundle \
  --bundle /tmp/bundle.json --preprocess /tmp/preprocess.json
.venv/bin/python scripts/ingest_qa.py evaluation init \
  --bundle /tmp/bundle.json --preprocess /tmp/preprocess.json --out /tmp/evaluation.json
```

验证：
- review-bundle 无 Python 异常
- evaluation.json 含 5 维 dimension_ratings
- evaluation.json defects 与 review-bundle 输出条数一致
- `eval_prompt_version == "phase1.5-v1"`

- [ ] **Step 3: 最终 commit 或 PR 汇总**

若各 task 已分别 commit，本步只需 push 或开 PR。PR 标题建议：

`phase 1 finalize + evaluation workflow + phase 1.5 bridge`

PR body 覆盖：实现内容、spec 对齐、反延展检查清单结果。

**验收：** 所有测试通过；端到端 smoke 无异常。

---

## 4. Spec 对齐对照

实施过程中持续对表，任何 task 完成后确认对应 spec 条目被覆盖：

| Spec 条目 | 对应实施任务 |
|---|---|
| endgame §7 gap 1（claim 对象未收集） | C1 + C2 |
| endgame §7 gap 2（as_of 未收集） | C1 + C2 |
| endgame §7 gap 3（source_type 分型未落地） | C3 |
| endgame §7 gap 4（schema_fit_review 空壳） | C4 |
| endgame §8 Phase 1.5 桥梁补丁 | C1–C5 |
| eval spec §3.2 L1 检查（复用现有 QA） | 无新工作；B2 聚合时覆盖 |
| eval spec §3.3 L2 维度 4 维 | B3 |
| eval spec §3.4 Defect 结构 | B2 |
| eval spec §3.5 Evaluation 输出 + 存储约定 | B1 + B2 |
| eval spec §4.1 L1 claim_candidates 检查 | C2 |
| eval spec §4.2 L2 claim_extraction_quality 维度 | C5 |
| eval spec §4.3 phase2_readiness 升格 | C5 |

gap 5（设计/实现字段集长期分叉）不在本计划；gap 6（memo 反向引用）自然延后到 Phase 3。

---

## 5. Sonnet 自检清单（每 task 开工前过一遍）

- [ ] 我要改的文件在 §3 File Map 里？不在就停下问
- [ ] 我写的步骤在本 task 的 Steps 列表里？不在就停下
- [ ] 我是否在引入 `ClaimRegistry` / `ClaimStore` / 新 Python 类？不要
- [ ] 我是否在从 Python 调 anthropic / openai / LLM API？不要
- [ ] 我是否在为 source_type 每个枚举值写独立 Python 分支代码？不要，仅 prompt
- [ ] 我是否在写 `industries/` / `arenas/` / `companies/` / `archive/`？不要
- [ ] 测试覆盖了 QA 规则的 positive + negative 两面？
- [ ] Commit message 格式 `feat|fix|docs|test(scope): detail`？

---

## 6. 后续

本计划完成后，下一条实施计划应为：**Phase 2: Claim Layer**，覆盖：
- claim registry 对象 + JSONL 或 SQLite 存储
- matching engine（纯 Python：entity + keyword + type 兼容）
- claim_candidates → claim attach / new 决策
- archive 11/6/8 写入门（用户审批）
- arena_candidate 审批流程
- eval 扩展：matching_accuracy / claim_lifecycle_discipline（eval spec §5）

**Phase 2 不在本计划范围**，实施本计划时不要提前实现任何 Phase 2 组件。
