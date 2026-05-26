"""Findings discovery — own + parent material reuse.

The single source of truth for "which findings does this topic synthesize from".
Used by workflow 04 (synthesize) and workflow 10 (peer-matrix).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from prism.scripts.topic import _topic_path, _read_yaml


def _own_findings_dir(slug: str, variant: str) -> Path:
    return _topic_path(slug, variant).parent / "outputs"


_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _read_frontmatter(path: Path) -> dict:
    """Read YAML frontmatter from a finding markdown file. Returns {} if absent."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}
    try:
        return yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return {}


def _first_data_bullet(path: Path, max_chars: int = 100) -> str:
    """Grab the first 1-2 substantial data lines from a finding for index summary."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    body = _FRONTMATTER_RE.sub("", text, count=1)
    for line in body.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or s.startswith(">"):
            continue
        s = re.sub(r"^[-*\d.\s]+", "", s)
        s = re.sub(r"\*+", "", s)
        if len(s) >= 20:
            return s[:max_chars] + ("…" if len(s) > max_chars else "")
    return ""


def _manifest_addresses_map(slug: str, variant: str) -> dict[str, list[str]]:
    """Return {mat_id: addresses} from manifest.yaml. Best-effort, [] if missing."""
    try:
        from prism.scripts.manifest import read_manifest
        mats = read_manifest(slug, variant).get("materials", [])
    except Exception:
        return {}
    return {m["id"]: list(m.get("addresses") or []) for m in mats}


def list_all_findings(slug: str, variant: str) -> list[dict[str, Any]]:
    """Return all findings paths for synthesis: own + parent_materials.

    Each entry: {mat_id, path (Path), source_slug, source_variant, addresses, note, reuse,
                 quality?, bias?, summary?}
    - reuse=False: own finding under outputs/findings_<mat_id>.md
    - reuse=True: parent's finding referenced via topic.yaml parent_materials

    addresses, quality, bias 优先从 finding frontmatter 读；frontmatter 缺失时
    回退到 manifest.yaml 的 addresses 字段（自有 findings only）。
    summary = 首条数据点的前 100 字（用于轻索引）。
    """
    topic_path = _topic_path(slug, variant)
    if not topic_path.exists():
        raise FileNotFoundError(f"Topic not found: {slug}/{variant}")
    data = _read_yaml(topic_path)

    out: list[dict[str, Any]] = []

    own_dir = _own_findings_dir(slug, variant)
    if own_dir.is_dir():
        own_addr_map = _manifest_addresses_map(slug, variant)
        for p in sorted(own_dir.glob("findings_mat-*.md")):
            mat_id = p.stem.replace("findings_", "")
            fm = _read_frontmatter(p)
            addr = fm.get("addresses") or own_addr_map.get(mat_id) or []
            out.append({
                "mat_id": mat_id,
                "path": p,
                "source_slug": slug,
                "source_variant": variant,
                "addresses": list(addr),
                "note": "",
                "reuse": False,
                "filename": fm.get("filename", ""),
                "quality": fm.get("quality", ""),
                "bias": fm.get("bias", ""),
                "summary": _first_data_bullet(p),
            })

    for ref in data.get("parent_materials") or []:
        psrc = ref.get("parent_slug")
        pvar = ref.get("parent_variant", variant)
        mat_id = ref.get("mat_id")
        if not (psrc and mat_id):
            continue
        finding_path = _topic_path(psrc, pvar).parent / "outputs" / f"findings_{mat_id}.md"
        if not finding_path.exists():
            continue
        fm = _read_frontmatter(finding_path)
        out.append({
            "mat_id": mat_id,
            "path": finding_path,
            "source_slug": psrc,
            "source_variant": pvar,
            "addresses": list(ref.get("addresses") or fm.get("addresses") or []),
            "note": ref.get("note", ""),
            "reuse": True,
            "filename": fm.get("filename", ""),
            "quality": fm.get("quality", ""),
            "bias": fm.get("bias", ""),
            "summary": _first_data_bullet(finding_path),
        })

    return out


def list_missing_parent_findings(slug: str, variant: str) -> list[dict[str, Any]]:
    """声明了 parent_materials 但 findings_{mat_id}.md 文件不存在的引用。

    H3 修法：03 起手暴露给用户，避免 04 时 list_all_findings 静默跳过
    （findings.py:113-114 silent skip）导致父级 finding 缺失却无人察觉。

    每条返回：{mat_id, parent_slug, parent_variant, expected_path, addresses, note}
    """
    topic_path = _topic_path(slug, variant)
    if not topic_path.exists():
        return []
    data = _read_yaml(topic_path)
    missing: list[dict[str, Any]] = []
    for ref in data.get("parent_materials") or []:
        psrc = ref.get("parent_slug")
        pvar = ref.get("parent_variant", variant)
        mat_id = ref.get("mat_id")
        if not (psrc and mat_id):
            continue
        finding_path = _topic_path(psrc, pvar).parent / "outputs" / f"findings_{mat_id}.md"
        if finding_path.exists():
            continue
        missing.append({
            "mat_id": mat_id,
            "parent_slug": psrc,
            "parent_variant": pvar,
            "expected_path": str(finding_path),
            "addresses": list(ref.get("addresses") or []),
            "note": ref.get("note", ""),
        })
    return missing


def list_findings_by_addresses(slug: str, variant: str, address_filter: list[str]) -> list[dict[str, Any]]:
    """Return findings whose addresses intersect with `address_filter`.

    用于 sub-workflow 按 K#/Q# 维度筛取相关 finding（如 06-risks 取 [risk, K1, K6]）。
    address_filter 空 → 返回全部（等价 list_all_findings）。
    """
    items = list_all_findings(slug, variant)
    if not address_filter:
        return items
    needle = set(address_filter)
    return [x for x in items if needle & set(x.get("addresses") or [])]


def build_findings_index(slug: str, variant: str, write: bool = True) -> str:
    """生成轻 findings 索引（每行 ~80-120 字）：mat_id | filename | addresses | quality/bias | 摘要。

    用途：04-synthesize 写每个批次前，主 agent 先看 index 判断 context 是否完整、
    哪些 finding 与本批次相关。22 份 ≈ 3-5K tokens，远低于全文 ~40K。

    write=True 时落盘到 outputs/_findings_index.md，返回路径字符串；
    write=False 仅返回 markdown 文本（用于直接嵌 prompt）。
    """
    items = list_all_findings(slug, variant)
    own = [x for x in items if not x["reuse"]]
    reuse = [x for x in items if x["reuse"]]

    lines: list[str] = []
    lines.append(f"# Findings Index — {slug}/{variant}")
    lines.append("")
    lines.append("> 主 agent 调度提示：写每批 output 前重读本文件，按 addresses 判断 context 是否覆盖所需维度；")
    lines.append("> 记忆模糊的 mat_id 单独 Read `outputs/findings_{mat_id}.md` 补回。")
    lines.append("")
    lines.append(f"## 自有 findings（{len(own)} 份）")
    lines.append("")
    for x in own:
        addr = ",".join(x["addresses"]) if x["addresses"] else "-"
        qb = f"{x['quality'] or '?'}/{x['bias'] or '?'}"
        fname = x["filename"] or x["path"].name
        summary = x["summary"] or "(no summary)"
        lines.append(f"- `{x['mat_id']}` | {fname} | addresses=[{addr}] | {qb} | {summary}")
    if reuse:
        lines.append("")
        lines.append(f"## 父级复用 findings（{len(reuse)} 份）")
        lines.append("")
        for x in reuse:
            addr = ",".join(x["addresses"]) if x["addresses"] else "-"
            qb = f"{x['quality'] or '?'}/{x['bias'] or '?'}"
            fname = x["filename"] or x["path"].name
            summary = x["summary"] or "(no summary)"
            lines.append(f"- `{x['mat_id']}` | {fname} | addresses=[{addr}] | {qb} | {summary} (parent={x['source_slug']})")

    md = "\n".join(lines) + "\n"
    if write:
        out_path = _own_findings_dir(slug, variant) / "_findings_index.md"
        out_path.write_text(md, encoding="utf-8")
        return str(out_path)
    return md


def format_findings_for_prompt(slug: str, variant: str) -> str:
    """Render the findings list as a markdown bullet block for dispatch prompts."""
    items = list_all_findings(slug, variant)
    own = [x for x in items if not x["reuse"]]
    reuse = [x for x in items if x["reuse"]]
    lines: list[str] = []
    if own:
        lines.append(f"**自有 findings（{len(own)} 份）**：")
        for x in own:
            lines.append(f"- {x['path']}")
    if reuse:
        lines.append("")
        lines.append(f"**父级复用 findings（{len(reuse)} 份）**：")
        for x in reuse:
            addr = f" addresses={x['addresses']}" if x["addresses"] else ""
            note = f" note={x['note']}" if x["note"] else ""
            lines.append(f"- {x['path']} (mat_id={x['mat_id']}, source={x['source_slug']}){addr}{note}")
    return "\n".join(lines)
