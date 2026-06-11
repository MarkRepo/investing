"""ADR 退市 / HFCAA / PCAOB 文本下载（零 LLM）。

与 fomc_fetch / qra_fetch / china_us_fetch 平行的「取文」fetcher。该输入是**事件型、制度性**指标——
没有干净的单值数据端点（当前状态甚至「制度性为零」：PCAOB 2022-12-15 撤销对华/港的检查无法
确定，故无发行人面临交易禁令）。立场判读（监管升级/缓和、是否有发行人面临退市）仍需 LLM，故走
取文通道：脚本零-LLM 把两份**官方**原文下到 inbox/ 本地缓存、写 local_cache_path，之后
macro_registry.llm_acquisition_mode 自动返回 local_file，headless LLM 用 Read 读本地文件判
立场，不再每轮 live 检索 → 降本。

双源（一个 fetcher 抓两源、合并入一份缓存）：
  · SEC HFCAA 页（官方·主源）= 真正的「谁被点名」面板：
      ① Provisional list（临时清单）——前沿信号，新点名先落这里（当前为空）。
      ② Conclusive list（最终清单）——历史 2022 名册（BeiGene/Baidu/iQIYI…），但每行
         "Current trading prohibition" 当前皆 "Not applicable"（因 PCAOB 已撤销认定）。
      ③ PCAOB Determination Update / Trading Prohibition Update 叙述段。
    → 脚本零-LLM 派生**状态摘要 + 报警信号**：临时清单是否非空、最终清单家数、以及关键的
      「current trading prohibition 是否有任何一行真正生效」（这才是退市警报）。
  · PCAOB Board Determinations 页（官方）= 认定本身的状态叙述（是否对华/港存在 active 认定，
    还是已 vacated）。叙述为主、随新认定改写，供 LLM 读判。

为何不抽 observed.value：当前材料是「制度性为零」——名册在、但无一行生效禁令。强行抽数会把
「0 家生效」与「取数失败」混淆。故只取文 + 派生状态摘要，立场/数值由 LLM 在本地缓存上判。

容错：两源各自 try/except，PCAOB 挂（改版）不连累 SEC；SEC（主源）取不到才算失败
（调度器记 fetch_error，自然回落 llm 现场检索）。

指纹 = 临时清单状态 + 最终清单家数 + 生效禁令发行人名单 + SEC 认定更新段内日期。
任一变（新点名 / 禁令生效 / PCAOB 出新认定）→ 去重门触发 LLM 重判；纯样板文案变不触发。

用法：
  python -m prism.scripts.hfcaa_fetch [slug] [variant]
"""
from __future__ import annotations

import re
import sys
from html import unescape
from pathlib import Path

import httpx

from prism.scripts import macro_registry as reg

_PRISM_ROOT = Path(__file__).resolve().parent.parent
_INPUT_NAME = "ADR 退市/HFCAA/PCAOB"

# SEC HFCAA 权威页（官方主源，含临时/最终清单）。注意：短链 /HFCAA 对脚本 UA 返回 403，
# 须用规范长链；SEC 要求声明式 UA（非浏览器伪装），见 _SEC_UA。
_SEC_URL = ("https://www.sec.gov/rules-regulations/"
            "holding-foreign-companies-accountable-act")
# SEC 拒绝空/浏览器伪装 UA，要求声明身份+联系方式（其 webmaster 政策）。
# 实测：须是简单的「名称 邮箱」形式——带括号/"contact:" 的变体会被判 403。
_SEC_UA = "prism-macro-research admin@prism.local"

# PCAOB 认定页（官方，认定状态叙述）。Cloudflare 类站点，用 Chrome UA 稳妥（同 macromicro）。
_PCAOB_URL = ("https://pcaobus.org/oversight/international/"
              "board-determinations-holding-foreign-companies-accountable-act-hfcaa")
_CHROME_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

# ── HTML 剥离（与 qra_fetch/china_us_fetch 同构） ────────────────────────────
_SCRIPT_STYLE = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
# 表格/清单结构靠换行保留：每个 td/th/p/标题/行都断行，便于按行解析清单
_PARA_TAG = re.compile(r"</?(?:p|h[1-6]|blockquote|section|article|tr|li|td|th)\b[^>]*/?>",
                       re.IGNORECASE)
