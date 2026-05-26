"""Material manifest for a research topic. Zero LLM calls."""
from __future__ import annotations

import shutil
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

# web-search material 的过期窗口
_WEB_SEARCH_STALE_DAYS = 30
_WEB_SEARCH_EXPIRE_DAYS = 90

_PRISM_ROOT = Path(__file__).resolve().parent.parent


def _topics_dir() -> Path:
    return _PRISM_ROOT / "topics"


def _materials_dir(slug: str) -> Path:
    return _topics_dir() / slug / "materials"


def _manifest_path(slug: str, variant: str) -> Path:
    if not variant:
        raise ValueError("必须显式指定 variant，例如 'sonnet' 或 'qwen3.6-plus'")
    return _topics_dir() / slug / variant / "manifest.yaml"


def _read_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _write_yaml(path: Path, data: dict) -> None:
    path.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_manifest(slug: str, variant: str) -> Path:
    path = _manifest_path(slug, variant)
    data = {"slug": slug, "variant": variant, "updated": _now_iso(), "materials": []}
    _write_yaml(path, data)
    # Create materials directory (shared across variants)
    _materials_dir(slug).mkdir(parents=True, exist_ok=True)
    return path


def read_manifest(slug: str, variant: str) -> dict:
    path = _manifest_path(slug, variant)
    if not path.exists():
        raise FileNotFoundError(f"Manifest not found for topic: {slug}/{variant}")
    return _read_yaml(path)


def get_material_path(slug: str, filename: str) -> Path | None:
    """Find material file in priority order:
    1. prism/topics/{slug}/materials/{filename}
    2. prism/inbox/manual/{filename}
    3. prism/inbox/auto/{filename}
    """
    locations = [
        _materials_dir(slug) / filename,
        _PRISM_ROOT / "inbox" / "manual" / filename,
        _PRISM_ROOT / "inbox" / "auto" / filename,
    ]
    for loc in locations:
        if loc.exists():
            return loc
    return None


_MINERU_NEEDED_TYPES = {"sell-side-note", "industry-research", "policy"}
_MINERU_NOT_NEEDED_TYPES = {"web-article", "manual-note", "data"}


def _default_mineru_state(filename: str, source_type: str) -> str:
    """根据文件类型 + 后缀判断初始 mineru 状态。

    needs    — PDF + research-类资料，需转换为 markdown 才能高质量提取
    not_needed — 非 PDF（md/txt/html）或非研报类
    """
    ext = Path(filename).suffix.lower()
    if ext != ".pdf":
        return "not_needed"
    if source_type == "annual-report":
        # 年报走 annual_report_extractor 不走 mineru
        return "not_needed"
    if source_type in _MINERU_NEEDED_TYPES:
        return "needs"
    return "not_needed"


