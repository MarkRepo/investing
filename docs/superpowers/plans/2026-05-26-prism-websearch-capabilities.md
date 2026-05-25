# Prism Web-Search 能力扩展实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 web-search 从"5 个 workflow 硬编码触发点 + 6 步重型仪式"扩展成"任何阶段可即兴调用 + 一行 helper 落地"，覆盖 03/04/05 三个原本断网的 workflow，给 LLM 加上 gap 自检、训练知识 baseline、sub-agent 深挖循环四类新能力。**不改决策权**：用户仍是 thesis 升版与最终判断的拍板人。

**Architecture:** 7 项纯能力扩展，分 4 个 phase。Phase 1 砌基础设施（helper 一行化 + 域名扩展），Phase 2 把 web-search 接进 03/04/05，Phase 3 加 gap detector + 训练知识 baseline，Phase 4 工具化下载脚本 + sub-agent 多轮深挖循环。每个 phase 跑通后用户确认再进下一阶段。

**Tech Stack:** Python 3.11、PyYAML、pytest、Anthropic 内置 WebSearch / WebFetch、Claude Code Agent dispatch（sub-agent 走订阅，零外部 API 费用）。

**纪律红线**（贯穿所有 phase）：
1. 脚本零 LLM——所有 WebSearch / WebFetch / 文本判断由主 agent 在对话或 sub-agent 中做
2. URL/snippet 必须来自 WebSearch 工具实际返回，禁止训练知识补 URL
3. sub-agent dispatch prompt 必须原文嵌硬规约（参 [[feedback_subagent_write_hallucination]]）
4. 修改任何已有 function / class / method 前先跑 `gitnexus_impact`，HIGH/CRITICAL 风险先停下来跟用户确认
5. 提交前必须跑 `gitnexus_detect_changes()`

---

## 文件结构

### Phase 1（基础设施）

**Modify:**
- `prism/scripts/web_prescan.py` — 新增 `register_web_search_batch()`；扩 `WHITELIST_DOMAINS` ~90 项

**Create:**
- `prism/scripts/test_web_prescan_batch.py` — 新 helper 的 unit test
- `prism/scripts/test_whitelist_domains.py` — 新增域名的命中 test

### Phase 2（03/04/05 接入）

**Modify:**
- `prism/workflows/03-extract-findings.md` — Step 2.4 新增"finding 训练知识冲突时即兴 web-search"
- `prism/workflows/04-synthesize/_shared.md` — 新章节"产出段缺事实数据时即兴 web-search"
- `prism/workflows/05-critic-review.md` — Step 6.5 新增"request-more 前先尝试 web-search 兜一轮"

### Phase 3（gap detector + baseline）

**Create:**
- `prism/scripts/gap_detector.py` — 扫 K# 证据数 / claim 时效 / source layer 分布
- `prism/scripts/test_gap_detector.py` — gap detector 单测
- `prism/workflows/_baseline_knowledge.md` — 训练知识 baseline 文档模版

**Modify:**
- `prism/workflows/00-research-topic.md` — Step 4.3 新增"训练知识 baseline" 章节（在 4.5 prescan 之前）
- `prism/scripts/topic.py` — 新增 `read_baseline_knowledge()` / `write_baseline_knowledge()`

### Phase 4（脚本工具化 + sub-agent 深挖）

**Create:**
- `prism/workflows/_subagent_deep_search.md` — sub-agent 深挖 prompt 模版（含防幻觉硬规约）
- `prism/workflows/_subagent_fetch_material.md` — sub-agent 抓取/下载 prompt 模版

**Modify:**
- `prism/workflows/03-extract-findings.md` — 加可选 "dispatch sub-agent 深挖" 路径
- `prism/workflows/05-critic-review.md` — Step 6.5 升级用 sub-agent 跑深挖循环（替代 Phase 2 的简版）
- `scripts/fetch_report_prism.py` — 文件头加 dispatch 用法 docstring（不改逻辑）

---

## Phase 1：Helper 一行化 + 信号源扩展

**Goal**：让主 agent 写一行 Python 完成"批量 register N 条 hit + 自动 log + 自动 resolve todos"，且 `WHITELIST_DOMAINS` 覆盖产业/数据/学术/政府四大类共 ~150 域名。

### Task 1.1：先跑 gitnexus_impact 看 register_web_search_result 的 blast radius

**Files:**
- 检查文件：`prism/scripts/web_prescan.py:259-348`

- [ ] **Step 1：跑 impact 分析**

```bash
# 在对话里调（CLAUDE.md 要求）
gitnexus_impact({target: "register_web_search_result", direction: "upstream"})
```

Expected：列出所有 caller。当前预期是 `_web_prescan_shared.md` workflow 引用，可能 0 个 Python caller（因为是 workflow 调）。如果 HIGH 或 CRITICAL，停下跟用户确认；如果 LOW，继续。

### Task 1.2：写 `register_web_search_batch` 失败测试

**Files:**
- Create: `prism/scripts/test_web_prescan_batch.py`

- [ ] **Step 1：创建测试文件**

```python
"""Tests for register_web_search_batch helper."""
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch

from prism.scripts import topic as topic_io
from prism.scripts.manifest import create_manifest, read_manifest


@pytest.fixture
def tmp_topic(monkeypatch):
    """Create a tmp topic with manifest, redirect PRISM_ROOT to tmp dir."""
    tmpdir = Path(tempfile.mkdtemp())
    monkeypatch.setattr("prism.scripts.web_prescan.PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.manifest._PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.topic.PRISM_ROOT", tmpdir)
    slug = "test-slug"
    variant = "test-variant"
    (tmpdir / "topics" / slug / variant).mkdir(parents=True)
    topic_io.create_topic(
        slug=slug, display_name="Test", topic_type="company",
        question="Q?", geo="US", depth="quick", variant=variant,
        ticker="US_TEST",
    )
    create_manifest(slug, variant)
    yield slug, variant, tmpdir
    shutil.rmtree(tmpdir)


def test_batch_registers_high_mid_skips_low(tmp_topic):
    """High and mid hits are registered; low is skipped."""
    from prism.scripts.web_prescan import register_web_search_batch

    slug, variant, _ = tmp_topic
    hits = [
        {"title": "Reuters report", "url": "https://reuters.com/x", "snippet": "..."},
        {"title": "Random blog", "url": "https://random.example/x", "snippet": "..."},
        {"title": "Sohu news", "url": "https://sohu.com/x", "snippet": "..."},
    ]
    summary = register_web_search_batch(
        slug=slug, variant=variant,
        query="Test query",
        addresses=["K1"],
        triggered_by="01-prescan",
        hits=hits,
    )
    assert summary["n_high"] >= 1   # reuters whitelist
    assert summary["n_low"] >= 1    # random.example
    # Manifest should contain registered ones
    mat_ids = [m for m in summary["mat_ids"] if m]
    manifest = read_manifest(slug, variant)
    assert len(manifest["materials"]) == len(mat_ids)


def test_batch_appends_search_log(tmp_topic):
    """Batch call appends one log entry with totals."""
    from prism.scripts.web_prescan import register_web_search_batch, list_search_log

    slug, variant, _ = tmp_topic
    register_web_search_batch(
        slug=slug, variant=variant, query="Q", addresses=["K1"],
        triggered_by="02-step0",
        hits=[{"title": "T", "url": "https://reuters.com/a", "snippet": "s"}],
    )
    entries = list_search_log(slug, variant)
    assert len(entries) == 1
    assert entries[0]["triggered_by"] == "02-step0"
    assert entries[0]["query"] == "Q"


def test_batch_resolves_matching_todos(tmp_topic):
    """Todos with matching addresses get auto-resolved."""
    from prism.scripts.web_prescan import register_web_search_batch

    slug, variant, _ = tmp_topic
    topic_io.set_user_todos(slug, [
        {"task": "find K1 evidence", "priority": "P0",
         "info_tier": "public", "addresses": ["K1"]},
    ], variant)
    summary = register_web_search_batch(
        slug=slug, variant=variant, query="Q", addresses=["K1"],
        triggered_by="02-step0",
        hits=[{"title": "T", "url": "https://reuters.com/a", "snippet": "s"}],
    )
    assert len(summary["resolved_todos"]) == 1
    assert summary["resolved_todos"][0]["task"] == "find K1 evidence"


def test_batch_with_explicit_confidence_overrides(tmp_topic):
    """Caller can override confidence per hit."""
    from prism.scripts.web_prescan import register_web_search_batch

    slug, variant, _ = tmp_topic
    hits = [
        {"title": "T", "url": "https://random.example/a", "snippet": "s",
         "confidence": 0.95, "domain_tier": "llm-judged-official"},
    ]
    summary = register_web_search_batch(
        slug=slug, variant=variant, query="Q", addresses=["K1"],
        triggered_by="01-prescan", hits=hits,
    )
    assert summary["n_high"] == 1   # overridden to high
```

