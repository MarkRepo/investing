"""β：登记表新字段 authority / availability 的枚举校验（可空，给值则须合法）。"""
import pytest
from prism.scripts import macro_registry as reg


@pytest.fixture
def tmp_reg(tmp_path, monkeypatch):
    monkeypatch.setattr(reg, "_PRISM_ROOT", tmp_path)
    reg.create_registry("m", "v")
    return "m", "v"


def _base(extra):
    return {"name": "X", "tier": "B", "cadence_type": "series",
            "mechanism": "CO", "importance": "confirming", **extra}


def test_valid_authority_availability_pass(tmp_reg):
    slug, variant = tmp_reg
    reg.upsert_input(slug, variant, _base({"authority": "official", "availability": "scripted"}))
    assert reg.validate_registry(slug, variant) == []


def test_bad_authority_flagged(tmp_reg):
    slug, variant = tmp_reg
    reg.upsert_input(slug, variant, _base({"authority": "bogus"}))
    assert any("authority" in e for e in reg.validate_registry(slug, variant))


def test_bad_availability_flagged(tmp_reg):
    slug, variant = tmp_reg
    reg.upsert_input(slug, variant, _base({"availability": "maybe"}))
    assert any("availability" in e for e in reg.validate_registry(slug, variant))


def test_absent_fields_ok(tmp_reg):
    slug, variant = tmp_reg
    reg.upsert_input(slug, variant, _base({}))
    assert reg.validate_registry(slug, variant) == []


def test_recipe_json_default_requires_json_path(tmp_reg):
    slug, variant = tmp_reg
    reg.upsert_input(slug, variant, _base({"fetch_recipe": {"url": "https://x", "parse": {}}}))
    assert any("json_path" in e for e in reg.validate_registry(slug, variant))


def test_recipe_csv_requires_value_column(tmp_reg):
    slug, variant = tmp_reg
    reg.upsert_input(slug, variant, _base(
        {"fetch_recipe": {"kind": "csv", "url": "https://x", "parse": {"date_column": "DATE"}}}))
    assert any("value_column" in e for e in reg.validate_registry(slug, variant))


def test_recipe_unknown_kind_flagged(tmp_reg):
    slug, variant = tmp_reg
    reg.upsert_input(slug, variant, _base(
        {"fetch_recipe": {"kind": "xml", "url": "https://x", "parse": {}}}))
    assert any("kind" in e for e in reg.validate_registry(slug, variant))


def test_recipe_valid_csv_passes(tmp_reg):
    slug, variant = tmp_reg
    reg.upsert_input(slug, variant, _base(
        {"fetch_recipe": {"kind": "csv", "url": "https://x", "parse": {"value_column": "Value"}}}))
    assert reg.validate_registry(slug, variant) == []


def _policy(extra_obs):
    return {"name": "货政报告", "tier": "B", "cadence_type": "policy",
            "mechanism": "CO", "importance": "confirming",
            "stance_scale": "hawk_dove", "observed": extra_obs}


def test_valid_stance_passes(tmp_reg):
    slug, variant = tmp_reg
    reg.upsert_input(slug, variant, _policy({"stance": "偏鹰", "evidence": "删去'保持耐心'"}))
    assert reg.validate_registry(slug, variant) == []


def test_bad_stance_scale_flagged(tmp_reg):
    slug, variant = tmp_reg
    reg.upsert_input(slug, variant, _base({"stance_scale": "bogus"}))
    assert any("stance_scale" in e for e in reg.validate_registry(slug, variant))


def test_stance_off_scale_flagged(tmp_reg):
    slug, variant = tmp_reg
    reg.upsert_input(slug, variant, _policy({"stance": "扩张", "evidence": "x"}))
    assert any("不在轴" in e for e in reg.validate_registry(slug, variant))


def test_stance_without_scale_flagged(tmp_reg):
    slug, variant = tmp_reg
    reg.upsert_input(slug, variant, _base({"observed": {"stance": "偏鹰", "evidence": "x"}}))
    assert any("未声明 stance_scale" in m for m in reg.validate_registry(slug, variant))


def test_stance_without_evidence_flagged(tmp_reg):
    slug, variant = tmp_reg
    reg.upsert_input(slug, variant, _policy({"stance": "偏鹰"}))   # 无 evidence
    assert any("evidence" in m for m in reg.validate_registry(slug, variant))


