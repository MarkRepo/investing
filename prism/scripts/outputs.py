"""Query output state for topics. Zero LLM calls."""
from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path

import markdown as _md
import yaml

_PRISM_ROOT = Path(__file__).resolve().parent.parent

# ── markdown 渲染（统一入口）────────────────────────────────────────────────
# Python-Markdown 的 tables 扩展硬要求表格前必须有空行：表格紧跟非空文本行时
# 不会被解析，整块退化成裸 `|` 文本。作者/LLM 漏空行很常见，故在渲染前统一归一化。
_MD_EXTENSIONS = ["tables", "fenced_code"]


def _is_md_table_delimiter(line: str) -> bool:
    """是否为表格分隔行（如 `|---|:--:|`）。要求同时含 `|` 与 `-`，避免把 setext
    下划线（`-----`）或水平线误判为表格。"""
    s = line.strip()
    if "|" not in s or "-" not in s:
        return False
    return all(ch in "|-: " for ch in s)


def _normalize_md_tables(raw: str) -> str:
    """在「表头行 + 分隔行」构成的表格块前补一个空行（仅当上一行非空且非表格行）。
    跳过 fenced code 块内部，幂等。"""
    lines = raw.split("\n")
    out: list[str] = []
    in_fence = False
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            out.append(line)
            continue
        if not in_fence and "|" in line and line.strip():
            nxt = lines[i + 1] if i + 1 < len(lines) else ""
            if _is_md_table_delimiter(nxt):
                prev = out[-1] if out else ""
                if prev.strip() and "|" not in prev:
                    out.append("")
        out.append(line)
    return "\n".join(out)


# 文件开头的 YAML frontmatter 块（--- … ---）。frontmatter 是后台记账
# （slug/output_key/version/companion 等），对读者无意义；尤其 companion 会把
# 后台文件名泄露到网页。render_markdown 不挂 meta 扩展，否则整块会被当正文渲染
# 成一坨 <hr>+段落。故在统一渲染入口前剥除。
_FRONTMATTER_RE = re.compile(r"^---\n(?P<fm>.*?)\n---\n", re.DOTALL)
_FM_KEY_RE = re.compile(r"^[A-Za-z_][\w-]*\s*:")


def _strip_frontmatter(raw: str) -> str:
    """剥掉文件开头的 YAML frontmatter 块。仅当开头确为 frontmatter（首行 `---`、
    块内至少一行形如 `key: value`）才剥，避免误吃正文开头的 `---` 水平线 / setext
    下划线。无 frontmatter 时原样返回。幂等。"""
    m = _FRONTMATTER_RE.match(raw)
    if not m:
        return raw
    if not any(_FM_KEY_RE.match(line) for line in m.group("fm").splitlines()):
        return raw  # 看着像 frontmatter 实为正文 `---` 分隔，放过
    return raw[m.end():]


# 顶层无序/有序列表项（marker + 至少一个空格 + 内容）。要求行首无缩进，故只认顶层项；
# `---`/`***` 等水平线、`-5` 这类负数行都不匹配（marker 后必须是「空白+非空」）。
_TOP_LIST_ITEM_RE = re.compile(r"^(?:[-*+]|\d+[.)])\s+\S")


def _normalize_md_lists(raw: str) -> str:
    """在「段落行 + 顶层列表项」之间补一个空行。python-markdown 要求列表前有空行，
    否则紧跟段落的 `- ` 行会被当成段落的惰性续行、渲染成字面 `- 文本`（不成列表）。
    与 _normalize_md_tables 同源：作者/LLM 常漏这个空行。

    保守规则——仅当当前行是「顶层」列表项（行首无缩进）、且上一行非空、非缩进、且本身
    不是顶层列表项时才补空行。故：连续列表项保持紧凑、嵌套/缩进续行不被打扰、fenced
    code 内部跳过。幂等。"""
    lines = raw.split("\n")
    out: list[str] = []
    in_fence = False
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            out.append(line)
            continue
        if not in_fence and _TOP_LIST_ITEM_RE.match(line):
            prev = out[-1] if out else ""
            if (
                prev.strip()
                and not prev.startswith((" ", "\t"))
                and not _TOP_LIST_ITEM_RE.match(prev)
            ):
                out.append("")
        out.append(line)
    return "\n".join(out)