- [ ] **Step 2：运行测试看它失败**

Run: `cd /Users/yangqi/investing && python -m pytest prism/scripts/test_web_prescan_batch.py -v`

Expected: 4 个测试全部 FAIL（`register_web_search_batch` 还不存在 → ImportError）。

### Task 1.3：实现 `register_web_search_batch`

**Files:**
- Modify: `prism/scripts/web_prescan.py`（在 `register_web_search_result` 之后插入）

- [ ] **Step 1：在 `register_web_search_result` 函数下方插入 helper**

定位到 `prism/scripts/web_prescan.py` `register_web_search_result` 函数末尾（约 line 348 之后），插入：

```python
def register_web_search_batch(
    slug: str,
    variant: str,
    query: str,
    addresses: list[str],
    triggered_by: str,
    hits: list[dict],
    full_texts: dict[str, str] | None = None,
) -> dict:
    """One-call batch wrapper for the 6-step prescan ritual.

    主 agent 把一轮 WebSearch 结果整批传进来，本 helper 完成：
      - 对每条 hit 调 register_web_search_result（自动判 domain_tier + funnel band）
      - 累计 mat_ids 后调 auto_resolve_todos
      - append_search_log（按 triggered_by 标签）

    每个 hit dict 必备 keys: title, url, snippet
    可选 keys: confidence (0-1, override), domain_tier ('whitelist'|'llm-judged-official'|'other')

    full_texts: optional dict of url → full_text fetched via WebFetch by main agent.
                Will be attached to the corresponding hit's inbox file (high band only).

    triggered_by ∈ {'00-prescan','01-prescan','02-step0','03-extract','04-synth',
                    '05-critic','06-daily-monitor','07-drilldown'}

    Returns:
        {
            'n_high': int, 'n_mid': int, 'n_low': int,
            'mat_ids': list[str|None],          # parallel to hits, None for low/skipped
            'resolved_todos': list[dict],        # auto-resolved todos
            'duplicates': int,                   # how many hits hit existing URLs
        }
    """
    full_texts = full_texts or {}
    results: list[dict] = []
    n_high = n_mid = n_low = duplicates = 0
    mat_ids: list[str | None] = []

    for hit in hits:
        url = hit.get("url", "")
        title = hit.get("title", "")
        snippet = hit.get("snippet", "")
        if not url or not title:
            mat_ids.append(None)
            n_low += 1
            continue
        r = register_web_search_result(
            slug=slug,
            variant=variant,
            query=query,
            url=url,
            title=title,
            snippet=snippet,
            addresses=addresses,
            full_text=full_texts.get(url),
            confidence=hit.get("confidence"),
            domain_tier=hit.get("domain_tier"),
        )
        results.append(r)
        mat_ids.append(r["mat_id"])
        band = r["band"]
        if band == "high":
            n_high += 1
        elif band == "mid":
            n_mid += 1
        else:
            n_low += 1
        if r.get("duplicate"):
            duplicates += 1

    new_ids = [m for m in mat_ids if m]
    resolved = auto_resolve_todos(slug, variant, new_ids) if new_ids else []

    append_search_log(
        slug=slug, variant=variant, query=query,
        n_results=len(hits),
        n_high=n_high, n_mid=n_mid, n_low=n_low,
        triggered_by=triggered_by,
    )

    return {
        "n_high": n_high,
        "n_mid": n_mid,
        "n_low": n_low,
        "mat_ids": mat_ids,
        "resolved_todos": resolved,
        "duplicates": duplicates,
    }
```

- [ ] **Step 2：运行测试，确认通过**

Run: `cd /Users/yangqi/investing && python -m pytest prism/scripts/test_web_prescan_batch.py -v`

Expected: 4/4 PASS。

- [ ] **Step 3：commit**

```bash
cd /Users/yangqi/investing
git add prism/scripts/web_prescan.py prism/scripts/test_web_prescan_batch.py
git commit -m "$(cat <<'EOF'
feat(prism): web_prescan 加 register_web_search_batch 一行 helper

把"调 WebSearch → 判 confidence → 入库 → resolve todos → 写 log"6 步压成一次调用，
便于在 03/04/05 等 workflow 即兴 web-search 时减少 ceremony。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

### Task 1.4：扩展 WHITELIST_DOMAINS

**Files:**
- Modify: `prism/scripts/web_prescan.py:29-56`

- [ ] **Step 1：在原 WHITELIST_DOMAINS 后追加新分类**

定位到 `prism/scripts/web_prescan.py:29` 起的 `WHITELIST_DOMAINS` 集合，把它替换为分类清晰的扩展版：

```python
WHITELIST_DOMAINS: set[str] = {
    # ---- 监管机构（已有） ----
    "csrc.gov.cn", "sec.gov", "hkex.com.hk", "hkma.gov.hk",
    "cac.gov.cn", "pbc.gov.cn", "mof.gov.cn", "miit.gov.cn",
    "sac.net.cn", "amac.org.cn",
    "federalreserve.gov", "treasury.gov", "ustr.gov",
    "fca.org.uk", "bankofengland.co.uk",
    "esma.europa.eu", "ecb.europa.eu",
    "fsa.go.jp", "boj.or.jp",
    "dart.fss.or.kr", "fss.or.kr", "bok.or.kr",
    "mas.gov.sg",
    # ---- 监管机构（新增） ----
    "ftc.gov", "fcc.gov", "doj.gov",
    "ec.europa.eu", "europarl.europa.eu", "ofcom.org.uk", "gov.uk",
    "meti.go.jp", "jftc.go.jp",
    # ---- 中国部委 + 行业协会（新增） ----
    "gov.cn", "stats.gov.cn", "ndrc.gov.cn", "mofcom.gov.cn",
    "sasac.gov.cn", "customs.gov.cn", "mee.gov.cn", "mohurd.gov.cn",
    "chinatax.gov.cn",
    "caam.org.cn", "cnpia.org",
    # ---- 交易所（已有） ----
    "sse.com.cn", "szse.cn", "bse.cn",
    "nasdaq.com", "nyse.com",
    "lseg.com", "londonstockexchange.com",
    "jpx.co.jp", "krx.co.kr",
    # ---- 交易所（新增） ----
    "asx.com.au", "tsx.com", "tmxmoney.com", "six-group.com",
    # ---- 国际组织（已有） ----
    "imf.org", "worldbank.org", "bis.org", "oecd.org",
    # ---- 国际组织 + 数据港（新增） ----
    "fred.stlouisfed.org", "bls.gov", "census.gov", "bea.gov", "eia.gov",
    "data.oecd.org",
    # ---- 主流财经媒体（已有） ----
    "ft.com", "wsj.com", "reuters.com", "bloomberg.com",
    "economist.com", "nikkei.com",
    "21jingji.com", "cls.cn", "caixin.com", "wallstreetcn.com",
    "yicai.com", "stcn.com", "cnstock.com",
    "sohu.com",
    # ---- 主流财经媒体（新增） ----
    "barrons.com", "marketwatch.com", "cnbc.com", "forbes.com",
    "scmp.com", "asia.nikkei.com", "channelnewsasia.com",
    # ---- 产业垂直（新增） ----
    "36kr.com", "huxiu.com", "tmtpost.com", "leiphone.com",
    "geekpark.net", "ithome.com", "jiqizhixin.com",
    "technode.com", "theinformation.com", "stratechery.com",
    "semianalysis.com", "techcrunch.com", "theverge.com",
    "arstechnica.com", "theregister.com",
    "eet-china.com",
    # ---- 数据/研究机构（新增） ----
    "counterpointresearch.com", "idc.com", "gartner.com", "semi.org",
    "trendforce.com", "omdia.com", "canalys.com", "statista.com",
    "ihsmarkit.com", "spglobal.com",
    "mckinsey.com", "bcg.com", "bain.com",
    "deloitte.com", "pwc.com", "ey.com", "kpmg.com",
    "iresearch.com.cn", "qianzhan.com",
    # ---- 学术（新增） ----
    "arxiv.org", "nature.com", "science.org", "scholar.google.com",
    "semanticscholar.org", "ieee.org", "acm.org", "sciencedirect.com",
    # ---- 公司公告平台（已有） ----
    "cninfo.com.cn", "edgar.sec.gov", "businesswire.com", "prnewswire.com",
    # ---- 投资者讨论 / 侧面信号（新增） ----
    "xueqiu.com", "jisilu.cn", "seekingalpha.com",
    "linkedin.com", "glassdoor.com",
}
```

- [ ] **Step 2：写 whitelist 命中测试**

Create: `prism/scripts/test_whitelist_domains.py`

```python
"""Sanity tests for WHITELIST_DOMAINS coverage."""
import pytest
from prism.scripts.web_prescan import classify_domain, WHITELIST_DOMAINS


