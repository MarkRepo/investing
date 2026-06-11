"""国债发行计划 QRA（季度再融资）文本下载（零 LLM）。

与 fomc_fetch 平行的「取文」fetcher：从 Treasury「Most Recent Quarterly Refunding
Documents」索引页提取本季两份关键公告链接 →
  · Policy Statement（季度再融资声明，含票息券 3/10/30Y 规模与 bills 指引 = 票/券构成）
  · Financing Estimates（可流通净借款估计 = 发行规模）
下载正文 → 剥标签 → 合并存 inbox/qra_latest.md，更新 local_cache_path，
供 headless LLM 以 Read 读本地文件判 expand/contract 立场（发行扩张/收缩）。

为何走取文而非数值通道：QRA 是季度政策公告，立场（扩/缩）与票/券构成藏在正文表格/叙述里，
需 LLM 读判；且 press-release ID 每季变（sb04xx→下季不同），故必须先抓**稳定索引页**解析
最新链接再读正文（与 FOMC 走 Fed 日历页同构）。

指纹 = 两份公告的 URL 路径（季度编号内嵌、发布即定型、每季更替）→ 去重门据此判内容是否变化。

用法：
  python -m prism.scripts.qra_fetch [slug] [variant]
"""
from __future__ import annotations

import re
import sys
from html import unescape
from pathlib import Path

import httpx

from prism.scripts import macro_registry as reg

_PRISM_ROOT = Path(__file__).resolve().parent.parent
_BASE = "https://home.treasury.gov"
_INDEX_URL = (_BASE + "/policy-issues/financing-the-government/quarterly-refunding/"
              "most-recent-quarterly-refunding-documents")
_INPUT_NAME = "国债发行计划 QRA + 票/券构成"

# 索引页锚文本前缀 → 抓哪份公告（Treasury 标准标签，稳定）。声明为主（含票/券构成），估计为辅。
_DOC_LABELS = [
    ("Policy Statement", "声明"),       # 季度再融资声明：票息券规模 + bills 指引
    ("Financing Estimates", "净借款估计"),  # 可流通净借款估计：发行规模
]

_SCRIPT_STYLE = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_PARA_TAG = re.compile(r"</?(?:p|h[1-6]|blockquote|section|article)\b[^>]*/?>", re.IGNORECASE)
_BLOCK_TAG = re.compile(r"</?(?:div|li|tr|header|footer)\b[^>]*/?>|<br\b[^>]*/?>", re.IGNORECASE)
_ANY_TAG = re.compile(r"<[^>]+>")
_INLINE_WS = re.compile(r"[ \t]+")
_MULTI_NL = re.compile(r"\n{3,}")

# 锚：<a href="/news/press-releases/sbXXXX">Policy Statement: 2026 - 2nd Quarter</a>
_ANCHOR = re.compile(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.IGNORECASE | re.DOTALL)
# 正文起始：Treasury 新闻稿统一以 "WASHINGTON" 地名行开篇；其前一行通常是日期
_BODY_START = "WASHINGTON"
# 正文结束：新闻稿正文以 "###" 收尾，其后为站点导航
_BODY_ENDS = ["###", "Use featured image", "\nLatest News"]
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
    """从已剥标签的纯文本里截出新闻稿正文：WASHINGTON 起、### 止。找不到起点则保留全文。"""
    start = text.find(_BODY_START)
    body = text[start:] if start != -1 else text
    for end_m in _BODY_ENDS:
        idx = body.find(end_m)
        if idx != -1:
            body = body[:idx]
            break
    return body.strip()


def _find_doc(index_html: str, label_prefix: str) -> tuple[str | None, str | None]:
    """在索引页找锚文本以 label_prefix 开头的最新公告链接。返回 (path, 季度标签)。"""
    for m in _ANCHOR.finditer(index_html):
        href = m.group(1)
        txt = _INLINE_WS.sub(" ", _ANY_TAG.sub(" ", m.group(2))).strip()
        if txt.startswith(label_prefix) and "/news/press-releases/" in href:
            # 季度标签：取冒号后部分（如 "2026 - 2nd Quarter"）
            quarter = txt.split(":", 1)[1].strip() if ":" in txt else ""
            return href, quarter
    return None, None


