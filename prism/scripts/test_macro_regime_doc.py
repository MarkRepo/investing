"""结构闸：_macro_regime.md 必须含 spec §5 机制纠错 + §6 多维/fragility 条款。
markdown 无逻辑可单测，用关键短语存在性钉住规范不被漏写。"""
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
DOC = _ROOT / "prism/workflows/04-synthesize/_macro_regime.md"
READ = _ROOT / "prism/topics/global-macro-rates-liquidity/opus4.8/outputs/m_regime_read.md"


def test_doc_has_mechanism_corrections():
    t = DOC.read_text(encoding="utf-8")
    # §5 八条纠错的关键锚点
    assert "中美10Y利差" in t or "中美 10Y 利差" in t
    assert "压力表" in t                     # 中美利差 A→B 降为压力表
    assert "去美元化" in t                   # 黄金机制改写
    assert "SOFR" in t                       # 净流动性降权、SOFR−IORB 升 binding
    assert "超预期" in t                     # PCE/CPI 触发用超预期非水平
    assert "OAS" in t                        # #3 信用利差 OAS 收敛单一 B
    assert "尾部" in t                       # #6 日元 carry 条件/阈值尾部触发
    assert "CFETS" in t                      # #7 DXY 中国侧改用 CFETS/广义美元
    assert "比特币" in t                     # #8 比特币维持 C


def test_doc_has_multidim_and_fragility():
    t = DOC.read_text(encoding="utf-8")
    assert "分维信心" in t or "分维度信心" in t
    assert "象限" in t                       # 增长/通胀象限
    assert "脆弱" in t                       # fragility 罚分


def test_regime_read_has_fragility_and_quadrant():
    t = READ.read_text(encoding="utf-8")
    assert "脆弱" in t
    assert "象限" in t
