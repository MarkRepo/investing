"""mofcom 取数通道（商务部数据中心·社会融资规模增量序列 → 派生指标）。零 LLM：读登记表里
fetch_method=='mofcom' 且 availability=='scripted' 且有 mofcom 配置块的输入，POST 拉社融**增量
(flow)月度序列**，按 mofcom.metric 算派生值 → record_observation。

与 fred_fetch / recipe_fetch / macromicro_fetch 等平行（脚本「数值」通道），但**多一步序列计算**：
其余通道取「最新单点」，本通道取**整条流量序列**做滚动/差分（信贷脉冲＝新增社融滚动12月/名义GDP
的同比差分，无现成单值源，故须自算）。recipe 的「按名派生」只读各腿最新 observed.value，装不下
滚动12月窗口，因此单列本通道。

两个非显然点（实测踩到）：
  - **TLS**：data.mofcom.gov.cn 在 OpenSSL 3 默认（SECLEVEL=2 + 禁 legacy 重协商）下握手直接失败
    （SSLV3_ALERT_HANDSHAKE_FAILURE）；系统 curl 能通。故造一个 SECLEVEL=1 + legacy-reneg 的
    SSLContext 给 httpx，进程内即可达，无需 curl 子进程（保持 client 可注入、可 mock）。
  - **GDP 分母**：社融流量来自本端点，但信贷脉冲分母「名义GDP」来自 akshare macro_china_gdp
    （季度累计YTD，端点正常、非 mofcom）。还原为「滚动4季名义GDP」（年内累计差分→单季→滚动4季和）。

口径（credit_impulse，按登记表 note 字面）：
    ratio(t) = Σ_window 社融增量(t) / 滚动4季名义GDP(t)
    CI(t)    = (ratio(t) − ratio(t−window)) × 100   # 同比差分，单位 pp(占GDP百分点)
GDP 取「季末月 ≤ t 的最近一季」的滚动4季年化（避免前视），月内保持不变。
"""
from __future__ import annotations

import math
import re
import ssl
import sys

from prism.scripts import macro_registry as reg

_QUERY_URL = "https://data.mofcom.gov.cn/datamofcom/front/gnmy/shrzgmQuery"
_REFERER = "https://data.mofcom.gov.cn/gnmy/shrzgm.shtml"
_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
_KNOWN_METRICS = ("credit_impulse",)
_QEND = {1: 3, 2: 6, 3: 9, 4: 12}   # 季 → 季末月


def _mofcom_ssl_ctx() -> ssl.SSLContext:
    """造能握手 data.mofcom.gov.cn 的 SSLContext：SECLEVEL=1 + 允许 legacy 重协商。
    该 gov 主机 cert/cipher 配置在 OpenSSL3 默认下被拒；放宽到 SECLEVEL=1 并开
    OP_LEGACY_SERVER_CONNECT 即可。证书不校验（verify_mode=CERT_NONE）——本通道仅低频自用取公开统计。"""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        ctx.set_ciphers("DEFAULT@SECLEVEL=1")
    except ssl.SSLError:
        pass
    for flag in ("OP_LEGACY_SERVER_CONNECT", "OP_ALLOW_UNSAFE_LEGACY_RENEGOTIATION"):
        if hasattr(ssl, flag):
            ctx.options |= getattr(ssl, flag)
    return ctx


def _to_float(v) -> float | None:
    """单元转 float；None/NaN/非数 → None。去千分位逗号。"""
    if v is None:
        return None
    if isinstance(v, str):
        v = v.replace(",", "").strip()
        if not v:
            return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else f


def _monthly_flows(rows, field: str = "tiosfs") -> list[tuple[str, float]]:
    """mofcom 行 [{date:'YYYYMM', tiosfs:.., ...}, ...] → [('YYYY-MM', flow), ...] 按月升序。
    date 不足 6 位或 field 非数的行跳过。重复月以后者覆盖。"""
    out: dict[str, float] = {}
    for r in rows:
        d = str(r.get("date", "")).strip()
        if len(d) < 6 or not d[:6].isdigit():
            continue
        val = _to_float(r.get(field))
        if val is None:
            continue
        out[f"{d[:4]}-{d[4:6]}"] = val
    return sorted(out.items())


