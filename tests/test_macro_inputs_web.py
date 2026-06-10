"""宏观层 Web：顶部导航 + 输入源信息表。"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

VARIANT = "opus4.8"
SLUG = "global-macro-rates-liquidity"


@pytest.fixture
def macro_web_client(tmp_path, monkeypatch):
    repo = Path(__file__).resolve().parent.parent
    shutil.copytree(repo / "app" / "templates", tmp_path / "app_templates")

    from app import config as cfg
    monkeypatch.setattr(cfg, "BASE_PATH", tmp_path)
    monkeypatch.setattr(cfg, "APP_TEMPLATES_DIR", tmp_path / "app_templates")
    monkeypatch.setattr(cfg, "STATIC_DIR", tmp_path / "static")
    monkeypatch.setattr(cfg, "PRISM_DIR", tmp_path / "prism")
    for name in ("companies", "industries", "watchlist", "macro", "data", "static"):
        (tmp_path / name).mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(cfg, "COMPANIES_DIR", tmp_path / "companies")
    monkeypatch.setattr(cfg, "INDUSTRIES_DIR", tmp_path / "industries")
    monkeypatch.setattr(cfg, "WATCHLIST_DIR", tmp_path / "watchlist")
    monkeypatch.setattr(cfg, "MACRO_DIR", tmp_path / "macro")
    monkeypatch.setattr(cfg, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(cfg, "FINANCIALS_DB", tmp_path / "data" / "financials.db")
    (tmp_path / "portfolio").mkdir(parents=True, exist_ok=True)
    (tmp_path / "portfolio" / "rules.md").write_text("# r\n")
    monkeypatch.setattr(cfg, "PORTFOLIO_DIR", tmp_path / "portfolio")
    (tmp_path / "journal" / "decisions").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(cfg, "JOURNAL_DIR", tmp_path / "journal")
    monkeypatch.setattr(cfg, "CONTROLLED_VOCAB_DIR", repo / "controlled-vocab")

    import prism.scripts.topic as t
    import prism.scripts.manifest as m
    import prism.scripts.outputs as o
    import prism.scripts.macro_registry as reg
    monkeypatch.setattr(t, "PRISM_ROOT", tmp_path / "prism")
    monkeypatch.setattr(m, "_PRISM_ROOT", tmp_path / "prism")
    monkeypatch.setattr(o, "_PRISM_ROOT", tmp_path / "prism")
    monkeypatch.setattr(reg, "_PRISM_ROOT", tmp_path / "prism")
    import prism.scripts.eval_snapshot as es
    monkeypatch.setattr(es, "_PRISM_ROOT", tmp_path / "prism")

    (tmp_path / "prism" / "topics").mkdir(parents=True)
    t.create_topic(SLUG, "宏观层 (利率/流动性/汇率体制)", "macro", "三体制传导", "GLOBAL", "deep", VARIANT)
    m.create_manifest(SLUG, VARIANT)
    # 最小登记表：一条 FRED 自动抓取的报警序列
    reg.create_registry(SLUG, VARIANT)
    reg.upsert_input(SLUG, VARIANT, {
        "name": "HY OAS", "tier": "B", "cadence_type": "series", "targets": ["liquidity"],
        "mechanism": "CO", "importance": "confirming", "source": "FRED", "fetch_method": "fred-api",
        "availability": "scripted", "fred_series_id": "BAMLH0A0HYM2", "alert_series": True,
        "alert_band": {"level": 4.5, "direction": "above"}, "monitoring": {"enabled": True},
    })

    from main import app
    return TestClient(app)


def test_nav_macro_points_to_detail(macro_web_client):
    """顶部「宏观层」指向详情页（而非直接输入表）——输入表是详情页里的 tab。"""
    r = macro_web_client.get("/prism")
    assert r.status_code == 200
    assert "宏观层" in r.text
    assert f'href="/prism/{SLUG}/{VARIANT}"' in r.text          # detail 页
    assert f"/prism/{SLUG}/{VARIANT}/macro-inputs" not in r.text  # 不再直挂输入表


def test_index_shows_macro_label(macro_web_client):
    r = macro_web_client.get("/prism")
    assert "宏观" in r.text          # 中文标签
    assert ">macro<" not in r.text   # 不暴露原始 type


def test_macro_inputs_table_renders(macro_web_client):
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/macro-inputs")
    assert r.status_code == 200
    assert "HY OAS" in r.text          # 输入名
    assert "FRED" in r.text            # 来源
    assert "自动" in r.text or "fred-api" in r.text   # 抓取方式


def test_macro_inputs_404_for_non_macro(macro_web_client):
    # 非 macro topic 命中该路由应 404（验证类型守卫，而非通配吞掉）
    import prism.scripts.topic as t
    import prism.scripts.manifest as m
    t.create_topic("cn-industry-x", "某行业", "industry", "Q", "CN", "deep", VARIANT)
    m.create_manifest("cn-industry-x", VARIANT)
    r = macro_web_client.get(f"/prism/cn-industry-x/{VARIANT}/macro-inputs")
    assert r.status_code == 404


def test_macro_inputs_shows_caveat_note(macro_web_client):
    """带 note（口径/代理说明）的输入要在表里显示，而非只埋在 CLI smoke / 代码注释里。"""
    import prism.scripts.macro_registry as reg
    reg.upsert_input(SLUG, VARIANT, {
        "name": "DXY", "source": "FRED", "fetch_method": "fred-api",
        "fred_series_id": "DTWEXAFEGS",
        "note": "代理 DTWEXAFEGS，非 ICE 真·DXY，数值不可直接对市场报价",
    })
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/macro-inputs")
    assert r.status_code == 200
    assert "非 ICE 真·DXY" in r.text


def test_macro_inputs_shows_llm_mode_badges(macro_web_client):
    """llm 输入按 source_url 在不在派生取数方式：有→固定页、无→检索（镜像 llm_acquisition_mode）。"""
    import prism.scripts.macro_registry as reg
    reg.upsert_input(SLUG, VARIANT, {
        "name": "MPR", "tier": "A", "cadence_type": "policy", "targets": ["rates"],
        "mechanism": "CD", "importance": "load_bearing", "causal_sentence": "x→y→z",
        "availability": "llm", "source_url": "https://example.gov/mpr.htm",
    })
    reg.upsert_input(SLUG, VARIANT, {
        "name": "关税", "tier": "A", "cadence_type": "policy", "targets": ["fx"],
        "mechanism": "CD", "importance": "load_bearing", "causal_sentence": "x→y→z",
        "availability": "llm",   # 无 source_url → 检索
    })
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/macro-inputs")
    assert r.status_code == 200
    assert "固定页" in r.text
    assert "检索" in r.text


def test_macro_detail_shows_input_tab_not_diag(macro_web_client):
    """macro 详情页 tab 条：读者向 + 输入源；隐藏 诊断/体检（对宏观层不适用）。"""
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}")
    assert r.status_code == 200
    assert "输入源" in r.text
    assert f"/prism/{SLUG}/{VARIANT}/macro-inputs" in r.text   # 输入源 tab 链接
    assert "诊断 / debug" not in r.text                        # 诊断 tab 不展示
    assert "体检" not in r.text                                # 体检 tab 不展示


def test_macro_inputs_page_has_tab_bar(macro_web_client):
    """输入源页本身带 tab 条，可切回读者向。"""
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/macro-inputs")
    assert r.status_code == 200
    assert "读者向" in r.text
    assert f'href="/prism/{SLUG}/{VARIANT}"' in r.text          # 读者向回链
    assert "输入源" in r.text


def test_diag_404_for_macro(macro_web_client):
    """诊断 tab 对宏观层不适用 → 直访路由也 404。"""
    assert macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/diag").status_code == 404


def test_checkup_404_for_macro(macro_web_client):
    """体检 tab 对宏观层不适用 → 直访路由也 404。"""
    assert macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/checkup").status_code == 404


def test_macro_nav_no_double_highlight(macro_web_client):
    """点「宏观层」时不应同时高亮「研究」（exclude 子树修复）。"""
    import re
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}")
    nav = re.search(r'<nav class="top">(.*?)</nav>', r.text, re.S).group(1)
    yanjiu = re.search(r'<a href="/prism"[^>]*>研究</a>', nav).group(0)
    assert "active" not in yanjiu                               # 研究 不亮
    macro_a = re.search(
        r'<a href="/prism/global-macro-rates-liquidity/opus4\.8"[^>]*>宏观层</a>', nav
    ).group(0)
    assert "active" in macro_a                                  # 宏观层 亮


def _write_transmission_map(tmp_root):
    """往 tmp topic 写一份最小传导地图 yaml（含 regime + 一只持仓 + 类别尾部）。"""
    out = tmp_root / "prism" / "topics" / SLUG / VARIANT / "outputs"
    out.mkdir(parents=True, exist_ok=True)
    (out / "transmission_map.yaml").write_text(
        "slug: %s\nvariant: %s\ngenerated: \"2026-06-07T00:00:00Z\"\n"
        "regime:\n"
        "  rates: {state: \"高位筑顶\", note: \"美钱仍贵\", confidence: 7}\n"
        "  composite: \"美紧中松分化体制 — 偏防御\"\n"
        "  conviction: 6\n  quadrant: 滞胀\n  fragility: high\n"
        "holdings:\n"
        "  - {slug: cn-kweichow-moutai-600519, display_name: 贵州茅台, duration: mid,\n"
        "     rate_beta: mid, usd_exposure: low, liquidity_beta: mid, exposure_score: mid,\n"
        "     regime_favor: [人民币企稳], regime_hurt: [中国紧信用],\n"
        "     plain: \"人民币内需防御票，几乎无美元暴露\"}\n"
        "categorical_tail:\n"
        "  - {name: 中美地缘/关税, state: 警示, note: \"关税战未停火\"}\n"
        % (SLUG, VARIANT),
        encoding="utf-8",
    )


def test_transmission_map_renders(macro_web_client, tmp_path):
    """传导地图上 web：路由渲染 regime banner + 每只持仓暴露行（不再 404 死指针）。"""
    _write_transmission_map(tmp_path)
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/transmission-map")
    assert r.status_code == 200
    assert "贵州茅台" in r.text                       # 持仓行
    assert "美紧中松分化体制" in r.text                # regime composite banner
    assert "滞胀" in r.text                            # 象限
    assert "人民币内需防御票" in r.text                # plain 人话
    assert "中美地缘/关税" in r.text                   # 类别尾部


def test_transmission_map_404_for_non_macro(macro_web_client):
    """非 macro topic 命中该路由应 404（类型守卫，而非通配吞掉）。"""
    import prism.scripts.topic as t
    import prism.scripts.manifest as m
    t.create_topic("cn-industry-y", "某行业", "industry", "Q", "CN", "deep", VARIANT)
    m.create_manifest("cn-industry-y", VARIANT)
    r = macro_web_client.get(f"/prism/cn-industry-y/{VARIANT}/transmission-map")
    assert r.status_code == 404


def test_macro_detail_has_transmission_tab(macro_web_client):
    """macro 详情页 tab 条新增「传导地图」，指向 transmission-map。"""
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}")
    assert r.status_code == 200
    assert "传导地图" in r.text
    assert f"/prism/{SLUG}/{VARIANT}/transmission-map" in r.text


def test_regime_read_annotations_have_alignment_hook(macro_web_client, tmp_path):
    """m_regime_read「活注解层」三句注解（这是什么/为什么看它/现在说明什么）需带对齐样式钩子，
    且每句渲染为以 <code> 标签起头的独立 li，供 CSS 把标签定宽成列、正文换行悬挂对齐。"""
    out = tmp_path / "prism" / "topics" / SLUG / VARIANT / "outputs"
    out.mkdir(parents=True, exist_ok=True)
    (out / "m_regime_read.md").write_text(
        "---\nslug: x\noutput_key: m_regime_read\n---\n"
        "### 关键输入指标\n\n"
        "**美国政策利率：3.50%–3.75%**\n"
        "- `这是什么`：全球资金价格的总锚。\n"
        "- `为什么看它`：利率体制的短端发动机。\n"
        "- `现在说明什么`：连续按兵不动，钱不会很快变便宜。\n",
        encoding="utf-8",
    )
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/m_regime_read")
    assert r.status_code == 200
    assert "regime-annot" in r.text                       # 对齐样式钩子（容器类）
    # 即便源文件「粗体标题行」与「- 注解项」之间漏了空行，也须渲染成真正的列表项
    # （否则退化成段落里的字面 `- ...`，既不换行也无从对齐）。
    assert "<li><code>这是什么</code>" in r.text
    assert "<li><code>为什么看它</code>" in r.text
    assert "<li><code>现在说明什么</code>" in r.text
    assert "- <code>这是什么</code>" not in r.text         # 不得留字面短横线


def test_eval_trace_renders_conclusions(macro_web_client):
    import prism.scripts.eval_snapshot as es
    es.append_evaluation(SLUG, VARIANT, {
        "input_snapshot": [{"name": "HY OAS", "value": 3.1, "as_of": "2026-06-01", "used": True}],
        "conclusions": [{"id": "liquidity", "label": "流动性体制", "state": "偏紧",
                         "based_on": [{"input": "HY OAS", "role": "confirming"}],
                         "causal": "HY OAS 走阔 → 风险偏好降 → 流动性偏紧"}]})
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/eval-trace")
    assert r.status_code == 200
    assert "流动性体制" in r.text
    assert "HY OAS 走阔" in r.text                  # causal 句


def test_eval_trace_404_for_non_macro(macro_web_client):
    import prism.scripts.topic as t
    import prism.scripts.manifest as m
    t.create_topic("cn-ind-z", "某行业", "industry", "Q", "CN", "deep", VARIANT)
    m.create_manifest("cn-ind-z", VARIANT)
    assert macro_web_client.get(f"/prism/cn-ind-z/{VARIANT}/eval-trace").status_code == 404


def test_macro_detail_has_eval_trace_tab(macro_web_client):
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}")
    assert r.status_code == 200
    assert "评估溯源" in r.text
    assert f"/prism/{SLUG}/{VARIANT}/eval-trace" in r.text


def test_macro_inputs_passes_diff(macro_web_client):
    """有快照时输入表能拿到 diff（用于 S3/S4 列）：现值与上次评估值都出现。"""
    import prism.scripts.macro_registry as reg
    import prism.scripts.eval_snapshot as es
    reg.record_observation(SLUG, VARIANT, "HY OAS", value=3.5, as_of="2026-06-07")
    es.append_evaluation(SLUG, VARIANT, {
        "input_snapshot": [{"name": "HY OAS", "value": 3.0, "as_of": "2026-06-01", "used": True}],
        "conclusions": [{"id": "liquidity", "based_on": [{"input": "HY OAS", "role": "confirming"}]}]})
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/macro-inputs")
    assert r.status_code == 200
    assert "3.0" in r.text and "3.5" in r.text     # 上次评估值 + 现值


def test_alert_board_shows_alert_series(macro_web_client):
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/macro-inputs")
    assert "承重报警序列" in r.text
    assert "HY OAS" in r.text          # 报警卡片里出现


def test_inputs_table_shows_participation(macro_web_client):
    import prism.scripts.macro_registry as reg
    import prism.scripts.eval_snapshot as es
    reg.record_observation(SLUG, VARIANT, "HY OAS", value=3.5, as_of="2026-06-07")
    es.append_evaluation(SLUG, VARIANT, {
        "input_snapshot": [{"name": "HY OAS", "value": 3.0, "as_of": "2026-06-01", "used": True}],
        "conclusions": [{"id": "liquidity", "based_on": [{"input": "HY OAS", "role": "confirming"}]}]})
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/macro-inputs")
    assert "参与" in r.text             # S4 参与徽章
    assert "liquidity" in r.text        # 支撑的结论 id
    assert "3.0" in r.text and "3.5" in r.text   # S3 上次评估值 + 现值


def test_monitoring_toggle_post_sets_enabled(macro_web_client):
    # fixture 里 HY OAS monitoring.enabled=True；POST enabled=false 关掉
    r = macro_web_client.post(f"/prism/{SLUG}/{VARIANT}/macro-inputs/monitoring",
                              data={"name": "HY OAS", "enabled": "false"}, follow_redirects=False)
    assert r.status_code == 303
    import prism.scripts.macro_registry as reg
    hy = next(e for e in reg.read_registry(SLUG, VARIANT)["inputs"] if e["name"] == "HY OAS")
    assert hy["monitoring"]["enabled"] is False


def test_monitoring_toggle_redirect_carries_anchor(macro_web_client):
    # 带 anchor → 重定向 Location 末尾带该行片段，浏览器滚回原行（不跳页顶）
    r = macro_web_client.post(f"/prism/{SLUG}/{VARIANT}/macro-inputs/monitoring",
                              data={"name": "HY OAS", "enabled": "false", "anchor": "input-3"},
                              follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"].endswith("/macro-inputs#input-3")


def test_monitoring_toggle_404_unknown_input(macro_web_client):
    r = macro_web_client.post(f"/prism/{SLUG}/{VARIANT}/macro-inputs/monitoring",
                              data={"name": "不存在的输入", "enabled": "true"}, follow_redirects=False)
    assert r.status_code == 404


def test_reeval_post_stamps_and_brief_shows(macro_web_client, monkeypatch):
    import prism.scripts.eval_snapshot as es
    import app.macro_jobs as mj
    monkeypatch.setattr(mj, "launch_reeval", lambda s, v, *, model=None: _FakeJob("job-re"))
    r = macro_web_client.post(f"/prism/{SLUG}/{VARIANT}/reeval", follow_redirects=False)
    assert r.status_code == 303
    assert es.read_eval_log(SLUG, VARIANT)["reeval_pending"] is not None
    r2 = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/macro-inputs")
    assert "重估简报" in r2.text


def test_reeval_launches_real_synthesis_job(macro_web_client, monkeypatch):
    """发起重估除盖戳外，还拉起一个真实合成 job（默认 opus4.8），JSON 回 job_id/name 供前端弹框。"""
    import app.macro_jobs as mj
    cap = {}

    def fake_launch_reeval(slug, variant, *, model=None):
        cap.update(slug=slug, variant=variant, model=model)
        return _FakeJob("job-re1")

    monkeypatch.setattr(mj, "launch_reeval", fake_launch_reeval)
    r = macro_web_client.post(f"/prism/{SLUG}/{VARIANT}/reeval",
                              headers={"Accept": "application/json"})
    assert r.status_code == 202
    body = r.json()
    assert body["job_id"] == "job-re1"
    assert body["name"] == mj.REEVAL_NAME == "__reeval__"
    assert body["model"] == mj.REEVAL_MODEL          # 默认 opus4.8
    assert cap["model"] == mj.REEVAL_MODEL


def test_reeval_passes_selected_model(macro_web_client, monkeypatch):
    """模型下拉选了 sonnet → 透传给 launch_reeval。"""
    import app.macro_jobs as mj
    cap = {}
    monkeypatch.setattr(mj, "launch_reeval",
                        lambda s, v, *, model=None: cap.update(model=model) or _FakeJob("j"))
    r = macro_web_client.post(f"/prism/{SLUG}/{VARIANT}/reeval",
                              data={"model": "claude-sonnet-4-6"},
                              headers={"Accept": "application/json"})
    assert r.status_code == 202
    assert cap["model"] == "claude-sonnet-4-6"


def test_reeval_output_endpoint_serves_reeval_cache(macro_web_client, monkeypatch, tmp_path):
    """重估输出走同一缓存端点（name=__reeval__）。"""
    import app.macro_jobs as mj
    _seed_cache(monkeypatch, tmp_path, mj.REEVAL_NAME, text="合成日志第一行\n第二行")
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/macro-inputs/output",
                             params={"name": mj.REEVAL_NAME})
    assert r.status_code == 200
    assert r.json()["text"] == "合成日志第一行\n第二行"


def test_affected_conclusions_render_chinese(macro_web_client):
    """变更汇总/重估简报的「受影响结论」显示中文 label（综合判断…），不再是裸 id。"""
    import prism.scripts.macro_registry as reg
    import prism.scripts.eval_snapshot as es
    reg.record_observation(SLUG, VARIANT, "HY OAS", value=3.5, as_of="2026-06-07")
    es.append_evaluation(SLUG, VARIANT, {
        "input_snapshot": [{"name": "HY OAS", "value": 3.0, "as_of": "2026-06-01", "used": True}],
        "conclusions": [{"id": "liquidity_us", "label": "美国流动性体制", "state": "偏紧",
                         "based_on": [{"input": "HY OAS", "role": "confirming"}],
                         "causal": "HY OAS 走阔 → 流动性偏紧"}]})
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/macro-inputs")
    assert r.status_code == 200
    assert "美国流动性体制" in r.text          # 中文 label
    assert ">liquidity_us<" not in r.text       # 不再裸露英文 id


def test_primer_uses_links_not_bare_filenames():
    """00_primer 正文里对后台产物的引用要用人话锚链，不留裸文件名（web 上不可点/看不懂）。

    直接读真实仓库文件做内容守卫（fixture 的 tmp topic 不含 primer）。frontmatter
    的 companion:/sources_note: 合法命名文件，故剥掉 frontmatter 只查正文。
    """
    repo = Path(__file__).resolve().parent.parent
    raw = (repo / "prism" / "topics" / SLUG / VARIANT / "outputs" / "00_primer.md").read_text("utf-8")
    body = raw.split("---", 2)[-1]  # 剥 YAML frontmatter，只留正文
    assert f"](/prism/{SLUG}/{VARIANT}/m_regime_read)" in body        # 活读数锚链
    assert f"](/prism/{SLUG}/{VARIANT}/transmission-map)" in body     # 传导地图锚链
    assert "transmission_map.yaml" not in body                        # 正文不留裸后台文件名
    assert "m_regime_read.md" not in body


def test_inputs_table_shows_source_and_grades(macro_web_client):
    import prism.scripts.macro_registry as reg
    reg.upsert_input(SLUG, VARIANT, {
        "name": "MOVE 债市波动率",
        "source": "ICE", "source_url": "https://example.com/move",
        "authority": "primary", "availability": "scriptable_todo"})
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/macro-inputs")
    assert "https://example.com/move" in r.text     # 具体源链接
    assert "primary" in r.text                       # 权威性
    assert "待脚本" in r.text                          # availability=scriptable_todo 的人话标签


def test_alert_board_is_table(macro_web_client):
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/macro-inputs")
    assert "承重报警序列" in r.text
    assert "支撑结论" in r.text          # 表格化后新表头列
    assert "alert-cards" not in r.text   # 卡片容器类（含 CSS）已移除


def test_change_summary_no_snapshot_hidden(macro_web_client):
    # fixture 未 append_evaluation → 无快照 → 不显示变更汇总
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/macro-inputs")
    assert "变更汇总" not in r.text


# --- 手动 headless LLM 取数端点（后台 job 化）---

class _FakeJob:
    def __init__(self, jid):
        self.id = jid


def test_macro_fetch_llm_launches_jobs(macro_web_client, monkeypatch):
    """POST 对每个合格输入 launch 一个后台 job，立即 202 返回 {jobs: {name: job_id}}，不阻塞。"""
    import prism.scripts.macro_registry as reg
    import app.macro_jobs as mj
    reg.upsert_input(SLUG, VARIANT, {
        "name": "ISM PMI", "tier": "A", "cadence_type": "series", "targets": ["rates"],
        "mechanism": "CD", "causal_sentence": "x", "importance": "load_bearing",
        "availability": "llm", "source_url": "https://ism"})
    launched = []

    def fake_launch(slug, variant, name, *, entry):
        launched.append((slug, variant, name, entry.get("availability")))
        return _FakeJob(f"job-{name}")

    monkeypatch.setattr(mj, "launch", fake_launch)
    r = macro_web_client.post(f"/prism/{SLUG}/{VARIANT}/macro-inputs/fetch-llm",
                              data={"names": "ISM PMI", "anchor": "input-0"},
                              headers={"Accept": "application/json"})
    assert r.status_code == 202
    body = r.json()
    assert body["jobs"] == {"ISM PMI": "job-ISM PMI"}
    assert body["started"] == ["ISM PMI"]
    assert launched and launched[0][2] == "ISM PMI" and launched[0][3] == "llm"


def test_macro_fetch_llm_filters_ineligible(macro_web_client, monkeypatch):
    """HY OAS 是 scripted（fixture）→ 不在 llm/todo 轴；传它应被过滤、launch 不被调用。"""
    import app.macro_jobs as mj
    seen = {"n": 0}

    def fake_launch(slug, variant, name, *, entry):
        seen["n"] += 1
        return _FakeJob("x")

    monkeypatch.setattr(mj, "launch", fake_launch)
    r = macro_web_client.post(f"/prism/{SLUG}/{VARIANT}/macro-inputs/fetch-llm",
                              data={"names": "HY OAS"}, headers={"Accept": "application/json"})
    assert r.status_code == 202
    assert seen["n"] == 0
    assert r.json()["jobs"] == {}


def test_macro_fetch_llm_no_js_fallback_redirects(macro_web_client, monkeypatch):
    """无 JS（非 JSON Accept）→ 303 回锚点（仍 launch 后台 job）。"""
    import prism.scripts.macro_registry as reg
    import app.macro_jobs as mj
    reg.upsert_input(SLUG, VARIANT, {
        "name": "ISM PMI", "tier": "A", "cadence_type": "series",
        "mechanism": "CD", "importance": "confirming", "availability": "llm"})
    monkeypatch.setattr(mj, "launch",
                        lambda s, v, n, *, entry: _FakeJob(f"job-{n}"))
    r = macro_web_client.post(f"/prism/{SLUG}/{VARIANT}/macro-inputs/fetch-llm",
                              data={"names": "ISM PMI", "anchor": "input-0"},
                              follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"].endswith("/macro-inputs#input-0")


def test_macro_jobs_status_and_stream_endpoints(macro_web_client, monkeypatch):
    """端到端（假 runner）：POST → /jobs 反映该 job → SSE 流重放输出行 + 终态。"""
    import prism.scripts.macro_registry as reg
    from prism.scripts import claude_runner
    reg.upsert_input(SLUG, VARIANT, {
        "name": "ISM PMI", "tier": "A", "cadence_type": "series",
        "mechanism": "CD", "importance": "confirming", "availability": "llm"})

    async def fake_runner(prompt, *, on_event, **kw):
        on_event({"type": "assistant",
                  "message": {"content": [{"type": "text", "text": "检索中"}]}})
        # 末尾合法空 JSON → parse 成功 → 终态 done（不触发 registry 写入）
        on_event({"type": "result", "total_cost_usd": 0.02, "duration_ms": 1500,
                  "session_id": "sid-w", "result": "```json\n[]\n```"})
        return ("ok", 0)

    monkeypatch.setattr(claude_runner, "run_headless_streaming", fake_runner)
    r = macro_web_client.post(f"/prism/{SLUG}/{VARIANT}/macro-inputs/fetch-llm",
                              data={"names": "ISM PMI"}, headers={"Accept": "application/json"})
    assert r.status_code == 202
    job_id = r.json()["jobs"]["ISM PMI"]

    st = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/macro-inputs/jobs").json()
    assert "ISM PMI" in st and st["ISM PMI"]["job_id"] == job_id

    # SSE 流：subscribe 在终态吐收尾行后结束 → TestClient 拿到完整 body
    s = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/macro-inputs/jobs/{job_id}/stream")
    assert s.status_code == 200
    assert "text/event-stream" in s.headers["content-type"]
    assert "检索中" in s.text
    assert "完成" in s.text          # 终态收尾行


def test_macro_jobs_stream_404_unknown(macro_web_client):
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/macro-inputs/jobs/job-nope/stream")
    assert r.status_code == 404


def test_inputs_table_shows_evidence_and_acq_note(macro_web_client):
    """observed.evidence（原因）与 acq_note（promote 判定）要在表里显示。"""
    import prism.scripts.macro_registry as reg
    reg.upsert_input(SLUG, VARIANT, {
        "name": "ISM PMI", "tier": "A", "cadence_type": "series",
        "mechanism": "CD", "importance": "confirming", "availability": "llm",
        "observed": {"value": 48.7, "as_of": "2026-06-02",
                     "evidence": "ISM 官网 6 月制造业 PMI 报告",
                     "acq_note": "无固定 JSON 端点，须人工检索，暂不可脚本化"}})
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/macro-inputs")
    assert "原因：" in r.text and "ISM 官网" in r.text
    assert "判定：" in r.text and "不可脚本化" in r.text


def test_inputs_table_shows_due_badge(macro_web_client):
    """开监控的 llm series 项 → due_llm_monitor_names 选中 → 渲染「到期·待拉取」提示徽章。"""
    import prism.scripts.macro_registry as reg
    reg.upsert_input(SLUG, VARIANT, {
        "name": "MOVE", "tier": "B", "cadence_type": "series",
        "mechanism": "CO", "importance": "confirming",
        "availability": "llm", "monitoring": {"enabled": True}})
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/macro-inputs")
    assert "到期·待拉取" in r.text


def test_inputs_table_shows_inflight_badge_from_jobs(macro_web_client, monkeypatch):
    """服务端 macro_jobs.status 报某项在途 → 表里出现「拉取中」徽章 + 查看输出按钮（刷新后状态一致）。"""
    import prism.scripts.macro_registry as reg
    import app.macro_jobs as mj
    reg.upsert_input(SLUG, VARIANT, {
        "name": "ISM PMI", "tier": "A", "cadence_type": "series",
        "mechanism": "CD", "importance": "confirming", "availability": "llm"})
    monkeypatch.setattr(mj, "status", lambda s, v: {
        "ISM PMI": {"status": "running", "job_id": "job-7", "started_at": 1.0, "inflight": True}})
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/macro-inputs")
    assert "拉取中" in r.text
    assert 'data-job-id="job-7"' in r.text
    assert "查看输出" in r.text


def test_macro_fetch_llm_404_non_macro(macro_web_client):
    import prism.scripts.topic as t
    import prism.scripts.manifest as m
    t.create_topic("cn-ind-y", "某行业", "industry", "Q", "CN", "deep", VARIANT)
    m.create_manifest("cn-ind-y", VARIANT)
    r = macro_web_client.post(f"/prism/cn-ind-y/{VARIANT}/macro-inputs/fetch-llm",
                              data={"names": "x"}, follow_redirects=False)
    assert r.status_code == 404


def test_change_summary_lists_changed(macro_web_client):
    import prism.scripts.macro_registry as reg
    import prism.scripts.eval_snapshot as es
    reg.record_observation(SLUG, VARIANT, "HY OAS", value=3.5, as_of="2026-06-07")
    es.append_evaluation(SLUG, VARIANT, {
        "input_snapshot": [{"name": "HY OAS", "value": 3.0, "as_of": "2026-06-01", "used": True}],
        "conclusions": [{"id": "liquidity",
                         "based_on": [{"input": "HY OAS", "role": "confirming"}]}]})
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/macro-inputs")
    assert "变更汇总" in r.text
    assert "3.0" in r.text and "3.5" in r.text


def test_change_summary_no_change_message(macro_web_client):
    import prism.scripts.eval_snapshot as es
    # 有快照、但 HY OAS 现值仍未抓（None）→ 有快照无变化
    es.append_evaluation(SLUG, VARIANT, {
        "input_snapshot": [{"name": "HY OAS", "value": None, "as_of": "2026-06-01", "used": False}],
        "conclusions": []})
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/macro-inputs")
    assert "变更汇总" in r.text
    assert "自上次评估无变化" in r.text


def test_inputs_table_chinese_labels(macro_web_client):
    # fixture HY OAS：cadence series / targets liquidity / importance confirming
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/macro-inputs")
    assert "序列" in r.text       # cadence series → 序列
    assert "流动性" in r.text      # target liquidity → 流动性
    assert "确认" in r.text        # importance confirming → 确认


def test_inputs_table_cadence_tooltip(macro_web_client):
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/macro-inputs")
    assert "可连续抓取的常规时间序列" in r.text   # series 悬停释义


def test_inputs_table_mechanism_tooltip(macro_web_client):
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/macro-inputs")
    assert "同步读数" in r.text     # HY OAS mechanism CO → 悬停释义


def test_eval_trace_has_logic_label(macro_web_client):
    import prism.scripts.eval_snapshot as es
    es.append_evaluation(SLUG, VARIANT, {
        "input_snapshot": [{"name": "HY OAS", "value": 3.1, "as_of": "2026-06-01", "used": True}],
        "conclusions": [{"id": "liquidity", "label": "流动性体制", "state": "偏紧",
                         "based_on": [{"input": "HY OAS", "role": "confirming"}],
                         "causal": "HY OAS 走阔 → 流动性偏紧"}]})
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/eval-trace")
    assert "评估逻辑" in r.text


# --- 单条脚本抓取端点（scripted 行手动「抓取」键）---

def test_macro_fetch_script_invokes_fred_with_only(macro_web_client, monkeypatch):
    """scripted/fred-api 项 → 调 run_fred_fetch(only={该项})，零 LLM。"""
    from prism.scripts import fred_fetch
    seen = {}

    def fake(slug, variant, *, client=None, only=None):
        seen["call"] = (slug, variant, only)
        return {"fetched": 1, "derived": 0, "skipped": 0, "failed": 0}

    monkeypatch.setattr(fred_fetch, "run_fred_fetch", fake)
    r = macro_web_client.post(f"/prism/{SLUG}/{VARIANT}/macro-inputs/fetch-script",
                              data={"name": "HY OAS", "anchor": "input-0"},
                              follow_redirects=False)
    assert r.status_code == 303
    assert seen["call"][2] == {"HY OAS"}   # only 限定单条


def test_macro_fetch_script_json_returns_summary(macro_web_client, monkeypatch):
    from prism.scripts import fred_fetch
    monkeypatch.setattr(fred_fetch, "run_fred_fetch",
                        lambda s, v, *, client=None, only=None:
                        {"fetched": 1, "derived": 0, "skipped": 0, "failed": 0})
    r = macro_web_client.post(f"/prism/{SLUG}/{VARIANT}/macro-inputs/fetch-script",
                              data={"name": "HY OAS"}, headers={"Accept": "application/json"})
    assert r.status_code == 200
    body = r.json()
    assert body["method"] == "fred-api" and body["fetched"] == 1


def test_macro_fetch_script_400_non_scripted(macro_web_client):
    import prism.scripts.macro_registry as reg
    reg.upsert_input(SLUG, VARIANT, {
        "name": "LLM项", "tier": "B", "cadence_type": "series",
        "mechanism": "CO", "importance": "confirming", "availability": "llm"})
    r = macro_web_client.post(f"/prism/{SLUG}/{VARIANT}/macro-inputs/fetch-script",
                              data={"name": "LLM项"}, follow_redirects=False)
    assert r.status_code == 400


def test_macro_fetch_script_404_unknown_input(macro_web_client):
    r = macro_web_client.post(f"/prism/{SLUG}/{VARIANT}/macro-inputs/fetch-script",
                              data={"name": "查无此项"}, follow_redirects=False)
    assert r.status_code == 404


# --- JSON 回包（前端展进度/结果用，Accept: application/json）---

def test_fetch_llm_json_returns_jobs(macro_web_client, monkeypatch):
    import prism.scripts.macro_registry as reg
    import app.macro_jobs as mj
    reg.upsert_input(SLUG, VARIANT, {
        "name": "ISM PMI", "tier": "A", "cadence_type": "series",
        "mechanism": "CD", "importance": "confirming", "availability": "llm"})

    monkeypatch.setattr(mj, "launch",
                        lambda s, v, n, *, entry: _FakeJob(f"job-{n}"))
    r = macro_web_client.post(f"/prism/{SLUG}/{VARIANT}/macro-inputs/fetch-llm",
                              data={"names": "ISM PMI"}, headers={"Accept": "application/json"})
    assert r.status_code == 202
    body = r.json()
    assert body["jobs"] == {"ISM PMI": "job-ISM PMI"} and body["started"] == ["ISM PMI"]


def test_reeval_json_returns_counts(macro_web_client, monkeypatch):
    import app.macro_jobs as mj
    monkeypatch.setattr(mj, "launch_reeval", lambda s, v, *, model=None: _FakeJob("job-rc"))
    r = macro_web_client.post(f"/prism/{SLUG}/{VARIANT}/reeval",
                              headers={"Accept": "application/json"})
    assert r.status_code == 202
    body = r.json()
    assert {"changed", "breached", "due", "affected"}.issubset(body.keys())


# --- 展示细节：上海时区 / 列图例 / 结果横幅默认隐藏 ---

def test_shanghai_filter_converts_utc():
    from app.routes.prism import _fmt_shanghai
    assert _fmt_shanghai("2026-06-09T00:30:00+00:00") == "2026-06-09 08:30"   # UTC→上海 +8
    assert _fmt_shanghai("") == "" and _fmt_shanghai(None) == ""


def test_inputs_table_shows_checked_at_in_shanghai(macro_web_client):
    import prism.scripts.macro_registry as reg
    reg.upsert_input(SLUG, VARIANT, {
        "name": "HY OAS", "observed": {"value": 4.0, "checked_at": "2026-06-09T00:30:00+00:00"}})
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/macro-inputs")
    assert "2026-06-09 08:30" in r.text   # 上次拉取按上海时区展示


def test_inputs_table_has_column_legend(macro_web_client):
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/macro-inputs")
    assert "列含义说明" in r.text
    assert "因果驱动" in r.text          # 机制 CD 释义在图例里


def test_flash_banner_hidden_by_default(macro_web_client):
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/macro-inputs")
    assert 'id="flash-banner"' in r.text and "hidden" in r.text   # 默认隐藏，点操作后才显示


# --- 批量按钮 = 只跑 scripted（零 LLM）---

def test_fetch_script_all_runs_fred_and_recipe(macro_web_client, monkeypatch):
    """批量端点跑 fred + recipe 全量（不传 only），合并计数回 {fred,recipe,fetched}；零 headless。"""
    from prism.scripts import fred_fetch, recipe_fetch
    calls = {}

    def fake_fred(slug, variant, *, client=None, only=None):
        calls["fred"] = (slug, variant, only)
        return {"fetched": 2, "derived": 0, "skipped": 0, "failed": 0}

    def fake_recipe(slug, variant, *, client=None, only=None):
        calls["recipe"] = (slug, variant, only)
        return {"fetched": 1, "skipped_todo": 0, "skipped_llm": 0, "failed": 0}

    monkeypatch.setattr(fred_fetch, "run_fred_fetch", fake_fred)
    monkeypatch.setattr(recipe_fetch, "run_recipe_fetch", fake_recipe)
    r = macro_web_client.post(f"/prism/{SLUG}/{VARIANT}/macro-inputs/fetch-script-all",
                              headers={"Accept": "application/json"})
    assert r.status_code == 200
    body = r.json()
    assert body["fred"] == 2 and body["recipe"] == 1 and body["fetched"] == 3
    assert calls["fred"][2] is None and calls["recipe"][2] is None   # 不传 only = 全量


def test_fetch_script_all_404_non_macro(macro_web_client):
    import prism.scripts.topic as t
    import prism.scripts.manifest as m
    t.create_topic("cn-ind-sa", "某行业", "industry", "Q", "CN", "deep", VARIANT)
    m.create_manifest("cn-ind-sa", VARIANT)
    r = macro_web_client.post(f"/prism/cn-ind-sa/{VARIANT}/macro-inputs/fetch-script-all",
                              follow_redirects=False)
    assert r.status_code == 404


def test_batch_button_targets_fetch_script_all(macro_web_client):
    """顶部批量按钮指向 fetch-script-all，文案标明只刷脚本项、零成本。"""
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/macro-inputs")
    assert "fetch-script-all" in r.text
    assert "批量刷新脚本项" in r.text


# --- 弹框 resume 重判端点 + composer ---

def test_jobs_say_returns_202(macro_web_client, monkeypatch):
    """POST /jobs/say（name+message[+model]）→ macro_jobs.say → 202 {job_id}。"""
    import app.macro_jobs as mj
    captured = {}

    async def fake_say(slug, variant, name, message, *, model=None):
        captured.update(slug=slug, variant=variant, name=name, message=message, model=model)
        return _FakeJob("job-r1")

    monkeypatch.setattr(mj, "say", fake_say)
    r = macro_web_client.post(f"/prism/{SLUG}/{VARIANT}/macro-inputs/jobs/say",
                              data={"name": "HY OAS", "message": "用 sonnet 重判", "model": "sonnet"},
                              headers={"Accept": "application/json"})
    assert r.status_code == 202
    assert r.json()["job_id"] == "job-r1"
    assert captured["name"] == "HY OAS" and captured["model"] == "sonnet"
    assert captured["message"] == "用 sonnet 重判"


def test_jobs_say_404_when_no_session(macro_web_client, monkeypatch):
    """无可续会话（say 返回 None）→ 404。"""
    import app.macro_jobs as mj

    async def fake_say(slug, variant, name, message, *, model=None):
        return None

    monkeypatch.setattr(mj, "say", fake_say)
    r = macro_web_client.post(f"/prism/{SLUG}/{VARIANT}/macro-inputs/jobs/say",
                              data={"name": "HY OAS", "message": "x"})
    assert r.status_code == 404


def test_modal_has_resume_composer(macro_web_client):
    """弹框底部有重判 composer：无模型下拉（改用 /model 指令切换）+ say 端点。"""
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/macro-inputs")
    assert "重判" in r.text
    assert "jobs/say" in r.text or "/say" in r.text
    assert "/model" in r.text                       # 提示用 /model 指令切换模型
    assert 'class="compose-model"' not in r.text    # 不再有模型下拉


def test_poll_defers_reload_while_modal_open(macro_web_client):
    """轮询检测到拉取完成时，若弹框正打开，不得整页 reload（会冲掉对话窗口/历史）；
    改为标记 pendingReload，等用户主动关闭弹框再刷新。"""
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/macro-inputs")
    assert "pendingReload" in r.text                 # 存在延迟刷新标记
    # 轮询的 done 分支不再无条件 reload：必须先判 modal.open
    poll_done = r.text.split("if (done)", 1)[1].split("}", 1)[0]
    assert "modal.open" in poll_done or "pendingReload" in poll_done


def test_compose_enter_ignores_ime_composition(macro_web_client):
    """输入法选词回车不得被当成发送：keydown 处理 Enter 时必须排除 IME 组字态
    （isComposing / keyCode 229），否则中文选字回车就误发。"""
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/macro-inputs")
    # Enter 分支需带组字态守卫
    enter_branch = r.text.split('e.key === "Enter"', 1)[1].split(")", 1)[0]
    assert "isComposing" in enter_branch or "229" in enter_branch


# --- 表格审计：上次 $X · 时间（解决 cost 闪一下就没）---

def test_inputs_table_shows_last_cost(macro_web_client, monkeypatch, tmp_path):
    import json
    import app.macro_jobs as mj
    root = tmp_path / "mf"
    monkeypatch.setattr(mj, "LOG_ROOT", root)
    d = root / SLUG / VARIANT
    d.mkdir(parents=True)
    safe = mj._safe("HY OAS")
    (d / f"{safe}.meta.json").write_text(json.dumps(
        {"name": "HY OAS", "cost": 0.0123,
         "ended_at": "2026-06-09T00:30:00+00:00", "session_id": "s"}), encoding="utf-8")
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/macro-inputs")
    assert "上次 $0.0123" in r.text


# --- 「查看输出」常驻：只要落盘缓存在就显示，可看缓存输出 ---

def _seed_cache(monkeypatch, tmp_path, name, *, text="· 模型 claude-haiku-4.5\n值=50", cost=0.02):
    import json
    import app.macro_jobs as mj
    root = tmp_path / "mf"
    monkeypatch.setattr(mj, "LOG_ROOT", root)
    d = root / SLUG / VARIANT
    d.mkdir(parents=True, exist_ok=True)
    safe = mj._safe(name)
    (d / f"{safe}.log").write_text(text, encoding="utf-8")
    (d / f"{safe}.meta.json").write_text(json.dumps(
        {"name": name, "cost": cost, "status": "done",
         "ended_at": "2026-06-09T00:30:00+00:00", "session_id": "s",
         "model": "claude-haiku-4.5"}), encoding="utf-8")


def test_output_endpoint_returns_cached_log(macro_web_client, monkeypatch, tmp_path):
    """GET …/macro-inputs/output?name= 回落盘 .log 全文（job 超 TTL 后仍可看）。"""
    _seed_cache(monkeypatch, tmp_path, "ISM 制造业 PMI", text="第一行\n第二行")
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/macro-inputs/output",
                             params={"name": "ISM 制造业 PMI"})
    assert r.status_code == 200
    assert r.json()["text"] == "第一行\n第二行"


def test_output_endpoint_404_when_no_cache(macro_web_client, monkeypatch, tmp_path):
    import app.macro_jobs as mj
    monkeypatch.setattr(mj, "LOG_ROOT", tmp_path / "empty")
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/macro-inputs/output",
                             params={"name": "查无此项"})
    assert r.status_code == 404


def test_view_output_button_shows_for_cached_row_without_live_job(macro_web_client, monkeypatch, tmp_path):
    """无在途 job、但有落盘缓存的 llm 行，也要渲染「查看输出」（按 data-name 读缓存）。"""
    import prism.scripts.macro_registry as reg
    reg.upsert_input(SLUG, VARIANT, {
        "name": "MPR", "tier": "A", "cadence_type": "policy", "targets": ["rates"],
        "mechanism": "CD", "importance": "load_bearing", "causal_sentence": "x→y→z",
        "availability": "llm", "source_url": "https://example.gov/mpr.htm",
    })
    _seed_cache(monkeypatch, tmp_path, "MPR")
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/macro-inputs")
    assert 'class="view-output-btn" data-name="MPR"' in r.text


def test_pull_auto_opens_output_modal(macro_web_client):
    """点「⟳ 拉取」（单条）后自动弹出输出框：fetch-llm 成功分支调用 openOutput。"""
    r = macro_web_client.get(f"/prism/{SLUG}/{VARIANT}/macro-inputs")
    assert "openOutput(jobs[names[0]]" in r.text
