"""Query output state for topics. Zero LLM calls."""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import markdown as _md
import yaml

_PRISM_ROOT = Path(__file__).resolve().parent.parent

_OUTPUT_KEYS_LABELS = [
    ("01_business_panorama", "商业全景"),
    ("02_cycle_positioning", "周期定位"),
    ("03_narrative_ecology", "叙事谱系"),
    ("04_implied_expectations", "隐含预期与观点光谱"),
    ("05_historical_mirrors", "历史镜像"),
    ("06_risk_blindspots", "风险盲点"),
    ("07_decision_kit", "决策辅助"),
    ("08_living_feed", "信息流时间线"),
    ("10_peer_matrix", "同行矩阵"),
]

# Additional outputs that can be generated via workflows
_EXTRA_OUTPUTS_LABELS = [
    ("05-critic-review", "批评者评审"),
    ("09_industry_to_arenas", "产业→竞技场选拔"),
    ("_synthesis_brief", "K# 校准 brief（04 副产物）"),
]


def _is_drilldown_file(filename: str) -> bool:
    return filename.startswith("drilldown_") and filename.endswith(".md")


def _parse_drilldown_info(filepath: Path) -> dict:
    try:
        raw = filepath.read_text(encoding="utf-8")
        if raw.startswith("---"):
            frontmatter_end = raw.find("---", 3)
            if frontmatter_end > 0:
                import yaml
                frontmatter = yaml.safe_load(raw[3:frontmatter_end])
                if isinstance(frontmatter, dict):
                    return {
                        "question": frontmatter.get("question", ""),
                        "generated": frontmatter.get("generated"),
                    }
    except Exception:
        pass
    return {"question": "", "generated": None}


def _topic_dir(slug: str, variant: str) -> Path:
    if not variant:
        raise ValueError("必须显式指定 variant，例如 'sonnet' 或 'qwen3.6-plus'")
    return _PRISM_ROOT / "topics" / slug / variant


def _read_topic_yaml(slug: str, variant: str) -> dict:
    path = _topic_dir(slug, variant) / "topic.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Topic not found: {slug}/{variant}")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def list_outputs(slug: str, variant: str) -> list[dict]:
    data = _read_topic_yaml(slug, variant)
    outputs_state = data.get("outputs_state", {})
    result = []
    for key, label in _OUTPUT_KEYS_LABELS:
        if key not in outputs_state:
            continue  # skip keys not relevant to this topic type
        state = outputs_state[key]
        out_path = _topic_dir(slug, variant) / "outputs" / f"{key}.md"
        last_updated = state.get("last_updated")
        if isinstance(last_updated, date):
            last_updated = last_updated.isoformat()
        result.append({
            "key": key,
            "label": label,
            "status": state.get("status", "pending"),
            "version": state.get("version", 0),
            "last_updated": last_updated,
            "file_exists": out_path.is_file(),
        })
    # Add extra outputs that exist in the directory
    for key, label in _EXTRA_OUTPUTS_LABELS:
        out_path = _topic_dir(slug, variant) / "outputs" / f"{key}.md"
        if out_path.is_file():
            # Try to read frontmatter to get version/generated
            version = 1
            last_updated = None
            try:
                raw = out_path.read_text(encoding="utf-8")
                if raw.startswith("---"):
                    frontmatter_end = raw.find("---", 3)
                    if frontmatter_end > 0:
                        import yaml
                        frontmatter = yaml.safe_load(raw[3:frontmatter_end])
                        if isinstance(frontmatter, dict):
                            version = frontmatter.get("version", 1)
                            last_updated = frontmatter.get("generated")
                            if isinstance(last_updated, date):
                                last_updated = last_updated.isoformat()
            except Exception:
                pass
            result.append({
                "key": key,
                "label": label,
                "status": "fresh",
                "version": version,
                "last_updated": last_updated,
                "file_exists": True,
            })
    # Add drilldown outputs
    out_dir = _topic_dir(slug, variant) / "outputs"
    if out_dir.is_dir():
        drilldown_files = sorted([f for f in out_dir.iterdir() if f.is_file() and _is_drilldown_file(f.name)])
        for filepath in drilldown_files:
            info = _parse_drilldown_info(filepath)
            question = info.get("question", filepath.name)
            # Make a short label
            label = f"深度钻探：{question[:20]}..." if len(question) > 20 else f"深度钻探：{question}"
            drilldown_updated = info.get("generated")
            if isinstance(drilldown_updated, date):
                drilldown_updated = drilldown_updated.isoformat()
            result.append({
                "key": filepath.name[:-3],  # without .md
                "label": label,
                "status": "fresh",
                "version": 1,
                "last_updated": drilldown_updated,
                "file_exists": True,
                "is_drilldown": True,
            })
    return result