def render_markdown(raw: str) -> str:
    """prism 内所有 md→HTML 的统一入口：先剥 frontmatter、补表格/列表空行再交给 markdown 扩展。"""
    normalized = _normalize_md_lists(_normalize_md_tables(_strip_frontmatter(raw)))
    return _md.markdown(normalized, extensions=_MD_EXTENSIONS)

_OUTPUT_KEYS_LABELS = [
    ("00_primer", "领域入门"),
    # 决策链成稿 case（按 topic.type 三选一，见 topic._DECISION_CHAIN_OUTPUTS）。
    # create_topic 按 type seed 决策链 key（00_primer + 对应 case + 08_living_feed）。
    # 旧 8 维并列产出（01_business_panorama…07_decision_kit）已随决策链重构退休：
    # 不再 seed、磁盘文件已清空，故不再列入 label 表（保留只会让遗留 topic 渲染出
    # file_exists=False 的死行 + 坏链）。list_outputs 用 skip-if-absent 渲染——
    # 遗留 topic 若 outputs_state 仍带这些 key，无 label 即自然跳过。
    ("c_investment_case", "投资决策链 case"),
    ("i_industry_case", "行业决策链 case"),
    ("a_arena_case", "竞技场决策链 case"),
    ("m_regime_read", "宏观体制读数"),
    ("08_living_feed", "信息流时间线"),
    # 注：sidecar（07_decision_kit / industry_to_arenas / peer_matrix）是 .yaml
    # 文件、无独立 markdown 视图（见 _contracts.md §六：sidecar yaml
    # 是 dashboard 竞技场层唯一契约，不再产出 .md）。它们由 dashboard 的 _load_*_sidecar
    # 专路渲染，**不列入本 md 产出表**——否则 list_outputs 按 {key}.md 探测必 file_exists=
    # False，detail 页渲染出"status=fresh 但置灰无链"的死行（peer_matrix 曾误列于此）。
]

