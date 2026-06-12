"""宏观层输入登记表（macro_inputs.yaml）的零-LLM CRUD + 机制纪律 validator。

与 manifest.py（materials 库）刻意分离：manifest 存"资料/搜索 hit"，本模块存
"会影响利率/流动性/汇率判断的输入"及其机制边（spec §2.2）。登记与抓取解耦——
本模块只管登记 + 观测值落盘 + 机制校验；FRED 自动抓等是第二期的事。

登记表 schema：
  slug, variant, updated, inputs: [ {input entry}, ... ]
每条 input entry（spec §2.2 + 运行时观测位）：
  name           中文输入名（唯一键）
  tier           "A"|"B"|"C"
  cadence_type   "event"|"series"|"policy"   (事/行/述)
  targets        ["rates"|"liquidity"|"fx", ...]
  mechanism      "CD"|"CF"|"CO"|"CR"
  causal_sentence  一句话因果链（CD/CF 必填）
  family         输入源族系（CANONICAL_FAMILIES 之一），词典/Web 表分组键
  gloss          {define, read, use} 门外汉三层词条（定义/为什么看/怎么用），与 causal_sentence 并存
  lag            领先/同步/滞后 + 时长（自由文本）
  importance     "load_bearing"|"confirming"|"background"
  source         FRED / web / PBoC / ... / TBD
  source_url     源链接（可空）。语义随 availability：
                 · scripted   = 真实数据端点（脚本直拉的 URL）
                 · llm 有值    = 固定页起点（索引/落地页，executor 从此起抓，读返回内容判下一跳）
                 · llm 无值    = 检索式（无稳定起点，executor 构造 query 发起 web 检索，采用源记入 observed.evidence 引文）
                 取数方式由 source_url 在不在派生，见 llm_acquisition_mode()——单一真相，UI 与未来 executor 共用
  authority      "official"|"primary"|"secondary"|"aggregator"（可空，权威性）
  availability   "scripted"|"scriptable_todo"|"llm"（可空，取数成本轴：
                 scripted=固定脚本直拉零LLM便宜 / scriptable_todo=能转脚本但recipe待写(降本待办,note记缺什么) /
                 llm=无法稳定脚本化,每轮LLM读或检索判(贵,note记原因)）
  derived        {op:"sub"|"add", series:[FRED series,...]}（可空，fred_series_id=="__DERIVED__" 时由各 series 计算，如 SOFR−IORB）
  fetch_method   脚本执行通道，仅对 availability=='scripted' 有意义：fred-api（走 fred_fetch）
                 / recipe（走 recipe_fetch，须配 fetch_recipe）/ akshare（走 akshare_fetch，须配
                 akshare 块{func,date_column,value_column}）。非 scripted 项不设 fetch_method
                 （其取数走 headless LLM，取法由 source_url 派生，见 llm_acquisition_mode）。
  fetch_recipe   {url, parse:{json_path, date_path}}（可空，recipe 通道 fetcher 用）
  text_fetch     脚本「取文」通道（可空）：值∈VALID_TEXT_FETCH，登记表驱动地把该输入路由到
                 textfetch._FETCHERS 对应 fetcher 下载原文存 local_cache_path。与 fetch_method（数值通道）
                 不同——取文只下原文、立场判读仍走 LLM，故仅 llm/scriptable_todo 项可设，且不可与 fetch_method 并存。
  state          "已有"|"新增"|"改"
  alert_series   bool（仅 series 可为 true）
  monitoring     {enabled: bool}            缺省视为 enabled=true
  alert_band     {delta: float} 或 {z: float}   仅 alert_series 用
  observed       {value, prev_value, z, as_of, next_due, last_proposed_value}  运行时位（fetcher/monitor 写）
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import yaml

_PRISM_ROOT = Path(__file__).resolve().parent.parent

VALID_TIER = ("A", "B", "C")
VALID_CADENCE = ("event", "series", "policy")
VALID_MECHANISM = ("CD", "CF", "CO", "CR")
VALID_IMPORTANCE = ("load_bearing", "confirming", "background")
VALID_TARGET = ("rates", "liquidity", "fx")
VALID_AUTHORITY = ("official", "primary", "secondary", "aggregator")
VALID_AVAILABILITY = ("scripted", "scriptable_todo", "llm")
VALID_FETCH_METHOD = ("fred-api", "recipe", "akshare", "yfinance", "macromicro", "barchart", "ecb", "safe", "cftc")   # 脚本「数值」通道，仅 scripted 项可设
VALID_TEXT_FETCH = ("fomc", "qra", "china_us", "hfcaa", "politburo")   # 脚本「取文」通道（下载原文存本地缓存），须与 textfetch._FETCHERS 键一致；
                               # 立场判读仍走 LLM，故仅 llm/scriptable_todo 项可设，与 fetch_method 互斥
VALID_RECIPE_KIND = ("json", "csv", "matrix", "html", "json_scan")   # 须与 recipe_fetch._PARSERS 键一致

# 输入源族系（input_glossary 词典/Web 表分组键，顺序=展示顺序，单一真相）
CANONICAL_FAMILIES = (
    "增长就业", "通胀", "货币政策", "流动性·数量", "利率·曲线结构",
    "信用与风险偏好", "资金面咬合", "汇率·跨境套利",
    "中国货币·流动性", "中国增长·外需", "跨资产代理",
)
# 每 kind 的必填 parse 键（缺则取不到值）：matrix 须 row_label（解析器靠它定位数据行；
# header_label/col_index/delimiter 有默认或仅影响日期）。html 须 value_regex（第 1 捕获组=值；
# date_regex 选填）。
_RECIPE_REQUIRED_PARSE = {"json": "json_path", "csv": "value_column", "matrix": "row_label",
                          "html": "value_regex", "json_scan": "match_regex"}

# policy 立场有序轴：轴名 → 档位元组（有序，索引升=趋势的"高"端）。diff 按索引差算方向。
STANCE_SCALES = {
    "hawk_dove": ("鸽", "偏鸽", "中性", "偏鹰", "鹰"),
    "ease_tighten": ("宽松", "偏松", "中性", "偏紧", "收紧"),
    "expand_contract": ("扩张", "中性", "收缩"),
    "path_shift": ("上移", "不变", "下移"),
    # 地缘/关税轴：无市场序列可 diff 的事件叙事型输入（如中美地缘/关税），把「升级↔缓和」判读
    # 落成可 diff 的立场档位（索引升=更紧张），使 LLM 结论进 observed.stance → 被 eval 战绩/翻牌消费。
    "geo_escalation": ("缓和", "偏缓", "中性", "偏紧", "升级"),
}
# 每轴方向取词：(索引上升时词, 索引下降时词)
STANCE_DIRECTION = {
    "hawk_dove": ("更鹰", "更鸽"),
    "ease_tighten": ("更紧", "更松"),
    "expand_contract": ("更收缩", "更扩张"),
    "path_shift": ("更下移", "更上移"),
    "geo_escalation": ("更升级", "更缓和"),
}


def _registry_path(slug: str, variant: str) -> Path:
    if not variant:
        raise ValueError("必须显式指定 variant")
    return _PRISM_ROOT / "topics" / slug / variant / "macro_inputs.yaml"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _write_yaml(path: Path, data: dict) -> None:
    path.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def create_registry(slug: str, variant: str) -> Path:
    path = _registry_path(slug, variant)
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_yaml(path, {"slug": slug, "variant": variant, "updated": _now_iso(), "inputs": []})
    return path


def read_registry(slug: str, variant: str) -> dict:
    path = _registry_path(slug, variant)
    if not path.exists():
        raise FileNotFoundError(f"macro_inputs.yaml not found: {slug}/{variant}")
    return _read_yaml(path)


def read_transmission_map(slug: str, variant: str) -> dict:
    """读传导地图 outputs/transmission_map.yaml（L4 持仓暴露契约）。

    它是 .yaml 产物（非 .md），故走不了 outputs.read_output_html 的 markdown 视图，
    由专属 web 路由直读渲染（同 macro_inputs 的模式）。缺文件返回 {}，让路由优雅
    显示「未生成」而非 500。
    """
    path = _PRISM_ROOT / "topics" / slug / variant / "outputs" / "transmission_map.yaml"
    if not path.exists():
        return {}
    return _read_yaml(path)


def llm_acquisition_mode(entry: dict) -> str | None:
    """llm 项的取数方式（单一真相，UI 与 executor 共用）。
    优先级：local_file > fixed_page > search。
      local_cache_path 存在且文件落盘 → "local_file"：用 Read 读本地缓存文件（最廉价）。
      有 source_url                  → "fixed_page"：从固定页起抓，LLM WebFetch 判读。
      无 source_url                  → "search"    ：LLM 构造 query 检索，采用源记入 evidence。
    非 llm 返回 None。"""
    if entry.get("availability") != "llm":
        return None
    path = entry.get("local_cache_path")
    if path and (_PRISM_ROOT / path).exists():
        return "local_file"
    return "fixed_page" if entry.get("source_url") else "search"


def monitoring_enabled(entry: dict) -> bool:
    """该输入是否在监控中。缺省随 rung：scripted 默认开（脚本抓廉价）、其余默认关
    （llm/scriptable_todo 走 headless LLM，烧钱，按项 opt-in）。显式 monitoring.enabled 覆盖缺省。"""
    m = entry.get("monitoring") or {}
    if "enabled" in m:
        return bool(m["enabled"])
    return entry.get("availability") == "scripted"


def monitor_mode(entry: dict) -> str:
    """被监控时怎么自动执行：scripted → "script"（fred-api/recipe 脚本直拉，零 LLM）；
    其余 → "headless_llm"（拉起 headless claude 取数+判 promote）。"""
    return "script" if entry.get("availability") == "scripted" else "headless_llm"


def upsert_input(slug: str, variant: str, entry: dict) -> None:
    """按 name 唯一键 upsert 一条 input（无校验，校验交 validate_registry）。零 LLM。"""
    if not entry.get("name"):
        raise ValueError("input entry 必须有 name")
    data = read_registry(slug, variant)
    for i, existing in enumerate(data["inputs"]):
        if existing["name"] == entry["name"]:
            data["inputs"][i] = {**existing, **entry}
            break
    else:
        data["inputs"].append(entry)
    data["updated"] = _now_iso()
    _write_yaml(_registry_path(slug, variant), data)


def remove_input(slug: str, variant: str, name: str) -> bool:
    """按 name 删一条 input（零 LLM）。删到返回 True，不存在返回 False（非致命）。
    拆分/重命名输入时用（upsert 按 name 合并、不能改名，故删旧+加新走本函数）。"""
    data = read_registry(slug, variant)
    before = len(data["inputs"])
    data["inputs"] = [e for e in data["inputs"] if e.get("name") != name]
    if len(data["inputs"]) == before:
        return False
    data["updated"] = _now_iso()
    _write_yaml(_registry_path(slug, variant), data)
    return True


def validate_registry(slug: str, variant: str) -> list[str]:
    """校验登记表的机制纪律（spec §2.2/§2.1）。返回错误串列表（空=通过）。零 LLM。

    规则：
      - 枚举合法：tier/cadence_type/mechanism/importance/targets。
      - tier A ⟹ mechanism ∈ {CD, CF}（CO/CR 只能 B/C）。
      - mechanism ∈ {CD, CF} ⟹ causal_sentence 非空。
      - alert_series=True ⟹ cadence_type == "series"。
      - name 不可重复。
    """
    data = read_registry(slug, variant)
    errors: list[str] = []
    seen: set[str] = set()
    for e in data["inputs"]:
        name = e.get("name", "<无名>")
        if name in seen:
            errors.append(f"[{name}] name 重复")
        seen.add(name)
        if e.get("tier") not in VALID_TIER:
            errors.append(f"[{name}] tier 非法: {e.get('tier')!r}")
        if e.get("cadence_type") not in VALID_CADENCE:
            errors.append(f"[{name}] cadence_type 非法: {e.get('cadence_type')!r}")
        if e.get("mechanism") not in VALID_MECHANISM:
            errors.append(f"[{name}] mechanism 非法: {e.get('mechanism')!r}")
        if e.get("importance") not in VALID_IMPORTANCE:
            errors.append(f"[{name}] importance 非法: {e.get('importance')!r}")
        for t in e.get("targets") or []:
            if t not in VALID_TARGET:
                errors.append(f"[{name}] target 非法: {t!r}")
        # 因果纪律
        if e.get("tier") == "A" and e.get("mechanism") in VALID_MECHANISM and e.get("mechanism") not in ("CD", "CF"):
            errors.append(f"[{name}] tier A 必须 mechanism ∈ CD/CF，得到 {e.get('mechanism')!r}")
        if e.get("mechanism") in ("CD", "CF") and not (e.get("causal_sentence") or "").strip():
            errors.append(f"[{name}] mechanism={e.get('mechanism')} 必须填 causal_sentence")
        if e.get("alert_series") and e.get("cadence_type") != "series":
            errors.append(f"[{name}] alert_series=True 仅允许 cadence_type=series")
        if e.get("authority") is not None and e.get("authority") not in VALID_AUTHORITY:
            errors.append(f"[{name}] authority 非法: {e.get('authority')!r}")
        if e.get("availability") is not None and e.get("availability") not in VALID_AVAILABILITY:
            errors.append(f"[{name}] availability 非法: {e.get('availability')!r}")
        fm = e.get("fetch_method")
        if fm is not None:
            if fm not in VALID_FETCH_METHOD:
                errors.append(f"[{name}] fetch_method 非法: {fm!r}（仅 {list(VALID_FETCH_METHOD)}）")
            if e.get("availability") != "scripted":
                errors.append(f"[{name}] fetch_method 只能出现在 scripted 项（取数通道），"
                              f"当前 availability={e.get('availability')!r}")
        tf = e.get("text_fetch")
        if tf is not None:
            if tf not in VALID_TEXT_FETCH:
                errors.append(f"[{name}] text_fetch 非法: {tf!r}（仅 {list(VALID_TEXT_FETCH)}）")
            if e.get("availability") not in ("llm", "scriptable_todo"):
                errors.append(f"[{name}] text_fetch 取文项立场判读走 LLM，availability 须 llm/scriptable_todo，"
                              f"当前 {e.get('availability')!r}")
            if e.get("fetch_method"):
                errors.append(f"[{name}] text_fetch（取文）与 fetch_method（取数值）互斥，勿同设")
        recipe = e.get("fetch_recipe")
        if recipe:
            kind = recipe.get("kind", "json")
            if kind not in VALID_RECIPE_KIND:
                errors.append(f"[{name}] fetch_recipe.kind 非法: {kind!r}")
            else:
                req = _RECIPE_REQUIRED_PARSE[kind]
                if not (recipe.get("parse") or {}).get(req):
                    errors.append(f"[{name}] fetch_recipe kind={kind} 缺 parse.{req}")
        if fm == "akshare":
            ak = e.get("akshare")
            if not ak:
                errors.append(f"[{name}] fetch_method=akshare 须配 akshare 块")
            else:
                for k in ("func", "date_column", "value_column"):
                    if not ak.get(k):
                        errors.append(f"[{name}] akshare 块缺 {k}")
        if fm == "yfinance":
            yfc = e.get("yfinance")
            if not yfc:
                errors.append(f"[{name}] fetch_method=yfinance 须配 yfinance 块")
            elif not yfc.get("ticker"):
                errors.append(f"[{name}] yfinance 块缺 ticker")
        if fm == "macromicro":
            mmc = e.get("macromicro")
            if not mmc:
                errors.append(f"[{name}] fetch_method=macromicro 须配 macromicro 块")
            else:
                for k in ("chart_id", "page_url"):
                    if not mmc.get(k):
                        errors.append(f"[{name}] macromicro 块缺 {k}")
        if fm == "barchart":
            bc = e.get("barchart")
            if not bc:
                errors.append(f"[{name}] fetch_method=barchart 须配 barchart 块")
            elif not bc.get("symbol"):
                errors.append(f"[{name}] barchart 块缺 symbol")
        if fm == "ecb":
            ec = e.get("ecb")
            if not ec:
                errors.append(f"[{name}] fetch_method=ecb 须配 ecb 块")
            elif not ec.get("mode"):
                errors.append(f"[{name}] ecb 块缺 mode")
        if fm == "safe":
            sf = e.get("safe")
            if not sf:
                errors.append(f"[{name}] fetch_method=safe 须配 safe 块")
            else:
                for k in ("article_url", "sheet", "row_label"):
                    if not sf.get(k):
                        errors.append(f"[{name}] safe 块缺 {k}")
        if fm == "cftc":
            cc = e.get("cftc")
            if not cc:
                errors.append(f"[{name}] fetch_method=cftc 须配 cftc 块")
            else:
                for k in ("dataset", "contract"):
                    if not cc.get(k):
                        errors.append(f"[{name}] cftc 块缺 {k}")
        scale = e.get("stance_scale")
        if scale is not None and scale not in STANCE_SCALES:
            errors.append(f"[{name}] stance_scale 非法: {scale!r}")
        stance = (e.get("observed") or {}).get("stance")
        if stance is not None:
            if scale is None:
                errors.append(f"[{name}] 设了 observed.stance 但未声明 stance_scale")
            elif scale in STANCE_SCALES and stance not in STANCE_SCALES[scale]:
                errors.append(f"[{name}] stance {stance!r} 不在轴 {scale} 档位内")
            if not str((e.get("observed") or {}).get("evidence") or "").strip():
                errors.append(f"[{name}] 设了 observed.stance 必须附 evidence")
        fam = e.get("family")
        if fam is not None and fam not in CANONICAL_FAMILIES:
            errors.append(f"[{name}] family 非法: {fam!r}（须在 CANONICAL_FAMILIES 内）")
        g = e.get("gloss")
        if g is not None:
            if not isinstance(g, dict):
                errors.append(f"[{name}] gloss 须为 dict")
            else:
                for k in ("define", "read", "use"):
                    if not str(g.get(k) or "").strip():
                        errors.append(f"[{name}] gloss 缺 {k}（三键 define/read/use 须齐全非空）")
    return errors


def inputs_missing_gloss(registry: dict) -> list[str]:
    """列出「被追踪却缺 gloss/family」的 input name（覆盖闸门 + 生成器共用）。零 LLM。

    被追踪=登记表 inputs 全集（含 monitoring=false 的 CIP 腿）。
    缺=无 family，或 gloss 三键(define/read/use)任一空缺。
    """
    missing = []
    for e in registry.get("inputs") or []:
        g = e.get("gloss") or {}
        ok = e.get("family") and all(str(g.get(k) or "").strip() for k in ("define", "read", "use"))
        if not ok:
            missing.append(e.get("name", "<无名>"))
    return missing


def record_observation(
    slug: str, variant: str, name: str, *,
    value: float | None = None, as_of: str | None = None,
    z: float | None = None, next_due: str | None = None,
    evidence: str | None = None, acq_note: str | None = None,
    stance: str | None = None, fingerprint: str | None = None,
) -> None:
    """把一次观测写进某 input 的 observed；旧 value 滚成 prev_value。零 LLM。

    fetcher（第二期）每次抓到新值调本函数；monitor 据 observed 判越带/到期。
    value 给定时滚动 prev_value；z/next_due 给定则覆盖对应位。
    evidence 给定则写 observed.evidence（headless LLM 取数记采用源/引文，尤其 search 模式）。
    acq_note 给定则写 observed.acq_note（本次取数/可否脚本化的判定留痕——无论是否 promote 都记）。
    stance 给定则写 observed.stance（policy 输入的鹰鸽/松紧立场档位，须在 stance_scale 轴内）。
    fingerprint 给定则写 observed.fingerprint（本次判读所依据的资料身份，如 FOMC=声明/纪要 URL；
        下次取数前对比，相同则视为内容未变、不再二次判读，见 mark_verified）。
    """
    data = read_registry(slug, variant)
    for e in data["inputs"]:
        if e["name"] == name:
            obs = dict(e.get("observed") or {})
            if value is not None:
                if "value" in obs:
                    obs["prev_value"] = obs["value"]
                obs["value"] = value
            if as_of is not None:
                obs["as_of"] = as_of
            if z is not None:
                obs["z"] = z
            if next_due is not None:
                obs["next_due"] = next_due
            if evidence is not None:
                obs["evidence"] = evidence
            if acq_note is not None:
                obs["acq_note"] = acq_note
            if stance is not None:
                obs["stance"] = stance
            if fingerprint is not None:
                obs["fingerprint"] = fingerprint
            obs.pop("fetch_error", None)  # 抓到本次观测=成功，清除上次失败标记
            obs["checked_at"] = _now_iso()
            # 维护连续越带计数（min_streak 用）
            if value is not None:
                breached = _reading_breaches({**e, "observed": obs})
                obs["streak"] = (obs.get("streak", 0) + 1) if breached else 0
            e["observed"] = obs
            data["updated"] = _now_iso()
            _write_yaml(_registry_path(slug, variant), data)
            return
    raise ValueError(f"input {name!r} 不在登记表中")


def mark_verified(slug: str, variant: str, name: str, *, fingerprint: str | None = None) -> None:
    """记一次「已核对、内容未变」：bump observed.verified_at（零 LLM）。

    去重降本路径用：取数前对比指纹，未变则跳过 LLM 重判、调本函数留痕。
    与 checked_at（=上次真正判读落值时间）语义区分——verified_at 表「最近一次确认资料未变」。
    fingerprint 给定则一并写入（补齐历史缺失指纹的 entry）。input 不存在则静默跳过（非致命）。"""
    data = read_registry(slug, variant)
    for e in data["inputs"]:
        if e["name"] == name:
            obs = dict(e.get("observed") or {})
            obs["verified_at"] = _now_iso()
            if fingerprint is not None:
                obs["fingerprint"] = fingerprint
            e["observed"] = obs
            data["updated"] = _now_iso()
            _write_yaml(_registry_path(slug, variant), data)
            return


def record_fetch_error(slug: str, variant: str, name: str, *, msg: str | None) -> None:
    """记/清一次脚本抓取失败到 observed.fetch_error（零 LLM）。fred/recipe/取文三通道共用。

    msg 给定 → 写 observed.fetch_error={msg, at}（at=失败时刻）：留痕「哪条、何时、何因」，
      供 web 顶部告警板提醒去修脚本或换源。**不动 value/checked_at**——失败时旧值保留、
      仅标记陈旧，而非污染（值的新鲜度看 checked_at，失败看 fetch_error.at）。
    msg=None → 清除 fetch_error（修好/成功时）。fred/recipe 成功走 record_observation 自动清，
      故本路径主要给取文通道（成功不调 record_observation）显式清错用。
    无变化（要清但本就没有）则不写盘。input 不存在则静默跳过（非致命，批量抓取里一条不连累其余）。"""
    data = read_registry(slug, variant)
    for e in data["inputs"]:
        if e["name"] == name:
            obs = dict(e.get("observed") or {})
            if msg is None:
                if "fetch_error" not in obs:
                    return  # 本就无错、无需清 → 不写盘
                obs.pop("fetch_error", None)
            else:
                obs["fetch_error"] = {"msg": str(msg)[:500], "at": _now_iso()}
            e["observed"] = obs
            data["updated"] = _now_iso()
            _write_yaml(_registry_path(slug, variant), data)
            return


def flag_scriptable(slug: str, variant: str, name: str, *, note: str) -> bool:
    """promote 闸门：llm 项经 headless LLM 判定可脚本化、且已实拉到数据后，
    升 availability llm→scriptable_todo + 写 note（提醒后台实现 recipe）。零 LLM。

    闸门读**已落盘的 observed.value**：仅当 availability=='llm' 且 observed.value 非空才升，
    否则返回 False、不动——杜绝「嘴上说能 script、其实没数据」。只有 evidence 无 value 的
    event/policy 立场项会被正确拒绝。升档成功返回 True。
    """
    data = read_registry(slug, variant)
    for e in data["inputs"]:
        if e["name"] == name:
            if e.get("availability") != "llm":
                return False
            if (e.get("observed") or {}).get("value") is None:
                return False
            e["availability"] = "scriptable_todo"
            if note:
                e["note"] = note
            data["updated"] = _now_iso()
            _write_yaml(_registry_path(slug, variant), data)
            return True
    raise ValueError(f"input {name!r} 不在登记表中")


def set_local_cache_path(slug: str, variant: str, name: str, rel_path: str) -> None:
    """写入 local_cache_path（相对 _PRISM_ROOT）。供文本缓存脚本（fomc_fetch 等）在下载后调用。
    llm_acquisition_mode 读此字段：文件存在 → 返回 local_file，优先于 fixed_page/search。"""
    data = read_registry(slug, variant)
    for e in data["inputs"]:
        if e["name"] == name:
            e["local_cache_path"] = rel_path
            data["updated"] = _now_iso()
            _write_yaml(_registry_path(slug, variant), data)
            return
    raise ValueError(f"input {name!r} 不在登记表中")


def _parse_date(s):
    from datetime import date as _date
    if not s:
        return None
    try:
        return _date.fromisoformat(str(s))
    except (ValueError, TypeError):
        return None


def _reading_breaches(entry: dict) -> bool:
    """单次读数是否越带：delta / z / level(+direction) 任一命中。"""
    band = entry.get("alert_band") or {}
    obs = entry.get("observed") or {}
    v, p = obs.get("value"), obs.get("prev_value")
    if "delta" in band and v is not None and p is not None:
        if abs(v - p) >= band["delta"]:
            return True
    if "z" in band:
        z = obs.get("z")
        if z is not None and abs(z) >= band["z"]:
            return True
    if "level" in band and v is not None:
        d = band.get("direction", "above")
        if d == "above" and v >= band["level"]:
            return True
        if d == "below" and v <= band["level"]:
            return True
        if d == "abs_above" and abs(v) >= band["level"]:
            return True
    return False


def _series_breached(entry: dict) -> bool:
    """alert_series 是否报警：当前读数越带 且 连续越带天数≥min_streak（默认1）。
    streak 由 record_observation 维护；未维护时默认 1（向后兼容旧 delta/z 行为）。"""
    if not _reading_breaches(entry):
        return False
    band = entry.get("alert_band") or {}
    obs = entry.get("observed") or {}
    return obs.get("streak", 1) >= band.get("min_streak", 1)


def due_llm_monitor_names(registry: dict, today=None) -> list[str]:
    """纯函数：选出「监控中」且走 headless LLM 的输入名（供定时循环批量取数）。零 LLM。

    规则（与 scan_macro_inputs 的报警语义平行，但只管 headless 轴）：
      - 仅 availability∈{llm, scriptable_todo} 且 monitoring_enabled(e)（缺省随 rung → 默认关）。
      - **今天已拉过的不再催**：observed.checked_at 的日期 ≥ today 即视为新鲜、跳过
        （否则拉完仍显示「到期·待拉取」——series 无到期概念，靠这条收口）。
      - event/policy：observed.next_due 可解析且 ≤ today 才取（到期才烧 token）。
      - series（及其余 cadence）：未当天拉过即取（无到期概念，新鲜度由 checked_at 兜底）。
    """
    from datetime import date as _date
    today = today or _date.today()
    names: list[str] = []
    for e in registry.get("inputs") or []:
        if e.get("availability") not in ("llm", "scriptable_todo"):
            continue
        if not monitoring_enabled(e):
            continue
        obs = e.get("observed") or {}
        # 今天已拉过 → 新鲜，不再催（checked_at 为 UTC isoformat，取日期段比对）
        checked = _parse_date(str(obs.get("checked_at") or "")[:10])
        if checked is not None and checked >= today:
            continue
        ctype = e.get("cadence_type")
        if ctype in ("event", "policy"):
            d = _parse_date(obs.get("next_due"))
            if d is None or d > today:
                continue
        names.append(e["name"])
    return names


def scan_macro_inputs(registry: dict, today=None) -> dict:
    """纯函数：把登记表分桶。不读文件。零 LLM。

    返回 {due_event, due_policy, alert_series, unparseable}，每项是 input entry 的浅拷贝。
    规则：
      - monitoring.enabled is False → 跳过。
      - cadence_type=event/policy：observed.next_due 可解析且 ≤ today → due_*；不可解析 → unparseable。
      - cadence_type=series 且 alert_series=True 且 _series_breached → alert_series。
      - 其余（含非 alert 的 series 小动）→ 不进任何桶。
    """
    from datetime import date as _date
    today = today or _date.today()
    out = {"due_event": [], "due_policy": [], "alert_series": [], "unparseable": []}
    for e in registry.get("inputs") or []:
        if (e.get("monitoring") or {}).get("enabled") is False:
            continue
        ctype = e.get("cadence_type")
        if ctype in ("event", "policy"):
            nd_raw = (e.get("observed") or {}).get("next_due")
            if nd_raw is None:
                continue  # 还没排期，不报
            d = _parse_date(nd_raw)
            if d is None:
                out["unparseable"].append(dict(e))
            elif d <= today:
                out["due_event" if ctype == "event" else "due_policy"].append(dict(e))
        elif ctype == "series" and e.get("alert_series") and _series_breached(e):
            out["alert_series"].append(dict(e))
    return out
