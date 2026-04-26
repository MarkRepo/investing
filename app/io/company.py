"""Create a new company directory by rendering markdown templates."""
import re
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

_PROFILE_KEYS = ("ticker", "market", "year", "profile_date", "source", "source_file")
_PROFILE_RE = re.compile(r"^profile-(\d{4})\.md$")

# (output filename, template filename)
_TEMPLATE_MAP = (
    ("meta.md", "meta.md.tmpl"),
    ("v0.md", "v0.md.tmpl"),
    ("competence-check.md", "competence-check.md.tmpl"),
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
    (out_dir / "claims.jsonl").write_text("")

    for out_name, tpl_name in _TEMPLATE_MAP:
        (out_dir / out_name).write_text(env.get_template(tpl_name).render(**ctx))

    profile_name = f"profile-{today.year}.md"
    (out_dir / profile_name).write_text(
        env.get_template("profile-YYYY.md.tmpl").render(**ctx)
    )

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
    """Return meta.md frontmatter dict, empty if missing."""
    path = _meta_path(ticker, market, base)
    if not path.exists():
        return {}
    fm, _ = _split_frontmatter(path.read_text(encoding="utf-8"))
    return fm


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


# --- profile-YYYY.md ---------------------------------------------------------


def _company_dir(ticker: str, market: str, base: Path | None) -> Path:
    companies_dir = Path(base) / "companies" if base else cfg.COMPANIES_DIR
    return companies_dir / f"{market}_{ticker}"


def list_profiles(ticker: str, market: str, base: Path | None = None) -> list[dict]:
    """Return all profile-YYYY.md entries sorted by year desc."""
    d = _company_dir(ticker, market, base)
    if not d.exists():
        return []
    out: list[dict] = []
    for p in d.iterdir():
        m = _PROFILE_RE.match(p.name)
        if not m:
            continue
        fm, _ = _split_frontmatter(p.read_text(encoding="utf-8"))
        out.append({
            "year": int(m.group(1)),
            "profile_date": fm.get("profile_date"),
            "source_file": fm.get("source_file") or fm.get("source"),
            "path": p.name,
        })
    out.sort(key=lambda r: r["year"], reverse=True)
    return out


def read_profile(
    ticker: str, market: str, year: int, base: Path | None = None
) -> dict:
    """Return ``{frontmatter, body, exists}`` for profile-{year}.md."""
    path = _company_dir(ticker, market, base) / f"profile-{year}.md"
    if not path.exists():
        return {"frontmatter": {}, "body": "", "exists": False}
    fm, body = _split_frontmatter(path.read_text(encoding="utf-8"))
    return {"frontmatter": fm, "body": body, "exists": True}


def _emit_profile_frontmatter(fm: dict) -> str:
    ordered: dict = {}
    for k in _PROFILE_KEYS:
        if k in fm and fm[k] not in (None, ""):
            ordered[k] = fm[k]
    for k, v in fm.items():
        if k not in ordered and v not in (None, ""):
            ordered[k] = v
    return "---\n" + yaml.safe_dump(ordered, allow_unicode=True, sort_keys=False).rstrip() + "\n---\n"


def write_profile(
    ticker: str,
    market: str,
    year: int,
    frontmatter: dict,
    body: str,
    base: Path | None = None,
) -> Path:
    """Write profile-{year}.md.

    ``source_file`` must point to a file under this company's ``sources/``
    directory (enforces DESIGN §8 坑 9: no news-as-fact).
    """
    company_dir = _company_dir(ticker, market, base)
    sources_dir = company_dir / "sources"
    source_file = str(frontmatter.get("source_file") or "").strip()
    if not source_file:
        raise ValueError(
            "source_file is required — fact layer must cite an annual report "
            "or filing under sources/ (DESIGN §8 坑 9)."
        )
    # Accept either relative ("sources/xyz.md") or just the filename.
    candidate_names = [source_file]
    if source_file.startswith("sources/"):
        candidate_names.append(source_file[len("sources/"):])
    resolved: Path | None = None
    for name in candidate_names:
        p = sources_dir / Path(name).name
        if p.exists():
            resolved = p
            break
    if resolved is None:
        raise ValueError(
            f"source_file {source_file!r} not found in {sources_dir}. "
            "Upload the annual report / filing first (fact layer rule)."
        )
    fm = {**frontmatter}
    fm["ticker"] = ticker
    fm["market"] = market
    fm["year"] = year
    fm["source_file"] = f"sources/{resolved.name}"
    fm.setdefault("profile_date", date.today().isoformat())
    fm.setdefault("source", "annual_report")

    path = company_dir / f"profile-{year}.md"
    company_dir.mkdir(parents=True, exist_ok=True)
    text = _emit_profile_frontmatter(fm) + "\n" + body.lstrip()
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text, encoding="utf-8")
    return path


def list_sources(ticker: str, market: str, base: Path | None = None) -> list[str]:
    d = _company_dir(ticker, market, base) / "sources"
    if not d.exists():
        return []
    return sorted(f.name for f in d.iterdir() if f.is_file())


def list_companies(base: Path | None = None) -> list[dict]:
    """Enumerate companies/ subdirectories and return summary rows."""
    companies_dir = Path(base) / "companies" if base else cfg.COMPANIES_DIR
    if not companies_dir.exists():
        return []

    out: list[dict] = []
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
    return out
