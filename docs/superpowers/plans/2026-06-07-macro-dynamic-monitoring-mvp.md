# 宏观层动态监控 · 第二期 MVP 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把静态一次性的宏观层升级为「输入完整登记（带机制字段、可审计）+ 按节奏扫描 + 行情型突变报警 + 由用户在 web 端触发重判」的活框架的 MVP 骨架。

**Architecture:** 新建一个**专属输入登记表** `macro_inputs.yaml` + 零-LLM CRUD 模块 `prism/scripts/macro_registry.py`（与 materials 的 `manifest.py` 分离，互不污染）；登记表带 §2.2 机制字段并由 validator 强制「tier A ⟹ 因果机制」纪律；扩 `monitor.py` 让 daily-monitor 认识 macro topic，对登记表做「事件/描述到期 + 行情型 alert_series 越带」分桶并写 `kind=macro_input` proposal 进既有 queue（确认永远人触发）；改 `_macro_regime.md` 合成规范吸收机制纠错与多维/fragility 读数；扩 `transmission_map.yaml` 契约与 `dashboard.py` banner 渲染多维读数 + 新鲜度/regime-decay 指示。抓取脚本（FRED 自动等）属第二步，本期不做——登记与抓取解耦。

**Tech Stack:** Python 3（pytest，零 LLM 脚本，PyYAML），prism 既有 monitor/dashboard/topic 机器，markdown workflow 规范。

**源真相：** 输入全集与机制字段以 `docs/superpowers/specs/2026-06-07-macro-dynamic-monitoring-and-maturation-design.md` 的 §2、§3、§5、§6 为准（下称「spec」）。

**项目铁律（每个改既有符号的任务都要遵守，已写进相应步骤）：**
- 改任何既有 function/method 前先跑 `gitnexus_impact({target, direction:"upstream"})` 并报告爆炸半径；HIGH/CRITICAL 必须先告警。
- 提交前跑 `gitnexus_detect_changes()` 核对影响范围。
- 每个任务用**显式 `git add <精确文件>`**，**绝不 `git add -A`**（仓库有 baijiu/popmart 等无关 WIP 不得卷入）。
- commit message 结尾加 `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`。

**枚举约定（代码用 ASCII，人读串用中文）：**
- `tier` ∈ `{"A","B","C"}`
- `cadence_type` ∈ `{"event","series","policy"}`（= spec 的 事/行/述）
- `mechanism` ∈ `{"CD","CF","CO","CR"}`
- `importance` ∈ `{"load_bearing","confirming","background"}`（= spec 的 承重/确认/背景）
- `alert_series` ∈ `{true,false}`

---

### Task 1: 登记表读写模块骨架 `macro_registry.py`

**Files:**
- Create: `prism/scripts/macro_registry.py`
- Test: `prism/scripts/test_macro_registry.py`

- [ ] **Step 1: 写失败测试 — create + read 往返**

Create `prism/scripts/test_macro_registry.py`:

```python
"""macro 输入登记表（macro_inputs.yaml）CRUD + 机制纪律 validator。零 LLM。"""
import shutil
import tempfile
from pathlib import Path

import pytest

from prism.scripts import macro_registry as mr

SLUG = "global-macro-rates-liquidity"
VARIANT = "opus4.8"


@pytest.fixture
def reg_env(monkeypatch):
    tmpdir = Path(tempfile.mkdtemp())
    monkeypatch.setattr("prism.scripts.macro_registry._PRISM_ROOT", tmpdir)
    (tmpdir / "topics" / SLUG / VARIANT).mkdir(parents=True)
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


def test_create_and_read_roundtrip(reg_env):
    path = mr.create_registry(SLUG, VARIANT)
    assert path.exists()
    data = mr.read_registry(SLUG, VARIANT)
    assert data["slug"] == SLUG
    assert data["variant"] == VARIANT
    assert data["inputs"] == []
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest prism/scripts/test_macro_registry.py::test_create_and_read_roundtrip -v`
Expected: FAIL with `ModuleNotFoundError` 或 `AttributeError: module 'prism.scripts.macro_registry' has no attribute 'create_registry'`

- [ ] **Step 3: 写最小实现**

Create `prism/scripts/macro_registry.py`:

```python
"""宏观层输入登记表（macro_inputs.yaml）的零-LLM CRUD + 机制纪律 validator。

与 manifest.py（materials 库）刻意分离：manifest 存"资料/搜索 hit"，本模块存
"会影响利率/流动性/汇率判断的输入"及其机制边（spec §2.2）。登记与抓取解耦——
本模块只管登记 + 观测值落盘 + 机制校验；FRED 自动抓等是第二期的事。

登记表 schema：
  slug, variant, updated, inputs: [ {input entry}, ... ]
每条 input entry（spec §2.2 + 运行时观测位）：
  name           中文输入名（唯一键）
  tier           "A"|"B"|"C"
  cadence_type   "event"|"series"|"policy"   (事/行/述)
  targets        ["rates"|"liquidity"|"fx", ...]
  mechanism      "CD"|"CF"|"CO"|"CR"
  causal_sentence  一句话因果链（CD/CF 必填）
  lag            领先/同步/滞后 + 时长（自由文本）
  importance     "load_bearing"|"confirming"|"background"
  source         FRED / web / PBoC / ... / TBD
  fetch_method   fred-api / llm-web / manual / TBD
  state          "已有"|"新增"|"改"
  alert_series   bool（仅 series 可为 true）
  monitoring     {enabled: bool}            缺省视为 enabled=true
  alert_band     {delta: float} 或 {z: float}   仅 alert_series 用
  observed       {value, prev_value, z, as_of, next_due, last_proposed_value}  运行时位（fetcher/monitor 写）
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import yaml

_PRISM_ROOT = Path(__file__).resolve().parent.parent

VALID_TIER = ("A", "B", "C")
VALID_CADENCE = ("event", "series", "policy")
VALID_MECHANISM = ("CD", "CF", "CO", "CR")
VALID_IMPORTANCE = ("load_bearing", "confirming", "background")
VALID_TARGET = ("rates", "liquidity", "fx")


def _registry_path(slug: str, variant: str) -> Path:
    if not variant:
        raise ValueError("必须显式指定 variant")
    return _PRISM_ROOT / "topics" / slug / variant / "macro_inputs.yaml"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _write_yaml(path: Path, data: dict) -> None:
    path.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def create_registry(slug: str, variant: str) -> Path:
    path = _registry_path(slug, variant)
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_yaml(path, {"slug": slug, "variant": variant, "updated": _now_iso(), "inputs": []})
    return path


def read_registry(slug: str, variant: str) -> dict:
    path = _registry_path(slug, variant)
    if not path.exists():
        raise FileNotFoundError(f"macro_inputs.yaml not found: {slug}/{variant}")
    return _read_yaml(path)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python3 -m pytest prism/scripts/test_macro_registry.py::test_create_and_read_roundtrip -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add prism/scripts/macro_registry.py prism/scripts/test_macro_registry.py
git commit -m "feat(prism): macro_registry 模块骨架 — 输入登记表 create/read

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: 登记 + upsert input + 机制纪律 validator

**Files:**
- Modify: `prism/scripts/macro_registry.py`
- Test: `prism/scripts/test_macro_registry.py`

- [ ] **Step 1: 写失败测试 — upsert + validator 纪律**

Append to `prism/scripts/test_macro_registry.py`:

```python
def _good_A_entry():
    return {
        "name": "非农就业 NFP", "tier": "A", "cadence_type": "event",
        "targets": ["rates", "fx"], "mechanism": "CD",
        "causal_sentence": "就业超预期 → Fed 维持限制性政策更久 → 短端利率↑",
        "lag": "同步", "importance": "load_bearing",
        "source": "FRED", "fetch_method": "fred-api", "state": "改",
        "alert_series": False,
    }


def test_upsert_input_adds_and_is_idempotent(reg_env):
    mr.create_registry(SLUG, VARIANT)
    mr.upsert_input(SLUG, VARIANT, _good_A_entry())
    data = mr.read_registry(SLUG, VARIANT)
    assert [i["name"] for i in data["inputs"]] == ["非农就业 NFP"]
    # 同名再 upsert → 覆盖字段，不新增一行
    e = _good_A_entry()
    e["importance"] = "confirming"
    mr.upsert_input(SLUG, VARIANT, e)
    data = mr.read_registry(SLUG, VARIANT)
    assert len(data["inputs"]) == 1
    assert data["inputs"][0]["importance"] == "confirming"


def test_validator_passes_clean_registry(reg_env):
    mr.create_registry(SLUG, VARIANT)
    mr.upsert_input(SLUG, VARIANT, _good_A_entry())
    errors = mr.validate_registry(SLUG, VARIANT)
    assert errors == []


