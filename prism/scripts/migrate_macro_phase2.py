"""一次性迁移（宏观第二期）：纯函数对 registry dict 变换 + main() 落盘。零 LLM。
按计划任务顺序累加：add_fred_series_ids（T3）/ set_alert_bands（T5）/ add_tail_inputs（T6）。"""
from __future__ import annotations

from prism.scripts import macro_registry as reg

SLUG, VAR = "global-macro-rates-liquidity", "opus4.8"

# 计划「FRED series_id 映射表」的精确落库版本。键=登记表 name 原文。
FRED_SERIES_ID = {
    "联邦基金目标区间": "DFEDTARU",
    "非农就业 NFP": "PAYEMS",
    "失业率": "UNRATE",
    "初请失业金": "ICSA",
    "JOLTS 职位空缺/离职率": "JTSJOL",
    "零售销售": "RSAFS",
    "时薪 / ECI": "CES0500000003",
    "核心 PCE": "PCEPILFE",
    "CPI(核心+supercore)": "CPILFESL",
    "PCE 三分项(supercore/住房/商品)": "PCEPILFE",
    "PPI": "PPIFIS",
    "WTI 油价(+供给/需求分解)": "DCOILWTICO",
    "5y5y/breakeven 通胀预期": "T5YIFR",
    "TGA 余额": "WTREGEN",
    "联邦赤字": "MTSDS133FMS",
    "美联储资产 WALCL(QT 节奏)": "WALCL",
    "RRP 逆回购": "RRPONTSYD",
    "净流动性(=资产−TGA−RRP)": "__DERIVED__",
    "银行准备金 + 准备金/GDP": "WRESBAL",
    "2Y/10Y/30Y 国债": "DGS10",
    "10Y 实际利率 TIPS": "DFII10",
    "2s10s 曲线斜率": "T10Y2Y",
    "IG OAS": "BAMLC0A0CM",
    "HY OAS": "BAMLH0A0HYM2",
    "VIX": "VIXCLS",
    "金融条件指数 FCI(NFCI/GS)": "NFCI",
    "广义/EM加权美元(Fed DTWEXBGS)": "DTWEXBGS",
    "DXY": "DTWEXAFEGS",  # 代理
    "USDJPY / 日元 carry": "DEXJPUS",
    "USDCNY": "DEXCHUS",
    # 黄金不在此表 → 改判 llm-web（见下）
}
RECLASSIFY_TO_WEB = {"黄金"}


def add_fred_series_ids(data: dict) -> dict:
    """给 fetch_method==fred-api 的输入补 fred_series_id；黄金改判 llm-web。原地改并返回。"""
    for e in data["inputs"]:
        name = e.get("name")
        if name in RECLASSIFY_TO_WEB:
            e["fetch_method"] = "llm-web"
            e["source"] = "web"
            continue
        if e.get("fetch_method") == "fred-api":
            sid = FRED_SERIES_ID.get(name)
            if sid:
                e["fred_series_id"] = sid
    return data


ALERT_BANDS = {
    "HY OAS": {"level": 450, "direction": "above", "level_alarm": 550},
    "MOVE 债市波动率": {"level": 120, "direction": "above", "level_alarm": 140},
    "跨币种基差(EUR/JPY-USD)": {"level": -40, "direction": "below", "level_alarm": -60},
    "USDJPY / 日元 carry": {"delta": 3.0, "level": 158, "direction": "above", "level_alarm": 160},
    "DR007/R007": {"level": 2.2, "direction": "above", "level_alarm": 2.5, "min_streak": 2},
    "CNH-CNY 价差": {"level": 0.015, "direction": "abs_above", "level_alarm": 0.030},
}


def set_alert_bands(data: dict) -> dict:
    """把 6 条 alert_series 的占位带替换为校准带。原地改并返回。"""
    for e in data["inputs"]:
        band = ALERT_BANDS.get(e.get("name"))
        if band is not None:
            e["alert_band"] = dict(band)
    return data


TAIL_INPUTS = [
    {
        "name": "中美地缘/关税(尾部)",
        "tier": "B", "cadence_type": "event", "targets": ["fx", "rates"],
        "mechanism": "CR", "importance": "background",
        "source": "PIIE US-China Trade War Tariffs chart + Trump trade war timeline 2.0",
        "fetch_method": "llm-web", "state": "新增(第二期尾部源)",
        "causal_sentence": "关税/地缘冲击经风险偏好与汇率渠道情境式影响中概与出口链（情境相关，非稳定因果）。",
        "lag": "事件驱动", "alert_series": False,
        "monitoring": {"enabled": True},
    },
    {
        "name": "ADR退市/HFCAA(尾部)",
        "tier": "B", "cadence_type": "event", "targets": ["fx"],
        "mechanism": "CR", "importance": "background",
        "source": "PCAOB HFCAA determinations + SEC Commission-Identified Issuers",
        "fetch_method": "llm-web", "state": "新增(第二期尾部源)",
        "causal_sentence": "PCAOB 新负面裁定触发 HFCAA 强制退市路径，情境式冲击中概 ADR 估值（情境相关）。",
        "lag": "事件驱动", "alert_series": False,
        "monitoring": {"enabled": True},
    },
]


def add_tail_inputs(data: dict) -> dict:
    """把 2 条类别尾部加为在册 llm-web 监控项（幂等：按 name 去重）。"""
    existing = {e.get("name") for e in data["inputs"]}
    for t in TAIL_INPUTS:
        if t["name"] not in existing:
            data["inputs"].append(dict(t))
    return data


def main():
    data = reg.read_registry(SLUG, VAR)
    add_fred_series_ids(data)
    set_alert_bands(data)
    add_tail_inputs(data)
    reg._write_yaml(reg._registry_path(SLUG, VAR), data)
    errs = reg.validate_registry(SLUG, VAR)
    print(f"迁移完成；validator {len(errs)} 错")
    for x in errs:
        print(" -", x)


if __name__ == "__main__":
    main()