# --- availability 4 档：自动化阶梯（scripted/scriptable_todo/llm_direct/llm_search 均合法）---

@pytest.mark.parametrize("avail", ["scripted", "scriptable_todo", "llm"])
def test_all_availability_rungs_pass(tmp_reg, avail):
    slug, variant = tmp_reg
    reg.upsert_input(slug, variant, _base({"availability": avail}))
    assert reg.validate_registry(slug, variant) == []


# --- fetch_method 是脚本执行通道：仅 scripted 项可设，取值 ∈ {fred-api, recipe} ---

@pytest.mark.parametrize("fm", ["fred-api", "recipe"])
def test_fetch_method_valid_on_scripted_passes(tmp_reg, fm):
    slug, variant = tmp_reg
    reg.upsert_input(slug, variant, _base({"availability": "scripted", "fetch_method": fm}))
    assert reg.validate_registry(slug, variant) == []


def test_fetch_method_bad_value_flagged(tmp_reg):
    slug, variant = tmp_reg
    reg.upsert_input(slug, variant, _base({"availability": "scripted", "fetch_method": "llm-web"}))
    assert any("fetch_method 非法" in e for e in reg.validate_registry(slug, variant))


@pytest.mark.parametrize("avail", ["scriptable_todo", "llm", None])
def test_fetch_method_only_on_scripted(tmp_reg, avail):
    """fetch_method 出现在非 scripted（含未声明 availability）项 → 报错。"""
    slug, variant = tmp_reg
    reg.upsert_input(slug, variant, _base({"availability": avail, "fetch_method": "fred-api"}))
    assert any("只能出现在 scripted" in e for e in reg.validate_registry(slug, variant))


# --- flag_scriptable：promote 闸门（llm + 已落 value → scriptable_todo + note）---

def test_flag_scriptable_promotes_when_value_present(tmp_reg):
    slug, variant = tmp_reg
    reg.upsert_input(slug, variant, _base({"name": "X", "availability": "llm"}))
    reg.record_observation(slug, variant, "X", value=12.3, as_of="2026-06-05")
    assert reg.flag_scriptable(slug, variant, "X", note="可由 ISM JSON 直拉") is True
    e = next(i for i in reg.read_registry(slug, variant)["inputs"] if i["name"] == "X")
    assert e["availability"] == "scriptable_todo"
    assert e["note"] == "可由 ISM JSON 直拉"


def test_flag_scriptable_refused_without_value(tmp_reg):
    """闸门：没落到 value（如只 evidence 的立场项）→ 拒绝升档、不动。"""
    slug, variant = tmp_reg
    reg.upsert_input(slug, variant, _base({"name": "X", "availability": "llm"}))
    assert reg.flag_scriptable(slug, variant, "X", note="n") is False
    e = next(i for i in reg.read_registry(slug, variant)["inputs"] if i["name"] == "X")
    assert e["availability"] == "llm"   # 未动


@pytest.mark.parametrize("avail", ["scripted", "scriptable_todo"])
def test_flag_scriptable_refused_when_not_llm(tmp_reg, avail):
    """非 llm 项不在 promote 轴上 → 即便有 value 也拒。"""
    slug, variant = tmp_reg
    reg.upsert_input(slug, variant, _base({"name": "X", "availability": avail}))
    reg.record_observation(slug, variant, "X", value=1.0)
    assert reg.flag_scriptable(slug, variant, "X", note="n") is False


def test_record_observation_writes_evidence(tmp_reg):
    slug, variant = tmp_reg
    reg.upsert_input(slug, variant, _base({"name": "X", "availability": "llm"}))
    reg.record_observation(slug, variant, "X", value=5.0, evidence="来源：ISM 官网 2026-06")
    e = next(i for i in reg.read_registry(slug, variant)["inputs"] if i["name"] == "X")
    assert e["observed"]["evidence"] == "来源：ISM 官网 2026-06"


# --- monitoring_enabled / monitor_mode：监控缺省随 rung ---