def test_tier_A_requires_causal_mechanism(reg_env):
    mr.create_registry(SLUG, VARIANT)
    bad = _good_A_entry()
    bad["mechanism"] = "CO"          # tier A 不允许 CO
    mr.upsert_input(SLUG, VARIANT, bad)
    errors = mr.validate_registry(SLUG, VARIANT)
    assert any("tier A" in e and "CD/CF" in e for e in errors)


def test_causal_mechanism_requires_sentence(reg_env):
    mr.create_registry(SLUG, VARIANT)
    bad = _good_A_entry()
    bad["causal_sentence"] = ""       # CD 必须有因果句
    mr.upsert_input(SLUG, VARIANT, bad)
    errors = mr.validate_registry(SLUG, VARIANT)
    assert any("causal_sentence" in e for e in errors)


def test_alert_series_only_on_series(reg_env):
    mr.create_registry(SLUG, VARIANT)
    bad = _good_A_entry()             # cadence_type=event 不能 alert_series
    bad["alert_series"] = True
    mr.upsert_input(SLUG, VARIANT, bad)
    errors = mr.validate_registry(SLUG, VARIANT)
    assert any("alert_series" in e and "series" in e for e in errors)


def test_enum_validation(reg_env):
    mr.create_registry(SLUG, VARIANT)
    bad = _good_A_entry()
    bad["tier"] = "Z"
    mr.upsert_input(SLUG, VARIANT, bad)
    errors = mr.validate_registry(SLUG, VARIANT)
    assert any("tier" in e for e in errors)
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest prism/scripts/test_macro_registry.py -v -k "upsert or validator or tier_A or causal or alert_series or enum"`
Expected: FAIL（`AttributeError: ... 'upsert_input'`）

- [ ] **Step 3: 实现 upsert_input + validate_registry**

Append to `prism/scripts/macro_registry.py`:

```python
def upsert_input(slug: str, variant: str, entry: dict) -> None:
    """按 name 唯一键 upsert 一条 input（无校验，校验交 validate_registry）。零 LLM。"""
    if not entry.get("name"):
        raise ValueError("input entry 必须有 name")
    data = read_registry(slug, variant)
    for i, existing in enumerate(data["inputs"]):
        if existing["name"] == entry["name"]:
            data["inputs"][i] = {**existing, **entry}
            break
    else:
        data["inputs"].append(entry)
    data["updated"] = _now_iso()
    _write_yaml(_registry_path(slug, variant), data)


def validate_registry(slug: str, variant: str) -> list[str]:
    """校验登记表的机制纪律（spec §2.2/§2.1）。返回错误串列表（空=通过）。零 LLM。

    规则：
      - 枚举合法：tier/cadence_type/mechanism/importance/targets。
      - tier A ⟹ mechanism ∈ {CD, CF}（CO/CR 只能 B/C）。
      - mechanism ∈ {CD, CF} ⟹ causal_sentence 非空。
      - alert_series=True ⟹ cadence_type == "series"。
      - name 不可重复。
    """
    data = read_registry(slug, variant)
    errors: list[str] = []
    seen: set[str] = set()
    for e in data["inputs"]:
        name = e.get("name", "<无名>")
        if name in seen:
            errors.append(f"[{name}] name 重复")
        seen.add(name)
        if e.get("tier") not in VALID_TIER:
            errors.append(f"[{name}] tier 非法: {e.get('tier')!r}")
        if e.get("cadence_type") not in VALID_CADENCE:
            errors.append(f"[{name}] cadence_type 非法: {e.get('cadence_type')!r}")
        if e.get("mechanism") not in VALID_MECHANISM:
            errors.append(f"[{name}] mechanism 非法: {e.get('mechanism')!r}")
        if e.get("importance") not in VALID_IMPORTANCE:
            errors.append(f"[{name}] importance 非法: {e.get('importance')!r}")
        for t in e.get("targets") or []:
            if t not in VALID_TARGET:
                errors.append(f"[{name}] target 非法: {t!r}")
        # 因果纪律
        if e.get("tier") == "A" and e.get("mechanism") not in ("CD", "CF"):
            errors.append(f"[{name}] tier A 必须 mechanism ∈ CD/CF，得到 {e.get('mechanism')!r}")
        if e.get("mechanism") in ("CD", "CF") and not (e.get("causal_sentence") or "").strip():
            errors.append(f"[{name}] mechanism={e.get('mechanism')} 必须填 causal_sentence")
        if e.get("alert_series") and e.get("cadence_type") != "series":
            errors.append(f"[{name}] alert_series=True 仅允许 cadence_type=series")
    return errors
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python3 -m pytest prism/scripts/test_macro_registry.py -v`
Expected: PASS（全部）

- [ ] **Step 5: 提交**

```bash
git add prism/scripts/macro_registry.py prism/scripts/test_macro_registry.py
git commit -m "feat(prism): macro_registry upsert + 机制纪律 validator

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: 用 spec §3 全集 seed `macro_inputs.yaml` + 无遗漏完整性测试

**Files:**
- Create: `prism/topics/global-macro-rates-liquidity/opus4.8/macro_inputs.yaml`
- Create: `prism/scripts/seed_macro_inputs.py`
- Test: `prism/scripts/test_macro_inputs_seed.py`

> 这是 spec §3 表（约 114 行）的逐行转录。每行的「输入」列去掉 `**` 与首尾空白后即 registry `name`；层/型/目标/机制/来源/重要度/状态映射到上面枚举；`causal_sentence` 取 spec §5/§3 的机制句（CD/CF 必填，可一句话概括该输入如何影响目标）；`alert_series=true` 仅给 spec §4.3 的六条：MOVE / HY OAS / 跨币种基差 / USDJPY-日元carry / CNH-CNY 价差 / DR007。

- [ ] **Step 1: 写完整性失败测试（spec 为真相源，保证无遗漏）**

Create `prism/scripts/test_macro_inputs_seed.py`:

```python
"""无遗漏闸：macro_inputs.yaml 必须覆盖 spec §3 表的每一行，且通过机制 validator。

源真相 = spec 文件的 §3 表。本测试解析 spec §3 各表的"输入"列（首列），断言每个
输入名都在登记表里出现（去 ** 与空白后比对）。这把"框架完整性"钉死在外部文档上，
直接兑现用户"输入不能有遗漏"的硬要求。
"""
import re
from pathlib import Path

import pytest

from prism.scripts import macro_registry as mr

SLUG = "global-macro-rates-liquidity"
VARIANT = "opus4.8"
_ROOT = Path(__file__).resolve().parent.parent.parent
SPEC = _ROOT / "docs/superpowers/specs/2026-06-07-macro-dynamic-monitoring-and-maturation-design.md"


def _clean(cell: str) -> str:
    return cell.replace("**", "").strip()


def _spec_input_names() -> list[str]:
    """抽 §3 各表首列输入名。§3 起于 '## 3.'，止于 '## 4.'。"""
    text = SPEC.read_text(encoding="utf-8")
    start = text.index("## 3. ")
    end = text.index("## 4. ")
    block = text[start:end]
    names: list[str] = []
    for line in block.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c for c in line.split("|")]
        # 去掉首尾空串
        cells = cells[1:-1] if len(cells) >= 2 else cells
        if not cells:
            continue
        first = _clean(cells[0])
        # 跳过表头与分隔行
        if first in ("输入", "") or set(first) <= set("-: "):
            continue
        names.append(first)
    return names


def test_spec_block_parsing_sane():
    names = _spec_input_names()
    # §3 表约 114 行；低于 110 说明解析漏了块或 spec 被改瘦
    assert len(names) >= 110, f"只解析到 {len(names)} 个输入名，疑似漏块"
    assert "非农就业 NFP" in names
    assert "结售汇 + 外汇占款 + 代客涉外收付" in names


def test_registry_covers_every_spec_input():
    reg_names = {i["name"] for i in mr.read_registry(SLUG, VARIANT)["inputs"]}
    missing = [n for n in _spec_input_names() if n not in reg_names]
    assert missing == [], f"登记表遗漏 {len(missing)} 个 spec 输入：{missing}"


def test_seed_registry_passes_validator():
    errors = mr.validate_registry(SLUG, VARIANT)
    assert errors == [], f"登记表机制纪律不过：{errors}"


def test_six_alert_series_marked():
    inputs = mr.read_registry(SLUG, VARIANT)["inputs"]
    alert = {i["name"] for i in inputs if i.get("alert_series")}
    expected = {
        "MOVE 债市波动率", "HY OAS", "跨币种基差(EUR/JPY-USD)",
        "USDJPY / 日元 carry", "CNH-CNY 价差", "DR007/R007",
    }
    assert expected <= alert, f"报警序列缺：{expected - alert}"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest prism/scripts/test_macro_inputs_seed.py -v`
