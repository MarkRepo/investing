#!/usr/bin/env python3
"""Workstream 2 — topic 图谱 / 跨层复用 单测。

覆盖：set_parent（tier/自指/解链/缺父校验）、get_relative_outputs（父+子成稿路径，
只列存在文件）、suggest_relatives（ticker 跨 sidecar 强信号 + geo 大小写无关 + 加权排序）、
gap_detector.relative_updated（亲属比本 case 新才 flag，flag-only）。

路径隔离：topic 与 outputs 两个模块各自算根，需同时 monkeypatch
topic._topics_dir 与 outputs._PRISM_ROOT 指向同一 tmp 布局（tmp/topics/<slug>/<variant>）。
"""
import os
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from prism.scripts import topic as topic_io
from prism.scripts import outputs as outputs_io
from prism.scripts import gap_detector


@contextmanager
def _sandbox():
    """tmp/topics 作 topics 根，同步 patch topic._topics_dir + outputs._PRISM_ROOT。"""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        topics_dir = tmp_root / "topics"
        topics_dir.mkdir(parents=True, exist_ok=True)
        orig_topics_dir = topic_io._topics_dir
        orig_outputs_root = outputs_io._PRISM_ROOT
        topic_io._topics_dir = lambda: topics_dir
        outputs_io._PRISM_ROOT = tmp_root
        try:
            yield tmp_root
        finally:
            topic_io._topics_dir = orig_topics_dir
            outputs_io._PRISM_ROOT = orig_outputs_root


