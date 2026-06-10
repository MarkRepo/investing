"""fetch_llm_batch 单测：选取过滤 + 单条取数落盘逻辑。mock 掉 headless 拉起，不发真实网络/不烧 token。"""
import json
import types

from prism.scripts import fetch_llm_batch as fb


def _fake_proc(items, *, rc=0, cost=0.01, fenced=True):
    """伪造 run_headless 的 CompletedProcess：stdout 是 --output-format json 信封，其 result 内含 LLM 文本。"""
    if items is None:
        body = "我没查到，留空。"  # 无 JSON
    else:
        arr = json.dumps(items, ensure_ascii=False)
        body = f"分析如下。\n```json\n{arr}\n```" if fenced else arr
    envelope = json.dumps({"type": "result", "result": body, "total_cost_usd": cost})
    return types.SimpleNamespace(returncode=rc, stdout=envelope, stderr="")


def test_select_targets_filters_load_bearing_llm_novalue(monkeypatch):
    fake = {"inputs": [
        {"name": "要", "importance": "load_bearing", "availability": "llm"},
        {"name": "有值", "importance": "load_bearing", "availability": "llm",
         "observed": {"value": 1.0}},
        {"name": "确认级", "importance": "confirming", "availability": "llm"},
        {"name": "已脚本", "importance": "load_bearing", "availability": "scripted"},
    ]}
    monkeypatch.setattr(fb.reg, "read_registry", lambda s, v: fake)
    names = [e["name"] for e in fb.select_targets("m", "v")]
    assert names == ["要"]


def _patch_entry(monkeypatch):
    """固定 prompt 构造 + 跳过真实 record/flag 的副作用收集器。"""
    monkeypatch.setattr(fb, "_build_macro_llm_prompt", lambda s, v, entries: "P")
    recorded, flagged = [], []
    monkeypatch.setattr(fb.reg, "record_observation",
                        lambda s, v, name, **kw: recorded.append((name, kw.get("value"))))
    monkeypatch.setattr(fb.reg, "flag_scriptable",
                        lambda s, v, name, **kw: flagged.append(name) or True)
    return recorded, flagged


def test_fetch_one_single_item_applied_despite_name(monkeypatch):
    """单 item 即使名字与注册表略不同，也落到目标名（prompt 只问一条）。"""
    recorded, flagged = _patch_entry(monkeypatch)
    monkeypatch.setattr(fb.claude_runner, "run_headless",
                        lambda p, **kw: _fake_proc([{"name": "简写", "value": 2.5,
                                                     "as_of": "2026-06-01", "scriptable": True}]))
    r = fb.fetch_one("m", "v", {"name": "正式全名"}, model="haiku")
    assert r["status"] == "ok" and r["value"] == 2.5
    assert recorded == [("正式全名", 2.5)]      # 落到目标名，非 LLM 回的简写
    assert flagged == ["正式全名"] and r["scriptable"] is True


def test_fetch_one_empty_array_is_honest_empty(monkeypatch):
    """LLM 返空数组 = 没查到 → status=empty、不写。"""
    _patch_entry(monkeypatch)
    monkeypatch.setattr(fb.claude_runner, "run_headless", lambda p, **kw: _fake_proc([]))
    r = fb.fetch_one("m", "v", {"name": "X"}, model="haiku")
    assert r["status"] == "empty" and r["value"] is None


def test_fetch_one_null_value_records_but_no_promote(monkeypatch):
    """单 item 但 value=null（诚实留空）：record 仍调用（写 null），但不 promote。"""
    recorded, flagged = _patch_entry(monkeypatch)
    monkeypatch.setattr(fb.claude_runner, "run_headless",
                        lambda p, **kw: _fake_proc([{"name": "X", "value": None,
                                                     "scriptable": True}]))
    r = fb.fetch_one("m", "v", {"name": "X"}, model="haiku")
    assert r["status"] == "ok" and r["value"] is None
    assert recorded == [("X", None)] and flagged == []   # value 为 null 不升档


def test_fetch_one_no_json_is_no_json(monkeypatch):
    _patch_entry(monkeypatch)
    monkeypatch.setattr(fb.claude_runner, "run_headless", lambda p, **kw: _fake_proc(None))
    r = fb.fetch_one("m", "v", {"name": "X"}, model="haiku")
    assert r["status"] == "no_json"


def test_fetch_one_nonzero_rc_failed(monkeypatch):
    _patch_entry(monkeypatch)
    monkeypatch.setattr(fb.claude_runner, "run_headless",
                        lambda p, **kw: _fake_proc([], rc=1))
    r = fb.fetch_one("m", "v", {"name": "X"}, model="haiku")
    assert r["status"] == "failed"
