"""一次性冷启动种子：把 PRISM_VALIDATION F4 实测的 CN 创新药权威源灌进
cn-innovative-drug overlay + 标 promotion log promoted。

族 key = 'cn-innovative-drug'（该 industry 根 topic 自身 slug；其 arena/company
子 topic 的 parent_topic 指向它，自动共享本 overlay）。

用法：  python3 -m prism.scripts.seed_overlay_cn_pharma
幂等：重复跑只会确保这些 host 在 overlay 内，不重复膨胀。
"""
from __future__ import annotations

from prism.scripts import web_prescan as wp

FAMILY = "cn-innovative-drug"        # 机器键（英文 kebab，= 该 industry 根 topic 的 slug）
DISPLAY_NAME = "中国创新药"           # 给人看的中文标签，写进 overlay 的 display_name 字段

# 均已核实在全局 WHITELIST_DOMAINS 判为 'other'（=确为缺口）
SEED_HOSTS = [
    # 通用 CN 金融/交易所/媒体（全局表缺，本族先补；后续可提案进代码级全局表）
    "hkexnews.hk", "news.cn", "thepaper.cn", "eeo.com.cn",
    "pdf.dfcfw.com", "eastmoney.com",
    # 药企 IR 根域（F4 明列）
    "hengrui.com", "akesobio.com", "kelun-biotech.com",
    "innoventbio.com", "beigene.com",
]


def seed() -> dict:
    """写 overlay + log（promoted）。返回 {'family','seeded','overlay_path'}。"""
    log = wp._read_promotion_log()
    fam = log.setdefault(FAMILY, {})
    for h in SEED_HOSTS:
        wp._append_to_overlay(FAMILY, h, display_name=DISPLAY_NAME)  # 写 overlay（幂等 union）
        entry = fam.setdefault(h, {"count": 0, "topics": [], "promoted": False})
        entry["promoted"] = True                  # 标已晋升，避免重复回流
        if "seed:F4" not in entry["topics"]:
            entry["topics"].append("seed:F4")
            entry["count"] = max(entry["count"], wp.PROMOTION_THRESHOLD)
    wp._write_json_atomic(wp._promotion_log_path(), log)
    return {
        "family": FAMILY,
        "seeded": sorted(SEED_HOSTS),
        "overlay_path": str(wp._overlay_path(FAMILY)),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(seed(), ensure_ascii=False, indent=2))
