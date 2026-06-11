"""ADR 退市 / HFCAA / PCAOB 取文通道：纯解析层。

零网络、无登记表副作用——只测从 SEC HFCAA 纯文本派生状态信号与指纹，覆盖实拉验证的结构要点：
  · 临时清单空（官方原句 "no issuer on the provisional list"）→ provisional_empty。
  · 最终清单按「名称/CIK/日期/当前禁令/此前禁令」五行一组解析（CIK 数字 + Month DD, YYYY 锚定）。
  · current trading prohibition = "Not applicable" → 不报警；真有日期 → active（退市警报）。
  · 指纹随「新点名 / 禁令生效 / 认定更新日期」变，纯样板不变。
"""
from __future__ import annotations

from prism.scripts import hfcaa_fetch as hf


# ── SEC HFCAA fixture（实拉形态：剥标签后清单按行排列） ──────────────────────────
# 当前真实态：临时清单空 + 最终清单历史名册，全部 Not applicable（PCAOB 已 vacated）。
_SEC_PLAIN = """PCAOB Determination Update
On December 15, 2022, the PCAOB vacated its 2021 determinations that the positions taken by authorities in mainland China and Hong Kong prevented it from inspecting completely.
Trading Prohibition Update
On December 29, 2022, the President signed the Consolidated Appropriations Act, 2023.
Provisional list of issuers identified under the HFCAA*
Issuer Name
CIK
Date provisionally identified
There is currently no issuer on the provisional list.
Conclusive list of issuers identified under the HFCAA
Issuer Name
CIK
Date conclusively identified
Current trading prohibition
Prior trading prohibition
BeiGene, Ltd.
1651308
March 30, 2022
Not applicable
Not applicable
Baidu, Inc.
1329099
April 21, 2022
Not applicable
Not applicable
Related Materials
PCAOB Release on its 2022 HFCAA Determination Report
"""

# 假想的「警报态」：一家发行人被临时点名 + 一家最终清单交易禁令真正生效。
_SEC_PLAIN_ALARM = """PCAOB Determination Update
On May 1, 2027, the PCAOB issued a new determination regarding mainland China.
Provisional list of issuers identified under the HFCAA*
Issuer Name
CIK
Date provisionally identified
Some New ADR Co.
9990001
April 1, 2027
Not applicable
Not applicable
Conclusive list of issuers identified under the HFCAA
Issuer Name
CIK
Date conclusively identified
Current trading prohibition
Prior trading prohibition
BeiGene, Ltd.
1651308
March 30, 2022
April 1, 2027
Not applicable
Related Materials
"""


def test_provisional_empty_detected():
    sig = hf.sec_signals(_SEC_PLAIN)
    assert sig["provisional_empty"] is True
    assert sig["provisional_rows"] == []


def test_conclusive_rows_parsed():
    sig = hf.sec_signals(_SEC_PLAIN)
    rows = sig["conclusive_rows"]
    assert len(rows) == 2
    by = {r["name"]: r for r in rows}
    assert by["BeiGene, Ltd."]["cik"] == "1651308"
    assert by["Baidu, Inc."]["date"] == "April 21, 2022"


def test_not_applicable_means_no_alarm():
    sig = hf.sec_signals(_SEC_PLAIN)
    # 全部 Not applicable → 无生效禁令（制度性为零）
    assert sig["active_rows"] == []
    assert all(not r["active"] for r in sig["conclusive_rows"])


def test_update_dates_extracted():
    sig = hf.sec_signals(_SEC_PLAIN)
    # 认定更新段内日期（出新认定即变）
    assert "December 15, 2022" in sig["update_dates"]


def test_alarm_state_flags_active_and_provisional():
    sig = hf.sec_signals(_SEC_PLAIN_ALARM)
    # 临时清单非空（新点名）
    assert sig["provisional_empty"] is False
    assert len(sig["provisional_rows"]) == 1
    assert sig["provisional_rows"][0]["name"] == "Some New ADR Co."
    # 最终清单一行交易禁令生效 → active
    active_names = {r["name"] for r in sig["active_rows"]}
    assert "BeiGene, Ltd." in active_names


def test_fingerprint_changes_on_alarm():
    calm = hf._fingerprint(hf.sec_signals(_SEC_PLAIN), pcaob_ok=True)
    alarm = hf._fingerprint(hf.sec_signals(_SEC_PLAIN_ALARM), pcaob_ok=True)
    assert calm != alarm
    # 平静态指纹应反映「临时清单空 + 无生效禁令」
    assert "prov:empty" in calm and "active:" in calm
    # 警报态指纹应带上生效发行人名
    assert "BeiGene" in alarm


def test_fingerprint_stable_on_boilerplate_noise():
    # 在清单之外追加纯样板文字，不应改变指纹（指纹只吃派生信号）
    noisy = _SEC_PLAIN + "\nSign up for email updates about the HFCAA.\nFooter nav links.\n"
    assert (hf._fingerprint(hf.sec_signals(noisy), pcaob_ok=True)
            == hf._fingerprint(hf.sec_signals(_SEC_PLAIN), pcaob_ok=True))


def test_status_summary_renders_zero_state():
    summary = "\n".join(hf._status_summary(hf.sec_signals(_SEC_PLAIN)))
    assert "临时清单" in summary and "空" in summary
    assert "无任何发行人当前交易禁令生效" in summary