def _write(path: Path, text: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------

def test_set_parent_validation():
    with _sandbox():
        topic_io.create_topic("ind", "行业", "industry", "Q", "CN", "deep", "v")
        topic_io.create_topic("arn", "竞技场", "arena", "Q", "CN", "deep", "v")
        topic_io.create_topic(
            "co", "公司", "company", "Q", "CN", "deep", "v",
            ticker="SZSE_002460", short_name="赣锋",
        )

        # 合法：industry(2) 作 arena(1) 父
        topic_io.set_parent("arn", "v", "ind")
        assert topic_io.read_topic("arn", "v")["parent_topic"] == "ind"

        # 合法：arena(1) 作 company(0) 父
        topic_io.set_parent("co", "v", "arn")
        assert topic_io.read_topic("co", "v")["parent_topic"] == "arn"

        # 解链
        topic_io.set_parent("co", "v", None)
        assert topic_io.read_topic("co", "v")["parent_topic"] is None

        # 自指 raise
        try:
            topic_io.set_parent("arn", "v", "arn")
            assert False, "自指应 raise"
        except ValueError:
            pass

        # tier 非递增 raise：company(0) 不能作 industry(2) 父
        try:
            topic_io.set_parent("ind", "v", "co")
            assert False, "tier 非递增应 raise"
        except ValueError:
            pass

        # 同 tier raise：arena 不能作 arena 父（造一个第二 arena）
        topic_io.create_topic("arn2", "竞技场2", "arena", "Q", "CN", "deep", "v")
        try:
            topic_io.set_parent("arn", "v", "arn2")
            assert False, "同 tier 应 raise"
        except ValueError:
            pass

        # 缺父 raise
        try:
            topic_io.set_parent("arn", "v", "nope")
            assert False, "父不存在应 raise"
        except ValueError:
            pass
    print("✓ test_set_parent_validation")


def test_get_relative_outputs():
    with _sandbox() as root:
        topic_io.create_topic("ind", "行业", "industry", "Q", "GLOBAL", "deep", "v")
        topic_io.create_topic("arn", "竞技场", "arena", "Q", "GLOBAL", "deep", "v")
        topic_io.create_topic(
            "co", "公司", "company", "Q", "CN", "deep", "v",
            ticker="SZSE_002460", short_name="赣锋",
        )
        topic_io.set_parent("arn", "v", "ind")
        topic_io.set_parent("co", "v", "arn")

        # 父 industry 落 primer + thesis_v0 + 09 sidecar；子 company 落 case
        ind_dir = root / "topics" / "ind" / "v"
        _write(ind_dir / "outputs" / "00_primer.md")
        _write(ind_dir / "thesis_v0.md")
        _write(ind_dir / "outputs" / "09_industry_to_arenas.yaml", "slug: ind\n")
        co_dir = root / "topics" / "co" / "v"
        _write(co_dir / "outputs" / "c_investment_case.md")

        rel = topic_io.get_relative_outputs("arn", "v")
        # 父
        assert rel["parent"] is not None
        assert rel["parent"]["slug"] == "ind"
        po = rel["parent"]["outputs"]
        assert "primer" in po and "thesis" in po and "sidecar" in po
        # 父没写 a_arena_case → 不应有 case 键（arena case 才叫 a_arena_case，且这是 industry）
        assert "case" not in po
        # 子
        assert len(rel["children"]) == 1
        child = rel["children"][0]
        assert child["slug"] == "co"
        assert "case" in child["outputs"]            # c_investment_case.md 存在
        assert "primer" not in child["outputs"]      # 没写 → 不列
    print("✓ test_get_relative_outputs")


def test_suggest_relatives_ticker_and_geo():
    with _sandbox() as root:
        # arena geo 大写 GLOBAL，company geo CN；靠 ticker 跨 sidecar 命中（强信号）
        topic_io.create_topic("arn", "竞技场", "arena", "Q", "GLOBAL", "deep", "v")
        topic_io.create_topic(
            "co", "公司", "company", "Q", "CN", "deep", "v",
            ticker="SZSE_002460", short_name="赣锋",
        )
        # arena 的 10_peer_matrix 含该 ticker
        arn_dir = root / "topics" / "arn" / "v"
        _write(
            arn_dir / "outputs" / "10_peer_matrix.yaml",
            "companies:\n  - ticker: SZSE_002460\n",
        )

        # company 端：arena 应作父候选，ticker-in-their-matrix 强信号 score≥3
        r = topic_io.suggest_relatives("co", "v")
        pc = {c["slug"]: c for c in r["parent_candidates"]}
        assert "arn" in pc, "arena 应在 company 父候选"
        assert "ticker-in-their-matrix" in pc["arn"]["signals"]
        assert pc["arn"]["score"] >= 3

        # arena 端：company 应作子候选（双向、顺序无关）
        r2 = topic_io.suggest_relatives("arn", "v")
        cc = {c["slug"]: c for c in r2["child_candidates"]}
        assert "co" in cc, "company 应在 arena 子候选"
        assert "their-ticker-in-our-matrix" in cc["co"]["signals"]

        # geo 大小写无关：造一个 GLOBAL（大写）industry，arena(global) 应经 geo 命中
        topic_io.create_topic("ind", "行业", "industry", "Q", "global", "deep", "v")
        r3 = topic_io.suggest_relatives("arn", "v")
        pc3 = {c["slug"]: c for c in r3["parent_candidates"]}
        assert "ind" in pc3 and "geo" in pc3["ind"]["signals"]
    print("✓ test_suggest_relatives_ticker_and_geo")


def test_relative_updated_flag():
    with _sandbox() as root:
        topic_io.create_topic("ind", "行业", "industry", "Q", "GLOBAL", "deep", "v")
        topic_io.create_topic(
            "co", "公司", "company", "Q", "CN", "deep", "v",
            ticker="SZSE_002460", short_name="赣锋",
        )
        topic_io.set_parent("co", "v", "ind")

        # 父 industry case 文件
        ind_case = root / "topics" / "ind" / "v" / "outputs" / "i_industry_case.md"
        _write(ind_case)

        # 本 company case 已合成（registers last_updated=now）
        topic_io.set_output_status("co", "c_investment_case", "fresh", "v", version=1)
        our_lu = topic_io.read_topic("co", "v")["outputs_state"]["c_investment_case"]["last_updated"]
        from datetime import datetime
        our_ts = datetime.fromisoformat(our_lu).timestamp()

        # 负例：父 case 比本 case 旧 → 不 flag
        os.utime(ind_case, (our_ts - 1000, our_ts - 1000))
        rep = gap_detector.detect_gaps("co", "v")
        assert "relative_updated" in rep
        assert rep["relative_updated"] == [], "父更旧不应 flag"

        # 正例：父 case 比本 case 新 → flag 一条
        os.utime(ind_case, (our_ts + 1000, our_ts + 1000))
        rep2 = gap_detector.detect_gaps("co", "v")
        assert len(rep2["relative_updated"]) == 1
        f = rep2["relative_updated"][0]
        assert f["relative_slug"] == "ind"
        assert f["relative_output"] == "case"
        assert f["our_output"] == "c_investment_case"
        assert "🔗 relative-updated" in gap_detector.format_summary(rep2)

        # 边界：本 case 从未合成（无 last_updated）→ 返空（无借用可过时）
        topic_io.create_topic("co2", "公司2", "company", "Q", "CN", "deep", "v",
                              ticker="SZSE_300073", short_name="当升")
        topic_io.set_parent("co2", "v", "ind")
        rep3 = gap_detector.detect_gaps("co2", "v")
        assert rep3["relative_updated"] == []
    print("✓ test_relative_updated_flag")


if __name__ == "__main__":
    test_set_parent_validation()
    test_get_relative_outputs()
    test_suggest_relatives_ticker_and_geo()
    test_relative_updated_flag()
    print("\n所有 Workstream 2 单测通过 ✅")
