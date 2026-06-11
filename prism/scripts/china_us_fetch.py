"""中美地缘/关税 文本下载（零 LLM）——双源：project44 关税税率 + USTR 官方新闻稿。

与 fomc_fetch / qra_fetch 平行的「取文」fetcher。该输入无单一数值（指标过宽、官方源无明确「中美关税」值），
故走取文通道：脚本零-LLM 把权威原文下到 inbox/ 本地缓存、写 local_cache_path，之后
macro_registry.llm_acquisition_mode 自动返回 local_file，headless LLM 用 Read 读本地文件判
升级/缓和立场，不再每轮 live 检索 → 降本。立场判读仍归 LLM，本脚本只取文。

双源（一个 fetcher 抓两源、合并入一份缓存）：
  · project44 tariff tracker = 双边**关税税率底座**（静态 HTML 表，data-title 单元格）。
    China 行**双向都有**（USA→China 与 China→USA），含起始日/税率/商品/状态/备注——
    独家补上 USTR 给不了的中方反制税率。聚合源，需 Chrome UA 过 Cloudflare。
  · USTR 新闻稿 = 美方**官方行动/叙事层**（Section 301、贸易谈判/协议）。索引页 reverse-chrono，
    正文 WASHINGTON→### 结构同 Treasury QRA。仅取标题含中国关键词者前 N 条。
  · 中方反制叙事 + 广义地缘（台海/科技管制/制裁）→ 缓存里**显式标注留给 LLM 补判**
    （no silent caps：脚本不假装覆盖全貌）。

容错：两源各自 try/except，一源挂（project44 改版/Cloudflare 变、USTR 改版）不连累另一源；
两源皆空才算失败（调度器记 fetch_error，自然回落 llm 现场检索）。

指纹 = project44 行(进>出@日=率) + USTR 命中路径（发布即定型）→ 任一源内容变 → 去重门触发 LLM 重判。

用法：
  python -m prism.scripts.china_us_fetch [slug] [variant]
"""
from __future__ import annotations

import re
import sys
from html import unescape
from pathlib import Path

import httpx

from prism.scripts import macro_registry as reg

_PRISM_ROOT = Path(__file__).resolve().parent.parent
_INPUT_NAME = "中美地缘/关税"
_MAX_USTR = 5

# project44：聚合关税税率表。Cloudflare 拦普通 UA，须整串 Chrome UA（同 macromicro recipe）。
_P44_URL = "https://www.project44.com/tariff-tracker/"
_CHROME_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

# USTR：美方官方新闻稿索引页（reverse-chrono），仅取标题含中国关键词者。
_USTR_BASE = "https://ustr.gov"
_USTR_INDEX = _USTR_BASE + "/about-us/policy-offices/press-office/press-releases"
_CHINA_KEYWORDS = ("china", "chinese", "beijing", "prc", "中国", "中美")

# ── project44 解析 ─────────────────────────────────────────────────────────
# 表格行：<tr>...<td data-title="IMPORTING COUNTRY">USA</td>...<td data-title="STATUS"><img .../></td>...
_TR = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.IGNORECASE | re.DOTALL)
_TD = re.compile(r'<td\b[^>]*data-title="([^"]+)"[^>]*>(.*?)</td>', re.IGNORECASE | re.DOTALL)
_STATUS_ACTIVE = re.compile(r"Green_Yes", re.IGNORECASE)   # 状态由 icon 文件名判：Green_Yes→active
_ANY_TAG = re.compile(r"<[^>]+>")
_INLINE_WS = re.compile(r"[ \t]+")

# data-title → 行字段键
_P44_FIELDS = {
    "IMPORTING COUNTRY": "importing",
    "EXPORTING COUNTRY": "exporting",
    "START DATE": "start_date",
    "TYPE OF TARIFF": "ttype",
    "AMOUNT": "amount",
    "ADDITIONAL NOTES": "notes",
}


def _cell_text(raw: str) -> str:
    return _INLINE_WS.sub(" ", unescape(_ANY_TAG.sub(" ", raw))).strip()


def _parse_p44_rows(html: str) -> list[dict]:
    """扫表格 <tr>，按 data-title 取单元格；保留 China ∈ {进口国,出口国} 的双向行。
    STATUS 由 icon 文件名（Green_Yes→active，否则 inactive）判。"""
    rows: list[dict] = []
    for tr in _TR.finditer(html):
        inner = tr.group(1)
        cells = {m.group(1).strip().upper(): m.group(2) for m in _TD.finditer(inner)}
        if not cells:
            continue
        row: dict = {}
        for title, key in _P44_FIELDS.items():
            row[key] = _cell_text(cells.get(title, ""))
        if "STATUS" in cells:
            row["status"] = "active" if _STATUS_ACTIVE.search(cells["STATUS"]) else "inactive"
        else:
            row["status"] = ""
        imp, exp = row.get("importing", ""), row.get("exporting", "")
        if "china" in imp.lower() or "china" in exp.lower():
            rows.append(row)
    return rows


