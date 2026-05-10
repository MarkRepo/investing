"""Query output state for topics. Zero LLM calls."""
from __future__ import annotations

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
]

# Additional outputs that can be generated via workflows
_EXTRA_OUTPUTS_LABELS = [
    ("05-critic-review", "批评者评审"),
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
        state = outputs_state.get(key, {"version": 0, "last_updated": None, "status": "pending"})
        out_path = _topic_dir(slug, variant) / "outputs" / f"{key}.md"
        result.append({
            "key": key,
            "label": label,
            "status": state.get("status", "pending"),
            "version": state.get("version", 0),
            "last_updated": state.get("last_updated"),
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
            result.append({
                "key": filepath.name[:-3],  # without .md
                "label": label,
                "status": "fresh",
                "version": 1,
                "last_updated": info.get("generated"),
                "file_exists": True,
                "is_drilldown": True,
            })
    return result


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
