"""Grep wrapper for full-text search across repo content.

Scopes limit where the search runs:
    all        → companies/, watchlist/, portfolio/, journal/, industries/, macro/
    companies  → companies/
    watchlist  → watchlist/
    journal    → journal/
"""
import subprocess
from pathlib import Path

from app import config as cfg

_SCOPE_DIRS: dict[str, tuple[str, ...]] = {
    "all": ("companies", "watchlist", "portfolio", "journal", "industries", "macro"),
    "companies": ("companies",),
    "watchlist": ("watchlist",),
    "journal": ("journal",),
    "portfolio": ("portfolio",),
}


def _resolved_paths(scope: str) -> list[Path]:
    dirs = _SCOPE_DIRS.get(scope, _SCOPE_DIRS["all"])
    out: list[Path] = []
    for d in dirs:
        p = cfg.BASE_PATH / d
        if p.exists():
            out.append(p)
    return out


def search(pattern: str, scope: str = "all", max_results: int = 200) -> list[dict]:
    """Return ``[{path, line_no, snippet}]`` for matches.

    Uses ``grep -rn --include=*.md --include=*.jsonl`` without shell=True so the
    pattern is passed as an argv element and not interpreted by the shell.
    """
    if not pattern:
        return []
    paths = _resolved_paths(scope)
    if not paths:
        return []

    cmd = [
        "grep", "-rn",
        "--include=*.md",
        "--include=*.jsonl",
        "--include=*.yaml",
        "--binary-files=without-match",
        "-F",  # fixed-string search; avoids regex surprises from user input
        pattern,
        *[str(p) for p in paths],
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return []

    results: list[dict] = []
    for line in proc.stdout.splitlines():
        # grep -n format: path:lineno:content
        parts = line.split(":", 2)
        if len(parts) < 3:
            continue
        path, line_no, snippet = parts
        try:
            lno = int(line_no)
        except ValueError:
            continue
        rel_path = path
        try:
            rel_path = str(Path(path).relative_to(cfg.BASE_PATH))
        except ValueError:
            pass
        results.append({"path": rel_path, "line_no": lno, "snippet": snippet.strip()})
        if len(results) >= max_results:
            break
    return results
