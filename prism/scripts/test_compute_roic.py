"""#3 — _compute_roic 金融业失真守卫测试（纯函数，无需 DB）

券商/银行客户资金并表 → 投入资本(总资产−流动负债)被净掉，残值极小致 ROIC 爆表
(如富途 2858%)。守卫：ic/ta<10% 或 |roic|>500% → roic=None、distorted=True。
"""
from prism.scripts.financial_data import _compute_roic


def test_normal_company_roic_ok():
    """常规工业：ic 占总资产 70%，ROIC 正常，不失真。"""
    # oi=100, ni=80, pretax=100 → tax_rate=0.2; ic=1000-300=700; ic/ta=0.7
    roic, distorted = _compute_roic(oi=100, ni=80, pretax=100, ta=1000, cl=300)
    assert distorted is False
    assert roic == round(100 * 0.8 / 700 * 100, 2)  # ≈ 11.43


def test_broker_client_funds_distortion_suppressed():
    """券商：巨额客户资产并表，ic 占比仅 1% → 失真，roic 置 None。"""
    roic, distorted = _compute_roic(oi=100, ni=80, pretax=100, ta=100_000, cl=99_000)
    assert distorted is True
    assert roic is None


def test_absurd_roic_backstop():
    """ic/ta 未触发(=0.1)，但 |roic|>500% 的爆表值由 backstop 拦下。"""
    # tax_rate=0; ic=1000-900=100; ic/ta=0.10(不<0.10); roic=600*1/100*100=600 >500
    roic, distorted = _compute_roic(oi=600, ni=600, pretax=600, ta=1000, cl=900)
    assert distorted is True
    assert roic is None


def test_missing_inputs_returns_none_not_distorted():
    """缺数据 → (None, False)：是数据缺失，不是失真。"""
    assert _compute_roic(oi=None, ni=80, pretax=100, ta=1000, cl=300) == (None, False)
    assert _compute_roic(oi=100, ni=80, pretax=0, ta=1000, cl=300) == (None, False)
    assert _compute_roic(oi=100, ni=80, pretax=100, ta=None, cl=300) == (None, False)


def test_non_positive_invested_capital_unavailable_not_distorted():
    """ic<=0（流动负债>总资产）→ (None, False)：算不出，但不标失真。"""
    roic, distorted = _compute_roic(oi=100, ni=80, pretax=100, ta=100, cl=200)
    assert roic is None
    assert distorted is False


def test_default_tax_rate_when_ni_missing():
    """ni 缺失时退回默认税率 0.15。"""
    # ic=700, ic/ta=0.7; roic=100*(1-0.15)/700*100
    roic, distorted = _compute_roic(oi=100, ni=None, pretax=100, ta=1000, cl=300)
    assert distorted is False
    assert roic == round(100 * 0.85 / 700 * 100, 2)