_BLOCK_TAG = re.compile(r"</?(?:div|header|footer)\b[^>]*/?>|<br\b[^>]*/?>", re.IGNORECASE)
_ANY_TAG = re.compile(r"<[^>]+>")
_INLINE_WS = re.compile(r"[ \t]+")
_MULTI_NL = re.compile(r"\n{3,}")

# 清单行：名称\nCIK(纯数字)\n日期(Month DD, YYYY)\n当前禁令\n此前禁令
_LIST_ROW = re.compile(
    r"\n([^\n]{2,90})\n(\d{3,10})\n([A-Z][a-z]+ \d{1,2}, \d{4})\n([^\n]+)\n([^\n]+)")
# "生效中"判定：current trading prohibition 非 "Not applicable"/"None"/"N/A"/空 即视为生效
_NOT_ACTIVE = re.compile(r"^(?:not applicable|none|n/?a|-+|\s*)$", re.IGNORECASE)
_DATE = re.compile(r"[A-Z][a-z]+ \d{1,2}, \d{4}")


def _strip_html(raw: str) -> str:
    raw = _SCRIPT_STYLE.sub(" ", raw)
    raw = _PARA_TAG.sub("\n", raw)
    raw = _BLOCK_TAG.sub("\n", raw)
    raw = _ANY_TAG.sub(" ", raw)
    raw = unescape(raw)
    lines = [_INLINE_WS.sub(" ", ln).strip() for ln in raw.splitlines()]
    text = "\n".join(ln for ln in lines if ln).strip()
    return _MULTI_NL.sub("\n\n", text)


def _slice(text: str, start: str, ends: list[str]) -> str:
    """从 start 标记起、到首个出现的 end 标记止，截出一段。找不到 start 则返回空串。"""
    i = text.find(start)
    if i == -1:
        return ""
    body = text[i:]
    cut = len(body)
    for e in ends:
        j = body.find(e, len(start))
        if j != -1:
            cut = min(cut, j)
    return body[:cut].strip()


def _parse_list_rows(region: str) -> list[dict]:
    """从清单区域文本解析发行人行。每行 = {name, cik, date, current, prior, active}。
    active = 当前交易禁令真正生效（非 Not applicable）——这才是退市警报信号。"""
    rows: list[dict] = []
    for m in _LIST_ROW.finditer("\n" + region):
        name, cik, date, current, prior = (g.strip() for g in m.groups())
        rows.append({
            "name": name, "cik": cik, "date": date,
            "current": current, "prior": prior,
            "active": not bool(_NOT_ACTIVE.match(current)),
        })
    return rows


def sec_signals(plain: str) -> dict:
    """从 SEC HFCAA 纯文本派生状态信号（零 LLM）。

    返回 {provisional_empty, provisional_rows, conclusive_rows, active_rows, update_dates}：
      provisional_empty   临时清单是否为空（官方原句「no issuer on the provisional list」）
      provisional_rows    临时清单解析出的发行人行（前沿点名信号）
      conclusive_rows     最终清单发行人行（历史名册）
      active_rows         current trading prohibition 真正生效的行（退市警报；当前应为空）
      update_dates        「PCAOB Determination Update」段内日期（出新认定即变）
    """
    prov_region = _slice(plain, "Provisional list of issuers",
                         ["Conclusive list of issuers"])
    concl_region = _slice(plain, "Conclusive list of issuers",
                          ["Related", "Sign up", "Last", "Modified", "Return to Top",
                           "Receive", "Stay Connected"])
    provisional_empty = "no issuer on the provisional list" in plain.lower()
    prov_rows = _parse_list_rows(prov_region)
    concl_rows = _parse_list_rows(concl_region)
    upd = _slice(plain, "PCAOB Determination Update", ["Provisional list of issuers"])
    return {
        "provisional_empty": provisional_empty,
        "provisional_rows": prov_rows,
        "conclusive_rows": concl_rows,
        "active_rows": [r for r in concl_rows + prov_rows if r["active"]],
        "update_dates": list(dict.fromkeys(_DATE.findall(upd))),  # 保序去重
    }