# Additional outputs that can be generated via workflows
_EXTRA_OUTPUTS_LABELS = [
    ("05-critic-review", "批评者评审"),
    ("industry_to_arenas", "产业→竞技场选拔"),
    ("_synthesis_brief", "K# 校准 brief（04 副产物）"),
    ("00b_input_glossary", "输入源词典"),
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

    **真实状态源 = thesis 的「命门 / K# 现状表」第 3 列「置信度」**（04 合成约定）。
    该列用 00 的置信度词表（高/中/低/uncertain，+ 复合如「中偏强」、描述如「平滑论成立」）。
    旧实现只 grep「已验证支持/已反驳/待验证」关键字——而 thesis 改用置信度格式后这些词
    一个都不出现，导致已定调的研究全部兜底 unverified（详情页假报「N 待验证」）。本版改为
    锚定 K# 表格行、按置信度列判定，并保留散文 + 旧关键字兼容。

    判定（每个 K# 优先取「首格为该 K# 的表格行」，无表格行时退回首次出现处的 8 行散文窗口）：
      1. 显式「已验证支持 / 已支持 / ✓支持」                → 'supported'
      2. 显式反驳「反驳 / 证伪 / 不成立 / 已破 / 被否决」     → 'refuted'
      3. 显式未决「uncertain / 待验证 / 未验证 / 未确定」      → 'unverified'
      4. 否则——表格行（有实质置信度列：高/中/低/强/弱/描述判断）→ 'supported'（已定调）；
                散文无任何关键字命中（v0 / 不含现状段）        → 'unverified' 兜底

    即：只有「genuine uncertain / 散文未定调」才算待验证；表格里给了置信度判断的命门
    一律视为已定调（方向由反驳关键字区分）。

    返回 {K1: status, K2: status, ...}，仅包含 thesis 中实际出现的 K#。
    """
    import re
    path = _topic_dir(slug, variant) / f"thesis_v{version}.md"
    if not path.is_file():
        return {}
    raw = path.read_text(encoding="utf-8")
    lines = raw.splitlines()
    supported_pat = re.compile(r"已验证支持|已支持|✓\s*支持")
    refuted_pat = re.compile(r"已验证反驳|已反驳|✗\s*反驳|反驳|证伪|不成立|已破|被否")
    unverified_pat = re.compile(r"仍未确定|未确定|待验证|未验证|uncertain", re.IGNORECASE)
    ks_in_order = sorted(set(re.findall(r"\bK\d+\b", raw)),
                         key=lambda x: int(x[1:]))
    out: dict[str, str] = {}
    for k in ks_in_order:
        # 优先锚定「首格为该 K# 的表格行」(| K1 | 维度 | 置信度 | 看空触发 |)，
        # 避免被散文里更早出现的 K# 引用(如顶部 changelog)误锚到无置信度的行
        table_idx = next(
            (i for i, l in enumerate(lines) if re.match(rf"\s*\|\s*{k}\s*\|", l)),
            None,
        )
        if table_idx is not None:
            scope, is_table = lines[table_idx], True
        else:
            idx = next((i for i, l in enumerate(lines) if re.search(rf"\b{k}\b", l)), None)
            if idx is None:
                continue
            scope, is_table = "\n".join(lines[idx: idx + 8]), False
        if supported_pat.search(scope):
            out[k] = "supported"
        elif refuted_pat.search(scope):
            out[k] = "refuted"
        elif unverified_pat.search(scope):
            out[k] = "unverified"
        elif is_table:
            # 表格行给了实质置信度(高/中/低/强/弱/描述)但无显式支持/反驳/未决词 → 已定调
            out[k] = "supported"
        else:
            out[k] = "unverified"
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
        'c_investment_case': {'reason': 'stale', 'new_mat_ids': [mat-xxx, ...]},
        '08_living_feed': {'reason': 'critic-stale', 'new_mat_ids': []},
        '00_primer': {'reason': 'fresh', 'new_mat_ids': []},
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
    # 枚举源 = 本 type 决策链 canonical 产出 ∪ 已有 outputs_state key（含遗留键）。
    # create_topic 改 file-first 空 seed 后，首次合成时 outputs_state 为空 {}，
    # 必须靠 _outputs_for_type 补出 canonical 集，否则首跑返回 {} → 漏产。
    # canonical 里 outputs_state 缺失的 key：state={} → ref=None → reason='new'，
    # 与旧"预置槽全 pending"行为字节等价（零回归）。
    outputs_state = data.get("outputs_state") or {}
    canonical = topic_io._outputs_for_type(data.get("type", ""))
    all_keys = list(dict.fromkeys([*canonical, *outputs_state.keys()]))
    for key in all_keys:
        state = outputs_state.get(key) or {}
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
    # 证据按 K# 归桶，**与 gap_detector 同源**：manifest 材料层（粗）∪ findings 层（细，
    # 03 抽取产出），按来源 id 去重（同一材料与其 finding 不重复计）。mat address 可能含
    # @event 锚（如 K1@2026Q2-earnings），按 key 归桶。
    # 旧 bug：只数材料层 addresses，漏掉只在 findings 层打 K# 标的 topic（prescan 入库的
    # 材料层多为 scope/background 占位）→ 误报「实际收集覆盖 0%」。本版对齐 gap_detector
    # 的 ev_sources 取并逻辑，使徽章反映真实收集证据。
    materials = m.get("materials", []) or []
    by_id: dict[str, dict] = {
        (mat.get("id") or f"mat:{mat.get('filename')}"): mat for mat in materials
    }
    ev: dict[str, dict] = {k: {} for k in thesis_ks}  # k -> {source_id: entry}
    for mat in materials:
        mid = mat.get("id") or f"mat:{mat.get('filename')}"
        for a in mat.get("addresses") or []:
            key = a.split("@", 1)[0] if isinstance(a, str) else ""
            if key in ev:
                ev[key].setdefault(mid, mat)
    try:
        from .findings import list_all_findings
        for f in list_all_findings(slug, variant):
            fid = f.get("mat_id") or str(f.get("path"))
            entry = by_id.get(fid) or {
                "id": fid, "filename": f.get("path"), "source_type": "finding",
            }
            for a in f.get("addresses") or []:
                key = a.split("@", 1)[0] if isinstance(a, str) else ""
                if key in ev:
                    ev[key].setdefault(fid, entry)
    except Exception:
        pass
    by_key: dict[str, list] = {k: list(ev[k].values()) for k in thesis_ks}
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
    html = render_markdown(raw)
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


def list_decomposition_files(slug: str, variant: str) -> list[int]:
    """列出 variant 目录下所有 decomposition_v{N}.md 文件的 version 号，升序。"""
    d = _topic_dir(slug, variant)
    if not d.is_dir():
        return []
    versions = []
    for p in d.iterdir():
        if p.is_file() and p.name.startswith("decomposition_v") and p.name.endswith(".md"):
            try:
                versions.append(int(p.name[len("decomposition_v"):-len(".md")]))
            except ValueError:
                continue
    return sorted(versions)


import re as _re_mat

# 正文里的资料引用形如 mat-9fb50a（6 位小写 hex）。三种常见写法 [mat-x] / 裸 mat-x /
# (mat-x) 都靠这个裸 token 正则命中——前后的方括号/圆括号不进 token，故无需分别匹配。
_MAT_REF_RE = _re_mat.compile(r"\bmat-[0-9a-f]{6}\b")


def linkify_mat_refs(html: str, slug: str, variant: str, valid_ids: set[str]) -> str:
    """把已渲染 HTML 正文里的 mat-XXX 引用包成指向诊断页对应来源行的链接。

    tag-safe：用 re.split 把 HTML 切成「标签段 / 文本段」交替序列，只在文本段上替换，
    绝不动标签内部（避免污染 <h2 id="..."> 之类属性，或把 href 里的串二次包链）。
    仅当 mid ∈ valid_ids（自有 manifest ∪ parent_materials）才成链；未知 id 保持纯文本，
    不造死链（可能是过期/残留引用）。纯函数，可单测。
    """
    if not html or not valid_ids:
        return html

    def _sub_text(text: str) -> str:
        def _repl(m: "_re_mat.Match") -> str:
            mid = m.group(0)
            if mid not in valid_ids:
                return mid
            return (f'<a class="mat-ref" '
                    f'href="/prism/{slug}/{variant}/diag#{mid}">{mid}</a>')
        return _MAT_REF_RE.sub(_repl, text)

    parts = _re_mat.split(r"(<[^>]+>)", html)
    # 偶数下标=文本段，奇数下标=标签段（split 用捕获组保留分隔符）
    return "".join(
        seg if (i % 2 == 1) else _sub_text(seg)
        for i, seg in enumerate(parts)
    )


def _citable_mat_ids(slug: str, variant: str) -> set[str]:
    """本 topic 正文里「可解析成链」的 mat id 全集：自有 manifest 的 id ∪ parent_materials
    的 mat_id。任意来源缺失/异常一律降级为空集，绝不让取 id 这一步拖垮渲染。"""
    ids: set[str] = set()
    from . import manifest as manifest_io
    from . import topic as topic_io
    try:
        man = manifest_io.read_manifest(slug, variant)
        for m in man.get("materials") or []:
            mid = m.get("id")
            if mid:
                ids.add(mid)
    except Exception:
        pass
    try:
        data = topic_io.read_topic(slug, variant)
        for pm in data.get("parent_materials") or []:
            mid = pm.get("mat_id")
            if mid:
                ids.add(mid)
    except Exception:
        pass
    return ids


def collect_parent_materials(slug: str, variant: str) -> list[dict]:
    """收集本 topic 复用的父级资料行（供诊断页「复用父级资料」子区渲染）。

    父级资料不在本 manifest——只在 topic.yaml: parent_materials 里登记
    {parent_slug, parent_variant, mat_id, addresses?, note?}。逐条回父 manifest 取
    filename/source_type/confidence/search_meta，复用 material_trust() 算可信，并探测父
    outputs/findings_{mat_id}.md 是否存在（决定是否给「父 findings」深链）。

    父 manifest 缺失/异常时降级为最小行（仅 mat_id/parent_*/addresses/note，无文件元数据、
    has_parent_findings=False），绝不抛错（缺父 topic 不该让子 topic 诊断页 500）。
    """
    from . import manifest as manifest_io
    from . import topic as topic_io
    try:
        data = topic_io.read_topic(slug, variant)
    except Exception:
        return []
    rows: list[dict] = []
    for pm in data.get("parent_materials") or []:
        mid = pm.get("mat_id")
        if not mid:
            continue
        p_slug = pm.get("parent_slug")
        p_variant = pm.get("parent_variant")
        row = {
            "mat_id": mid,
            "parent_slug": p_slug,
            "parent_variant": p_variant,
            "addresses": pm.get("addresses") or [],
            "note": pm.get("note"),
            "filename": None,
            "source_type": None,
            "confidence": None,
            "search_meta": None,
            "trust": None,
            "has_parent_findings": False,
        }
        try:
            p_man = manifest_io.read_manifest(p_slug, p_variant)
            src = next((m for m in p_man.get("materials") or [] if m.get("id") == mid), None)
            if src:
                row["filename"] = src.get("filename")
                row["source_type"] = src.get("source_type")
                row["confidence"] = src.get("confidence")
                row["search_meta"] = src.get("search_meta")
                row["trust"] = material_trust(src)
        except Exception:
            pass
        try:
            p_find = _topic_dir(p_slug, p_variant) / "outputs" / f"findings_{mid}.md"
            row["has_parent_findings"] = p_find.is_file()
        except Exception:
            pass
        rows.append(row)
    return rows


def read_output_html(slug: str, output_key: str, variant: str) -> str:
    # Handle drilldown outputs
    if output_key.startswith("drilldown_"):
        out_path = _topic_dir(slug, variant) / "outputs" / f"{output_key}.md"
    else:
        out_path = _topic_dir(slug, variant) / "outputs" / f"{output_key}.md"
    if not out_path.is_file():
        raise FileNotFoundError(f"Output not yet generated: {output_key}")
    raw = out_path.read_text(encoding="utf-8")
    html = render_markdown(raw)
    # 正文资料引用 mat-XXX → 诊断页对应来源行的链接（仅可解析 id 成链）
    return linkify_mat_refs(html, slug, variant, _citable_mat_ids(slug, variant))


# ── 诊断页（/diag）中间产物读取器 ───────────────────────────────────────────────
# 这些是 workflow 链路上的中间稿，读者向页面不展示，只在诊断 tab 露出。
# 设计原则：文件缺失一律优雅降级（返回 None / 空），永不抛错——老 topic、早期
# variant 都可能缺任意一段。

def read_decomposition_html(slug: str, variant: str, version: int) -> str:
    """读取 decomposition_v{N}.md（命门拆解）并渲染为 HTML。文件在 variant 根目录。
    照搬 read_thesis_html 的 K# 锚点逻辑，便于和 thesis/coverage 互跳。
    """
    import re
    out_path = _topic_dir(slug, variant) / f"decomposition_v{version}.md"
    if not out_path.is_file():
        raise FileNotFoundError(f"Decomposition not found: decomposition_v{version}.md")
    raw = out_path.read_text(encoding="utf-8")
    html = render_markdown(raw)
    seen: set[str] = set()
    def _add_anchor(m: "re.Match") -> str:
        k = m.group(0)
        if k in seen:
            return k
        seen.add(k)
        return f'<span id="{k}" class="k-anchor">{k}</span>'
    return re.sub(r"\bK\d+\b", _add_anchor, html)


def collect_findings(slug: str, variant: str) -> dict:
    """收集逐料 findings（证据层），供诊断页展示。

    返回:
        {
            'index_html': <_findings_index.md 渲染，含 addresses=[K#] 人读分组> | None,
            'files': [{mat_id, filename, source_type, quality, bias, body_html}, ...],
            'total': int,
        }
    分组以 _findings_index.md 自带的 K# 结构为准（它本就是按 addresses 组织的人读视图），
    逐料全文则以折叠 <details> 形式挂在下方，避免在路由里重造一套分组逻辑。
    """
    import re
    d = _topic_dir(slug, variant) / "outputs"
    index_html = None
    idx_path = d / "_findings_index.md"
    if idx_path.is_file():
        index_html = render_markdown(idx_path.read_text(encoding="utf-8"))

    files: list[dict] = []
    if d.is_dir():
        for p in sorted(d.glob("findings_*.md")):
            raw = p.read_text(encoding="utf-8")
            meta = {"mat_id": p.stem, "filename": p.name,
                    "source_type": None, "quality": None, "bias": None}
            # 解析 frontmatter（mat_id/filename/source_type/quality/bias）
            fm = re.match(r"^---\n(.*?)\n---\n", raw, re.DOTALL)
            body = raw
            if fm:
                for line in fm.group(1).splitlines():
                    if ":" in line:
                        k, _, v = line.partition(":")
                        k, v = k.strip(), v.strip()
                        if k in meta:
                            meta[k] = v
                body = raw[fm.end():]
            meta["body_html"] = render_markdown(body)
            files.append(meta)

    return {"index_html": index_html, "files": files, "total": len(files)}


def collect_critic_artifacts(slug: str, variant: str) -> dict:
    """收集 critic 裁决产物，两个 canonical 落点（依 05-critic-review.md 文档）：

      1. 完整评审文件 outputs/05-critic-review.md（Step 5「保存评审结果」）
      2. case 头「🧪 承重充分性」横幅（Step 5.5——裁决必须进被消费的产出本身）

    刻意不收 00_quality_screen / workflow_review / _process_notes / _final_report：
    workflow 文档 0 处提及，是测试残留而非流程产物。

    返回 {'banner': str|None, 'review_html': str|None}。
    """
    topic_dir = _topic_dir(slug, variant)
    review_path = topic_dir / "outputs" / "05-critic-review.md"
    review_html = (
        render_markdown(review_path.read_text(encoding="utf-8"))
        if review_path.is_file() else None
    )

    # case 头「承重充分性」横幅：扫成稿 case 文件正文里那一行
    banner = None
    for stem in ("c_investment_case", "i_industry_case", "a_arena_case"):
        cpath = topic_dir / "outputs" / f"{stem}.md"
        if cpath.is_file():
            for line in cpath.read_text(encoding="utf-8").splitlines():
                if "承重充分性" in line:
                    banner = line.lstrip("> ").strip()
                    break
        if banner:
            break

    return {"banner": banner, "review_html": review_html}


def read_synthesis_brief_html(slug: str, variant: str) -> str | None:
    """读取 _synthesis_brief.md（合成阶段内部备忘，canonical 辅助产物）。缺失返回 None。"""
    path = _topic_dir(slug, variant) / "outputs" / "_synthesis_brief.md"
    if not path.is_file():
        return None
    return render_markdown(path.read_text(encoding="utf-8"))


# source_type → 可信信号（非 web 料不走 domain_tier，可信度由来源性质定）
_SOURCE_TRUST = {
    "quarterly-report": ("一手", "official"),
    "annual-report": ("一手", "official"),
    "company-filing": ("一手", "official"),
    "sec-section": ("一手", "official"),
    "transcript": ("一手·口径", "official"),
    "policy": ("官方", "official"),
    "data": ("数据", "white"),
    "web-search": ("web", "low"),
}


def material_trust(m: dict) -> dict:
    """给一份 manifest 材料返回可信信号 {label, css}。
    web-search 料用 domain_tier；其余按 source_type 性质判（一手 SEC/财报 > web）。
    """
    st = m.get("source_type")
    if st == "web-search":
        tier = (m.get("search_meta") or {}).get("domain_tier")
        if tier and "official" in tier:
            return {"label": "web·官方判定", "css": "official"}
        if tier and "whitelist" in tier:
            return {"label": "web·白名单", "css": "white"}
        return {"label": "web·未分级", "css": "low"}
    label, css = _SOURCE_TRUST.get(st, ("—", "low"))
    return {"label": label, "css": css}


def read_roadmap_yaml(slug: str, variant: str) -> str | None:
    """读取 roadmap.yaml 原文（K# 计划），原样返回文本供 <pre> 展示。缺失返回 None。"""
    path = _topic_dir(slug, variant) / "roadmap.yaml"
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")