def _fetch_body(url: str, client: httpx.Client) -> tuple[str, str | None]:
    """下载新闻稿，返回 (正文, 日期串|None)。"""
    resp = client.get(url, timeout=30, follow_redirects=True,
                      headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    plain = _strip_html(resp.text)
    date_m = _DATE_BEFORE.search(plain)
    return _extract_body(plain), (date_m.group(1) if date_m else None)


def fetch_qra_texts(slug: str, variant: str, *, client: httpx.Client | None = None,
                    input_name: str | None = None) -> dict:
    """下载最新 QRA 声明 + 净借款估计，合并存 inbox/qra_latest.md，更新 local_cache_path。

    返回 {"docs": [{label,path,quarter,date,ok}], "cache_path", "ok", "fingerprint"}。
    ok = 主文档（Policy Statement）下到即真；估计为辅，缺失不阻断。
    fingerprint = "声明path|估计path"（季度编号内嵌，发布即定型）。
    """
    target_name = input_name or _INPUT_NAME
    owns = client is None
    if owns:
        client = httpx.Client()
    try:
        # 1. 拉稳定索引页
        idx = client.get(_INDEX_URL, timeout=30, follow_redirects=True,
                         headers={"User-Agent": "Mozilla/5.0"})
        idx.raise_for_status()
        index_html = idx.text

        # 2. 解析两份公告链接（声明为主）
        docs = []
        paths_for_fp: list[str] = []
        for label_prefix, zh in _DOC_LABELS:
            path, quarter = _find_doc(index_html, label_prefix)
            docs.append({"label": label_prefix, "zh": zh, "path": path,
                         "quarter": quarter, "date": None, "ok": False, "body": None})
            paths_for_fp.append(path or "")
        if not docs[0]["path"]:
            return {"error": "索引页未找到 Policy Statement（季度再融资声明）链接"}

        # 3. 下载正文
        for d in docs:
            if not d["path"]:
                continue
            try:
                body, date_s = _fetch_body(_BASE + d["path"], client)
                d["body"] = body
                d["date"] = date_s
                d["ok"] = bool(body)
            except httpx.HTTPError:
                pass  # 单份失败（如估计尚未发布）不阻断；声明缺失已在上方拦截

        # 4. 合并写 inbox/qra_latest.md
        inbox_dir = _PRISM_ROOT / "topics" / slug / "inbox"
        inbox_dir.mkdir(parents=True, exist_ok=True)
        out_path = inbox_dir / "qra_latest.md"

        sections: list[str] = []
        title_zh = {"Policy Statement": "QRA 季度再融资声明（票/券构成）",
                    "Financing Estimates": "可流通净借款估计（发行规模）"}
        first = True
        for d in docs:
            if not d.get("body"):
                continue
            head = title_zh.get(d["label"], d["label"])
            meta = " · ".join(x for x in [d["quarter"], d["date"]] if x)
            if not first:
                sections += ["", "---", ""]
            first = False
            sections += [f"# {head}（{meta}）" if meta else f"# {head}",
                         f"来源：{_BASE + d['path']}", "", d["body"]]
        out_path.write_text("\n".join(sections), encoding="utf-8")

        # 5. 更新 local_cache_path（相对 _PRISM_ROOT）
        rel = str(out_path.relative_to(_PRISM_ROOT))
        reg.set_local_cache_path(slug, variant, target_name, rel)

        return {
            "docs": [{k: d[k] for k in ("label", "zh", "path", "quarter", "date", "ok")} for d in docs],
            "cache_path": str(out_path),
            "ok": docs[0]["ok"],   # 声明下到即算成功（净借款估计可后发/缺失）
            "fingerprint": "|".join(paths_for_fp),
        }
    finally:
        if owns:
            client.close()


def fetch_one(slug: str, variant: str, entry: dict, *, client: httpx.Client | None = None) -> dict:
    """取文调度器入口（text_fetch=='qra' 路由到此）。用 entry['name'] 作目标输入名。"""
    return fetch_qra_texts(slug, variant, client=client, input_name=entry.get("name"))


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    slug = argv[0] if len(argv) > 0 else "global-macro-rates-liquidity"
    variant = argv[1] if len(argv) > 1 else "opus4.8"
    result = fetch_qra_texts(slug, variant)
    if "error" in result:
        print(f"错误: {result['error']}")
        sys.exit(1)
    for d in result["docs"]:
        mark = "✓" if d["ok"] else "✗"
        print(f"{mark} {d['zh']}: {d['quarter'] or '?'} {d['date'] or ''}  {d['path'] or '(未找到)'}")
    print(f"缓存: {result['cache_path']}")
    print(f"指纹: {result['fingerprint']}")
    print("local_cache_path 已更新 → LLM 下次拉取将读本地文件判发行扩张/收缩立场")


if __name__ == "__main__":
    main()