Expected: `test_spec_block_parsing_sane` PASS（spec 已在仓库）；其余因登记表不存在/为空而 FAIL（`FileNotFoundError` 或 missing 非空）

- [ ] **Step 3: 写 seed 脚本，逐行转录 spec §3**

Create `prism/scripts/seed_macro_inputs.py`. 用下面的 helper + 把 spec §3 每行写成一个 `upsert_input` 调用。**示例覆盖全部 cadence_type / mechanism / tier / alert 组合**，其余行照同样规则转录（输入名 = spec 首列去 `**`；causal_sentence 对 CD/CF 必填，可据 spec §3 机制列/§5 概括）：

```python
"""一次性 seed：把 spec §3 全集写进 macro_inputs.yaml。零 LLM。可重复运行（upsert 幂等）。

运行：  python3 -m prism.scripts.seed_macro_inputs
"""
from prism.scripts import macro_registry as mr

SLUG = "global-macro-rates-liquidity"
VARIANT = "opus4.8"


def E(name, tier, cadence_type, targets, mechanism, importance, source,
      fetch_method, state, causal_sentence="", lag="同步", alert_series=False,
      alert_band=None):
    e = {
        "name": name, "tier": tier, "cadence_type": cadence_type,
        "targets": targets, "mechanism": mechanism, "importance": importance,
        "source": source, "fetch_method": fetch_method, "state": state,
        "causal_sentence": causal_sentence, "lag": lag,
        "alert_series": alert_series, "monitoring": {"enabled": True},
    }
    if alert_band:
        e["alert_band"] = alert_band
    return e


# 转录规则：
#   层 A/B/C → tier；型 事/行/述 → event/series/policy；
#   目标 R/L/FX → rates/liquidity/fx；机制 CD/CF/CO/CR 原样；
#   重要度 承重/确认/背景 → load_bearing/confirming/background；状态原样。
#   alert_band：六条报警序列先给占位粗档（spec §11 待用户回填精值），
#   delta 为"n 日绝对变动阈值"，z 为"z-score 阈值"。
INPUTS = [
    # ── §3.1 美国 增长/通胀/政策 ─────────────────────────────────────────
    E("联邦基金目标区间", "A", "event", ["rates", "liquidity", "fx"], "CD",
      "load_bearing", "FRED", "fred-api", "已有",
      "政策利率是所有资产贴现率的锚 → 直接定利率体制", "同步"),
    E("非农就业 NFP", "A", "event", ["rates", "fx"], "CD",
      "load_bearing", "FRED", "fred-api", "改",
      "就业超预期 → Fed 维持限制性更久 → 短端利率↑、美元偏强", "同步(月)"),
    E("核心 PCE", "A", "event", ["rates"], "CD",
      "load_bearing", "FRED", "fred-api", "新增",
      "核心通胀超预期 → 推迟降息 → 短端利率↑（分期限：长端可反向，触发用超预期非水平）",
      "滞后(月)"),
    # ── §3.3 利率市场/信用/波动率（含 series + alert）─────────────────────
    E("MOVE 债市波动率", "B", "series", ["rates", "liquidity"], "CO",
      "load_bearing", "web", "llm-web", "新增",
      lag="同步", alert_series=True, alert_band={"z": 2.0}),
    E("HY OAS", "B", "series", ["liquidity"], "CO",
      "load_bearing", "FRED", "fred-api", "改",
      lag="同步", alert_series=True, alert_band={"delta": 75.0}),  # bp
    # ── §3.4 美元/全球流动性（CF 资金流渠道 + alert）──────────────────────
    E("跨币种基差(EUR/JPY-USD)", "A", "series", ["liquidity", "fx"], "CF",
      "load_bearing", "web", "llm-web", "改",
      "美元融资紧张 → 基差走负 → 离岸美元流动性收缩 → 全球风险资产承压",
      "领先", alert_series=True, alert_band={"delta": 25.0}),  # bp
    E("USDJPY / 日元 carry", "A", "series", ["liquidity", "fx"], "CF",
      "load_bearing", "FRED", "fred-api", "改",
      "日元急升 → carry 平仓 → 全球去杠杆（条件/阈值尾部触发）",
      "领先", alert_series=True, alert_band={"z": 2.5}),
    E("比特币", "C", "series", ["liquidity"], "CR",
      "background", "web", "llm-web", "已有", lag="同步"),  # CR：仅相关，C 层无因果句
    # ── §3.6/§3.8 中国（CD + CF + alert DR007）────────────────────────────
    E("DR007/R007", "A", "series", ["liquidity", "rates"], "CO",
      "load_bearing", "CFETS", "llm-web", "已有",
      lag="同步", alert_series=True, alert_band={"delta": 30.0}),  # bp
    E("CNH-CNY 价差", "A", "series", ["fx"], "CF",
      "load_bearing", "web", "llm-web", "已有",
      "离岸贬值预期 → CNH 弱于 CNY → 资本外流压力",
      "领先", alert_series=True, alert_band={"delta": 0.015}),  # 元
    E("结售汇 + 外汇占款 + 代客涉外收付", "A", "event", ["fx"], "CF",
      "load_bearing", "SAFE", "TBD", "新增",
      "结售汇逆差 → 实需购汇压人民币 + 外汇占款收缩境内流动性", "滞后(月)"),
    # ── §3.10 类别尾部（policy + always-alert）────────────────────────────
    E("中美地缘/关税", "A", "policy", ["fx", "liquidity"], "CD",
      "load_bearing", "web", "llm-web", "新增",
      "关税/制裁升级 → 风险溢价↑ + 人民币贬压（headline 驱动，always-alert）", "领先"),
    E("ADR 退市/HFCAA/PCAOB", "A", "policy", ["fx", "liquidity"], "CD",
      "load_bearing", "web", "llm-web", "新增",
      "退市风险升 → 中概强制资金外流 + 折价（always-alert）", "领先"),
    # …… 其余 spec §3 所有行照此规则继续转录，直到覆盖 §3.1–§3.10 全部约 114 行。
    # 不得遗漏；test_registry_covers_every_spec_input 会逐行核对。
]


def main():
    try:
        mr.read_registry(SLUG, VARIANT)
    except FileNotFoundError:
        mr.create_registry(SLUG, VARIANT)
    for e in INPUTS:
        mr.upsert_input(SLUG, VARIANT, e)
    errors = mr.validate_registry(SLUG, VARIANT)
    print(f"seeded {len(INPUTS)} inputs; validator errors: {len(errors)}")
    for err in errors:
        print("  ✗", err)


if __name__ == "__main__":
    main()
```

实现要求（给实现者）：把 `INPUTS` 补全为 spec §3 全集（约 114 条），逐行对照 spec 表；非 CD/CF 的 B/C 行可留空 `causal_sentence`；CD/CF 行必须给一句因果链；六条 `alert_series=True` 行各带占位 `alert_band`（具体精值列入 spec §11 待用户回填）。

- [ ] **Step 4: 运行 seed 脚本并跑测试确认通过**

Run:
```bash
python3 -m prism.scripts.seed_macro_inputs
python3 -m pytest prism/scripts/test_macro_inputs_seed.py -v
```
Expected: seed 打印 `validator errors: 0`；测试全 PASS（尤其 `test_registry_covers_every_spec_input` 的 `missing == []`）

- [ ] **Step 5: 提交**

```bash
git add prism/scripts/seed_macro_inputs.py prism/scripts/test_macro_inputs_seed.py prism/topics/global-macro-rates-liquidity/opus4.8/macro_inputs.yaml
git commit -m "feat(prism): seed 宏观输入登记表全集（spec §3，~114 项）+ 无遗漏闸

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: 观测值落盘 CRUD `record_observation`

**Files:**
- Modify: `prism/scripts/macro_registry.py`
- Test: `prism/scripts/test_macro_registry.py`

> 这是 fetcher（第二期）与 monitor 共用的运行时写入口：把一次观测值写进某 input 的 `observed`，并把旧 `value` 滚成 `prev_value`（series 越带探测要前后值）。本期由测试与手工 seed 行使。

- [ ] **Step 1: 写失败测试**

Append to `prism/scripts/test_macro_registry.py`:

```python
def test_record_observation_rolls_prev_value(reg_env):
    mr.create_registry(SLUG, VARIANT)
    mr.upsert_input(SLUG, VARIANT, _good_A_entry())
    mr.record_observation(SLUG, VARIANT, "非农就业 NFP", value=150.0, as_of="2026-05-02")
    mr.record_observation(SLUG, VARIANT, "非农就业 NFP", value=90.0, as_of="2026-06-06")
    obs = {i["name"]: i["observed"] for i in mr.read_registry(SLUG, VARIANT)["inputs"]}["非农就业 NFP"]
    assert obs["value"] == 90.0
    assert obs["prev_value"] == 150.0
    assert obs["as_of"] == "2026-06-06"


