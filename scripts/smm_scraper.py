"""Scrape public SMM (上海有色网) price commentary for prism research.

数据范围：
- 今日精确报价数字需登录（不抓）
- 但「评述」段（市场分析、期货走势、原因解读）公开可读——含期货合约价、趋势方向，对 thesis 跟踪足够

固态电池 topic 相关类目（K2 + K3 验证）：
  K2 液态成本：方形磷酸铁锂电池 314Ah 指数、电池级碳酸锂指数、三元电芯
  K3 路线分化：硫化物电解质 LPSC、氧化物电解质 LATP/LLZO、电池级硫化锂、电池级金属锂

Usage:
    python -m scripts.smm_scraper 202601160010
    python -m scripts.smm_scraper 202601160010 --slug global-solid-state-battery --variant claude-opus-4-7
    python -m scripts.smm_scraper --preset ssb-k2-k3 --slug global-solid-state-battery --variant claude-opus-4-7
"""
from __future__ import annotations

import argparse
import logging
import re
import sys
import time
from datetime import date
from pathlib import Path

import requests

log = logging.getLogger("smm_scraper")

_BASE_URL = "https://hq.smm.cn/new-energy/category/{cat_id}"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept-Encoding": "gzip, deflate, br",
}

# 预设的 K2/K3 相关类目集合（针对固态电池 topic）
_PRESETS: dict[str, list[tuple[str, str]]] = {
    "ssb-k2-k3": [
        # K2 — 液态电芯/碳酸锂成本曲线
        ("202601160010", "SMM 方形磷酸铁锂电池 314Ah 指数"),
        ("202212050001", "SMM 电池级碳酸锂指数"),
        ("202105120003", "方形磷酸铁锂电芯"),
        ("202405230003", "6 系方形三元电芯"),
        # K3 — 固态路线分化（硫化物 vs 氧化物）
        ("202512080002", "SMM 硫化物电解质 LPSC"),
        ("202511190015", "氧化物电解质 LATP"),
        ("202601200007", "氧化物电解质 LLZO"),
        ("202508060001", "电池级硫化锂（硫化物路线原料）"),
        ("202601050004", "电池级金属锂（锂金属负极）"),
    ],
}


def _slug_safe(name: str) -> str:
    """文件名安全：去掉 Windows/Unix 都不支持的字符"""
    return re.sub(r"[<>:\"/\\|?*\s]+", "_", name).strip("_")


def fetch_page(cat_id: str) -> tuple[str, dict]:
    """Fetch raw HTML + parse out structured fields. Returns (html, parsed_dict)."""
    url = _BASE_URL.format(cat_id=cat_id)
    r = requests.get(url, headers=_HEADERS, timeout=30)
    r.raise_for_status()
    html = r.text

    # Title
    title_m = re.search(r"<title>([^<]+)</title>", html)
    title = title_m.group(1).strip() if title_m else f"SMM 类目 {cat_id}"
    # 清理 SEO 标题：去 _上海有色网 + 取第一段（去掉 _价格走势图 _价格查询 重复后缀）
    title = re.sub(r"_上海有色网\s*$", "", title)
    title = title.split("_")[0]

    # Update date
    date_m = re.search(r"更新日期[：:\s]*(\d{4}-\d{2}-\d{2})", html)
    update_date = date_m.group(1) if date_m else ""

    # Unit (单位)
    unit_m = re.search(r"单位[：:\s]*(元/[A-Za-z吨]+)", html)
    unit = unit_m.group(1) if unit_m else ""

    # Spec (规格)
    spec_m = re.search(r"规格[：:\s]*([^<\n]{2,80})", html)
    spec = spec_m.group(1).strip() if spec_m else ""

    # 评述段（最重要）— 找所有「评述」「市场分析」「日评」等带数字段落
    commentary = _extract_commentary(html)

    return html, {
        "cat_id": cat_id,
        "title": title,
        "update_date": update_date,
        "unit": unit,
        "spec": spec,
        "commentary": commentary,
        "url": url,
    }


_COMMENTARY_TRIGGERS = (
    r"现货价格较|期货方面|今日SMM|今日[一-鿿]{2,10}现货|"
    r"主力合约|近月合约|远月合约|"
    r"高开|低开|收盘报|收跌|收涨"
)
_COMMENTARY_END_MARKERS = ("登录 查看更多信息", "登录查看", "查看更多信息", "登录 查看", " 展开 ")


def _extract_commentary(html: str) -> list[dict]:
    """从市场分析段抽数据。

    SMM 评述段是 server-rendered，前几句话公开可读，后续需登录。
    用「现货价格较」「期货方面」「今日SMM」等关键短语定位段落开头，
    截到「登录 查看更多」边界。比 grep 「评述」准（后者会命中导航菜单噪音）。
    """
    commentaries: list[dict] = []
    seen_starts: set[int] = set()

    for kw_match in re.finditer(_COMMENTARY_TRIGGERS, html):
        i = kw_match.start()
        # 防止重复抓取同一段
        if any(abs(i - s) < 200 for s in seen_starts):
            continue
        seen_starts.add(i)

        # 回退到段落起点（最近的 >）
        start_back = html.rfind(">", max(0, i - 200), i)
        start = start_back + 1 if start_back > 0 else i

        chunk = html[start:start + 4000]
        text = re.sub(r"<script[^>]*>.*?</script>", "", chunk, flags=re.DOTALL)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        # 截到边界
        end_idx = len(text)
        for marker in _COMMENTARY_END_MARKERS:
            mi = text.find(marker)
            if 30 < mi < end_idx:
                end_idx = mi
        text = text[:end_idx].strip()
        text = text[:1200]
        # 必须含数字才算有价值（光说"上涨/下跌"无数字的丢弃）
        if any(c.isdigit() for c in text) and len(text) > 30:
            commentaries.append({
                "raw": text,
            })
        if len(commentaries) >= 5:
            break
    return commentaries


