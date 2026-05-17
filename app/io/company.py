"""Create a new company directory by rendering markdown templates."""
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

import yaml

from app import config as cfg
from app.config import VALID_MARKETS

_META_KEYS = (
    "ticker",
    "market",
    "name",
    "industry_slugs",
    "arenas",
    "themes",
    "listed_date",
    "currency",
    "website",
)

# (output filename, template filename)
_TEMPLATE_MAP = (
    ("meta.md", "meta.md.tmpl"),
    ("v0.md", "v0.md.tmpl"),
    ("valuation.md", "valuation.md.tmpl"),
    ("trade-log.md", "trade-log.md.tmpl"),
)


def create_company(
    ticker: str,
    market: str,
    name: str,
    industry_slugs: list[str] | None = None,
    currency: str = "USD",
    base: Path | None = None,
    templates_dir: Path | None = None,
    today: date | None = None,
) -> Path:
    """Lay down a new company directory with all template files rendered.

    ``industry_slugs`` is a free-form list of industry slugs the company
    belongs to (multi-industry supported). No whitelist enforcement — the
    industry layer owns the canonical registry.
    """
    if market not in VALID_MARKETS:
        raise ValueError(f"unknown market {market!r}; valid: {VALID_MARKETS}")

    ticker = ticker.strip().upper()
    if not ticker:
        raise ValueError("ticker cannot be empty")

    industry_slugs = list(industry_slugs or [])

    today = today or date.today()
    base_path = Path(base) if base else cfg.BASE_PATH
    companies_dir = base_path / "companies" if base else cfg.COMPANIES_DIR
    tpl_dir = Path(templates_dir) if templates_dir else cfg.TEMPLATES_DIR

    out_dir = companies_dir / f"{market}_{ticker}"
    if out_dir.exists():
        raise FileExistsError(f"{out_dir} already exists")

    env = Environment(
        loader=FileSystemLoader(str(tpl_dir)),
        keep_trailing_newline=True,
    )
    ctx = {
        "ticker": ticker,
        "market": market,
        "name": name,
        "industry_slugs": industry_slugs,
        "currency": currency,
        "today": today.isoformat(),
        "year": today.year,
        "action": "buy",
    }

    out_dir.mkdir(parents=True)
    (out_dir / "sources").mkdir()

    for out_name, tpl_name in _TEMPLATE_MAP:
        (out_dir / out_name).write_text(env.get_template(tpl_name).render(**ctx))

    _ensure_narrative_skeletons(ticker, market, name, base)

    return out_dir


def _split_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    fm = yaml.safe_load(text[3:end].strip()) or {}
    if "ticker" in fm and not isinstance(fm["ticker"], str):
        # all-digit tickers (BSE 920118, A-share 600519, HK 0700) in unquoted YAML
        # come back as int; every IO callsite treats ticker as str, so normalize here.
        fm["ticker"] = str(fm["ticker"])
    return fm, text[end + len("\n---") :].lstrip("\n")


def _meta_path(ticker: str, market: str, base: Path | None) -> Path:
    companies_dir = Path(base) / "companies" if base else cfg.COMPANIES_DIR
    return companies_dir / f"{market}_{ticker}" / "meta.md"


def read_meta(ticker: str, market: str, base: Path | None = None) -> dict:
    """Return meta.md frontmatter dict, falling back to prism topics."""
    path = _meta_path(ticker, market, base)
    if path.exists():
        fm, _ = _split_frontmatter(path.read_text(encoding="utf-8"))
        return fm
    # Fall back to prism company topics
    for pt in _prism_company_topics():
        if pt["key"] == f"{market}_{ticker}":
            return {"name": pt["name"], "ticker": ticker, "market": market}
    return {}


def read_meta_with_body(
    ticker: str, market: str, base: Path | None = None
) -> dict:
    """Return ``{frontmatter, body, exists}`` for meta.md."""
    path = _meta_path(ticker, market, base)
    if not path.exists():
        return {"frontmatter": {}, "body": "", "exists": False}
    fm, body = _split_frontmatter(path.read_text(encoding="utf-8"))
    return {"frontmatter": fm, "body": body, "exists": True}