def test_record_observation_unknown_name_raises(reg_env):
    mr.create_registry(SLUG, VARIANT)
    with pytest.raises(ValueError):
        mr.record_observation(SLUG, VARIANT, "不存在", value=1.0, as_of="2026-06-06")
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest prism/scripts/test_macro_registry.py -v -k record_observation`
Expected: FAIL（`AttributeError: ... 'record_observation'`）

- [ ] **Step 3: 实现 record_observation**

Append to `prism/scripts/macro_registry.py`:

```python
def record_observation(
    slug: str, variant: str, name: str, *,
    value: float | None = None, as_of: str | None = None,
    z: float | None = None, next_due: str | None = None,
) -> None:
    """把一次观测写进某 input 的 observed；旧 value 滚成 prev_value。零 LLM。

    fetcher（第二期）每次抓到新值调本函数；monitor 据 observed 判越带/到期。
    value 给定时滚动 prev_value；z/next_due 给定则覆盖对应位。
    """
    data = read_registry(slug, variant)
    for e in data["inputs"]:
        if e["name"] == name:
            obs = dict(e.get("observed") or {})
            if value is not None:
                if "value" in obs:
                    obs["prev_value"] = obs["value"]
                obs["value"] = value
            if as_of is not None:
                obs["as_of"] = as_of
            if z is not None:
                obs["z"] = z
            if next_due is not None:
                obs["next_due"] = next_due
            obs["checked_at"] = _now_iso()
            e["observed"] = obs
            data["updated"] = _now_iso()
            _write_yaml(_registry_path(slug, variant), data)
            return
    raise ValueError(f"input {name!r} 不在登记表中")
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python3 -m pytest prism/scripts/test_macro_registry.py -v`
Expected: PASS（全部）

- [ ] **Step 5: 提交**

```bash
git add prism/scripts/macro_registry.py prism/scripts/test_macro_registry.py
git commit -m "feat(prism): macro_registry record_observation（观测落盘+滚动 prev_value）

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: 纯函数 `scan_macro_inputs` — 到期/越带分桶

**Files:**
- Modify: `prism/scripts/macro_registry.py`
- Test: `prism/scripts/test_macro_registry.py`

> 纯函数（不读文件、传入 registry dict + today），把登记表分桶成 `due_event` / `due_policy` / `alert_series` / `unparseable`。规则见 docstring；行情型非 alert_series 一律不进桶（守住"小动只显示不打扰"）。

- [ ] **Step 1: 写失败测试**

Append to `prism/scripts/test_macro_registry.py`:

```python
from datetime import date


def test_scan_macro_inputs_buckets():
    reg = {"inputs": [
        # event 到期（next_due 已过）
        {"name": "NFP", "cadence_type": "event", "tier": "A", "importance": "load_bearing",
         "monitoring": {"enabled": True}, "observed": {"next_due": "2026-06-01"}},
        # event 未到期
        {"name": "零售", "cadence_type": "event", "monitoring": {"enabled": True},
         "observed": {"next_due": "2026-12-31"}},
        # policy 到期
        {"name": "FOMC声明", "cadence_type": "policy", "tier": "A", "importance": "load_bearing",
         "monitoring": {"enabled": True}, "observed": {"next_due": "2026-06-05"}},
        # series alert_series 越 delta 带
        {"name": "HY OAS", "cadence_type": "series", "alert_series": True, "tier": "B",
         "importance": "load_bearing", "monitoring": {"enabled": True},
         "alert_band": {"delta": 75.0}, "observed": {"value": 400.0, "prev_value": 300.0}},
        # series alert_series 未越带
        {"name": "MOVE", "cadence_type": "series", "alert_series": True,
         "monitoring": {"enabled": True}, "alert_band": {"z": 2.0},
         "observed": {"z": 1.0}},
        # series 非 alert（即便大动也不进桶）
        {"name": "比特币", "cadence_type": "series", "alert_series": False,
         "monitoring": {"enabled": True}, "observed": {"value": 100.0, "prev_value": 10.0}},
        # 日期坏 → unparseable
        {"name": "坏日期", "cadence_type": "event", "monitoring": {"enabled": True},
         "observed": {"next_due": "soon"}},
        # monitoring 关 → 跳过
        {"name": "关掉的", "cadence_type": "event", "monitoring": {"enabled": False},
         "observed": {"next_due": "2026-06-01"}},
    ]}
    out = mr.scan_macro_inputs(reg, today=date(2026, 6, 7))
    assert {x["name"] for x in out["due_event"]} == {"NFP"}
    assert {x["name"] for x in out["due_policy"]} == {"FOMC声明"}
    assert {x["name"] for x in out["alert_series"]} == {"HY OAS"}
    assert {u["name"] for u in out["unparseable"]} == {"坏日期"}
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest prism/scripts/test_macro_registry.py::test_scan_macro_inputs_buckets -v`
Expected: FAIL（`AttributeError: ... 'scan_macro_inputs'`）

- [ ] **Step 3: 实现 scan_macro_inputs**

Append to `prism/scripts/macro_registry.py`（顶部已 import datetime；补一个日期解析 helper）：

```python
def _parse_date(s):
    from datetime import date as _date
    if not s:
        return None
    try:
        return _date.fromisoformat(str(s))
    except (ValueError, TypeError):
        return None


def _series_breached(entry: dict) -> bool:
    """alert_series 是否越带：delta=|value-prev_value|≥band.delta；z=|observed.z|≥band.z。"""
    band = entry.get("alert_band") or {}
    obs = entry.get("observed") or {}
    if "delta" in band:
        v, p = obs.get("value"), obs.get("prev_value")
        if v is not None and p is not None:
            return abs(v - p) >= band["delta"]
    if "z" in band:
        z = obs.get("z")
        if z is not None:
            return abs(z) >= band["z"]
    return False


def scan_macro_inputs(registry: dict, today=None) -> dict:
    """纯函数：把登记表分桶。不读文件。零 LLM。

    返回 {due_event, due_policy, alert_series, unparseable}，每项是 input entry 的浅拷贝。
    规则：
      - monitoring.enabled is False → 跳过。
      - cadence_type=event/policy：observed.next_due 可解析且 ≤ today → due_*；不可解析 → unparseable。
      - cadence_type=series 且 alert_series=True 且 _series_breached → alert_series。
      - 其余（含非 alert 的 series 小动）→ 不进任何桶。
    """
    from datetime import date as _date
    today = today or _date.today()
    out = {"due_event": [], "due_policy": [], "alert_series": [], "unparseable": []}
    for e in registry.get("inputs") or []:
        if (e.get("monitoring") or {}).get("enabled") is False:
            continue
        ctype = e.get("cadence_type")
        if ctype in ("event", "policy"):
            nd_raw = (e.get("observed") or {}).get("next_due")
            if nd_raw is None:
                continue  # 还没排期，不报
            d = _parse_date(nd_raw)
            if d is None:
                out["unparseable"].append(dict(e))
            elif d <= today:
                out["due_event" if ctype == "event" else "due_policy"].append(dict(e))
        elif ctype == "series" and e.get("alert_series") and _series_breached(e):
            out["alert_series"].append(dict(e))
    return out
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python3 -m pytest prism/scripts/test_macro_registry.py -v`
Expected: PASS（全部）

- [ ] **Step 5: 提交**

```bash
git add prism/scripts/macro_registry.py prism/scripts/test_macro_registry.py
git commit -m "feat(prism): scan_macro_inputs — 到期/越带分桶纯函数

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: 把 macro 分支接进 `monitor.scan_due_events`

**Files:**
- Modify: `prism/scripts/monitor.py:172-263`（`scan_due_events`）
- Test: `prism/scripts/test_monitor_macro.py`（新建）

> macro topic 无 `07_decision_kit.yaml`；要在 sidecar 加载**之前**截流，调 `macro_registry.scan_macro_inputs` 并把结果挂到 scan 输出的新桶 `macro_due` / `macro_alert`。watchlist 仍是成本闸（macro topic 不在关注清单则不扫）。

- [ ] **Step 1: 跑 gitnexus 影响分析（铁律）**

```
gitnexus_impact({target: "scan_due_events", direction: "upstream"})
```
把直接调用者 / 受影响流程 / 风险等级报告给用户；若 HIGH/CRITICAL 先告警再继续。预期调用者：`monitor.propose_price_breaches`、`app/monitor_runtime.run_monitor_cycle`、`monitor._print_scan`。

- [ ] **Step 2: 写失败测试**

Create `prism/scripts/test_monitor_macro.py`:

```python
"""macro topic 接进 daily-monitor：scan 多出 macro_due/macro_alert 桶。"""
import shutil
import tempfile
from pathlib import Path