@pytest.mark.parametrize("url,expected", [
    # CN regulators
    ("https://www.csrc.gov.cn/abc", "whitelist"),
    ("https://www.miit.gov.cn/abc", "whitelist"),
    ("https://www.ndrc.gov.cn/abc", "whitelist"),
    # New: ftc/fcc/ec
    ("https://www.ftc.gov/news/abc", "whitelist"),
    ("https://ec.europa.eu/competition/abc", "whitelist"),
    # New: 产业垂直
    ("https://36kr.com/article/abc", "whitelist"),
    ("https://www.theinformation.com/articles/abc", "whitelist"),
    ("https://semianalysis.com/p/abc", "whitelist"),
    # New: 数据机构
    ("https://www.counterpointresearch.com/abc", "whitelist"),
    ("https://www.idc.com/getdoc.jsp?abc", "whitelist"),
    ("https://www.trendforce.com/abc", "whitelist"),
    # New: 学术
    ("https://arxiv.org/abs/2401.00001", "whitelist"),
    ("https://www.nature.com/articles/abc", "whitelist"),
    # New: 数据港
    ("https://fred.stlouisfed.org/series/abc", "whitelist"),
    ("https://www.bls.gov/news.release/abc", "whitelist"),
    # IR sub-domain heuristic
    ("https://ir.tencent.com/news", "whitelist"),
    ("https://investors.apple.com/abc", "whitelist"),
    # Off-whitelist
    ("https://random-blog.example/x", "other"),
])
def test_classify_domain(url, expected):
    assert classify_domain(url) == expected


def test_whitelist_size_grew():
    """Sanity: whitelist扩展后至少 130 项（原 ~60，新增 ~90 → ~150）。"""
    assert len(WHITELIST_DOMAINS) >= 130
```

- [ ] **Step 3：运行测试**

Run: `cd /Users/yangqi/investing && python -m pytest prism/scripts/test_whitelist_domains.py -v`

Expected: 全部 PASS（17+ 用例 + 1 size sanity）。

- [ ] **Step 4：跑现有 web-search-related test 防回归**

Run:
```bash
cd /Users/yangqi/investing
python -m pytest prism/scripts/ -v -k "prescan or whitelist or manifest" 2>&1 | tail -40
```

Expected: 无回归失败。

- [ ] **Step 5：commit**

```bash
git add prism/scripts/web_prescan.py prism/scripts/test_whitelist_domains.py
git commit -m "$(cat <<'EOF'
feat(prism): WHITELIST_DOMAINS 扩展 ~90 项（产业/数据/学术/政府）

加 36kr/theinformation/semianalysis/counterpoint/idc/trendforce/arxiv/nature
等产业与学术域名；加 ftc/fcc/ndrc/mofcom/eia/bls 等监管和数据港域名。
原 ~60 项扩到 ~150 项，覆盖海外英文内容更全面。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

### Task 1.5：Phase 1 收尾 — gitnexus_detect_changes + 用户确认

- [ ] **Step 1：跑 detect_changes 验证**

```bash
# 在对话里调
gitnexus_detect_changes()
```

Expected: 改动只涉及 `web_prescan.py` 和两个新测试文件，影响的 process 应只在 web-search 链路。无意外。

- [ ] **Step 2：用户确认 Phase 1**

汇报给用户：
```
✅ Phase 1 完成
  - register_web_search_batch() 一行 helper（4 测试通过）
  - WHITELIST_DOMAINS 扩到 150+ 域名（17 测试通过）
  - 无回归
请确认是否进入 Phase 2（03/04/05 接 web-search）。
```

---

## Phase 2：03/04/05 接 web-search

**Goal**：让 03-extract、04-synthesize、05-critic-review 三个 workflow 都允许 LLM 即兴调 WebSearch + register_web_search_batch。Phase 2 用最简形态——主 agent 在对话里直接调，不引 sub-agent。

### Task 2.1：03-extract-findings 加 Step 2.4 "训练知识冲突即兴 web-search"

**Files:**
- Modify: `prism/workflows/03-extract-findings.md` 在 Step 2.3 之后插入

- [ ] **Step 1：插入新章节**

在 `prism/workflows/03-extract-findings.md` Step 2.3 末尾（line 232 `质量备注` 段之后、Step 3 之前）插入：

```markdown

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
    addresses=['{相关 K# 或 Q#}'],
    triggered_by='03-extract',
    hits=[
        {'title': '...', 'url': 'https://...', 'snippet': '...'},
        # 可选: 'confidence': 0.85, 'domain_tier': 'llm-judged-official'
    ],
)
```

3. 入库的 web-search material 在下一轮 03 处理时会自然进入 unprocessed 队列
4. 在当前 finding 笔记里**注明**："此处与训练知识 / 资料 X 冲突，已即兴 web-search 入库 mat-xxx 备核"

**纪律**：
- 单份资料 03 处理过程中即兴 web-search 不超过 3 条（避免变成 prescan）
- 若冲突点超过 3 条 → 标记 user_todos，stage 回退 02-gather-materials 走完整 prescan
- 即兴 web-search 必须填 addresses，否则 manifest coverage 算不进
```

- [ ] **Step 2：手动验证 markdown 渲染正常**

Run: `cd /Users/yangqi/investing && grep -n "Step 2.4" prism/workflows/03-extract-findings.md`

Expected: 显示新增章节的行号，行号在原 Step 3 之前。

### Task 2.2：04-synthesize/_shared.md 加章节"产出段缺事实即兴 web-search"

**Files:**
- Modify: `prism/workflows/04-synthesize/_shared.md`

- [ ] **Step 1：读取目标文件最后一段，定位插入点**

Read: `prism/workflows/04-synthesize/_shared.md`（看到全文）

- [ ] **Step 2：在文件末尾追加新章节**

在 `_shared.md` 末尾追加：

```markdown