def extract_killer_questions(slug: str, variant: str, version: int) -> list[str]:
    """从 thesis_v{N}.md 解析所有 K# 编号（K1/K2/...），升序去重。"""
    import re
    path = _topic_dir(slug, variant) / f"thesis_v{version}.md"
    if not path.is_file():
        return []
    raw = path.read_text(encoding="utf-8")
    ks = set(re.findall(r"\bK(\d+)\b", raw))
    return [f"K{i}" for i in sorted(int(k) for k in ks)]


def extract_k_status(slug: str, variant: str, version: int) -> dict[str, str]:
    """从 thesis_v{N}.md 解析每个 K# 的验证状态。

    约定（见 04-synthesize/_shared.md 写 thesis_v1 章节）：
      - 已验证支持 → 'supported'
      - 已验证反驳 → 'refuted'
      - 仍未确定   → 'unverified'

    解析策略：在每个 K# 出现位置之后的 ~8 行内查找状态关键字，命中第一个为准。
    无关键字命中（v0 或不含现状段）→ 'unverified' 兜底，前端可视为「待验证」。

    返回 {K1: status, K2: status, ...}，仅包含 thesis 中实际出现的 K#。
    """
    import re
    path = _topic_dir(slug, variant) / f"thesis_v{version}.md"
    if not path.is_file():
        return {}
    raw = path.read_text(encoding="utf-8")
    lines = raw.splitlines()
    keywords = [
        ("supported", re.compile(r"已验证支持|已支持|✓\s*支持")),
        ("refuted", re.compile(r"已验证反驳|已反驳|✗\s*反驳|反驳")),
        ("unverified", re.compile(r"仍未确定|未确定|待验证|未验证")),
    ]
    ks_in_order = sorted(set(re.findall(r"\bK\d+\b", raw)),
                         key=lambda x: int(x[1:]))
    out: dict[str, str] = {}
    for k in ks_in_order:
        # locate first occurrence of K#
        idx = next((i for i, l in enumerate(lines) if re.search(rf"\b{k}\b", l)), None)
        if idx is None:
            continue
        window = "\n".join(lines[idx: idx + 8])
        status = "unverified"
        for s, pat in keywords:
            if pat.search(window):
                status = s
                break
        out[k] = status
    return out


def extract_research_questions(slug: str, variant: str, version: int) -> list[str]:
    """同上，但解析 Q# 编号（5.2 八问的引用）。"""
    import re
    path = _topic_dir(slug, variant) / f"thesis_v{version}.md"
    if not path.is_file():
        return []
    raw = path.read_text(encoding="utf-8")
    qs = set(re.findall(r"\bQ(\d+)\b", raw))
    return [f"Q{i}" for i in sorted(int(q) for q in qs)]


def validate_roadmap_thesis_coverage(slug: str, variant: str, version: int) -> dict:
    """校验 roadmap.yaml 的 L4 + materials 是否覆盖 thesis 的所有 Killer Question。

    返回：{
        'thesis_ks': [K1, K2, ...],         # thesis 里出现的 K#
        'l4_covered': [K1, K3],             # L4 question 的 addresses 字段引用的 K#
        'material_covered': [K1, K2],       # tier1/tier2/tier3 material 的 addresses 字段引用的 K#
        'uncovered_in_l4': [K2, K4, K5],    # L4 没有 question 对应的 K#
        'uncovered_in_material': [K3, K4],  # 没有任何 material 攻打的 K#
        'ok': bool,                          # 全部覆盖 == True
        'roadmap_exists': bool,
    }
    """
    import yaml
    roadmap_path = _topic_dir(slug, variant) / "roadmap.yaml"
    thesis_ks = extract_killer_questions(slug, variant, version)
    if not roadmap_path.is_file():
        return {
            "thesis_ks": thesis_ks, "l4_covered": [], "material_covered": [],
            "uncovered_in_l4": thesis_ks, "uncovered_in_material": thesis_ks,
            "ok": False, "roadmap_exists": False,
        }
    roadmap = yaml.safe_load(roadmap_path.read_text()) or {}

    l4 = (roadmap.get("learning_track") or {}).get("l4_hunting") or []
    l4_addrs: set[str] = set()
    for q in l4:
        for a in (q.get("addresses") or []):
            if a.startswith("K"):
                l4_addrs.add(a)

    mat_addrs: set[str] = set()
    for tier in ("tier1", "tier2", "tier3"):
        for m in (roadmap.get("material_priority") or {}).get(tier) or []:
            for a in (m.get("addresses") or []):
                if a.startswith("K"):
                    mat_addrs.add(a)

    l4_covered = [k for k in thesis_ks if k in l4_addrs]
    mat_covered = [k for k in thesis_ks if k in mat_addrs]
    uncovered_l4 = [k for k in thesis_ks if k not in l4_addrs]
    uncovered_mat = [k for k in thesis_ks if k not in mat_addrs]
    return {
        "thesis_ks": thesis_ks,
        "l4_covered": l4_covered,
        "material_covered": mat_covered,
        "uncovered_in_l4": uncovered_l4,
        "uncovered_in_material": uncovered_mat,
        "ok": not uncovered_l4 and not uncovered_mat,
        "roadmap_exists": True,
    }