import pytest
import yaml

from prism.scripts import topic as topic_io
from prism.scripts import macro_registry as mr
from prism.scripts import monitor

SLUG = "global-macro-rates-liquidity"
VARIANT = "opus4.8"


@pytest.fixture
def macro_monitor_env(monkeypatch):
    tmpdir = Path(tempfile.mkdtemp())
    monkeypatch.setattr("prism.scripts.topic.PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.dashboard.PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.monitor.PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.monitor.WATCHLIST_PATH", tmpdir / "watchlist.yaml")
    monkeypatch.setattr("prism.scripts.monitor.QUEUE_PATH", tmpdir / "monitor_queue.yaml")
    monkeypatch.setattr("prism.scripts.macro_registry._PRISM_ROOT", tmpdir)
    (tmpdir / "topics").mkdir()
    topic_io.create_topic(
        slug=SLUG, display_name="宏观层", topic_type="macro",
        question="Q", geo="GLOBAL", depth="deep", variant=VARIANT,
        search_terms=["利率"],
    )
    mr.create_registry(SLUG, VARIANT)
    # 一条到期 event + 一条越带 alert series
    mr.upsert_input(SLUG, VARIANT, {
        "name": "NFP", "tier": "A", "cadence_type": "event", "targets": ["rates"],
        "mechanism": "CD", "causal_sentence": "x", "importance": "load_bearing",
        "source": "FRED", "fetch_method": "fred-api", "state": "改",
        "alert_series": False, "monitoring": {"enabled": True},
        "observed": {"next_due": "2026-06-01"},
    })
    mr.upsert_input(SLUG, VARIANT, {
        "name": "HY OAS", "tier": "B", "cadence_type": "series", "targets": ["liquidity"],
        "mechanism": "CO", "importance": "load_bearing", "source": "FRED",
        "fetch_method": "fred-api", "state": "改", "alert_series": True,
        "alert_band": {"delta": 75.0}, "monitoring": {"enabled": True},
        "observed": {"value": 400.0, "prev_value": 300.0},
    })
    yield SLUG, VARIANT, tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


def test_macro_not_scanned_without_watch(macro_monitor_env):
    scan = monitor.scan_due_events(within_days=14)
    assert scan["macro_due"] == []
    assert scan["macro_alert"] == []


def test_macro_scanned_when_watched(macro_monitor_env):
    slug, variant, _ = macro_monitor_env
    monitor.add_watch(slug, scope="topic", variant=variant)
    scan = monitor.scan_due_events(within_days=14)
    assert {x["name"] for x in scan["macro_due"]} == {"NFP"}
    assert {x["name"] for x in scan["macro_alert"]} == {"HY OAS"}
```

- [ ] **Step 3: 跑测试确认失败**

Run: `python3 -m pytest prism/scripts/test_monitor_macro.py -v`
Expected: FAIL（`KeyError: 'macro_due'`）

- [ ] **Step 4: 实现 — 在 scan_due_events 加 macro 桶与分支**

在 `prism/scripts/monitor.py` 顶部 import 区加：

```python
from prism.scripts import macro_registry
```

在 `scan_due_events` 的 `out = {...}` 字典里加两个桶（保持现有键不动）：

```python
    out = {
        "due_signposts": [], "due_kills": [], "price_breach": [],
        "recurring_review": [], "unparseable": [],
        "price_unavailable": [], "skipped_no_sidecar": [],
        "macro_due": [], "macro_alert": [],
    }
```

在 `ttype = _topic_type(slug, variant)` 之后、`if ttype in ("industry", "arena"):` 分支**之前**插入 macro 截流分支：

```python
        # macro：无 07 sidecar，读 macro_inputs 登记表分桶（事件/描述到期 + 行情越带）
        if ttype == "macro":
            try:
                reg = macro_registry.read_registry(slug, variant)
            except FileNotFoundError:
                continue
            mscan = macro_registry.scan_macro_inputs(reg, today=today)
            for x in mscan["due_event"] + mscan["due_policy"]:
                out["macro_due"].append({"slug": slug, "variant": variant, **x})
            for x in mscan["alert_series"]:
                out["macro_alert"].append({"slug": slug, "variant": variant, **x})
            for u in mscan["unparseable"]:
                out["unparseable"].append({"slug": slug, "variant": variant,
                                           "field": "macro_input", "locator": u.get("name")})
            continue
```

- [ ] **Step 5: 跑测试确认通过（含既有 monitor 测试不回归）**

Run:
```bash
python3 -m pytest prism/scripts/test_monitor_macro.py prism/scripts/test_monitor_scan.py -v
```
Expected: PASS（新测试 + 既有 scan 测试全绿）

- [ ] **Step 6: 跑变更检测（铁律）并提交**

```
gitnexus_detect_changes()
```
确认仅触及 `scan_due_events` 与新增桶。然后：

```bash
git add prism/scripts/monitor.py prism/scripts/test_monitor_macro.py
git commit -m "feat(prism): daily-monitor 认识 macro topic — scan 输出 macro_due/macro_alert 桶

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: `propose_macro_updates` + macro_input proposal 经 confirm 落 living_feed

**Files:**
- Modify: `prism/scripts/monitor.py`（新增 `propose_macro_updates`；扩 `confirm_flip` 的 living_feed 默认文案路径）
- Test: `prism/scripts/test_monitor_macro.py`

> macro proposal 是**信息型**：confirm 只追加 living_feed + 盖"建议重判"戳（load_bearing 或 alert），**绝不改 regime_read**。复用既有 `propose_flips` / `confirm_flip`（kind 走通用路径，已天然跳过 sidecar 回写与证据注册）。

- [ ] **Step 1: 写失败测试**

Append to `prism/scripts/test_monitor_macro.py`:

```python
def test_propose_macro_updates_writes_queue(macro_monitor_env):
    slug, variant, _ = macro_monitor_env
    monitor.add_watch(slug, scope="topic", variant=variant)
    res = monitor.propose_macro_updates(within_days=14)
    assert res["added"] == 2  # NFP(due) + HY OAS(alert)
    q = {p["locator"]: p for p in monitor.load_queue()}
    assert "NFP" in q and "HY OAS" in q
    assert q["NFP"]["kind"] == "macro_input"
    # load_bearing → 建议重判
    assert q["NFP"]["requires_thesis_review"] is True
    assert q["NFP"]["living_feed_entry"]  # 预写文案非空


def test_confirm_macro_input_appends_living_feed(macro_monitor_env):
    slug, variant, tmpdir = macro_monitor_env
    monitor.add_watch(slug, scope="topic", variant=variant)
    monitor.propose_macro_updates(within_days=14)
    pid = {p["locator"]: p["proposal_id"] for p in monitor.load_queue()}["HY OAS"]
    out = monitor.confirm_flip(pid)
    assert out["status"] == "confirmed"
    feed = (tmpdir / "topics" / slug / variant / "outputs" / "08_living_feed.md").read_text(encoding="utf-8")
    assert "HY OAS" in feed
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest prism/scripts/test_monitor_macro.py -v -k "propose_macro or confirm_macro"`
Expected: FAIL（`AttributeError: ... 'propose_macro_updates'`）

- [ ] **Step 3: 实现 propose_macro_updates**

在 `prism/scripts/monitor.py` 的 `propose_price_breaches` 之后加：

```python
def propose_macro_updates(within_days: int = 14) -> dict:
    """零 LLM 路径：scan macro 桶 → 写 kind='macro_input' proposal 进 queue。

    macro proposal 是信息型——confirm 只追加 living_feed + 盖"建议重判"戳，
    绝不自动改 regime_read（判断永远人在 web 端触发）。
    importance=load_bearing 或越带 alert → requires_thesis_review=True。
    """
    scan = scan_due_events(within_days=within_days)
    proposals = []
    today_str = date.today().isoformat()
    for item in scan["macro_due"]:
        name = item.get("name", "")
        imp = item.get("importance")
        entry = (
            f"## {today_str} 宏观输入到期：{name}\n"
            f"**来源**：{item.get('source', '—')}（{item.get('cadence_type')}）\n"
            f"**关键信息**：该输入已到发布/排期点，待取新值与旧读数对比\n"
            f"**对已有判断的影响**：{item.get('causal_sentence') or '（见登记表机制句）'}\n"
            f"**当前判断更新**：维持，等用户在 web 端决定是否重判"
        )
        proposals.append({
            "slug": item["slug"], "variant": item["variant"], "kind": "macro_input",
            "locator": name, "proposed_value": "due",
            "living_feed_entry": entry,
            "rationale": f"{name} 到期（{item.get('cadence_type')}）",
            "requires_thesis_review": imp == "load_bearing",
        })
    for item in scan["macro_alert"]:
        name = item.get("name", "")
        obs = item.get("observed") or {}
        entry = (
            f"## {today_str} 宏观承重序列越带：{name}\n"
            f"**来源**：{item.get('source', '—')}（行情型 alert_series）\n"
            f"**关键信息**：最新 {obs.get('value', obs.get('z', '—'))} / 上次 {obs.get('prev_value', '—')}，越预设报警带\n"
            f"**对已有判断的影响**：{item.get('causal_sentence') or '承重序列突变，可能预示体制切换'}\n"
            f"**当前判断更新**：维持，强烈建议用户重判"
        )
        proposals.append({
            "slug": item["slug"], "variant": item["variant"], "kind": "macro_input",
            "locator": name, "proposed_value": "alert",
            "living_feed_entry": entry,
            "rationale": f"{name} 越报警带",
            "requires_thesis_review": True,
        })
    result = propose_flips(proposals)
    result["scanned_macro"] = len(scan["macro_due"]) + len(scan["macro_alert"])
    return result
```