def _md_cell(s: str) -> str:
    return (s or "").replace("|", "\\|").replace("\n", " ").strip()


def _render_p44_md(rows: list[dict]) -> str:
    """渲染中文 markdown 表（进口国/出口国/起始日/税率/商品/状态/备注）。"""
    head = ("| 进口国 | 出口国 | 起始日 | 税率 | 商品/类型 | 状态 | 备注 |\n"
            "|---|---|---|---|---|---|---|")
    lines = [head]
    for r in rows:
        lines.append("| " + " | ".join(_md_cell(r.get(k, "")) for k in
                     ("importing", "exporting", "start_date", "amount", "ttype", "status", "notes")) + " |")
    return "\n".join(lines)


def _p44_sig(rows: list[dict]) -> str:
    """每行 (进>出@日=率) 拼接做指纹片段（税率/起始日变即变）。"""
    return ";".join(f"{r.get('importing','')}>{r.get('exporting','')}"
                    f"@{r.get('start_date','')}={r.get('amount','')}" for r in rows)


# ── USTR 解析（结构同 qra_fetch） ───────────────────────────────────────────
_SCRIPT_STYLE = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_PARA_TAG = re.compile(r"</?(?:p|h[1-6]|blockquote|section|article)\b[^>]*/?>", re.IGNORECASE)
_BLOCK_TAG = re.compile(r"</?(?:div|li|tr|header|footer)\b[^>]*/?>|<br\b[^>]*/?>", re.IGNORECASE)
_MULTI_NL = re.compile(r"\n{3,}")
_ANCHOR = re.compile(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.IGNORECASE | re.DOTALL)
# 真新闻稿 href：/.../press-releases/<年>/<月>/<slug>（年-only/分页链接无月段，借此排除）
_RELEASE_HREF = re.compile(r"/press-releases/20\d\d/[a-z]+/[a-z0-9-]+", re.IGNORECASE)
_BODY_START = "WASHINGTON"
_BODY_ENDS = ["###", "Stay in the Know", "\nLatest News"]
_DATE_BEFORE = re.compile(r"([A-Z][a-z]+ \d{1,2}, \d{4})\s*\n+WASHINGTON")


def _strip_html(raw: str) -> str:
    raw = _SCRIPT_STYLE.sub(" ", raw)
    raw = _PARA_TAG.sub("\n\n", raw)
    raw = _BLOCK_TAG.sub("\n", raw)
    raw = _ANY_TAG.sub(" ", raw)
    raw = unescape(raw)
    lines = [_INLINE_WS.sub(" ", ln).strip() for ln in raw.splitlines()]
    text = "\n".join(ln for ln in lines if ln).strip()
    return _MULTI_NL.sub("\n\n", text)


def _extract_body(text: str) -> str:
    """从已剥标签纯文本截新闻稿正文：WASHINGTON 起、###/Stay in the Know 止。无起点则保留全文。"""
    start = text.find(_BODY_START)
    body = text[start:] if start != -1 else text
    for end_m in _BODY_ENDS:
        idx = body.find(end_m)
        if idx != -1:
            body = body[:idx]
            break
    return body.strip()


def _find_china_releases(index_html: str) -> list[tuple[str, str]]:
    """扫索引页锚，标题含任一中国关键词的真新闻稿，保序去重（页面 newest-first），取前 _MAX_USTR。"""
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for m in _ANCHOR.finditer(index_html):
        href = m.group(1)
        if not _RELEASE_HREF.search(href):
            continue
        title = _INLINE_WS.sub(" ", _ANY_TAG.sub(" ", m.group(2))).strip()
        low = title.lower()
        if not any(kw in low for kw in _CHINA_KEYWORDS):
            continue
        if href in seen:
            continue
        seen.add(href)
        out.append((href, title))
        if len(out) >= _MAX_USTR:
            break
    return out