def validate_manifest_coverage(slug: str, variant: str, version: int) -> dict:
    """校验已收集的 materials 是否覆盖 thesis 所有 Killer Question。

    与 validate_roadmap_thesis_coverage 区别：
    - roadmap 校验 = "计划要收什么"
    - manifest 校验 = "实际收了什么"
    两者可能背离——roadmap 100% 覆盖但 manifest K2=0 表示计划写了但没去收。

    返回：{
        'thesis_ks': [K1, K2, ...],
        'by_key': {'K1': [mat_dict, ...], 'K2': [], ...},  # 每个 K# 对应的 material
        'uncovered': ['K2'],
        'covered': ['K1', 'K3', 'K4', 'K5'],
        'coverage_pct': 80,
        'manifest_exists': bool,
    }
    """
    from . import manifest as manifest_io
    thesis_ks = extract_killer_questions(slug, variant, version)
    try:
        m = manifest_io.read_manifest(slug, variant)
    except FileNotFoundError:
        return {
            "thesis_ks": thesis_ks, "by_key": {k: [] for k in thesis_ks},
            "uncovered": thesis_ks, "covered": [], "coverage_pct": 0,
            "manifest_exists": False,
        }
    by_key: dict[str, list] = {k: [] for k in thesis_ks}
    for mat in m.get("materials", []) or []:
        for a in mat.get("addresses") or []:
            if a in by_key:
                by_key[a].append(mat)
    covered = [k for k in thesis_ks if by_key[k]]
    uncovered = [k for k in thesis_ks if not by_key[k]]
    pct = round(100 * len(covered) / len(thesis_ks)) if thesis_ks else 0
    return {
        "thesis_ks": thesis_ks,
        "by_key": by_key,
        "covered": covered,
        "uncovered": uncovered,
        "coverage_pct": pct,
        "manifest_exists": True,
    }


def read_thesis_html(slug: str, variant: str, version: int) -> str:
    """读取 thesis_v{N}.md 并渲染为 HTML。文件在 variant 根目录（非 outputs/）。
    渲染后给表格里的 K# 加锚点 span，方便 #K1 跳转和反查链接。
    """
    import re
    out_path = _topic_dir(slug, variant) / f"thesis_v{version}.md"
    if not out_path.is_file():
        raise FileNotFoundError(f"Thesis not found: thesis_v{version}.md")
    raw = out_path.read_text(encoding="utf-8")
    html = _md.markdown(raw, extensions=["tables", "fenced_code"])
    # 第一个出现的每个 K# 加 id 锚点（用于详情页 coverage strip 跳转）
    seen: set[str] = set()
    def _add_anchor(m: "re.Match") -> str:
        k = m.group(0)
        if k in seen:
            return k
        seen.add(k)
        return f'<span id="{k}" class="k-anchor">{k}</span>'
    html = re.sub(r"\bK\d+\b", _add_anchor, html)
    return html


def list_thesis_files(slug: str, variant: str) -> list[int]:
    """列出 variant 目录下所有 thesis_v{N}.md 文件的 version 号，升序。"""
    d = _topic_dir(slug, variant)
    if not d.is_dir():
        return []
    versions = []
    for p in d.iterdir():
        if p.is_file() and p.name.startswith("thesis_v") and p.name.endswith(".md"):
            try:
                versions.append(int(p.name[len("thesis_v"):-len(".md")]))
            except ValueError:
                continue
    return sorted(versions)


def read_output_html(slug: str, output_key: str, variant: str) -> str:
    # Handle drilldown outputs
    if output_key.startswith("drilldown_"):
        out_path = _topic_dir(slug, variant) / "outputs" / f"{output_key}.md"
    else:
        out_path = _topic_dir(slug, variant) / "outputs" / f"{output_key}.md"
    if not out_path.is_file():
        raise FileNotFoundError(f"Output not yet generated: {output_key}")
    raw = out_path.read_text(encoding="utf-8")
    return _md.markdown(raw, extensions=["tables", "fenced_code"])