- [ ] **Step 4: 确认 confirm_flip 对 macro_input 无需改动**

阅读 `monitor.py:470-545` 的 `confirm_flip`：`kind` 非 `signpost`/`kill` 时跳过 sidecar 回写；`if kind in ("signpost","kill")` 跳过证据注册；末尾追加 living_feed + 盖 `requires_thesis_review` 戳的逻辑对 `macro_input` 通用适用。**无需改 confirm_flip**。若 Step 5 测试失败再回看。

- [ ] **Step 5: 跑测试确认通过**

Run: `python3 -m pytest prism/scripts/test_monitor_macro.py -v`
Expected: PASS（全部）

- [ ] **Step 6: 提交**

```bash
git add prism/scripts/monitor.py prism/scripts/test_monitor_macro.py
git commit -m "feat(prism): propose_macro_updates — macro_input proposal（信息型，人触发重判）

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: monitor_runtime 巡检循环纳入 macro + CLI 命令

**Files:**
- Modify: `app/monitor_runtime.py`（`run_monitor_cycle` 调 `propose_macro_updates`）
- Modify: `prism/scripts/monitor.py`（`__main__` 加 `macro` 命令）
- Test: `prism/scripts/test_monitor_macro.py`

- [ ] **Step 1: 跑 gitnexus 影响分析（铁律）**

```
gitnexus_impact({target: "run_monitor_cycle", direction: "upstream"})
```
报告爆炸半径（预期：web「立即巡检」按钮 + 定时器 `_loop`）。HIGH/CRITICAL 先告警。

- [ ] **Step 2: 写失败测试（CLI macro 命令产出 JSON）**

Append to `prism/scripts/test_monitor_macro.py`:

```python
import json
import subprocess
import sys


def test_cli_macro_command(macro_monitor_env, monkeypatch):
    # CLI 直接调进程内函数即可验证命令分支存在；这里验证函数签名稳定
    slug, variant, _ = macro_monitor_env
    monitor.add_watch(slug, scope="topic", variant=variant)
    res = monitor.propose_macro_updates(within_days=14)
    assert "scanned_macro" in res
```

- [ ] **Step 3: 跑测试确认通过/失败基线**

Run: `python3 -m pytest prism/scripts/test_monitor_macro.py::test_cli_macro_command -v`
Expected: PASS（`propose_macro_updates` 已在 Task 7 实现；本测试锁定返回含 `scanned_macro`）

- [ ] **Step 4: 给 monitor.py 的 `__main__` 加 `macro` 命令**

在 `prism/scripts/monitor.py` 末尾 `if __name__ == "__main__":` 块的 `elif cmd == "price":` 后加：

```python
    elif cmd == "macro":
        import json
        print(json.dumps(propose_macro_updates(within), ensure_ascii=False, indent=2))
```
并把最后的 usage 串改为 `（支持 scan / price / macro）`。

- [ ] **Step 5: 把 macro 接进 run_monitor_cycle**

阅读 `app/monitor_runtime.py:54-90` 的 `run_monitor_cycle`。在调 `monitor.propose_price_breaches()`（零 LLM 路径）之后、scan 之前，加一段对称的 macro 零-LLM 路径：

```python
        # macro 输入到期/越带（零 LLM）：写 macro_input proposal
        try:
            macro_res = await asyncio.to_thread(monitor.propose_macro_updates)
            _log(f"macro: scanned={macro_res.get('scanned_macro', 0)} "
                 f"added={macro_res.get('added', 0)}")
        except Exception as e:
            _log(f"macro propose failed: {e}")
```
（与既有 price 块同构；`asyncio`/`monitor`/`_log` 均已在该函数作用域内。）

- [ ] **Step 6: 跑测试 + 烟测 CLI**

Run:
```bash
python3 -m pytest prism/scripts/test_monitor_macro.py -v
python3 -m prism.scripts.monitor macro 14
```
Expected: 测试 PASS；CLI 打出 JSON（真实仓库下 macro topic 若未在 watchlist，则 `scanned_macro: 0` —— 正常）

- [ ] **Step 7: 跑变更检测（铁律）并提交**

```
gitnexus_detect_changes()
```

```bash
git add app/monitor_runtime.py prism/scripts/monitor.py prism/scripts/test_monitor_macro.py
git commit -m "feat(prism): 巡检循环纳入 macro 输入 + monitor CLI macro 命令

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9: `transmission_map.yaml` 契约扩展（多维信心 + 象限 + fragility + 类别尾部）

**Files:**
- Modify: `prism/workflows/04-synthesize/_macro_regime.md`（§4 Step 4 的 schema 块）
- Modify: `prism/topics/global-macro-rates-liquidity/opus4.8/outputs/transmission_map.yaml`（按新契约补字段）
- Test: `prism/scripts/test_dashboard_macro.py`（扩 fixture + 断言新字段被渲染——在 Task 10 实测）

> 这是 spec §6.1（多维读数）/§6.2（fragility 罚分）/§3.10（类别尾部）落进 dashboard 消费契约的一步。**只加字段、不改既有字段名**（dashboard 现读 `regime.rates/liquidity/fx.{state,note}`、`composite`、`conviction`、`holdings[].exposure_score`，必须保持）。

- [ ] **Step 1: 在 `_macro_regime.md` §4 的 schema 块补新字段**

把 `prism/workflows/04-synthesize/_macro_regime.md` 中 Step 4 的 yaml schema（约 179-193 行）扩成：

```yaml
slug: <slug>
variant: <variant>
generated: "<ISO8601>"
regime:
  rates:     {state: ..., note: ..., confidence: <0-10>}   # 新增分维信心
  liquidity: {state: ..., note: ..., confidence: <0-10>}
  fx:        {state: ..., note: ..., confidence: <0-10>}
  composite: ...
  conviction: <0-10>
  quadrant: ...        # 新增：增长/通胀象限（复苏/过热/滞胀/衰退），独立于三体制（spec §6.1）
  fragility: ...       # 新增：脆弱度（low/mid/high）——强度越"干净"越临近崩，折减信心（spec §6.2）
holdings:
  - {slug: ..., display_name: ..., duration: long|short, rate_beta: high|mid|low,
     usd_exposure: high|mid|low, liquidity_beta: high|mid|low, exposure_score: high|mid|low,
     regime_favor: [...], regime_hurt: [...], plain: "一句大白话传导链"}
categorical_tail:       # 新增：spec §3.10 类别尾部 always-alert 状态快照（无市场序列可 diff）
  - {name: ..., state: 平静|警示|触发, note: "一句话"}
```
并在字段语义说明里补三行：`confidence`=该体制单独的判读信心 0-10；`quadrant`=增长/通胀象限；`fragility`=脆弱度（high 时即便 conviction 高也要在 dashboard 标"信心X/脆弱度高"）。

- [ ] **Step 2: 把现有 transmission_map.yaml 升级到新契约**

读 `prism/topics/global-macro-rates-liquidity/opus4.8/outputs/transmission_map.yaml`，在 `regime` 下给三体制各补 `confidence`，补 `quadrant` 与 `fragility`，并加 `categorical_tail`（至少含 spec §3.10 的「中美地缘/关税」「ADR 退市/HFCAA」两条，state 据当前读数填）。**不动既有 `holdings` 行的现有字段**。

- [ ] **Step 3: 校验 yaml 可解析**

Run:
```bash
python3 -c "import yaml; d=yaml.safe_load(open('prism/topics/global-macro-rates-liquidity/opus4.8/outputs/transmission_map.yaml',encoding='utf-8')); print('quadrant=',d['regime'].get('quadrant'),'fragility=',d['regime'].get('fragility'),'tail=',len(d.get('categorical_tail') or []))"
```
Expected: 打印 `quadrant=... fragility=... tail=2`（或更多）

- [ ] **Step 4: 提交**

