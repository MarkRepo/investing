"""Scrape SMM newenergy public price tables for prism research.

数据范围：
- newenergy.smm.cn/price/{board_id} 页面的 ant-table 直接 server-rendered，
  公开可读，含产品名/规格/价格区间/均价/涨跌/单位/日期/SMM cat_id
- 比 hq.smm.cn 单类目页强：一页就是一张品类总表，30+ 产品的最新报价

固态电池 topic 相关 board（K2 + K3）：
  14042-15013  电芯模组（25 行：三元/磷酸铁锂各规格电芯 + 储能电池 + Pack）→ K2
  14042-15010  锂现货（37 行：碳酸锂/氢氧化锂/六氟磷酸锂 + LPSC/LATP/LLZO + 锂辉石）→ K2+K3

Usage:
    python -m scripts.smm_price_scraper 14042-15013
    python -m scripts.smm_price_scraper 14042-15013 --slug global-solid-state-battery --variant claude-opus-4-7 --addresses K2
    python -m scripts.smm_price_scraper --preset ssb --slug global-solid-state-battery --variant claude-opus-4-7
"""
from __future__ import annotations

import argparse
import logging
import re
import time
from datetime import date
from pathlib import Path

import requests

log = logging.getLogger("smm_price_scraper")

_BASE_URL = "https://newenergy.smm.cn/price/{board}"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept-Encoding": "gzip, deflate, br",
}

# 合法 board 白名单 —— 仅允许 newenergy.smm.cn/price/14042-15010 同级（锂电池系 11 板）
# 与 151036-* 全固态电池专板（4 板）。其他来源（钠电 14004-*、光伏 9014-*）不属于本研究域。
_ALLOWED_BOARDS: dict[str, str] = {
    # 14042-* 锂电池系（14042-15010 同级，共 11 个 board）
    "14042-15010": "锂",
    "14042-15011": "钴",
    "14042-15004": "正极材料",
    "14042-15008": "磷",
    "14042-15005": "碳素负极",
    "14042-15012": "隔膜",
    "14042-15014": "电解液",
    "14042-15013": "电芯模组",
    "14042-15009": "锂电再生",
    "14042-15007": "镍锰",
    "14042-15006": "其他材料",
    # 151036-* 全固态电池专板（4 个 board）
    "151036-151037": "全固态-正极",
    "151036-151038": "全固态-负极",
    "151036-151039": "全固态-电解质",
    "151036-151041": "全固态-其他材料",
}


def _validate_board(board: str) -> None:
    if board not in _ALLOWED_BOARDS:
        raise ValueError(
            f"Board '{board}' not in allowed set. "
            f"Allowed (via newenergy.smm.cn/price/14042-15010 + 全固态 151036-*): "
            f"{sorted(_ALLOWED_BOARDS)}"
        )


# 预设 board 集合（固态电池 topic）
_PRESETS: dict[str, list[tuple[str, str, list[str]]]] = {
    "ssb": [
        # K2 — 液态 LFP/三元降本：电芯单价 + 上游锂/正极/电解液/隔膜/负极
        ("14042-15013", "SMM 电芯模组现货价格", ["K2"]),
        ("14042-15010", "SMM 锂现货价格", ["K2"]),
        ("14042-15004", "SMM 正极材料现货价格", ["K2"]),
        ("14042-15014", "SMM 电解液现货价格", ["K2"]),
        ("14042-15005", "SMM 碳素负极现货价格", ["K2"]),
        # K3 — 固态电解质路线分化（专板，与 K2 上游对照）
        ("151036-151037", "SMM 全固态正极现货价格", ["K3"]),
        ("151036-151038", "SMM 全固态负极（锂金属）现货价格", ["K3"]),
        ("151036-151039", "SMM 全固态电解质现货价格", ["K3"]),
        ("151036-151041", "SMM 全固态其他材料现货价格", ["K3"]),
    ],
    # 全集（锂电 + 全固态所有 15 板），其他锂电 topic 可复用
    "all-lithium": [
        (b, f"SMM {label}现货价格", []) for b, label in _ALLOWED_BOARDS.items()
    ],
}


def _slug_safe(name: str) -> str:
    return re.sub(r"[<>:\"/\\|?*\s]+", "_", name).strip("_")


def fetch_page(board: str) -> tuple[str, str]:
    """Fetch price page. Returns (html, page_title)."""
    _validate_board(board)
    url = _BASE_URL.format(board=board)
    r = requests.get(url, headers=_HEADERS, timeout=30)
    r.raise_for_status()
    html = r.text
    title_m = re.search(r"<title>([^<]+)</title>", html)
    title = title_m.group(1).strip() if title_m else f"SMM board {board}"
    title = re.sub(r"_新能源材料今日价格_上海有色网\s*$", "", title)
    title = re.sub(r"_上海有色网\s*$", "", title)
    return html, title