def test_monitoring_enabled_default_by_rung():
    assert reg.monitoring_enabled({"availability": "scripted"}) is True
    assert reg.monitoring_enabled({"availability": "scriptable_todo"}) is False
    assert reg.monitoring_enabled({"availability": "llm"}) is False
    assert reg.monitoring_enabled({}) is False   # 未声明 availability → 默认关


def test_monitoring_enabled_explicit_overrides():
    assert reg.monitoring_enabled({"availability": "llm", "monitoring": {"enabled": True}}) is True
    assert reg.monitoring_enabled({"availability": "scripted", "monitoring": {"enabled": False}}) is False


def test_monitor_mode():
    assert reg.monitor_mode({"availability": "scripted"}) == "script"
    assert reg.monitor_mode({"availability": "scriptable_todo"}) == "headless_llm"
    assert reg.monitor_mode({"availability": "llm"}) == "headless_llm"


# --- due_llm_monitor_names：监控中且走 headless 的到期名 ---

def test_due_llm_monitor_names_picks_opted_in():
    from datetime import date
    today = date(2026, 6, 9)
    registry = {"inputs": [
        # series llm 开监控 → 恒取
        {"name": "S", "availability": "llm", "cadence_type": "series", "monitoring": {"enabled": True}},
        # event llm 开监控但到期才取：已到期
        {"name": "E_due", "availability": "scriptable_todo", "cadence_type": "event",
         "monitoring": {"enabled": True}, "observed": {"next_due": "2026-06-08"}},
        # event llm 开监控但未到期 → 不取
        {"name": "E_future", "availability": "llm", "cadence_type": "event",
         "monitoring": {"enabled": True}, "observed": {"next_due": "2026-12-01"}},
        # llm 未开监控（默认关）→ 不取
        {"name": "S_off", "availability": "llm", "cadence_type": "series"},
        # scripted 走脚本，不在 headless 轴
        {"name": "Scr", "availability": "scripted", "cadence_type": "series", "monitoring": {"enabled": True}},
    ]}
    names = reg.due_llm_monitor_names(registry, today=today)
    assert set(names) == {"S", "E_due"}


def test_due_excludes_items_checked_today():
    """今天已拉过的项不再算到期（避免拉完仍显示「到期·待拉取」）。series 与 event 同理。"""
    from datetime import date
    today = date(2026, 6, 9)
    registry = {"inputs": [
        # series 今天已拉 → 新鲜，不催
        {"name": "Fresh", "availability": "scriptable_todo", "cadence_type": "series",
         "monitoring": {"enabled": True},
         "observed": {"value": 3.85, "checked_at": "2026-06-09T14:50:10.643923+00:00"}},
        # series 昨天拉的 → 仍到期
        {"name": "Stale", "availability": "scriptable_todo", "cadence_type": "series",
         "monitoring": {"enabled": True},
         "observed": {"value": 1.0, "checked_at": "2026-06-08T10:00:00+00:00"}},
        # series 从未拉 → 到期
        {"name": "Never", "availability": "llm", "cadence_type": "series",
         "monitoring": {"enabled": True}},
        # event 今天已拉、即使 next_due 仍过期 → 当天不再催
        {"name": "E_fresh", "availability": "llm", "cadence_type": "event",
         "monitoring": {"enabled": True},
         "observed": {"next_due": "2026-06-01", "checked_at": "2026-06-09T08:00:00+00:00"}},
    ]}
    names = reg.due_llm_monitor_names(registry, today=today)
    assert set(names) == {"Stale", "Never"}


# --- llm 取数方式：从 source_url 在不在派生（固定页 vs 检索），单一真相 ---

def test_llm_mode_fixed_page_when_source_url_present():
    assert reg.llm_acquisition_mode(
        {"availability": "llm", "source_url": "https://x/index.htm"}) == "fixed_page"


def test_llm_mode_search_when_no_source_url():
    assert reg.llm_acquisition_mode({"availability": "llm"}) == "search"
    assert reg.llm_acquisition_mode({"availability": "llm", "source_url": ""}) == "search"


@pytest.mark.parametrize("avail", ["scripted", "scriptable_todo", None])
def test_llm_mode_none_for_non_llm(avail):
    """非 llm 项不在本轴上（取数由 fetch_method/availability 决定）。"""
    assert reg.llm_acquisition_mode(
        {"availability": avail, "source_url": "https://x"}) is None