def _emit_meta_frontmatter(fm: dict) -> str:
    ordered: dict = {}
    for k in _META_KEYS:
        if k in fm and fm[k] not in (None, ""):
            ordered[k] = fm[k]
    for k, v in fm.items():
        if k not in ordered and v not in (None, ""):
            ordered[k] = v
    return "---\n" + yaml.safe_dump(ordered, allow_unicode=True, sort_keys=False).rstrip() + "\n---\n"


def write_meta(
    ticker: str,
    market: str,
    frontmatter: dict,
    body: str,
    base: Path | None = None,
) -> Path:
    """Write meta.md.

    ``industry_slugs`` accepts either a list[str] or a comma-separated string
    (which gets coerced to a list). No whitelist — industry slugs are managed
    by the industry layer.

    ``themes`` is allowed as a list[str] — used by portfolio theme exposure rule.
    """
    fm = {**frontmatter}
    fm["ticker"] = ticker
    fm["market"] = market
    industry_slugs = fm.get("industry_slugs")
    if industry_slugs is not None:
        if isinstance(industry_slugs, str):
            industry_slugs = [s.strip() for s in industry_slugs.split(",") if s.strip()]
        if not isinstance(industry_slugs, list) or not all(
            isinstance(s, str) for s in industry_slugs
        ):
            raise ValueError("industry_slugs must be a list of strings")
        fm["industry_slugs"] = industry_slugs
    themes = fm.get("themes")
    if themes is not None:
        if isinstance(themes, str):
            themes = [t.strip() for t in themes.split(",") if t.strip()]
        if not isinstance(themes, list) or not all(isinstance(t, str) for t in themes):
            raise ValueError("themes must be a list of strings")
        fm["themes"] = themes
    arenas = fm.get("arenas")
    if arenas is not None:
        if isinstance(arenas, str):
            arenas = [a.strip() for a in arenas.split(",") if a.strip()]
        if not isinstance(arenas, list) or not all(isinstance(a, str) for a in arenas):
            raise ValueError("arenas must be a list of strings")
        fm["arenas"] = arenas
    path = _meta_path(ticker, market, base)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = _emit_meta_frontmatter(fm) + "\n" + body.lstrip()
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text, encoding="utf-8")
    return path


def _company_dir(ticker: str, market: str, base: Path | None) -> Path:
    companies_dir = Path(base) / "companies" if base else cfg.COMPANIES_DIR
    return companies_dir / f"{market}_{ticker}"


def list_sources(ticker: str, market: str, base: Path | None = None) -> list[str]:
    d = _company_dir(ticker, market, base) / "sources"
    if not d.exists():
        return []
    return sorted(f.name for f in d.iterdir() if f.is_file())


def _prism_company_topics() -> list[dict]:
    """Collect company-type prism topics with tickers as synthetic company entries."""
    try:
        from prism.scripts.topic import list_topics as prism_list_topics
    except Exception:
        return []
    all_topics = prism_list_topics()
    seen: set[str] = set()
    result: list[dict] = []
    for t in all_topics:
        if t.get("type") != "company":
            continue
        scope = t.get("scope") or {}
        ticker_full = scope.get("ticker", "")
        if not ticker_full:
            continue
        # ticker may be plain code (e.g. "001270") with market in separate field,
        # or legacy format "SZSE_001270"
        if "_" in ticker_full:
            market, code = ticker_full.split("_", 1)
        else:
            market = scope.get("market", "")
            code = ticker_full
        if not market or not code:
            continue
        key = f"{market}_{code}"
        if key in seen:
            continue
        seen.add(key)
        result.append({
            "key": key,
            "ticker": code,
            "market": market,
            "name": t.get("display_name") or code,
            "industry_slugs": [],
            "v0_status": "prism",
            "competence_score": None,
            "in_competence": None,
        })
    return result