def render_markdown(parsed: dict) -> str:
    """渲染抓取结果为 markdown，可直接 ingest 到 prism manifest。"""
    today = date.today().isoformat()
    parts = [
        "---",
        f"title: \"{parsed['title']}\"",
        f"source: {parsed['url']}",
        f"smm_category_id: {parsed['cat_id']}",
        f"update_date: {parsed['update_date']}",
        f"scraped: {today}",
        f"unit: {parsed['unit']}",
        f"spec: {parsed['spec']}",
        "source_type: smm-commentary",
        "---",
        "",
        f"# {parsed['title']}",
        "",
        f"**类目 ID**: `{parsed['cat_id']}` · **更新日期**: {parsed['update_date']} · **抓取日期**: {today}",
        f"**单位**: {parsed['unit']} · **规格**: {parsed['spec']}",
        "",
        f"> 数据源：{parsed['url']}（公开评述段，今日精确报价数字需登录）",
        "",
        "## 评述（市场分析）",
        "",
    ]
    if parsed["commentary"]:
        for i, c in enumerate(parsed["commentary"], 1):
            parts.append(f"### 评述 {i}")
            parts.append("")
            parts.append(c["raw"])
            parts.append("")
    else:
        parts.append("(本次抓取未抓到评述段——可能页面结构变化或当日无更新)")
        parts.append("")
    return "\n".join(parts)


def scrape_to_file(
    cat_id: str,
    out_dir: Path,
    title_hint: str = "",
) -> tuple[Path, dict]:
    """抓取一个类目并写入 markdown 文件。返回 (file_path, parsed_dict)。"""
    log.info("Fetching SMM category %s (%s)...", cat_id, title_hint or "?")
    _, parsed = fetch_page(cat_id)
    if title_hint and not parsed["title"]:
        parsed["title"] = title_hint

    # 文件名: SMM_{date}_{catid}_{title}.md
    today = date.today().isoformat()
    safe_title = _slug_safe(parsed["title"])[:60]
    fname = f"SMM_{today}_{cat_id}_{safe_title}.md"
    out_path = out_dir / fname

    md = render_markdown(parsed)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")
    log.info("Saved → %s (%d bytes, %d commentaries)", out_path, len(md), len(parsed["commentary"]))
    return out_path, parsed


def scrape_and_register(
    cat_id: str,
    slug: str,
    variant: str,
    title_hint: str = "",
    addresses: list[str] | None = None,
) -> str | None:
    """抓取 + 写入 topic materials/ + 登记到 manifest。返回 mat_id。"""
    from prism.scripts.manifest import add_material, create_manifest, read_manifest

    materials_dir = Path(__file__).parent.parent / "prism" / "topics" / slug / "materials"
    materials_dir.mkdir(parents=True, exist_ok=True)

    out_path, parsed = scrape_to_file(cat_id, materials_dir, title_hint)

    try:
        read_manifest(slug, variant)
    except FileNotFoundError:
        create_manifest(slug, variant)

    mat_id = add_material(
        slug=slug,
        filename=out_path.name,
        source_type="data",  # 报价数据归为 data 类型
        variant=variant,
        notes=f"SMM 公开评述抓取 — {parsed['title']} (cat {cat_id})",
        addresses=addresses,
    )
    log.info("Registered manifest: %s → %s", out_path.name, mat_id)
    return mat_id


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Scrape SMM commentary for prism research")
    parser.add_argument("cat_id", nargs="?", help="SMM category id (e.g. 202601160010)")
    parser.add_argument("--preset", choices=list(_PRESETS), help="Use a preset category bundle")
    parser.add_argument("--slug", help="prism topic slug — register in manifest")
    parser.add_argument("--variant", help="prism variant")
    parser.add_argument("--out", type=Path, help="Output dir (when no --slug)")
    parser.add_argument("--addresses", help="Comma-separated K#/Q# addresses for manifest")
    args = parser.parse_args()

    if not args.cat_id and not args.preset:
        parser.error("Need cat_id OR --preset")
    if args.slug and not args.variant:
        parser.error("--variant required with --slug")

    targets: list[tuple[str, str, list[str]]] = []
    if args.preset:
        # preset 类目 → 推断 addresses（基于 ssb-k2-k3 的硬编码归类）
        K2_IDS = {"202601160010", "202212050001", "202105120003", "202405230003"}
        K3_IDS = {"202512080002", "202511190015", "202601200007", "202508060001", "202601050004"}
        for cid, name in _PRESETS[args.preset]:
            addrs = []
            if cid in K2_IDS: addrs.append("K2")
            if cid in K3_IDS: addrs.append("K3")
            targets.append((cid, name, addrs))
    else:
        addrs = [a.strip() for a in (args.addresses or "").split(",") if a.strip()]
        targets.append((args.cat_id, "", addrs))

    for cid, name, addrs in targets:
        try:
            if args.slug:
                scrape_and_register(cid, args.slug, args.variant, name, addrs)
            else:
                out_dir = args.out or Path(".")
                scrape_to_file(cid, out_dir, name)
            time.sleep(1)  # 礼貌限速
        except Exception as e:
            log.error("FAILED %s (%s): %s", cid, name, e)


if __name__ == "__main__":
    main()