def _parse_gdp_quarter(label: str) -> tuple[int, int] | None:
    """'2026年第1季度'→(2026,1)；'2025年第1-2季度'→(2025,2)（累计到第几季）；'第1-4'→(.,4)。
    认不出 → None。"""
    m = re.match(r"(\d{4})", str(label))
    if not m:
        return None
    y = int(m.group(1))
    s = str(label)
    for token, q in (("第1-4", 4), ("第1-3", 3), ("第1-2", 2)):
        if token in s:
            return y, q
    return y, 1


def _annual_gdp_map(gdp_rows) -> dict[tuple[int, int], float]:
    """gdp_rows: [(季度label, 国内生产总值-绝对值累计YTD), ...] → {(year,q): 滚动4季名义GDP}。
    年内累计差分还原单季（Q1=cum(Q1); Qk=cum(1-k)−cum(1-(k-1))），再取连续4单季和。
    某季缺单季所需累计 → 该季不入 map（诚实留空）。"""
    cum: dict[tuple[int, int], float] = {}
    for label, value in gdp_rows:
        yq = _parse_gdp_quarter(label)
        v = _to_float(value)
        if yq is not None and v is not None:
            cum[yq] = v

    def single_q(y: int, q: int) -> float | None:
        if q == 1:
            return cum.get((y, 1))
        a, b = cum.get((y, q)), cum.get((y, q - 1))
        return None if a is None or b is None else a - b

    out: dict[tuple[int, int], float] = {}
    for (y, q) in cum:
        acc = 0.0
        yy, qq = y, q
        ok = True
        for _ in range(4):                 # 累加 (y,q) 起往前 4 个单季
            s = single_q(yy, qq)
            if s is None:
                ok = False
                break
            acc += s
            qq -= 1
            if qq == 0:
                qq, yy = 4, yy - 1
        if ok:
            out[(y, q)] = acc
    return out


def _annual_gdp_at(gdp_map: dict[tuple[int, int], float], ym: str) -> float | None:
    """月 'YYYY-MM' 对应的滚动4季名义GDP：取「季末月 ≤ 该月」的最近一季（避免前视）。无 → None。"""
    y, m = int(ym[:4]), int(ym[5:7])
    best = None
    for (yy, qq) in gdp_map:
        if yy < y or (yy == y and _QEND[qq] <= m):
            if best is None or (yy, _QEND[qq]) > (best[0], _QEND[best[1]]):
                best = (yy, qq)
    return gdp_map.get(best) if best else None


def credit_impulse(flows: list[tuple[str, float]],
                   gdp_map: dict[tuple[int, int], float],
                   *, window: int = 12) -> tuple[float | None, str | None]:
    """信贷脉冲：CI=(Σ_window社融(t)/年化GDP(t) − 同(t−window))×100，pp。flows 须按月升序连续。
    取「两个窗口与各自GDP 都齐备」的最新月。数据不足/对不上 → 诚实 (None, None)。"""
    if window < 1 or len(flows) < 2 * window:
        return None, None
    yms = [k for k, _ in flows]
    vals = [v for _, v in flows]

    def roll(i: int) -> float:
        return sum(vals[i - window + 1:i + 1])

    for i in range(len(flows) - 1, 2 * window - 2, -1):
        ym_t, ym_p = yms[i], yms[i - window]
        g_t = _annual_gdp_at(gdp_map, ym_t)
        g_p = _annual_gdp_at(gdp_map, ym_p)
        if g_t and g_p:
            ci = (roll(i) / g_t - roll(i - window) / g_p) * 100.0
            return ci, ym_t
    return None, None