```bash
git add prism/workflows/04-synthesize/_macro_regime.md prism/topics/global-macro-rates-liquidity/opus4.8/outputs/transmission_map.yaml
git commit -m "feat(prism): transmission_map 契约扩展 — 分维信心/象限/fragility/类别尾部

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 10: dashboard banner 渲染多维读数 + 新鲜度/regime-decay 指示

**Files:**
- Modify: `prism/scripts/dashboard.py:395-424`（`_collect_macro_banner`）、`:457-496`（`_render_dashboard` Section 0）
- Test: `prism/scripts/test_dashboard_macro.py`

> spec §6.1/§6.2/§6.9：banner 不再只一行综合判断。要展示三体制分维信心、增长/通胀象限、fragility（脆弱度），并区分"无新事件"与"读数仍新鲜"（沉默 ≠ 确认）——用 m_regime_read 的 data_freshness + 待确认 macro_input proposal 数做 regime-decay 指示。

- [ ] **Step 1: 跑 gitnexus 影响分析（铁律）**

```
gitnexus_impact({target: "_collect_macro_banner", direction: "upstream"})
gitnexus_impact({target: "_render_dashboard", direction: "upstream"})
```
报告爆炸半径（`_render_dashboard` 被 `build_dashboard` 调，是核心渲染——预期 MEDIUM+）。HIGH/CRITICAL 先告警。

- [ ] **Step 2: 写失败测试**

扩 `prism/scripts/test_dashboard_macro.py`：在 `macro_env` fixture 的 `sidecar["regime"]` 里补新字段，并加断言。把 fixture 的 regime 改为：

```python
        "regime": {
            "rates": {"state": "下行", "note": "美联储转向在即", "confidence": 6},
            "liquidity": {"state": "偏松", "note": "净流动性回升", "confidence": 4},
            "fx": {"state": "人民币承压", "note": "中美利差倒挂", "confidence": 5},
            "composite": "温和宽松早期",
            "conviction": 5.5,
            "quadrant": "复苏早期",
            "fragility": "high",
        },
```
新增测试函数：

```python
def test_banner_renders_multidim_and_fragility(macro_env):
    company_rows = dashboard._collect_company_rows()
    other_rows = dashboard._collect_non_company_rows()
    banner = dashboard._collect_macro_banner()
    md = dashboard._render_dashboard(company_rows, other_rows, banner)
    assert "复苏早期" in md          # 象限
    assert "脆弱度" in md            # fragility 标签词
    assert "信心" in md              # 分维信心展示
    assert banner["regime"]["fragility"] == "high"
    assert banner["regime"]["quadrant"] == "复苏早期"
```

- [ ] **Step 3: 跑测试确认失败**

Run: `python3 -m pytest prism/scripts/test_dashboard_macro.py -v`
Expected: `test_banner_renders_multidim_and_fragility` FAIL（`复苏早期`/`脆弱度` 未出现）；既有 4 个测试仍 PASS

- [ ] **Step 4: 改 _render_dashboard 的 Section 0**

把 `prism/scripts/dashboard.py` Section 0 的体制表与综合判断块（约 481-496 行）改为带分维信心 + 象限 + fragility：

```python
        lines += [
            "## 🌐 宏观体制",
            "",
            f"> [{macro['display_name']}](/prism/{macro['slug']}/{macro['variant']})　{_fmt_freshness(fr)}",
            "",
            "| 维度 | 体制 | 信心 | 说明 |",
            "|------|------|------|------|",
            f"| 利率 | {rg.get('rates', {}).get('state', '—')} | {rg.get('rates', {}).get('confidence', '—')} | {rg.get('rates', {}).get('note', '—')} |",
            f"| 流动性 | {rg.get('liquidity', {}).get('state', '—')} | {rg.get('liquidity', {}).get('confidence', '—')} | {rg.get('liquidity', {}).get('note', '—')} |",
            f"| 汇率 | {rg.get('fx', {}).get('state', '—')} | {rg.get('fx', {}).get('confidence', '—')} | {rg.get('fx', {}).get('note', '—')} |",
            "",
        ]
        quad = rg.get("quadrant")
        if quad:
            lines += [f"**增长/通胀象限**：{quad}", ""]
        composite = rg.get("composite")
        if composite:
            conv = rg.get("conviction")
            frag = rg.get("fragility")
            conv_str = f"（强度 {conv}` " if conv is not None else ""
            frag_str = f" · 脆弱度 {frag}" if frag else ""
            lines += [f"**综合判断**：{composite}（强度 {conv if conv is not None else '—'}{frag_str}）", ""]
        # regime-decay：待确认 macro 输入更新 → 沉默≠确认，提示重判
        n_macro_pending = sum(
            1 for p in _load_monitor_queue()
            if p.get("kind") == "macro_input" and p.get("slug") == macro["slug"]
        )
        if n_macro_pending:
            lines += [f"**⚠️ {n_macro_pending} 项宏观输入有更新待确认 —— 建议重判（沉默≠确认）**", ""]
        if macro["exposed"]:
            names = "、".join(h.get("display_name", h.get("slug", "")) for h in macro["exposed"])
            lines += [f"**当前体制最暴露持仓**：{names}", ""]
        lines += ["---", ""]
```
> 注意删掉上一版 `conv_str` 的临时写法，最终综合判断行用上面那条 `**综合判断**：...（强度 X · 脆弱度 Y）`。`_load_monitor_queue` 已在 dashboard.py 顶部定义（见 `:62`），直接用。

- [ ] **Step 5: 跑测试确认通过（含既有不回归）**

Run: `python3 -m pytest prism/scripts/test_dashboard_macro.py -v`
Expected: PASS（5 个全绿）

- [ ] **Step 6: 跑变更检测（铁律）并提交**

```
gitnexus_detect_changes()
```

```bash
git add prism/scripts/dashboard.py prism/scripts/test_dashboard_macro.py
git commit -m "feat(prism): dashboard 宏观 banner — 分维信心/象限/脆弱度 + regime-decay 提示

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 11: `_macro_regime.md` 合成规范吸收机制纠错（spec §5）+ 多维/fragility 读数（spec §6.1-6.2）

**Files:**
- Modify: `prism/workflows/04-synthesize/_macro_regime.md`
- Modify: `prism/topics/global-macro-rates-liquidity/opus4.8/outputs/m_regime_read.md`（按新规范补结构）
- Test: `prism/scripts/test_macro_regime_doc.py`（新建：结构性断言）

> 这是把"框架成熟化"写进可执行规范的一步：合成时必须遵守 §5 的因果/相关纠错，并产出多维读数（三体制分维信心 + 象限）+ fragility 折减。markdown 无 pytest 逻辑可测，故用**结构性 grep 断言**钉住关键条款不被漏写。

- [ ] **Step 1: 写失败测试（结构性断言）**

Create `prism/scripts/test_macro_regime_doc.py`:

```python
"""结构闸：_macro_regime.md 必须含 spec §5 机制纠错 + §6 多维/fragility 条款。
markdown 无逻辑可单测，用关键短语存在性钉住规范不被漏写。"""
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
DOC = _ROOT / "prism/workflows/04-synthesize/_macro_regime.md"
READ = _ROOT / "prism/topics/global-macro-rates-liquidity/opus4.8/outputs/m_regime_read.md"


def test_doc_has_mechanism_corrections():
    t = DOC.read_text(encoding="utf-8")
    # §5 八条纠错的关键锚点
    assert "中美10Y利差" in t or "中美 10Y 利差" in t
    assert "压力表" in t                     # 中美利差 A→B 降为压力表
    assert "去美元化" in t                   # 黄金机制改写
    assert "SOFR" in t                       # 净流动性降权、SOFR−IORB 升 binding
    assert "超预期" in t                     # PCE/CPI 触发用超预期非水平


def test_doc_has_multidim_and_fragility():
    t = DOC.read_text(encoding="utf-8")
    assert "分维信心" in t or "分维度信心" in t
    assert "象限" in t                       # 增长/通胀象限
    assert "脆弱" in t                       # fragility 罚分


def test_regime_read_has_fragility_and_quadrant():
    t = READ.read_text(encoding="utf-8")
    assert "脆弱" in t
    assert "象限" in t
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest prism/scripts/test_macro_regime_doc.py -v`
Expected: FAIL（短语未出现）

- [ ] **Step 3: 给 `_macro_regime.md` 加「§5 机制纠错」与「多维/fragility」两节**

在 `_macro_regime.md` 的 §3（三体制活读数）与 §4 之间插入一节「**3.5 机制纠错与多维读数（合成必遵守）**」，照 spec §5/§6 写明：