def _fetch_body(url: str, client: httpx.Client) -> tuple[str, str | None]:
    """下载新闻稿，返回 (正文, 日期串|None)。"""
    resp = client.get(url, timeout=30, follow_redirects=True,
                      headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    plain = _strip_html(resp.text)
    date_m = _DATE_BEFORE.search(plain)
    return _extract_body(plain), (date_m.group(1) if date_m else None)


# ── 合并入口 ────────────────────────────────────────────────────────────────
def fetch_china_us(slug: str, variant: str, *, client: httpx.Client | None = None,
                   input_name: str | None = None) -> dict:
    """抓 project44（关税税率）+ USTR（官方新闻稿），合并存 inbox/china_us_tariff_latest.md。

    返回 {"p44_rows", "ustr_releases", "cache_path", "ok", "fingerprint"}。
    ok = 至少一源成功（p44 有行 或 USTR 有正文）。两源皆空 → {"error": ...}（调度器记 fetch_error）。
    fingerprint = "p44:"+行签名 + "|ustr:"+命中路径——任一源变 → 去重门触发 LLM 重判。
    """
    target_name = input_name or _INPUT_NAME
    owns = client is None
    if owns:
        client = httpx.Client()
    try:
        rows: list[dict] = []
        p44_err: str | None = None
        try:
            r = client.get(_P44_URL, timeout=30, follow_redirects=True,
                           headers={"User-Agent": _CHROME_UA})
            r.raise_for_status()
            rows = _parse_p44_rows(r.text)
        except (httpx.HTTPError, ValueError) as exc:   # 改版/Cloudflare 变 → 仅丢本源
            p44_err = str(exc)

        releases: list[dict] = []
        ustr_err: str | None = None
        try:
            idx = client.get(_USTR_INDEX, timeout=30, follow_redirects=True,
                             headers={"User-Agent": "Mozilla/5.0"})
            idx.raise_for_status()
            for href, title in _find_china_releases(idx.text):
                url = href if href.startswith("http") else _USTR_BASE + href
                try:
                    body, date_s = _fetch_body(url, client)
                except httpx.HTTPError:
                    body, date_s = "", None
                releases.append({"path": href, "title": title, "date": date_s,
                                 "body": body, "ok": bool(body)})
        except httpx.HTTPError as exc:
            ustr_err = str(exc)

        ustr_ok = [r for r in releases if r["ok"]]
        if not rows and not ustr_ok:
            return {"error": f"两源皆空（project44: {p44_err or '无中国行'}; USTR: {ustr_err or '无命中'}）"}

        # 合并写 inbox/china_us_tariff_latest.md
        inbox_dir = _PRISM_ROOT / "topics" / slug / "inbox"
        inbox_dir.mkdir(parents=True, exist_ok=True)
        out_path = inbox_dir / "china_us_tariff_latest.md"

        sections: list[str] = []
        sections += ["# 中美关税税率（project44 tariff tracker · 双边 · 聚合源）",
                     f"来源：{_P44_URL}", ""]
        sections.append(_render_p44_md(rows) if rows else
                        f"（project44 本次未取到中国行：{p44_err or '表中无 China 行'}）")
        sections += ["", "---", "",
                     f"# USTR 中国相关新闻稿（最近 {len(ustr_ok)} 条 · 美方官方行动）"]
        if ustr_ok:
            for r in ustr_ok:
                meta = r["date"] or ""
                sections += ["", f"## {r['title']}（{meta}）" if meta else f"## {r['title']}",
                             f"来源：{_USTR_BASE + r['path'] if not r['path'].startswith('http') else r['path']}",
                             "", r["body"]]
        else:
            sections += ["", f"（USTR 本次无中国相关新闻稿命中：{ustr_err or '索引页无匹配'}）"]
        sections += ["", "---", "",
                     "> 注：本缓存仅覆盖 ①双边关税税率(project44 聚合源) ②美方官方贸易行动(USTR)。",
                     "> 中方反制叙事、广义地缘(台海/科技管制/制裁/实体清单)需 LLM 在此之上补判。"]
        out_path.write_text("\n".join(sections), encoding="utf-8")

        rel = str(out_path.relative_to(_PRISM_ROOT))
        reg.set_local_cache_path(slug, variant, target_name, rel)

        fingerprint = "p44:" + _p44_sig(rows) + "|ustr:" + "|".join(r["path"] for r in ustr_ok)
        return {
            "p44_rows": rows,
            "ustr_releases": [{k: r[k] for k in ("path", "title", "date", "ok")} for r in releases],
            "cache_path": str(out_path),
            "ok": bool(rows) or bool(ustr_ok),
            "fingerprint": fingerprint,
        }
    finally:
        if owns:
            client.close()


def fetch_one(slug: str, variant: str, entry: dict, *, client: httpx.Client | None = None) -> dict:
    """取文调度器入口（text_fetch=='china_us' 路由到此）。用 entry['name'] 作目标输入名。"""
    return fetch_china_us(slug, variant, client=client, input_name=entry.get("name"))


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    slug = argv[0] if len(argv) > 0 else "global-macro-rates-liquidity"
    variant = argv[1] if len(argv) > 1 else "opus4.8"
    result = fetch_china_us(slug, variant)
    if "error" in result:
        print(f"错误: {result['error']}")
        sys.exit(1)
    print(f"project44: {len(result['p44_rows'])} 条中国双边关税行")
    hit = [r for r in result["ustr_releases"] if r["ok"]]
    print(f"USTR: {len(hit)} 条中国相关新闻稿")
    for r in hit:
        print(f"  · {r['date'] or '?'}  {r['title'][:60]}")
    print(f"缓存: {result['cache_path']}")
    print(f"指纹: {result['fingerprint']}")
    print("local_cache_path 已更新 → LLM 下次拉取将读本地文件判中美关税/地缘升级或缓和")


if __name__ == "__main__":
    main()