def _fetch_flow_rows(*, client=None) -> list:
    """POST shrzgmQuery 取社融增量月度序列（裸 POST 即返全量 list）。client 可注入（测试 mock）。"""
    owns = client is None
    if owns:
        import httpx
        client = httpx.Client(verify=_mofcom_ssl_ctx(), timeout=30, follow_redirects=True)
    try:
        resp = client.post(_QUERY_URL, headers={"User-Agent": _UA, "Referer": _REFERER})
        resp.raise_for_status()
        rows = resp.json()
    finally:
        if owns:
            client.close()
    if not isinstance(rows, list):
        raise ValueError("mofcom shrzgmQuery 返回非列表（源结构可能变更）")
    return rows


def _fetch_gdp_rows() -> list[tuple[str, float]]:
    """akshare macro_china_gdp → [(季度label, 国内生产总值-绝对值), ...]。隔离于此便于 run 层 mock。"""
    import akshare as ak
    df = ak.macro_china_gdp()
    return list(zip(df["季度"].tolist(), df["国内生产总值-绝对值"].tolist()))


def fetch_by_mofcom(cfg: dict, *, client=None, gdp_rows=None) -> tuple[float | None, str | None]:
    """按 mofcom 配置算一个派生值。cfg: {metric, flow_field?='tiosfs', window_months?=12}。
    metric=='credit_impulse'：拉社融增量序列 + GDP → 信贷脉冲(pp)。
    client 注入 mofcom POST mock；gdp_rows 注入 GDP（缺省现取 akshare）。未知 metric 抛 ValueError。"""
    metric = cfg.get("metric")
    if metric not in _KNOWN_METRICS:
        raise ValueError(f"未知 mofcom.metric: {metric!r}（支持 {list(_KNOWN_METRICS)}）")
    field = cfg.get("flow_field", "tiosfs")
    window = int(cfg.get("window_months", 12))
    flows = _monthly_flows(_fetch_flow_rows(client=client), field=field)
    if not flows:
        return None, None
    if metric == "credit_impulse":
        gdp_map = _annual_gdp_map(gdp_rows if gdp_rows is not None else _fetch_gdp_rows())
        return credit_impulse(flows, gdp_map, window=window)
    return None, None   # 不可达（metric 已校验）


def run_mofcom_fetch(slug: str, variant: str, *, only: set[str] | None = None,
                     client=None) -> dict:
    """抓所有 fetch_method=='mofcom' 且 availability=='scripted' 且有 mofcom 配置的输入。
    llm 项诚实跳过计数（它们走 headless LLM）。only 给定时只抓名字在其中的项。
    失败（抛异常/取不到值）记 record_fetch_error 并计数，不连累其余。返回 summary。"""
    data = reg.read_registry(slug, variant)
    fetched = skipped_todo = skipped_llm = failed = 0
    for e in data["inputs"]:
        if e.get("fetch_method") != "mofcom":
            continue
        if only is not None and e["name"] not in only:
            continue
        avail = e.get("availability")
        if avail == "llm":
            skipped_llm += 1
            continue
        if avail != "scripted" or not e.get("mofcom"):
            skipped_todo += 1
            continue
        try:
            val, as_of = fetch_by_mofcom(e["mofcom"], client=client)
        except Exception as exc:                       # 配置/网络/TLS/解析等：记错、跳过，不连累其余
            reg.record_fetch_error(slug, variant, e["name"], msg=str(exc))
            failed += 1
            continue
        if val is None:
            reg.record_fetch_error(slug, variant, e["name"],
                                   msg=f"mofcom 未取到值（序列不足或源变更）: metric={e['mofcom'].get('metric')}")
            failed += 1
            continue
        reg.record_observation(slug, variant, e["name"], value=val, as_of=as_of)
        fetched += 1
    return {"fetched": fetched, "skipped_todo": skipped_todo,
            "skipped_llm": skipped_llm, "failed": failed}


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    slug = argv[0] if len(argv) > 0 else "global-macro-rates-liquidity"
    variant = argv[1] if len(argv) > 1 else "opus4.8"
    print(f"mofcom 抓取: {run_mofcom_fetch(slug, variant)}")


if __name__ == "__main__":
    main()