- 机制纠错八条（逐条）：中美 10Y 利差 A→B 降为**压力表**（真 A=中间价/逆周期因子+管制+顺差）；黄金机制改写为**去美元化读数**、不得当实际利率代理；信用利差 OAS 收敛单一 B、删"领先"；净流动性降权、**SOFR−IORB** 升为 binding driver；核心 PCE/CPI **分期限** + 触发用**超预期**非水平；日元 carry 标条件/阈值尾部；DXY 中国侧降 B（改用 CFETS/广义美元）；比特币维持 C。
- 多维读数（§6.1）：三体制各给读数 + **分维信心**；另设**增长/通胀象限**（复苏/过热/滞胀/衰退）独立于三体制。
- fragility 罚分（§6.2）：综合信心要被**脆弱度**（利差极窄+低波动+carry 拥挤+承重假设数）折减，输出"信心X/脆弱度高"。

并在 §4 顶部加一句：transmission_map 的 `regime` 必须落 `confidence/quadrant/fragility`（Task 9 已加进 schema）。

- [ ] **Step 4: 给 `m_regime_read.md` 顶部补多维结构**

在 `m_regime_read.md` 顶部「综合判断 + 强度分」之后，加一小节：三体制**分维信心**（各 0-10）、**增长/通胀象限**当前落点、**脆弱度**评估（含为何）。可据现有读数填，缺数标"训练知识估算"。

- [ ] **Step 5: 跑测试确认通过**

Run: `python3 -m pytest prism/scripts/test_macro_regime_doc.py -v`
Expected: PASS（全部）

- [ ] **Step 6: 提交**

```bash
git add prism/workflows/04-synthesize/_macro_regime.md prism/topics/global-macro-rates-liquidity/opus4.8/outputs/m_regime_read.md prism/scripts/test_macro_regime_doc.py
git commit -m "feat(prism): _macro_regime 合成规范吸收机制纠错(§5)+多维/fragility 读数(§6)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 12: `06-daily-monitor.md` 增宏观巡检分支 + 启用 macro topic 监控

**Files:**
- Modify: `prism/workflows/06-daily-monitor.md`
- Modify: `prism/topics/global-macro-rates-liquidity/opus4.8/topic.yaml`（monitoring/tier）
- Test: `prism/scripts/test_macro_regime_doc.py`（追加 workflow 分支存在性断言）

- [ ] **Step 1: 写失败测试（workflow 含 macro 分支）**

Append to `prism/scripts/test_macro_regime_doc.py`:

```python
MONITOR_DOC = _ROOT / "prism/workflows/06-daily-monitor.md"


def test_monitor_doc_has_macro_branch():
    t = MONITOR_DOC.read_text(encoding="utf-8")
    assert "macro_due" in t
    assert "macro_alert" in t
    assert "propose_macro_updates" in t
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest prism/scripts/test_macro_regime_doc.py::test_monitor_doc_has_macro_branch -v`
Expected: FAIL

- [ ] **Step 3: 给 06-daily-monitor.md 加宏观分支说明**

在 `06-daily-monitor.md` 的 Step 3（recurring_review）之后加「**Step 3.5：宏观输入（macro topic）**」：

- `scan` 现多两桶 `macro_due`（事件/描述型到期）/ `macro_alert`（行情型 alert_series 越带）。
- 这两桶走**零 LLM 路径**：`python3 -m prism.scripts.monitor macro` 或运行时自动调 `monitor.propose_macro_updates`，机械写 `kind=macro_input` proposal（信息型，预写 living_feed 文案）。
- **绝不自动改 regime_read**；承重/越带项标 `requires_thesis_review=True`，仅在 web「建议重判」点名，等用户说「合成 global-macro」走 `_macro_regime.md` 重出三件套。
- 描述型（policy）全文抓取/findings 抽取属第二期；本期到期只提示"该取新值"。

并在 Step 1 的分桶表里加两行 `macro_due` / `macro_alert` 的说明。

- [ ] **Step 4: 启用 macro topic 的监控（让巡检真的会扫到）**

改 `prism/topics/global-macro-rates-liquidity/opus4.8/topic.yaml`：把 `monitoring_tier: dormant` 改 `watch`，`monitoring.enabled: false` 改 `true`。
> 真正的成本闸仍是 watchlist（用户在 web 勾选 / 或 `monitor.add_watch('global-macro-rates-liquidity', scope='topic')`）。这里只是让 tier/enabled 与"该被监控"一致。

- [ ] **Step 5: 跑测试 + 校验 topic.yaml 可解析**

Run:
```bash
python3 -m pytest prism/scripts/test_macro_regime_doc.py -v
python3 -c "import yaml; d=yaml.safe_load(open('prism/topics/global-macro-rates-liquidity/opus4.8/topic.yaml',encoding='utf-8')); assert d['monitoring']['enabled'] is True and d['monitoring_tier']=='watch'; print('ok')"
```
Expected: 测试 PASS；打印 `ok`

- [ ] **Step 6: 提交**

```bash
git add prism/workflows/06-daily-monitor.md prism/topics/global-macro-rates-liquidity/opus4.8/topic.yaml prism/scripts/test_macro_regime_doc.py
git commit -m "feat(prism): 06-daily-monitor 增宏观巡检分支 + 启用 macro topic 监控

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 13: 全量回归 + 最终评审

**Files:**
- 无新增；跑全套测试 + gitnexus 终检

- [ ] **Step 1: 跑 prism 全量测试**

Run: `python3 -m pytest prism/scripts/ -q`
Expected: 全绿（重点核对 `test_monitor_*`、`test_dashboard_macro`、`test_macro_*`、`test_outputs_macro` 无回归）

- [ ] **Step 2: 端到端烟测（真实仓库）**

Run:
```bash
python3 -m prism.scripts.seed_macro_inputs
python3 -c "from prism.scripts import macro_registry as mr; print('validator errors:', len(mr.validate_registry('global-macro-rates-liquidity','opus4.8')))"
python3 -m prism.scripts.monitor scan 14 | python3 -c "import sys,json; d=json.load(sys.stdin); print('macro_due:',len(d['macro_due']),'macro_alert:',len(d['macro_alert']))"
```
Expected: `validator errors: 0`；scan 输出含 macro 两桶（数值取决于 observed 是否已 seed，可能为 0 —— 正常，因 fetcher 属第二期）

- [ ] **Step 3: gitnexus 终检**

```
gitnexus_detect_changes()
```
确认改动范围仅限本计划涉及的符号/文件；无意外波及白酒/泡泡玛特等无关 WIP。

- [ ] **Step 4: 汇报**

向用户汇报：MVP 已落地（登记表全集无遗漏闸通过、monitor 认识 macro、banner 多维化、合成规范吸收机制纠错），并列出 spec §11 仍待用户回填的开放项（六条报警序列精值、TBD 源、类别尾部信息源），以及第二步（FRED 自动抓）/第三步（战绩台账）作为后续独立计划。

---

## 自检（writing-plans Self-Review）

**Spec 覆盖（§7 本期 MVP 第一步）：**
- 建宏观登记表（§3 全集 + §2.2 机制字段，TBD 占位）→ Task 1-3 ✅（含无遗漏闸 + validator）
- 扩 monitor：认识 macro topic + 事件 diff + 行情 §4.3 报警 + 描述型到期 → Task 5-8 ✅
- 改 `_macro_regime.md` 吸收机制纠错(§5) + 多维/fragility(§6.1-6.2) → Task 11 ✅
- dashboard 多维 banner + regime-decay/staleness 指示 → Task 9-10 ✅
- transmission_map / m_regime_read 结构改 → Task 9、Task 11 ✅
- 容器映射（spec §8 七处文件）→ 全部被某 Task 覆盖（manifest→改为 macro_inputs.yaml 并在抬头说明）✅
- 用户回填 TBD（§7 第 2 步）→ 非编码任务，Task 13 Step 4 列为开放项交还用户 ✅

**Placeholder 扫描：** 唯一刻意保留的 `TBD` 是登记表的 `source/fetch_method`（spec §7/§11 明确"先登记，源后补"）与六条报警序列的 `alert_band` 占位值（spec §11 待用户回填）——这是设计状态而非计划缺口，已在相应步骤标注其性质与回填路径。

**类型一致性：** 枚举（tier/cadence_type/mechanism/importance）在 Task 1 定义后，Task 2 validator、Task 3 seed、Task 5 scan、Task 7 propose 全程一致；`scan_macro_inputs` 桶名（due_event/due_policy/alert_series/unparseable）与 monitor 桶名（macro_due/macro_alert）映射在 Task 6 明确；transmission_map 新字段（confidence/quadrant/fragility/categorical_tail）在 Task 9 定义、Task 10 渲染、Task 11 产出，一致。

**范围：** 本计划是 spec §7「本期 MVP」单一子系统；FRED 自动抓（第二步）、战绩台账/DCF（第三步）刻意排除，各自后续独立成计划。