## 即兴 web-search（新增）

合成某份产出过程中，如发现某段需要的关键事实数据**当前 manifest 缺失**（如"2025 Q3 全球 EV 销量"、"某公司最新季报营收"），主 agent 可以即兴调一次 WebSearch 而不必回退 02：

适用场景（**只在以下情况**才即兴）：
- 04 写产出时缺一个具体数字（销量/单价/市占率/估值倍数）
- 该数字训练知识无法准确给出（时效性过新）
- 已有 manifest 里搜了所有 findings 都没覆盖

执行（与 03-extract 用同一 helper）：

```python
from prism.scripts.web_prescan import register_web_search_batch
register_web_search_batch(
    slug='{slug}', variant='{variant}',
    query='缺失数据查询词，例如 "global EV sales 2025 Q3 IEA"',
    addresses=['{对应 K# 或 Q#}'],
    triggered_by='04-synth',
    hits=[...],  # WebSearch 返回的 hit
)
```

入库后在产出 frontmatter 的 `mat_ids_referenced` 列表中加入新 mat_id，确保 `set_output_referenced_mats` 调用时引用正确。

**纪律**：
- 单份产出合成过程即兴 web-search 不超过 5 条（避免膨胀）
- 引用 web-search 入库 material 时**仍需写 mat_id**（不准直接引 WebSearch URL，保溯源链）
- 如果即兴搜不到 → 在该段产出中标注"此处数据缺失，建议人工补充"，不要编造数字
```

- [ ] **Step 3：人工 review 章节流畅性**

Read: `prism/workflows/04-synthesize/_shared.md` 最后 100 行，确认新章节衔接 OK。

### Task 2.3：05-critic-review Step 6.5 "request-more 前先 web-search 兜一轮"

**Files:**
- Modify: `prism/workflows/05-critic-review.md`

- [ ] **Step 1：在 Step 6 之后插入 Step 6.5**

定位 `prism/workflows/05-critic-review.md` 当前 Step 6 末尾（line 110 附近）和 Step 7 之间。在两个 Step 之间插入：

```markdown
---

## Step 6.5：critic 缺口先 web-search 兜底（**新增**）

如果 Step 4 的修改建议指向"需要补 X 资料"或"K# 论证薄弱因为缺 Y 数据"，**先尝试 web-search 兜一轮**再决定 verdict——而不是直接 `request-more`。

判定流程：

```
critic 找到缺口
  ↓
该缺口能用 web-search 找到？
  ↓ Yes → 即兴 web-search 1-3 条 query → 入库 → 重新看 critic 缺口是否还成立
  ↓ No  → 直接 verdict = request-more（让用户上传一手资料）
```

「能用 web-search 找到」的典型场景：
- 公开数据：行业规模、监管文件、龙头公告、公开财报
- 半公开：卖方研报标题/摘要、新闻报道、产业协会数据

「web-search 不够」的典型场景：
- 一手专家访谈、付费墙后内容、未公开内部数据、产业链调研

执行：

```python
# 主 agent 在对话里调 WebSearch 拉一批 hit，再一行入库
from prism.scripts.web_prescan import register_web_search_batch
summary = register_web_search_batch(
    slug='{slug}', variant='{variant}',
    query='critic 缺口的精准查询',
    addresses=['{涉及的 K#}'],
    triggered_by='05-critic',
    hits=[...],
)
print(f"web-search 兜底：高/中/低 = {summary['n_high']}/{summary['n_mid']}/{summary['n_low']}")
```

入库后**重新读一次相关 finding / 产出**，看 critic 缺口是否被消除：
- 是 → verdict 改为 `approve` 或 `request-rewrite`（让 04 用新 mat 重写部分产出）
- 否 → verdict 仍为 `request-more`，但在 user_todos 里只列 web-search 拿不到的部分

**纪律**：
- Step 6.5 即兴 web-search 不超过 5 条 query × 5-10 hit/query = 不超过 50 hit/critic 轮
- 即兴 web-search 入库的 mat 在 verdict='request-rewrite' 时，set_output_status 把对应 output 标 stale
- **保溯源链**：判 critic 缺口"已被消除"时必须 cite 新入库的 mat_id

---
```

- [ ] **Step 2：人工 review 衔接到 Step 7**

Read: `prism/workflows/05-critic-review.md`，确认 Step 6 → Step 6.5 → Step 7 的逻辑流畅，且 Step 7 仍能正常工作（既有 verdict 三选一逻辑不变，只是 6.5 让"request-more"概率下降）。

### Task 2.4：手动 sanity test — 跑现有 topic 走一遍 03/05

**Files:**
- 测试用 topic：`prism/topics/us-circle/claude-opus-4-7/`（或选另一个用户最近研究的）

- [ ] **Step 1：选 topic 跑 03 dry-read（不实际调 LLM）**

```bash
ls prism/topics/ | head -20
ls prism/topics/us-circle/ 2>/dev/null
```

- [ ] **Step 2：跑 helper smoke test（用真实 topic）**

```bash
cd /Users/yangqi/investing
python3 << 'EOF'
# Smoke test register_web_search_batch on a real topic
from prism.scripts.web_prescan import register_web_search_batch
import json

