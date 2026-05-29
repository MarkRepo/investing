"""Query output state for topics. Zero LLM calls."""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import markdown as _md
import yaml

_PRISM_ROOT = Path(__file__).resolve().parent.parent

_OUTPUT_KEYS_LABELS = [
    ("00_primer", "领域入门"),
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


def _is_decision_file(filename: str) -> bool:
    return filename.startswith("decision_") and filename.endswith(".md") and "_review_" not in filename


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


def _parse_decision_info(filepath: Path) -> dict:
    try:
        raw = filepath.read_text(encoding="utf-8")
        if raw.startswith("---"):
            frontmatter_end = raw.find("---", 3)
            if frontmatter_end > 0:
                import yaml
                frontmatter = yaml.safe_load(raw[3:frontmatter_end])
                if isinstance(frontmatter, dict):
                    return {
                        "date": frontmatter.get("date"),
                        "action": frontmatter.get("action", ""),
                        "position_pct": frontmatter.get("position_pct"),
                    }
    except Exception:
        pass
    return {"date": None, "action": "", "position_pct": None}


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
            "last_error": state.get("last_error"),  # 修 9: {"at": ts, "message": ...} 或 None
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
                "last_error": None,
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
                "last_error": None,
            })

        # Add decision records (decision_YYYYMMDD.md), newest first
        decision_files = sorted(
            [f for f in out_dir.iterdir() if f.is_file() and _is_decision_file(f.name)],
            reverse=True,
        )
        for filepath in decision_files:
            info = _parse_decision_info(filepath)
            d = info.get("date")
            if isinstance(d, (date, datetime)):
                date_str = d.isoformat()[:10]
            elif isinstance(d, int):
                s = str(d)
                date_str = f"{s[:4]}-{s[4:6]}-{s[6:8]}" if len(s) == 8 else s
            elif isinstance(d, str):
                date_str = d
            else:
                date_str = filepath.name[len("decision_"):-3]
                if len(date_str) == 8 and date_str.isdigit():
                    date_str = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
            action = info.get("action") or "—"
            label = f"决策记录：{date_str} ({action})"
            result.append({
                "key": filepath.name[:-3],  # without .md
                "label": label,
                "status": "fresh",
                "version": 1,
                "last_updated": date_str,
                "file_exists": True,
                "is_decision": True,
                "last_error": None,
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

    # K# 匹配时去掉 @event 后缀；event 锚是 todo/mat 级精度，roadmap 规划层只到 K#
    def _key(a: str) -> str:
        return a.split("@", 1)[0] if isinstance(a, str) else ""

    l4 = (roadmap.get("learning_track") or {}).get("l4_hunting") or []
    l4_addrs: set[str] = set()
    for q in l4:
        for a in (q.get("addresses") or []):
            k = _key(a)
            if k.startswith("K"):
                l4_addrs.add(k)

    mat_addrs: set[str] = set()
    for tier in ("tier1", "tier2", "tier3"):
        for m in (roadmap.get("material_priority") or {}).get(tier) or []:
            for a in (m.get("addresses") or []):
                k = _key(a)
                if k.startswith("K"):
                    mat_addrs.add(k)

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


_DEFAULT_IGNORED_SOURCE_TYPES = ("drilldown",)
_DEFAULT_EXCLUDED_TRIGGERED_BY = (
    "00-prescan-baseline",
    "00-prescan",
    "01-prescan",
)


def list_affected_outputs(
    slug: str,
    variant: str,
    ignore_source_types: tuple[str, ...] = _DEFAULT_IGNORED_SOURCE_TYPES,
    exclude_triggered_by: tuple[str, ...] = _DEFAULT_EXCLUDED_TRIGGERED_BY,
) -> dict:
    """判定 04-synthesize 增量重写时哪些 output 需要 refresh。

    逻辑：对每个 output_key 比对
      outputs_state[key].referenced_mat_ids  vs  manifest 当前 processed=True 的 mat_ids
    分四种 reason：
      - 'new'           → 从未合成过（referenced_mat_ids is None），首次必须写
      - 'stale'         → manifest 有 mat 不在 referenced_mat_ids（新材料入库或重抽 finding）
      - 'critic-stale'  → outputs_state[key].status == 'stale' 但无新 mat
                          （critic verdict='request-rewrite' 显式标的，必须重写）
      - 'fresh'         → 全部 mat 都已纳入且 status != 'stale'，无需重写
    drift（referenced 里有 mat 但 manifest 没了 / processed 翻回 False）也归 stale。

    `ignore_source_types` 默认 ('drilldown',) — 跳过 07-drilldown 入库的 mat，
    避免每次深挖都让 ~5 份 output 标 stale 触发 04 大重写（修 M6）。
    若 drilldown 真的动摇了 thesis，让 07 显式调 set_output_status(stale)
    走 critic-stale 路径，不依赖 list_affected_outputs 自动判定。
    传 () 可包含所有 source_type（用户显式要求"全重写"时）。

    `exclude_triggered_by` 默认 ('00-prescan-baseline','00-prescan','01-prescan') —
    跳过 Role α prescan 入库的 web-search mat。原因：这些 hit 在 baseline §六
    + roadmap 起草阶段已被消化进 thesis_v0，不应再单独触发 04 重写；它们
    在 list_unprocessed 里同样被默认排除（保持两层一致）。Role β（02-step0）
    / Role γ（03/04/05 即兴）正常计入 stale 判定。
    传 () 可包含所有 triggered_by。

    返回：{
        '01_business_panorama': {'reason': 'stale', 'new_mat_ids': [mat-xxx, ...]},
        '04_implied_expectations': {'reason': 'critic-stale', 'new_mat_ids': []},
        '02_cycle_positioning': {'reason': 'fresh', 'new_mat_ids': []},
        ...
    }
    """
    from . import topic as topic_io
    from . import manifest as manifest_io
    data = topic_io.read_topic(slug, variant)
    try:
        manifest = manifest_io.read_manifest(slug, variant)
    except FileNotFoundError:
        manifest = {"materials": []}
    ignored = set(ignore_source_types or ())
    excluded_tb = set(exclude_triggered_by or ())

    def _kept(m: dict) -> bool:
        if not m.get("processed"):
            return False
        if m.get("source_type") in ignored:
            return False
        tb = (m.get("search_meta") or {}).get("triggered_by", "unknown")
        if tb in excluded_tb:
            return False
        return True

    processed_ids = sorted({
        m["id"] for m in (manifest.get("materials") or []) if _kept(m)
    })
    out: dict = {}
    for key, state in (data.get("outputs_state") or {}).items():
        ref = state.get("referenced_mat_ids")
        status = state.get("status")
        if ref is None:
            out[key] = {"reason": "new", "new_mat_ids": processed_ids}
            continue
        expanded = _expand_aggregate_refs(slug, variant, ref)
        # 未解析的虚拟 ID（aggregated_from 缺失/finding 不存在）→ 保守标 stale
        unresolved = {x for x in expanded if x.startswith("ws-aggregate-")}
        real_refs = expanded - unresolved
        new_ids = [mid for mid in processed_ids if mid not in real_refs]
        if not new_ids and not unresolved:
            # mat 集合 ref 已覆盖全部 processed mat，且无未解析虚拟 ID
            # 注：不再 strict-equality 比对 ref_set 与 processed_ids；
            # ref 多出的 mat 可能是按 triggered_by/source_type 过滤掉的合法历史引用，
            # 不应触发 stale 重写（修 [[feedback_addresses_granularity]] 同类陷阱）
            if status == "stale":
                out[key] = {"reason": "critic-stale", "new_mat_ids": []}
            else:
                out[key] = {"reason": "fresh", "new_mat_ids": []}
        else:
            out[key] = {"reason": "stale", "new_mat_ids": new_ids}
    return out


def _expand_aggregate_refs(slug: str, variant: str, refs: list[str]) -> set[str]:
    """展开 referenced_mat_ids 里的聚合虚拟 ID（ws-aggregate-*）。

    背景：04-synthesize 写大产出时若某 K# 收了 20+ web-search hit，主 agent 会
    聚合写成一份 `findings_ws-aggregate-K#.md` 并把虚拟 ID 登记到 referenced_mat_ids。
    比对 manifest 时这条虚拟 ID 不对应任何真 mat，导致 84 条真 mat 全被
    判 new → 产出误标 stale → 04 死循环（实测 cn-commercial-space 9/9 中招）。

    展开规则：
      - 真 mat_id（不以 'ws-aggregate-' 开头）→ 原样保留
      - 'ws-aggregate-*' → 读 `outputs/findings_{mat_id}.md` frontmatter，
        把 `aggregated_from` 列出的真 mat_ids 加入集合
      - finding 文件不存在 / frontmatter 缺 aggregated_from → **保留虚拟 ID**
        （视为 unknown 集合，让 stale 判定保守地认为"覆盖不全"，触发重写而非误标 fresh）
    """
    from prism.scripts.findings import _read_frontmatter

    out: set[str] = set()
    findings_dir = _topic_dir(slug, variant) / "outputs"
    for mid in refs or []:
        if not isinstance(mid, str):
            continue
        if not mid.startswith("ws-aggregate-"):
            out.add(mid)
            continue
        # 优先按 canonical findings_{mat_id}.md 查；找不到再 fallback 到 legacy
        # findings_mat-{suffix}.md（cn-commercial-space 原始命名 — 'ws-aggregate-K1'
        # 落在 'findings_mat-ws-K1.md'）
        suffix = mid[len("ws-aggregate-"):]
        candidates = [
            findings_dir / f"findings_{mid}.md",
            findings_dir / f"findings_mat-ws-{suffix}.md",
        ]
        fm: dict = {}
        for cand in candidates:
            if cand.is_file():
                fm = _read_frontmatter(cand)
                break
        expanded = fm.get("aggregated_from") or []
        if expanded and isinstance(expanded, list):
            out.update(str(x) for x in expanded if x)
        else:
            # fallback：保留虚拟 ID，让上层 stale 判定保守
            out.add(mid)
    return out


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
    # mat address 可能含 @event 锚（如 K1@2026Q2-earnings），按 key 归桶
    by_key: dict[str, list] = {k: [] for k in thesis_ks}
    for mat in m.get("materials", []) or []:
        for a in mat.get("addresses") or []:
            key = a.split("@", 1)[0] if isinstance(a, str) else ""
            if key in by_key:
                by_key[key].append(mat)
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