def add_material(
    slug: str,
    filename: str,
    source_type: str,
    variant: str,
    notes: str = "",
    source_path: Path | None = None,
    addresses: list[str] | None = None,
    confidence: float | None = None,
    search_meta: dict | None = None,
    parent_mat: str | None = None,
    sec_section: str | None = None,
) -> str:
    """Add a material to the manifest.

    addresses: list of K#/Q# tags this material attacks (e.g. ['K1', 'Q3']).
               Links the material back to thesis Killer Questions and roadmap questions.
    confidence: 0.0-1.0, currently only set for web-search materials.
    search_meta: only set for web-search materials. Required keys: query, url,
                 searched_at, stale_at, expire_at, domain, domain_tier.
    parent_mat: mat_id of a parent material (used for SEC section children pointing back
                to the original htm filing).
    sec_section: section key (e.g. 'item_1_business') when the entry is a SEC section file.
    If source_path is provided, copies the file to topic's materials directory.
    Dedup: if filename already in manifest, returns existing mat_id without re-adding.
    """
    data = read_manifest(slug, variant)

    # Copy file if source_path provided (do before dedup check so we know final filename)
    if source_path and source_path.exists():
        materials_dir = _materials_dir(slug)
        materials_dir.mkdir(parents=True, exist_ok=True)
        dest_path = materials_dir / source_path.name
        if not dest_path.exists():
            shutil.copy2(source_path, dest_path)
        filename = dest_path.name

    # Dedup: filename already in manifest → update addresses/notes in-place, no new entry
    for mat in data["materials"]:
        if mat["filename"] == filename:
            updated = False
            if addresses:
                existing = set(mat.get("addresses") or [])
                merged = sorted(existing | set(addresses))
                if merged != list(existing):
                    mat["addresses"] = merged
                    updated = True
            if notes and notes not in (mat.get("notes") or ""):
                mat["notes"] = ((mat.get("notes") or "") + " | " + notes).strip(" |")
                updated = True
            # web-search 重复登记时更新 search_meta（视为刷新搜索时间）
            if search_meta:
                mat["search_meta"] = search_meta
                updated = True
            if confidence is not None:
                mat["confidence"] = confidence
                updated = True
            if updated:
                data["updated"] = _now_iso()
                _write_yaml(_manifest_path(slug, variant), data)
            return mat["id"]

    mat_id = f"mat-{uuid.uuid4().hex[:6]}"
    entry = {
        "id": mat_id,
        "filename": filename,
        "source_type": source_type,
        "added": _now_iso(),
        "processed": False,
        "notes": notes,
        "mineru_state": _default_mineru_state(filename, source_type),
    }
    if addresses:
        entry["addresses"] = sorted(set(addresses))
    if confidence is not None:
        entry["confidence"] = confidence
    if search_meta:
        entry["search_meta"] = search_meta
    if parent_mat:
        entry["parent_mat"] = parent_mat
    if sec_section:
        entry["sec_section"] = sec_section
    data["materials"].append(entry)
    data["updated"] = _now_iso()
    _write_yaml(_manifest_path(slug, variant), data)
    return mat_id


def add_sec_sections_from_meta(
    slug: str,
    variant: str,
    parent_mat_id: str,
    meta_path: Path,
    sections_root: Path | None = None,
) -> list[str]:
    """读 split_file 输出的 _meta.yaml，把每个 found 的 section 登记为子 mat。

    parent_mat_id: 原 htm 文件的 mat_id（必须已在 manifest 中）。
    meta_path:    sec/{stem}/_meta.yaml 绝对路径。
    sections_root: section 文件所在目录（默认 = meta_path.parent）。

    返回新增的子 mat_id 列表（按 _meta.yaml sections 顺序；跳过已存在 + 跳过 found=False）。
    每个子 mat 的 filename 用相对 materials/ 的 POSIX 路径（含 sec/{stem}/ 前缀），
    便于下游通过 get_material_path 解析（仍以 materials/ 为根）。
    """
    meta = _read_yaml(meta_path)
    if not meta.get("split_ok"):
        return []
    sections_dir = sections_root or meta_path.parent
    materials_dir = _materials_dir(slug)
    # 子 filename 用相对 materials/ 的 POSIX 路径
    try:
        rel_dir = sections_dir.resolve().relative_to(materials_dir.resolve())
    except ValueError:
        raise ValueError(
            f"sections dir {sections_dir} must be under {materials_dir}"
        )

    new_ids: list[str] = []
    for s in meta.get("sections", []):
        if not s.get("found") or not s.get("file"):
            continue
        section_filename = (Path(rel_dir) / s["file"]).as_posix()
        mat_id = add_material(
            slug=slug,
            filename=section_filename,
            source_type="sec-section",
            variant=variant,
            notes=f"split from {meta.get('source_htm')} ({s.get('item','?')})",
            addresses=s.get("addresses") or None,
            parent_mat=parent_mat_id,
            sec_section=s.get("name"),
        )
        new_ids.append(mat_id)
    return new_ids