def list_companies(base: Path | None = None) -> list[dict]:
    """Enumerate companies/ subdirectories, augmented with prism company topics."""
    companies_dir = Path(base) / "companies" if base else cfg.COMPANIES_DIR
    out: list[dict] = []
    if companies_dir.exists():
        for d in sorted(companies_dir.iterdir()):
            if not d.is_dir():
                continue
            name = d.name
            if "_" not in name:
                continue
            market, ticker = name.split("_", 1)
            meta_path = d / "meta.md"
            v0_path = d / "v0.md"
            comp_path = d / "competence-check.md"

            meta_fm: dict = {}
            if meta_path.exists():
                meta_fm, _ = _split_frontmatter(meta_path.read_text(encoding="utf-8"))

            v0_status = "missing"
            if v0_path.exists():
                v0_fm, _ = _split_frontmatter(v0_path.read_text(encoding="utf-8"))
                v0_status = v0_fm.get("status") or "missing"

            comp_score = None
            comp_pass = None
            if comp_path.exists():
                comp_fm, _ = _split_frontmatter(comp_path.read_text(encoding="utf-8"))
                comp_score = comp_fm.get("universal_score")
                comp_pass = comp_fm.get("in_competence")

            out.append(
                {
                    "key": name,
                    "ticker": ticker,
                    "market": market,
                    "name": meta_fm.get("name") or ticker,
                    "industry_slugs": list(meta_fm.get("industry_slugs") or []),
                    "v0_status": v0_status,
                    "competence_score": comp_score,
                    "in_competence": comp_pass,
                }
            )

    # Merge prism company topics (companies/ entries take precedence)
    existing_keys = {c["key"] for c in out}
    for pt in _prism_company_topics():
        if pt["key"] not in existing_keys:
            out.append(pt)
        else:
            existing = next(c for c in out if c["key"] == pt["key"])
            if existing.get("name") == existing.get("ticker") and pt["name"] != pt["ticker"]:
                existing["name"] = pt["name"]

    return out


# ---------- Narrative (8-dim, spec §4.1) ----------

_COMPANY_CN_TITLES = {
    "business_model": "业务模式",
    "moat": "护城河与竞争策略",
    "growth_engine": "增长引擎与未来规划",
    "management": "管理层与治理",
    "financial_profile": "财务分析",
    "catalysts": "关键事件与催化剂",
    "risks": "风险",
    "valuation": "估值",
}

_COMPANY_NARRATIVE_TEMPLATE = """
### 来源 {institution} {date} (sha8={sha8})
source_id: {source_id}

{block}
"""


def _narratives_dir(ticker: str, market: str, base: Path | None) -> Path:
    return _company_dir(ticker, market, base) / "narratives"


def _narrative_path(ticker: str, market: str, dim: str, base: Path | None) -> Path:
    if dim not in cfg.COMPANY_DIMENSIONS:
        raise ValueError(f"unknown company dim {dim!r}; must be one of {cfg.COMPANY_DIMENSIONS}")
    return _narratives_dir(ticker, market, base) / f"{dim.replace('_', '-')}.md"


def _ensure_narrative_skeletons(ticker: str, market: str, name: str, base: Path | None) -> None:
    narr_dir = _narratives_dir(ticker, market, base)
    narr_dir.mkdir(exist_ok=True)
    for dim in cfg.COMPANY_DIMENSIONS:
        path = _narrative_path(ticker, market, dim, base)
        if not path.exists():
            header = f"# {_COMPANY_CN_TITLES[dim]} · {name}\n\n*{market}_{ticker} · 维度: {dim}*\n\n"
            path.write_text(header, encoding="utf-8")


def read_narrative(ticker: str, market: str, dim: str, base: Path | None = None) -> str:
    path = _narrative_path(ticker, market, dim, base)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def append_narrative_block(
    ticker: str, market: str, dim: str, block: str,
    source_meta: dict, base: Path | None = None,
) -> None:
    path = _narrative_path(ticker, market, dim, base)
    for key in ("institution", "date", "sha8", "source_id"):
        if key not in source_meta:
            raise ValueError(f"source_meta missing {key}")
    rendered = _COMPANY_NARRATIVE_TEMPLATE.format(
        institution=source_meta["institution"],
        date=source_meta["date"],
        sha8=source_meta["sha8"],
        source_id=source_meta["source_id"],
        block=block.rstrip(),
    )
    with path.open("a", encoding="utf-8") as f:
        f.write(rendered)