def _status_summary(sig: dict) -> list[str]:
    """渲染中文状态摘要（脚本派生，零 LLM），置于缓存文件顶部供人与 LLM 一眼看清。"""
    prov = "空（无发行人）" if sig["provisional_empty"] or not sig["provisional_rows"] \
        else f"{len(sig['provisional_rows'])} 家（注意：新点名先落临时清单）"
    active = sig["active_rows"]
    alarm = ("无任何发行人当前交易禁令生效（current trading prohibition 全为 Not applicable）"
             if not active else
             f"⚠ {len(active)} 家发行人当前交易禁令已生效：" +
             "、".join(r["name"] for r in active))
    upd = "、".join(sig["update_dates"]) or "（未解析到日期）"
    return [
        "## 状态摘要（脚本派生 · 零 LLM）",
        f"- 临时清单（Provisional）：{prov}",
        f"- 最终清单（Conclusive）：{len(sig['conclusive_rows'])} 家历史名册",
        f"- 退市警报：{alarm}",
        f"- SEC 认定更新段日期：{upd}",
        "",
        "> 判读要点：临时清单非空 / 任一行 current trading prohibition 生效 = 退市风险重启；"
        "否则维持「制度性为零」。详情见下方 SEC/PCAOB 原文。",
    ]


def _render_rows_md(rows: list[dict]) -> str:
    head = ("| 发行人 | CIK | 认定日期 | 当前交易禁令 | 此前交易禁令 |\n"
            "|---|---|---|---|---|")
    if not rows:
        return head + "\n| （无） | | | | |"
    body = "\n".join(
        "| " + " | ".join((r[k] or "").replace("|", "\\|")
                          for k in ("name", "cik", "date", "current", "prior")) + " |"
        for r in rows)
    return head + "\n" + body


def _fingerprint(sig: dict, pcaob_ok: bool) -> str:
    """稳定身份指纹：临时清单状态 + 最终家数 + 生效禁令名单 + 认定更新日期。
    新点名 / 禁令生效 / PCAOB 出新认定（更新段日期变）→ 指纹变 → 去重门触发 LLM 重判。"""
    prov = "empty" if (sig["provisional_empty"] or not sig["provisional_rows"]) \
        else f"N={len(sig['provisional_rows'])}"
    active = ",".join(sorted(r["name"] for r in sig["active_rows"]))
    return (f"prov:{prov}|concl:{len(sig['conclusive_rows'])}|active:{active}"
            f"|upd:{','.join(sig['update_dates'])}|pcaob:{'ok' if pcaob_ok else 'miss'}")