def make_search_meta(
    query: str,
    url: str,
    domain: str,
    domain_tier: str,
    searched_at: str | None = None,
) -> dict:
    """Construct a search_meta dict with computed stale_at/expire_at.

    domain_tier ∈ {'whitelist', 'llm-judged-official', 'other'}
    searched_at defaults to now (ISO UTC).
    """
    if domain_tier not in {"whitelist", "llm-judged-official", "other"}:
        raise ValueError(f"Invalid domain_tier: {domain_tier!r}")
    if searched_at is None:
        searched_at_dt = datetime.now(timezone.utc)
        searched_at = searched_at_dt.isoformat()
    else:
        # parse user-supplied ISO string
        searched_at_dt = datetime.fromisoformat(searched_at.replace("Z", "+00:00"))
    stale_at = (searched_at_dt + timedelta(days=_WEB_SEARCH_STALE_DAYS)).isoformat()
    expire_at = (searched_at_dt + timedelta(days=_WEB_SEARCH_EXPIRE_DAYS)).isoformat()
    return {
        "query": query,
        "url": url,
        "domain": domain,
        "domain_tier": domain_tier,
        "searched_at": searched_at,
        "stale_at": stale_at,
        "expire_at": expire_at,
    }


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def list_by_source_type(slug: str, variant: str, source_type: str) -> list[dict]:
    """List all materials with the given source_type (e.g., 'web-search')."""
    return [m for m in read_manifest(slug, variant)["materials"] if m.get("source_type") == source_type]


def find_by_url(slug: str, variant: str, url: str) -> dict | None:
    """按 search_meta.url 反查已存在的 web-search material。
    用于 register_web_search_result 在 90 天 expire 重扫时避免重复入库。
    """
    if not url:
        return None
    for m in read_manifest(slug, variant)["materials"]:
        sm = m.get("search_meta") or {}
        if sm.get("url") == url:
            return m
    return None


def refresh_web_search_meta(
    slug: str, variant: str, mat_id: str,
    query: str | None = None, searched_at: str | None = None,
    addresses: list[str] | None = None,
) -> None:
    """对已存在的 web-search material 刷新搜索时间，并可合并 addresses + 追加新 query。
    用于 URL 命中已有条目时只更新元信息，不新建 mat。
    """
    data = read_manifest(slug, variant)
    for mat in data["materials"]:
        if mat["id"] != mat_id:
            continue
        sm = mat.get("search_meta") or {}
        if not sm:
            return
        new_meta = make_search_meta(
            query=query or sm.get("query", ""),
            url=sm.get("url", ""),
            domain=sm.get("domain", ""),
            domain_tier=sm.get("domain_tier", "other"),
            searched_at=searched_at,
        )
        # 保留旧 query 历史
        prev_queries = sm.get("prev_queries") or []
        if query and query != sm.get("query"):
            prev_queries = sorted(set(prev_queries + [sm.get("query")]))
            new_meta["prev_queries"] = prev_queries
        elif prev_queries:
            new_meta["prev_queries"] = prev_queries
        mat["search_meta"] = new_meta
        if addresses:
            existing = set(mat.get("addresses") or [])
            mat["addresses"] = sorted(existing | set(addresses))
        data["updated"] = _now_iso()
        _write_yaml(_manifest_path(slug, variant), data)
        return
    raise ValueError(f"mat_id {mat_id!r} not found")


def list_stale_web_search(slug: str, variant: str) -> list[dict]:
    """Return web-search materials past their stale_at (30 days default)."""
    now = datetime.now(timezone.utc)
    out = []
    for m in list_by_source_type(slug, variant, "web-search"):
        sm = m.get("search_meta") or {}
        stale_at = _parse_iso(sm.get("stale_at"))
        if stale_at and stale_at < now:
            out.append(m)
    return out


def list_expired_web_search(slug: str, variant: str) -> list[dict]:
    """Return web-search materials past their expire_at (90 days default).
    These should be re-scanned by daily-monitor."""
    now = datetime.now(timezone.utc)
    out = []
    for m in list_by_source_type(slug, variant, "web-search"):
        sm = m.get("search_meta") or {}
        expire_at = _parse_iso(sm.get("expire_at"))
        if expire_at and expire_at < now:
            out.append(m)
    return out


