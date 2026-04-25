"""Valuation I/O + three-scenario weighted average + five-tier signal.

File: ``companies/{market}_{ticker}/valuation.md``. Structure:

- YAML frontmatter with prices/probabilities/discount rate/current price
- Free-form markdown body (three scenarios, relative, inverse, conclusion)

Five-tier signal (DESIGN §3.2 V0 template):
  - ≤ bear × 1.2      : HEAVY_BUY (最深档)
  - ≤ base × 0.7      : BUY (30% 安全边际)
  - ≈ base (±10%)     : FAIR (不买不卖)
  - ≥ base × 1.3      : TRIM (减仓)
  - ≥ bull            : EXIT (纯梦想定价)
"""
from pathlib import Path
from typing import Any

import yaml

from app import config as cfg

_FRONTMATTER_KEYS = (
    "ticker", "market", "valuation_date",
    "bull_price", "base_price", "bear_price",
    "prob_bull", "prob_base", "prob_bear",
    "weighted_expected", "current_price",
    "implied_return_to_base", "discount_rate",
)


def _path(ticker: str, market: str, base: Path | None) -> Path:
    root = Path(base) / "companies" if base else cfg.COMPANIES_DIR
    return root / f"{market}_{ticker}" / "valuation.md"


def _split_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    fm = yaml.safe_load(text[3:end].strip()) or {}
    if "ticker" in fm and not isinstance(fm["ticker"], str):
        fm["ticker"] = str(fm["ticker"])
    return fm, text[end + len("\n---") :].lstrip("\n")


def _emit_frontmatter(fm: dict) -> str:
    ordered: dict = {}
    for k in _FRONTMATTER_KEYS:
        if k in fm:
            ordered[k] = fm[k]
    for k, v in fm.items():
        if k not in ordered:
            ordered[k] = v
    return "---\n" + yaml.safe_dump(ordered, allow_unicode=True, sort_keys=False).rstrip() + "\n---\n"


def compute_weighted(
    bull: float, base: float, bear: float,
    p_bull: float, p_base: float, p_bear: float,
) -> float:
    total = p_bull + p_base + p_bear
    if abs(total - 1.0) > 1e-6:
        raise ValueError(f"probabilities must sum to 1.0 (got {total:.4f})")
    return bull * p_bull + base * p_base + bear * p_bear


def discount_rate_default(long_term_yield: float, premium: float = 0.055) -> float:
    return long_term_yield + premium


# Regime verdict → extra premium bps added on top of the baseline.
# Intuition: hot = complacency, ask for more margin of safety. panic = fat
# tail, ask for a lot more. cold = starting point, baseline is already fine.
_REGIME_PREMIUM_ADDON = {
    "hot": 0.01,
    "neutral": 0.0,
    "cold": 0.0,
    "panic": 0.02,
}


def discount_rate_suggest(
    ust_10y_yield: float | None,
    regime_verdict: str | None = None,
    base_premium: float = 0.055,
) -> dict | None:
    """Return ``{baseline, addon, suggested, rationale}`` or None if no yield.

    ``baseline = ust_10y_yield + base_premium`` (DESIGN §2.3).
    ``addon`` depends on the regime verdict — ``panic`` demands much more margin
    of safety than ``hot``, both higher than baseline.
    """
    if ust_10y_yield is None:
        return None
    try:
        y = float(ust_10y_yield)
    except (TypeError, ValueError):
        return None
    addon = _REGIME_PREMIUM_ADDON.get((regime_verdict or "").lower(), 0.0)
    baseline = y + base_premium
    suggested = baseline + addon
    rat = f"10Y 国债 {y*100:.2f}% + 股票风险溢价 {base_premium*100:.1f}%"
    if addon:
        rat += f" + 钟摆 {regime_verdict} 加码 {addon*100:.1f}%"
    return {
        "baseline": round(baseline, 4),
        "addon": round(addon, 4),
        "suggested": round(suggested, 4),
        "rationale": rat,
    }


def five_tier_signal(
    current: float, bull: float, base: float, bear: float,
) -> dict:
    """Return ``{tier, label, rationale}`` describing the signal level."""
    if current <= 0 or base <= 0:
        return {"tier": "unknown", "label": "数据不足", "rationale": "当前价或基准价为 0"}

    if current <= bear * 1.2:
        return {
            "tier": "HEAVY_BUY",
            "label": "重仓",
            "rationale": f"当前价 {current:.2f} ≤ 悲观 {bear:.2f} × 1.2 = {bear*1.2:.2f}，加到买入区间最深档",
        }
    if current <= base * 0.7:
        return {
            "tier": "BUY",
            "label": "可买",
            "rationale": f"当前价 {current:.2f} ≤ 基准 {base:.2f} × 0.7 = {base*0.7:.2f}，有 30% 安全边际",
        }
    if current >= bull:
        return {
            "tier": "EXIT",
            "label": "清仓",
            "rationale": f"当前价 {current:.2f} ≥ 乐观 {bull:.2f}，已是纯梦想定价",
        }
    if current >= base * 1.3:
        return {
            "tier": "TRIM",
            "label": "减仓",
            "rationale": f"当前价 {current:.2f} ≥ 基准 {base:.2f} × 1.3 = {base*1.3:.2f}，通常降到 50% 原仓位",
        }
    return {
        "tier": "FAIR",
        "label": "公允",
        "rationale": f"当前价 {current:.2f} 接近基准 {base:.2f}，不买不卖",
    }


def read_valuation(ticker: str, market: str, base: Path | None = None) -> dict:
    path = _path(ticker, market, base)
    if not path.exists():
        raise FileNotFoundError(str(path))
    fm, body = _split_frontmatter(path.read_text(encoding="utf-8"))
    return {"frontmatter": fm, "body": body}


def write_valuation(
    ticker: str,
    market: str,
    fm: dict,
    body: str,
    base: Path | None = None,
) -> Path:
    """Persist valuation.md; caller is responsible for recomputing derived fields."""
    path = _path(ticker, market, base)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_emit_frontmatter(fm) + "\n" + body.lstrip("\n"), encoding="utf-8")
    return path
