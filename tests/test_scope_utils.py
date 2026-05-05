import pytest
from app.io.scope_utils import split_scope, join_scope, is_valid_scope


class TestSplitScope:
    def test_industry(self):
        assert split_scope("industry/cn-pet-industry") == ("industry", "cn-pet-industry")

    def test_company(self):
        assert split_scope("company/SSE_603011") == ("company", "SSE_603011")

    def test_arena(self):
        assert split_scope("arena/cn-fusion-magnet") == ("arena", "cn-fusion-magnet")

    def test_brand(self):
        assert split_scope("brand:玛氏") == ("brand", "玛氏")

    def test_cross_cutting(self):
        assert split_scope("cross_cutting") == ("cross_cutting", "")

    def test_empty_industry_ref_raises(self):
        with pytest.raises(ValueError, match="empty ref"):
            split_scope("industry/")

    def test_empty_brand_ref_raises(self):
        with pytest.raises(ValueError, match="empty brand ref"):
            split_scope("brand:")

    def test_invalid_scope_raises(self):
        with pytest.raises(ValueError, match="invalid scope"):
            split_scope("garbage")


class TestJoinScope:
    def test_industry(self):
        assert join_scope("industry", "cn-pet-industry") == "industry/cn-pet-industry"

    def test_company(self):
        assert join_scope("company", "SSE_603011") == "company/SSE_603011"

    def test_arena(self):
        assert join_scope("arena", "cn-fusion-magnet") == "arena/cn-fusion-magnet"

    def test_brand(self):
        assert join_scope("brand", "玛氏") == "brand:玛氏"

    def test_cross_cutting(self):
        assert join_scope("cross_cutting", "") == "cross_cutting"

    def test_invalid_scope_type_raises(self):
        with pytest.raises(ValueError):
            join_scope("unknown", "ref")


class TestIsValidScope:
    def test_valid_industry(self):
        assert is_valid_scope("industry/cn-pet-industry") is True

    def test_valid_company(self):
        assert is_valid_scope("company/SSE_603011") is True

    def test_valid_arena(self):
        assert is_valid_scope("arena/cn-fusion-magnet") is True

    def test_valid_brand(self):
        assert is_valid_scope("brand:玛氏") is True

    def test_valid_cross_cutting(self):
        assert is_valid_scope("cross_cutting") is True

    def test_invalid_garbage(self):
        assert is_valid_scope("garbage") is False

    def test_invalid_empty_brand(self):
        assert is_valid_scope("brand:") is False

    def test_invalid_empty_industry_ref(self):
        assert is_valid_scope("industry/") is False


class TestRoundTrip:
    def test_roundtrip_industry(self):
        scope = "industry/cn-nuclear-fusion"
        assert join_scope(*split_scope(scope)) == scope

    def test_roundtrip_brand(self):
        scope = "brand:玛氏宝路"
        assert join_scope(*split_scope(scope)) == scope

    def test_roundtrip_cross_cutting(self):
        scope = "cross_cutting"
        assert join_scope(*split_scope(scope)) == scope