def set_mineru_state(slug: str, variant: str, mat_id: str, state: str) -> None:
    """更新 mineru 状态。state ∈ {needs, in_progress, done, failed, not_needed}"""
    if state not in {"needs", "in_progress", "done", "failed", "not_needed"}:
        raise ValueError(f"Invalid mineru_state: {state}")
    data = read_manifest(slug, variant)
    for mat in data["materials"]:
        if mat["id"] == mat_id:
            mat["mineru_state"] = state
            break
    data["updated"] = _now_iso()
    _write_yaml(_manifest_path(slug, variant), data)


def list_pending_mineru(slug: str, variant: str) -> list[dict]:
    """列出 mineru_state == 'needs' 的 material 条目（含 filename, id）。"""
    data = read_manifest(slug, variant)
    return [m for m in data["materials"] if m.get("mineru_state") == "needs"]


def mineru_state_counts(slug: str, variant: str) -> dict:
    """统计各 mineru 状态数量。"""
    from collections import Counter
    data = read_manifest(slug, variant)
    c = Counter(m.get("mineru_state", "not_needed") for m in data["materials"])
    return dict(c)


def dedupe_manifest(slug: str, variant: str) -> int:
    """删除 manifest 中按 filename 重复的条目（保留最早的；合并 addresses/notes）。
    返回删除的条目数。"""
    data = read_manifest(slug, variant)
    seen: dict[str, dict] = {}
    deduped: list[dict] = []
    removed = 0
    for mat in data["materials"]:
        fname = mat["filename"]
        if fname not in seen:
            seen[fname] = mat
            deduped.append(mat)
        else:
            # 合并 addresses/notes 到已存在条目，丢弃当前
            existing = seen[fname]
            if mat.get("addresses"):
                existing["addresses"] = sorted(set((existing.get("addresses") or []) + mat["addresses"]))
            if mat.get("notes"):
                existing["notes"] = ((existing.get("notes") or "") + " | " + mat["notes"]).strip(" |")
            removed += 1
    if removed:
        data["materials"] = deduped
        data["updated"] = _now_iso()
        _write_yaml(_manifest_path(slug, variant), data)
    return removed


def remove_material(slug: str, variant: str, mat_id: str | None = None, filename: str | None = None, delete_file: bool = False) -> int:
    """按 mat_id 或 filename 删除 manifest 条目。返回删除条目数。
    delete_file=True 时同时删除 materials/ 下的文件。
    """
    if not mat_id and not filename:
        raise ValueError("需要 mat_id 或 filename")
    data = read_manifest(slug, variant)
    kept, removed = [], []
    for m in data["materials"]:
        if (mat_id and m["id"] == mat_id) or (filename and m["filename"] == filename):
            removed.append(m)
        else:
            kept.append(m)
    if not removed:
        return 0
    data["materials"] = kept
    data["updated"] = _now_iso()
    _write_yaml(_manifest_path(slug, variant), data)
    if delete_file:
        for m in removed:
            fp = _materials_dir(slug) / m["filename"]
            if fp.exists():
                fp.unlink()
    return len(removed)


def mark_processed(slug: str, mat_id: str, variant: str) -> None:
    data = read_manifest(slug, variant)
    for mat in data["materials"]:
        if mat["id"] == mat_id:
            mat["processed"] = True
            break
    data["updated"] = _now_iso()
    _write_yaml(_manifest_path(slug, variant), data)


def list_unprocessed(slug: str, variant: str) -> list[dict]:
    return [m for m in read_manifest(slug, variant)["materials"] if not m["processed"]]


def material_count(slug: str, variant: str) -> dict:
    materials = read_manifest(slug, variant)["materials"]
    processed = sum(1 for m in materials if m["processed"])
    out = {
        "total": len(materials),
        "processed": processed,
        "unprocessed": len(materials) - processed,
        "self_total": len(materials),
        "parent_total": 0,
    }
    try:
        from prism.scripts.topic import read_topic
        parent_mats = read_topic(slug, variant).get("parent_materials") or []
        out["parent_total"] = len(parent_mats)
    except (FileNotFoundError, ImportError):
        pass
    return out