def fetch_hfcaa(slug: str, variant: str, *, client: httpx.Client | None = None,
                input_name: str | None = None) -> dict:
    """抓 SEC HFCAA（主源·清单）+ PCAOB 认定页，合并存 inbox/hfcaa_latest.md，更新 local_cache_path。

    返回 {"signals", "pcaob_ok", "cache_path", "ok", "fingerprint"}。
    ok = SEC 主源成功（取到页面并能解析）；PCAOB 为辅，缺失不阻断。
    SEC 取不到 → {"error": ...}（调度器记 fetch_error，回落 llm 现场检索）。
    """
    target_name = input_name or _INPUT_NAME
    owns = client is None
    if owns:
        client = httpx.Client()
    try:
        # 1. SEC HFCAA（主源）
        sec_err: str | None = None
        sec_body = ""
        sig: dict = {}
        try:
            r = client.get(_SEC_URL, timeout=40, follow_redirects=True,
                           headers={"User-Agent": _SEC_UA})
            r.raise_for_status()
            plain = _strip_html(r.text)
            sig = sec_signals(plain)
            # 叙述正文：认定更新 + 交易禁令更新（截到临时清单前，清单另行渲染表）
            sec_body = _slice(plain, "PCAOB Determination Update",
                              ["Provisional list of issuers"])
        except (httpx.HTTPError, ValueError) as exc:
            sec_err = str(exc)

        if sec_err or not sig:
            return {"error": f"SEC HFCAA 主源取不到：{sec_err or '页面无法解析清单'}"}

        # 2. PCAOB 认定页（辅源）
        pcaob_body = ""
        try:
            r2 = client.get(_PCAOB_URL, timeout=40, follow_redirects=True,
                            headers={"User-Agent": _CHROME_UA})
            r2.raise_for_status()
            p2 = _strip_html(r2.text)
            pcaob_body = _slice(p2, "In December 2020, Congress",
                                ["AuditorSearch", "Stay Connected", "Related",
                                 "Footer", "Sign up", "Return to Top"])[:5000]
        except httpx.HTTPError:
            pass  # 辅源失败不阻断
        pcaob_ok = bool(pcaob_body)

        # 3. 合并写 inbox/hfcaa_latest.md
        inbox_dir = _PRISM_ROOT / "topics" / slug / "inbox"
        inbox_dir.mkdir(parents=True, exist_ok=True)
        out_path = inbox_dir / "hfcaa_latest.md"

        sections: list[str] = ["# ADR 退市 / HFCAA / PCAOB（官方双源 · 零 LLM 取文）", ""]
        sections += _status_summary(sig)
        sections += ["", "---", "",
                     "# SEC HFCAA — 认定与交易禁令更新（官方）", f"来源：{_SEC_URL}", "",
                     sec_body or "（未截取到叙述段）"]
        sections += ["", "## 临时清单 Provisional list（前沿点名信号）",
                     _render_rows_md(sig["provisional_rows"])]
        sections += ["", "## 最终清单 Conclusive list（历史名册）",
                     _render_rows_md(sig["conclusive_rows"])]
        sections += ["", "---", "",
                     "# PCAOB — 对华/港认定状态（官方）", f"来源：{_PCAOB_URL}", ""]
        sections.append(pcaob_body if pcaob_ok else
                        "（PCAOB 认定页本次未取到，叙述层留待 LLM 补判）")
        sections += ["", "---", "",
                     "> 注：本缓存覆盖 ①SEC 临时/最终清单与交易禁令状态 ②PCAOB 对华/港认定叙述。",
                     "> 个股层退市通知（NYSE/Nasdaq）、中方 MOF/CSRC 反应、新立法动向需 LLM 在此之上补判。"]
        out_path.write_text("\n".join(sections), encoding="utf-8")

        rel = str(out_path.relative_to(_PRISM_ROOT))
        reg.set_local_cache_path(slug, variant, target_name, rel)

        return {
            "signals": {
                "provisional_empty": sig["provisional_empty"],
                "provisional_count": len(sig["provisional_rows"]),
                "conclusive_count": len(sig["conclusive_rows"]),
                "active_prohibitions": [r["name"] for r in sig["active_rows"]],
                "update_dates": sig["update_dates"],
            },
            "pcaob_ok": pcaob_ok,
            "cache_path": str(out_path),
            "ok": True,
            "fingerprint": _fingerprint(sig, pcaob_ok),
        }
    finally:
        if owns:
            client.close()


def fetch_one(slug: str, variant: str, entry: dict, *, client: httpx.Client | None = None) -> dict:
    """取文调度器入口（text_fetch=='hfcaa' 路由到此）。用 entry['name'] 作目标输入名。"""
    return fetch_hfcaa(slug, variant, client=client, input_name=entry.get("name"))


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    slug = argv[0] if len(argv) > 0 else "global-macro-rates-liquidity"
    variant = argv[1] if len(argv) > 1 else "opus4.8"
    result = fetch_hfcaa(slug, variant)
    if "error" in result:
        print(f"错误: {result['error']}")
        sys.exit(1)
    s = result["signals"]
    print(f"临时清单: {'空' if s['provisional_empty'] else s['provisional_count']}")
    print(f"最终清单: {s['conclusive_count']} 家")
    print(f"生效禁令: {s['active_prohibitions'] or '无（制度性为零）'}")
    print(f"PCAOB 认定页: {'✓' if result['pcaob_ok'] else '✗'}")
    print(f"缓存: {result['cache_path']}")
    print(f"指纹: {result['fingerprint']}")
    print("local_cache_path 已更新 → LLM 下次拉取将读本地文件判 ADR 退市/审计监管升级或缓和")


if __name__ == "__main__":
    main()