# 不实际调 WebSearch，构造 mock hits 验证 helper 在真实 topic 上能跑通
slug, variant = "us-circle", "claude-opus-4-7"  # 调整为存在的 topic
try:
    summary = register_web_search_batch(
        slug=slug, variant=variant,
        query="USDC 监管 smoke test",
        addresses=["K1"],
        triggered_by="03-extract",
        hits=[
            {"title": "Reuters", "url": "https://reuters.com/smoketest", "snippet": "test"},
        ],
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    # cleanup smoke test material
    from prism.scripts.manifest import remove_material
    for mid in summary["mat_ids"]:
        if mid:
            remove_material(slug, variant, mat_id=mid, delete_file=True)
    print("smoke test cleaned up")
except FileNotFoundError as e:
    print(f"topic 不存在，换一个：{e}")
EOF
```

Expected: summary 输出 + cleanup OK；如果 topic 不存在换一个。

### Task 2.5：Phase 2 收尾

- [ ] **Step 1：跑 detect_changes**

```bash
gitnexus_detect_changes()
```

Expected: 改动 = 3 个 workflow markdown，不涉及代码逻辑改变。

- [ ] **Step 2：commit**

```bash
cd /Users/yangqi/investing
git add prism/workflows/03-extract-findings.md prism/workflows/04-synthesize/_shared.md prism/workflows/05-critic-review.md
git commit -m "$(cat <<'EOF'
feat(prism): 03/04/05 workflow 接入即兴 web-search

新章节让 LLM 在 03-extract、04-synthesize、05-critic-review 阶段
直接调 WebSearch + register_web_search_batch helper 入库，
critic 缺口在 verdict 之前先 web-search 兜底（减少回 02 的次数）。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 3：用户确认 Phase 2**

汇报：
```
✅ Phase 2 完成
  - 03 / 04-shared / 05 三个 workflow 都加了即兴 web-search 章节
  - smoke test 在真实 topic 跑通
  - 03 限 3 条/份资料，04 限 5 条/份产出，05 限 50 hit/critic 轮
请确认是否进入 Phase 3（gap detector + 训练知识 baseline）。
```

---

## Phase 3：gap detector + 训练知识 baseline

**Goal**：LLM 主动汇报"哪些 K# 证据不足 / 哪些 claim 时效性堪忧"——不替用户决定，只汇报；同时给每个 topic 一份训练知识 baseline 文档以便溯源对照。

### Task 3.1：gap_detector 失败测试

**Files:**
- Create: `prism/scripts/test_gap_detector.py`

- [ ] **Step 1：写测试**

```python
"""Tests for gap_detector."""
import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta, timezone

from prism.scripts import topic as topic_io
from prism.scripts.manifest import create_manifest, add_material


@pytest.fixture
def tmp_topic_with_findings(monkeypatch):
    tmpdir = Path(tempfile.mkdtemp())
    monkeypatch.setattr("prism.scripts.manifest._PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.topic.PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.gap_detector.PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.web_prescan.PRISM_ROOT", tmpdir)
    slug, variant = "test-gap", "test"
    (tmpdir / "topics" / slug / variant).mkdir(parents=True)
    topic_io.create_topic(
        slug=slug, display_name="T", topic_type="company",
        question="Q?", geo="US", depth="quick", variant=variant,
        ticker="US_T",
    )
    create_manifest(slug, variant)
    yield slug, variant, tmpdir
    shutil.rmtree(tmpdir)


def test_gap_detects_uncovered_k(tmp_topic_with_findings):
    """K# without any material → gap reports it as uncovered."""
    from prism.scripts.gap_detector import detect_gaps

    slug, variant, tmpdir = tmp_topic_with_findings
    # write thesis with K1, K2
    thesis_path = tmpdir / "topics" / slug / variant / "thesis_v0.md"
    thesis_path.write_text(
        "## Killer Question\n\nK1: Does X happen?\nK2: Does Y happen?\n",
        encoding="utf-8"
    )
    topic_io.set_thesis(slug, variant, version=0, summary="t",
                       stage_set_at="01-roadmap-pending")
    # add material covering only K1
    add_material(slug=slug, filename="m1.md", source_type="web-article",
                 variant=variant, addresses=["K1"])

    report = detect_gaps(slug, variant)
    assert "K2" in report["uncovered_ks"]
    assert "K1" not in report["uncovered_ks"]


def test_gap_detects_thin_evidence(tmp_topic_with_findings):
    """K# with < min_evidence material → flagged as thin."""
    from prism.scripts.gap_detector import detect_gaps

    slug, variant, tmpdir = tmp_topic_with_findings
    thesis_path = tmpdir / "topics" / slug / variant / "thesis_v0.md"
    thesis_path.write_text("K1: X?\n", encoding="utf-8")
    topic_io.set_thesis(slug, variant, version=0, summary="t",
                       stage_set_at="01-roadmap-pending")
    add_material(slug=slug, filename="m1.md", source_type="web-article",
                 variant=variant, addresses=["K1"])

    report = detect_gaps(slug, variant, min_evidence=2)
    assert "K1" in report["thin_evidence"]


def test_gap_detects_stale_web_search(tmp_topic_with_findings):
    """web-search material > 90d expire → flagged as stale claims."""
    from prism.scripts.gap_detector import detect_gaps
    from prism.scripts.manifest import make_search_meta

    slug, variant, tmpdir = tmp_topic_with_findings
    thesis_path = tmpdir / "topics" / slug / variant / "thesis_v0.md"
    thesis_path.write_text("K1: X?\n", encoding="utf-8")
    topic_io.set_thesis(slug, variant, version=0, summary="t",
                       stage_set_at="01-roadmap-pending")
    # Add expired web-search material
    old_dt = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
    sm = make_search_meta(query="q", url="https://reuters.com/x",
                          domain="reuters.com", domain_tier="whitelist",
                          searched_at=old_dt)
    add_material(slug=slug, filename="m1.md", source_type="web-search",
                 variant=variant, addresses=["K1"], search_meta=sm)

    report = detect_gaps(slug, variant)
    assert len(report["expired_web_materials"]) == 1


def test_gap_summary_string(tmp_topic_with_findings):
    """detect_gaps returns a human-readable summary."""
    from prism.scripts.gap_detector import detect_gaps, format_summary

    slug, variant, _ = tmp_topic_with_findings
    report = detect_gaps(slug, variant)
    summary = format_summary(report)
    assert isinstance(summary, str)
    assert len(summary) > 0
```

- [ ] **Step 2：跑测试看它失败**

Run: `cd /Users/yangqi/investing && python -m pytest prism/scripts/test_gap_detector.py -v`

Expected: 4/4 FAIL（gap_detector 模块不存在）。

### Task 3.2：实现 gap_detector

**Files:**
- Create: `prism/scripts/gap_detector.py`

- [ ] **Step 1：写实现**

```python
"""Knowledge gap detector — zero LLM calls.

Reports (does NOT decide) which K# need more evidence, which web-search
materials are stale, and which claims have only training-knowledge basis.

LLM 自己看 report 决定继续搜还是停。
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from prism.scripts import topic as topic_io
from prism.scripts.manifest import read_manifest, list_expired_web_search

PRISM_ROOT = Path(__file__).resolve().parent.parent


def _addr_key(addr: str) -> str:
    return addr.split("@", 1)[0] if isinstance(addr, str) else ""


def detect_gaps(
    slug: str,
    variant: str,
    min_evidence: int = 2,
) -> dict:
    """Detect knowledge gaps in a topic's research.

    Returns:
        {
            'topic': {slug, variant, thesis_version},
            'uncovered_ks':       [K#, ...],     # 0 evidence
            'thin_evidence':      [K#, ...],     # < min_evidence
            'evidence_count':     {K#: int},
            'expired_web_materials': [mat, ...], # web-search > 90d
            'training_only_claims': [...],       # placeholder, requires baseline
        }
    """
    try:
        topic = topic_io.read_topic(slug, variant)
    except FileNotFoundError:
        return {"error": f"topic not found: {slug}/{variant}"}

    thesis_block = topic.get("thesis") or {}
    cur_v = thesis_block.get("current_version")

    ks: list[str] = []
    if cur_v is not None:
        try:
            from prism.scripts.outputs import extract_killer_questions
            ks = list(extract_killer_questions(slug, variant, cur_v))
        except Exception:
            ks = []

    try:
        manifest = read_manifest(slug, variant)
    except FileNotFoundError:
        manifest = {"materials": []}

    evidence_count: dict[str, int] = {k: 0 for k in ks}
    for m in manifest.get("materials") or []:
        addrs = m.get("addresses") or []
        seen_keys = {_addr_key(a) for a in addrs}
        for k in seen_keys:
            if k in evidence_count:
                evidence_count[k] += 1

    uncovered = [k for k in ks if evidence_count[k] == 0]
    thin = [k for k in ks if 0 < evidence_count[k] < min_evidence]

    expired = list_expired_web_search(slug, variant) if manifest.get("materials") else []

    # training_only: 暂时是空，Phase 3 的 baseline 文档落地后会填
    training_only: list[str] = []

    return {
        "topic": {
            "slug": slug,
            "variant": variant,
            "thesis_version": cur_v,
        },
        "uncovered_ks": uncovered,
        "thin_evidence": thin,
        "evidence_count": evidence_count,
        "expired_web_materials": [
            {"id": m["id"], "filename": m["filename"],
             "expire_at": (m.get("search_meta") or {}).get("expire_at")}
            for m in expired
        ],
        "training_only_claims": training_only,
    }


def format_summary(report: dict) -> str:
    """Human-readable summary for主 agent 在对话里展示给用户。"""
    if "error" in report:
        return f"⚠ {report['error']}"
    lines = []
    t = report["topic"]
    lines.append(
        f"📊 Gap report: {t['slug']}/{t['variant']} "
        f"(thesis_v{t['thesis_version']})"
    )
    if report["uncovered_ks"]:
        lines.append(
            f"  ❌ 0 evidence: {', '.join(report['uncovered_ks'])}"
        )
    if report["thin_evidence"]:
        ec = report["evidence_count"]
        thin_str = ", ".join(f"{k}({ec[k]})" for k in report["thin_evidence"])
        lines.append(f"  ⚠ thin: {thin_str}")
    if report["expired_web_materials"]:
        lines.append(
            f"  ⏰ expired web-search: {len(report['expired_web_materials'])} 条 (>90d)"
        )
    if not (report["uncovered_ks"] or report["thin_evidence"]
            or report["expired_web_materials"]):
        lines.append("  ✅ no gaps detected")
    return "\n".join(lines)
```

- [ ] **Step 2：跑测试**

Run: `cd /Users/yangqi/investing && python -m pytest prism/scripts/test_gap_detector.py -v`

Expected: 4/4 PASS。

- [ ] **Step 3：commit**

```bash
git add prism/scripts/gap_detector.py prism/scripts/test_gap_detector.py
git commit -m "$(cat <<'EOF'
feat(prism): 加 gap_detector — K# 证据数 / 过期 web-search 自检

零 LLM 调用，只汇报缺口让主 agent 决定下一步是搜还是停。
detect_gaps() 返回 uncovered_ks / thin_evidence / expired_web_materials；
format_summary() 输出对话里展示用的人读字符串。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

### Task 3.3：训练知识 baseline 模版与读写函数

**Files:**
- Create: `prism/workflows/_baseline_knowledge.md`
- Modify: `prism/scripts/topic.py` 末尾加两函数

- [ ] **Step 1：创建模版**

Create `prism/workflows/_baseline_knowledge.md`:

```markdown
# 训练知识 Baseline 模版

**用法**：在 workflow 00 Step 4.3（新增）里被调用，让 LLM 先把"我训练时对此 topic 知道什么"写下来，作为后续 web-search / 用户资料的对照基线。

**写入位置**：`prism/topics/{slug}/{variant}/baseline_knowledge.md`

**模版**：

````markdown
---
slug: {slug}
variant: {variant}
written_at: {iso_ts}
training_cutoff_estimate: {YYYY-MM}    # LLM 自评训练截止月（如 2025-01）
---

# 训练知识 Baseline — {display_name}

> 本文记录 LLM 在**训练截止时**对该 topic 的认知现状。
> 后续 web-search / 用户资料的事实校准必须 cite 本文记忆条目。

## 一、关键事实记忆（{n} 条）

每条格式：
- `[fact-NN]` 训练时记得的事实，含数字/时间/主体（如 "fact-01: 2024 年全球 EV 销量 1450 万台"）
- 标注**置信度**：高 / 中 / 低（LLM 自评）
- 不确定的标 "uncertain"，跳过比编造好

## 二、关键人物 / 公司 / 产品

每条 1 句话定位 + 训练时知道的最新动作

## 三、产业链 / 竞争格局认知

3-5 段，主线 + 主要玩家相对位

## 四、训练知识盲点（自我承认）

LLM 自评以下方面训练时不够 / 不知道：
- {领域 / 时段 / 数据类型}
- {具体盲点}

## 五、需要 web-search 校准的优先项

按优先级列 5-10 条："这条事实需要 web-search 拉最新数据" — 接下来 Step 4.5 prescan 的种子。
````

**纪律**：
- 自评置信度时**保守**——宁可标 "uncertain" 也不编造
- 第四节的盲点必须诚实写——它是 prescan 攻打方向的来源
- 写完即落盘到 `prism/topics/{slug}/{variant}/baseline_knowledge.md`，后续 03/04 可 cite
```

- [ ] **Step 2：在 topic.py 末尾加读写函数**

在 `prism/scripts/topic.py` 末尾追加：

```python
def baseline_knowledge_path(slug: str, variant: str) -> Path:
    return _topic_path(slug, variant).parent / "baseline_knowledge.md"


def read_baseline_knowledge(slug: str, variant: str) -> str | None:
    """Return the baseline knowledge markdown content, or None if not written yet."""
    p = baseline_knowledge_path(slug, variant)
    if not p.is_file():
        return None
    return p.read_text(encoding="utf-8")


def has_baseline_knowledge(slug: str, variant: str) -> bool:
    return baseline_knowledge_path(slug, variant).is_file()
```

- [ ] **Step 3：写最小 sanity test**

Append to `prism/scripts/test_gap_detector.py`:

```python
def test_baseline_path_helpers(tmp_topic_with_findings):
    from prism.scripts.topic import (
        has_baseline_knowledge, read_baseline_knowledge,
        baseline_knowledge_path,
    )
    slug, variant, _ = tmp_topic_with_findings
    assert not has_baseline_knowledge(slug, variant)
    assert read_baseline_knowledge(slug, variant) is None
    p = baseline_knowledge_path(slug, variant)
    p.write_text("baseline test", encoding="utf-8")
    assert has_baseline_knowledge(slug, variant)
    assert read_baseline_knowledge(slug, variant) == "baseline test"
```

- [ ] **Step 4：跑测试**

Run: `cd /Users/yangqi/investing && python -m pytest prism/scripts/test_gap_detector.py -v`

Expected: 5/5 PASS（含新增 baseline test）。

### Task 3.4：00-research-topic 加 Step 4.3 训练知识 baseline 章节

**Files:**
- Modify: `prism/workflows/00-research-topic.md`

- [ ] **Step 1：在 Step 4.5 之前插入 Step 4.3**

定位 `prism/workflows/00-research-topic.md` Step 4 末尾（line 80 附近）和 Step 4.5 之间。在两者之间插入：

```markdown

---

## Step 4.3：写训练知识 baseline（**新增 — 必跑**）

**为什么必须做**：训练知识是研究的第一层数据源（web-search 第二层、用户兜底第三层）。先把"训练时记得什么"显式写下来，后续每条 web-search hit 都能对照"我有的 vs 新拿到的差在哪"。同时这份 baseline 是 Step 4.5 prescan 的种子——盲点列表直接转成 prescan 优先 query。

**执行**：参 `prism/workflows/_baseline_knowledge.md` 模版，让 LLM（即当前主 agent）写一份 `prism/topics/{slug}/{variant}/baseline_knowledge.md`：

```bash
# 主 agent 用 Write 工具落盘
# 落盘后调脚本只用于注册（不改 topic 主流程）
python3 -c "
from prism.scripts.topic import has_baseline_knowledge
print('baseline 已落盘:', has_baseline_knowledge('{slug}', '{variant}'))
"
```

**例外可跳过**：concept 类 topic（纯方法论）；用户明确说"不需要 baseline"。company / industry / arena 默认必跑。

**纪律**：
- baseline 自评置信度保守（uncertain 优于编造）
- 第四节的盲点列表直接喂给 Step 4.5 prescan 作为优先 query
- 后续 03/04 引用训练知识时 cite `baseline_knowledge.md` 的 fact-NN 编号
```

- [ ] **Step 2：人工 review 衔接到 Step 4.5**

Read: `prism/workflows/00-research-topic.md`，确认 Step 4 → 4.3 → 4.5 → 5 流畅。

### Task 3.5：Phase 3 收尾

- [ ] **Step 1：跑全部新增 test**

```bash
cd /Users/yangqi/investing
python -m pytest prism/scripts/test_gap_detector.py prism/scripts/test_web_prescan_batch.py prism/scripts/test_whitelist_domains.py -v
```

Expected: 全部 PASS（4 + 4 + 17 + 1 + 1 = 27 测试）。

- [ ] **Step 2：detect_changes**

```bash
gitnexus_detect_changes()
```

- [ ] **Step 3：commit**

```bash
git add prism/scripts/topic.py prism/scripts/gap_detector.py prism/scripts/test_gap_detector.py prism/workflows/_baseline_knowledge.md prism/workflows/00-research-topic.md
git commit -m "$(cat <<'EOF'
feat(prism): gap_detector + 训练知识 baseline

gap_detector.detect_gaps() 汇报 K# 证据数 / 过期 web-search，让 LLM 自决继续搜还是停。
00-research-topic 新增 Step 4.3 训练知识 baseline 必跑章节，
let LLM 显式写下训练时知道什么，作为 web-search 校准的对照基线。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 4：用户确认**

汇报：
```
✅ Phase 3 完成
  - gap_detector.py（5 测试）
  - topic.py 加 baseline 读写函数
  - _baseline_knowledge.md 模版
  - 00-research-topic Step 4.3 必跑章节
请确认是否进入 Phase 4（脚本工具化 + sub-agent 深挖循环）。
```

---

## Phase 4：脚本工具化 + sub-agent 多轮深挖循环

**Goal**：把"看 snippet → 出下一轮 query"的多轮深挖从主对话转移到 sub-agent context（H3 路径，零外部 API 费用）。同时把 `fetch_report_prism.py` 等下载脚本注册成 LLM 可即兴 dispatch 的能力。

### Task 4.1：sub-agent 深挖 prompt 模版

**Files:**
- Create: `prism/workflows/_subagent_deep_search.md`

- [ ] **Step 1：写模版**

Create `prism/workflows/_subagent_deep_search.md`:

```markdown
# Sub-agent Deep Search Prompt 模版

**用途**：当某个 K# 或具体问题需要多轮"看 snippet → 出新 query → 再 search"的深挖循环时，主 agent dispatch 一个 sub-agent 在独立 context 中跑这个循环，避免污染主对话。零外部 API（用 Anthropic 内置 WebSearch）。

**调用方**：03 / 04 / 05 / 07 任意需要深挖的场景。

---

## Sub-agent dispatch 模版

主 agent 调用 `Agent` 工具时使用以下 prompt（替换 `{...}`）：

```
你是一个 web-search 深挖 sub-agent。任务范围严格限定在以下：

**目标**：围绕 "{深挖问题，如 'USDC 储备金 SVB 危机后变化'}" 收集 5-10 条高质量证据。

**纪律（必须严格遵守，违反视为任务失败）**：

1. **不写文件，不调 Edit/Write 工具，不用 Bash heredoc 写文件**——
   你只通过 final message 返回结果。这是硬规约，参 prism memory feedback_subagent_write_hallucination。

2. **只调 WebSearch / WebFetch 工具收集证据**，不做合成 / 不写产出。

3. **多轮循环模式**（最多 {max_rounds} 轮，默认 3）：
   - Round 1：用初始 query 调 WebSearch 1-2 次
   - Round 1 末：基于结果识别 2-3 个值得深挖的子问题，写新 query
   - Round 2：调 WebSearch 攻打子问题
   - Round 2 末：再筛 1-2 条值得 WebFetch 抓 full text
   - Round 3：用 WebFetch 拿 full text，提炼关键 quote/数字
   - 任一轮发现"已经够"则提前停

4. **不引用训练知识补 URL** — URL 必须来自工具实际返回的 search_result block。

5. **每条 hit 自评 confidence**（0-1）+ domain_tier ('whitelist'/'llm-judged-official'/'other')，
   未来主 agent 用这两个字段决定是否入库。

6. **每条 query 后简短记录**："Round N query='...' → 找到 X 条相关，下一轮聚焦 Y"。

---

## Final message 格式（必须严格按此结构）

```
## 摘要（2-3 句）
{深挖结论概述}

## 证据列表

### Hit 1
- title: {...}
- url: {...}
- snippet: {...}
- domain_tier: {whitelist|llm-judged-official|other}
- confidence: {0.0-1.0}
- 关键 quote / 数字: {...}
- addresses: [K?]    # 跟主 agent 说的 K# 一致

### Hit 2
{同格式}

...

## 搜索过程日志
- Round 1: query="..." → N 条
- Round 2: query="..." → M 条
- Round 3 (WebFetch): url="..." → 关键发现 = ...

## 自评 / 局限
- 哪些子问题没搜到 / 数据陈旧 / 需用户兜底
```

---

## 调用代码（主 agent 在对话里写）

```python
# 主 agent 在 Phase 2/3 的即兴 web-search 不够用时升级为深挖
# Agent 工具调用（伪代码 — 主 agent 实际通过 tool 调）：
agent_result = Agent(
    description="K1 深挖 web-search",
    subagent_type="general-purpose",
    prompt="""[把上面的模版填好后整段粘贴进来]""",
    # 不传 model（跟随主 agent，参 memory feedback_subagent_model）
)
# 主 agent 收到 final message 后解析 hits，用 Phase 1 helper 入库：
from prism.scripts.web_prescan import register_web_search_batch
summary = register_web_search_batch(
    slug='{slug}', variant='{variant}',
    query='K1 深挖（sub-agent dispatched）',
    addresses=['K1'],
    triggered_by='{03-extract|04-synth|05-critic|07-drilldown}',
    hits=parsed_hits,  # 主 agent 从 sub-agent final message 解析出的列表
)
```

---

## 何时升级到 sub-agent 深挖（vs 主 agent 即兴搜）

| 场景 | 用主 agent 即兴 | 用 sub-agent 深挖 |
|---|---|---|
| 1-3 条 query 能搞定 | ✅ | ❌（杀鸡用牛刀） |
| 需要 5+ 轮迭代 | ❌（污染主 context） | ✅ |
| critic 缺口涉及多个独立子问题 | ❌ | ✅ |
| 主 agent context 已经很满 | ❌ | ✅（深挖移到 sub-agent context） |
| 多个 K# 并行深挖 | ❌ | ✅（dispatch 多个 sub-agent 并行） |
```

### Task 4.2：03/05 加可选 sub-agent 深挖路径

**Files:**
- Modify: `prism/workflows/03-extract-findings.md`（在 Phase 2 加的 Step 2.4 之后追加 2.4b）
- Modify: `prism/workflows/05-critic-review.md`（升级 Step 6.5）

- [ ] **Step 1：03 Step 2.4 末尾追加 2.4b 选项**

定位 `prism/workflows/03-extract-findings.md` Phase 2 加的 Step 2.4 末尾（"即兴 web-search 必须填 addresses" 之后），插入：

```markdown

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
```

- [ ] **Step 2：05 Step 6.5 升级**

定位 `prism/workflows/05-critic-review.md` Phase 2 加的 Step 6.5（"web-search 兜底"）末尾，追加 6.5b：

```markdown

### Step 6.5b：缺口涉及多子问题时升级为 sub-agent 深挖

如果 critic 缺口指向"K# 论证薄弱因为缺 3 个独立子问题的数据"——主 agent 应**dispatch sub-agent 并行深挖**而不是自己串行调 5×WebSearch：

执行方式（参 `prism/workflows/_subagent_deep_search.md`）：

```python
# 主 agent 同时 dispatch 多个 sub-agent（不同 K# / 不同子问题各一）
# 每个 sub-agent 独立跑 1-3 轮深挖
# 全部回来后批量 register_web_search_batch
```

**适用判定**：
- critic 列出 ≥3 个独立缺口子问题 → sub-agent
- critic 列出 1-2 个简单缺口 → 主 agent 即兴 web-search（Step 6.5 原路径）

**收回 verdict**：所有 sub-agent 入库后，重新读 critic 缺口判定是否被消除——逻辑同 Step 6.5。
```

### Task 4.3：fetch_report_prism.py 加 dispatch docstring

**Files:**
- Modify: `scripts/fetch_report_prism.py`（仅文件头加 docstring，不改逻辑）

- [ ] **Step 1：读取当前文件头**

Read: `scripts/fetch_report_prism.py`（前 30 行）

- [ ] **Step 2：替换文件头 docstring**

把当前 module docstring（如果有）替换为：

```python
"""下载公司财报到 inbox 目录。A 股从巨潮资讯网，美股从 SEC EDGAR。

LLM 工具用法（被 03/05 sub-agent dispatch 时）:
    主 agent 在 03-extract 或 05-critic 流程中识别到"需要补一份具体年报/季报"时，
    可以 dispatch sub-agent 运行本脚本：

    python -m scripts.fetch_report_prism --ticker {market}_{code} --year YYYY [--quarter Q]

    sub-agent dispatch prompt 标准格式参 prism/workflows/_subagent_fetch_material.md。
    脚本退出码 0 = 已下载到 prism/topics/{slug}/inbox/auto/；非 0 = 失败（让 sub-agent 报告失败原因）。

    下载完成后由主 agent 跑 workflow 02 把 PDF 登记入 manifest（含 mineru 转换）。
"""
```

- [ ] **Step 3：smoke check**

Run: `cd /Users/yangqi/investing && python -c "import scripts.fetch_report_prism; print('import OK')"`

Expected: `import OK`（不报错）。

### Task 4.4：sub-agent fetch material prompt 模版

**Files:**
- Create: `prism/workflows/_subagent_fetch_material.md`

- [ ] **Step 1：写模版**

Create `prism/workflows/_subagent_fetch_material.md`:

```markdown
# Sub-agent Fetch Material Prompt 模版

**用途**：当 web-search 拿到一个公开财报 / 公告 PDF 的 URL 后，主 agent dispatch sub-agent 跑下载脚本，让主 agent 自己不必离开当前任务流。

**调用 prompt 模版**：

```
你是 prism 系统的 fetch-material sub-agent。任务范围：

**目标**：下载 {标的} 的 {资料类型} 到 prism/topics/{slug}/inbox/。

**可用工具**：
- Bash：跑 fetch_report_prism / curl / wget 等
- Read：检查下载文件是否完整（看大小）

**纪律**：
1. 不写其他文件、不改 manifest（manifest 由主 agent 走 workflow 02 处理）
2. 下载完成后用 Bash `ls -la` 验证文件存在 + 大小 > 50KB（小于即视为失败）
3. 失败时 final message 必须写明原因（404? 鉴权? URL 错？）

**调用例**：

```bash
python -m scripts.fetch_report_prism --ticker SZSE_300073 --year 2024
# 或
curl -L "{pdf_url}" -o prism/topics/{slug}/inbox/{filename}.pdf
```

**Final message 格式**：
- 成功：写出 `success: prism/topics/{slug}/inbox/{filename}.pdf ({size}KB)`
- 失败：写出 `failure: {原因}` + 主 agent 应如何接续（建议手动上传 / 换 URL / 跳过）
```

### Task 4.5：integration smoke — 现有 topic 跑一次 deep search

**Files:**
- 测试用 topic：选一个用户最近研究的（如 us-circle / global-futu）

- [ ] **Step 1：选 topic + 跑 gap_detector**

```bash
cd /Users/yangqi/investing
python3 -c "
from prism.scripts.gap_detector import detect_gaps, format_summary
slug, variant = 'us-circle', 'claude-opus-4-7'  # 调整
report = detect_gaps(slug, variant)
print(format_summary(report))
"
```

Expected: 看到 K# 证据汇总 / uncovered 列表。如果 topic 不存在换一个。

- [ ] **Step 2：human-in-loop 验证 sub-agent 模版**

主 agent（你自己）在对话里**dry-run** _subagent_deep_search.md 的模版构造一次（不实际 dispatch，只验证 prompt 文本结构能 fill），打印出来给用户看。

### Task 4.6：Phase 4 收尾

- [ ] **Step 1：跑全部 test**

```bash
cd /Users/yangqi/investing
python -m pytest prism/scripts/ -v 2>&1 | tail -30
```

Expected: 无回归。

- [ ] **Step 2：detect_changes**

```bash
gitnexus_detect_changes()
```

- [ ] **Step 3：commit**

```bash
git add prism/workflows/_subagent_deep_search.md prism/workflows/_subagent_fetch_material.md prism/workflows/03-extract-findings.md prism/workflows/05-critic-review.md scripts/fetch_report_prism.py
git commit -m "$(cat <<'EOF'
feat(prism): sub-agent 深挖循环 + 下载脚本 LLM 工具化

新增 _subagent_deep_search.md / _subagent_fetch_material.md 模版（含
防写文件幻觉硬规约）。03/05 在即兴 web-search 不够时升级为 dispatch
sub-agent 跑多轮深挖，零外部 API 费用。fetch_report_prism 文件头加
dispatch 用法 docstring。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 4：最终汇报**

```
✅ Phase 4 完成 — 全部 7 项能力扩展落地

  Phase 1: register_web_search_batch helper / WHITELIST x150
  Phase 2: 03/04/05 接入即兴 web-search
  Phase 3: gap_detector + 训练知识 baseline
  Phase 4: sub-agent 深挖循环 + 脚本工具化 docstring

下一步建议（不在本 plan 范围）：
  - 在 dashboard 加 "LLM 求知进度 / sub-agent dispatched 累计" 卡
  - 跑 1-2 个真实 topic 验证全链路（特别是 sub-agent 深挖在 critic 缺口下的实际行为）
  - 观察 2-4 周后看是否需要 H 路线（外部 Serper/Tavily API）
```

---

## Self-Review Checklist

执行前自查（writing-plans skill 要求）：

**1. Spec coverage** — 7 项能力是否全有任务？
- [x] 项 1：03/04/05 接 web-search → Phase 2 Task 2.1/2.2/2.3
- [x] 项 2：一行 helper → Phase 1 Task 1.2/1.3
- [x] 项 3：下载脚本 LLM tool → Phase 4 Task 4.3/4.4
- [x] 项 4：gap detector → Phase 3 Task 3.1/3.2
- [x] 项 5：训练知识 baseline → Phase 3 Task 3.3/3.4
- [x] 项 6：信号源扩展 → Phase 1 Task 1.4
- [x] 项 7（H）：sub-agent 深挖 → Phase 4 Task 4.1/4.2

**2. Placeholder scan** — 无 TBD / 无 "implement later" / 无 "fill in details"。code 块均为可粘贴可执行内容，commit message 已用 heredoc 格式写好。

**3. Type consistency** — `register_web_search_batch` 在 Task 1.2 测试用 `summary["n_high"]`，Task 1.3 实现也是 `n_high`。`detect_gaps` 测试 / 实现 / format_summary 字段名一致（uncovered_ks / thin_evidence / expired_web_materials）。

**4. 风险红线再确认**：
- 修 web_prescan.py 前必须跑 gitnexus_impact（Task 1.1 已包含）
- 提交前必须跑 detect_changes（每个 phase 收尾步骤已包含）
- sub-agent prompt 必须嵌防写文件硬规约（Task 4.1 / 4.2 已写明）
- 不改决策权（用户仍主导 thesis 升版 / 最终判断）—— 全程不修改 set_thesis / set_critic_verdict 的语义

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-05-26-prism-websearch-capabilities.md`.**

执行选择（用户已表态"分阶段确认"，建议）：

**Inline Execution — 分阶段执行**（推荐）

- Phase 1（基础设施）跑完 → 用户确认 → Phase 2
- Phase 2（03/04/05 接入）跑完 → 用户确认 → Phase 3
- Phase 3（gap + baseline）跑完 → 用户确认 → Phase 4
- Phase 4（sub-agent 深挖 + 脚本工具化）跑完 → 整体收尾

每个 phase 收尾会跑 detect_changes + 汇报，用户回复"继续" / "调整" / "停"任一可控。