def parse_price_table(html: str) -> list[dict]:
    """Parse ant-table rows into structured price records.

    每行字段：name, cat_id (-> hq.smm.cn 子页), spec, low, high, avg, change, unit, date
    """
    trs = re.findall(r'<tr[^>]*class="ant-table-row[^"]*"[^>]*>(.*?)</tr>', html, re.DOTALL)
    rows: list[dict] = []
    for tr in trs:
        # 产品名 + cat_id（链接到 hq.smm.cn/new-energy/category/{cat_id}）
        prod_m = re.search(r'category/(\d+)[^>]*>([^<]+)</a>', tr)
        name = prod_m.group(2).strip() if prod_m else "?"
        cat_id = prod_m.group(1) if prod_m else ""

        # 清掉 svg/script/style，把剩下的 tag 当分隔符
        clean = re.sub(r'<svg.*?</svg>', '', tr, flags=re.DOTALL)
        clean = re.sub(r'<(?:script|style)[^>]*>.*?</(?:script|style)>', '', clean, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', '|', clean)
        cells_raw = [c.strip() for c in re.split(r'\|+', text) if c.strip()]

        # 第一个 cell 是产品名（已抽出），后续应为 spec / 区间 / 均价 / 涨跌 / 单位 / 日期 / "加自选"
        body = cells_raw[1:] if cells_raw and cells_raw[0] == name else cells_raw
        body = [c for c in body if c not in ("加自选",)]
        if len(body) < 6:
            continue
        spec, price_range, avg, change, unit, day = body[:6]
        low, high = None, None
        m = re.match(r"\s*([\d.,]+)\s*~\s*([\d.,]+)\s*", price_range)
        if m:
            low, high = m.group(1), m.group(2)
        rows.append({
            "cat_id": cat_id,
            "name": name,
            "spec": spec,
            "low": low,
            "high": high,
            "avg": avg,
            "change": change,
            "unit": unit,
            "date": day,
        })
    return rows


def render_markdown(board: str, title: str, rows: list[dict], url: str) -> str:
    today = date.today().isoformat()
    # 日期范围（页内各行的最新日期）
    dates_seen = sorted({r["date"] for r in rows if r.get("date")})
    latest = dates_seen[-1] if dates_seen else today

    lines = [
        "---",
        f"title: \"{title}\"",
        f"source: {url}",
        f"smm_board: {board}",
        f"latest_quote_date: {latest}",
        f"scraped: {today}",
        f"row_count: {len(rows)}",
        "source_type: smm-price-table",
        "---",
        "",
        f"# {title}",
        "",
        f"**SMM board**: `{board}` · **报价最新日期**: {latest} · **抓取**: {today} · **共 {len(rows)} 行**",
        f"> 数据源：{url}（公开 server-rendered 价格表）",
        "",
        "| 产品 | 规格 | 低 | 高 | 均价 | 涨跌 | 单位 | 报价日 | SMM 类目 |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- |",
    ]
    for r in rows:
        # 表格里 | 要转义
        def esc(s):
            return str(s or "").replace("|", "\\|")
        cat_link = f"[{r['cat_id']}](https://hq.smm.cn/new-energy/category/{r['cat_id']})" if r["cat_id"] else ""
        lines.append(
            f"| {esc(r['name'])} | {esc(r['spec'])} | {esc(r['low'])} | {esc(r['high'])} | "
            f"{esc(r['avg'])} | {esc(r['change'])} | {esc(r['unit'])} | {esc(r['date'])} | {cat_link} |"
        )
    lines.append("")
    return "\n".join(lines)


def scrape_to_file(board: str, out_dir: Path, title_hint: str = "") -> tuple[Path, list[dict], str]:
    log.info("Fetching SMM board %s (%s)...", board, title_hint or "?")
    html, title = fetch_page(board)
    if title_hint:
        title = title_hint
    rows = parse_price_table(html)
    url = _BASE_URL.format(board=board)
    md = render_markdown(board, title, rows, url)

    today = date.today().isoformat()
    # 文件名用稳定的 board id（不含 title），避免 title 微调导致 manifest 重复
    out_path = out_dir / f"SMM_{today}_{board}.md"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")
    log.info("Saved → %s (%d bytes, %d rows)", out_path, len(md), len(rows))
    return out_path, rows, title


def scrape_and_register(
    board: str,
    slug: str,
    variant: str,
    title_hint: str = "",
    addresses: list[str] | None = None,
) -> str | None:
    from prism.scripts.manifest import add_material, create_manifest, read_manifest

    materials_dir = Path(__file__).parent.parent / "prism" / "topics" / slug / "materials"
    materials_dir.mkdir(parents=True, exist_ok=True)

    out_path, rows, title = scrape_to_file(board, materials_dir, title_hint)
    if not rows:
        log.warning("Board %s parsed 0 rows — skipping manifest registration", board)
        return None

    try:
        read_manifest(slug, variant)
    except FileNotFoundError:
        create_manifest(slug, variant)

    mat_id = add_material(
        slug=slug,
        filename=out_path.name,
        source_type="data",
        variant=variant,
        notes=f"SMM 公开价格表 — {title} (board {board}, {len(rows)} 行)",
        addresses=addresses,
    )
    log.info("Registered manifest: %s → %s", out_path.name, mat_id)
    return mat_id


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser(description="Scrape SMM newenergy public price tables")
    p.add_argument("board", nargs="?", help="board id like 14042-15013")
    p.add_argument("--preset", choices=list(_PRESETS), help="Use preset board bundle")
    p.add_argument("--slug", help="prism topic slug — register in manifest")
    p.add_argument("--variant", help="prism variant")
    p.add_argument("--out", type=Path, help="Output dir (when no --slug)")
    p.add_argument("--addresses", help="Comma-separated K#/Q# addresses")
    p.add_argument("--title", help="Override page title")
    args = p.parse_args()

    if not args.board and not args.preset:
        p.error("Need board OR --preset")
    if args.slug and not args.variant:
        p.error("--variant required with --slug")

    targets: list[tuple[str, str, list[str]]]
    if args.preset:
        targets = list(_PRESETS[args.preset])
    else:
        addrs = [a.strip() for a in (args.addresses or "").split(",") if a.strip()]
        targets = [(args.board, args.title or "", addrs)]

    for board, name, addrs in targets:
        try:
            if args.slug:
                scrape_and_register(board, args.slug, args.variant, name, addrs)
            else:
                out_dir = args.out or Path(".")
                scrape_to_file(board, out_dir, name)
            time.sleep(1)
        except Exception as e:
            log.error("FAILED %s (%s): %s", board, name, e)


if __name__ == "__main__":
    main()
