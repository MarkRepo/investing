"""Bundle v3 scope helpers."""

VALID_SCOPE_TYPES = {"industry", "arena", "company", "brand", "cross_cutting"}


def split_scope(scope: str) -> tuple[str, str]:
    """
    'industry/cn-pet-industry' -> ('industry', 'cn-pet-industry')
    'company/SSE_603011'        -> ('company', 'SSE_603011')
    'arena/cn-fusion-magnet'    -> ('arena', 'cn-fusion-magnet')
    'brand:玛氏'                  -> ('brand', '玛氏')
    'cross_cutting'              -> ('cross_cutting', '')
    """
    if scope == "cross_cutting":
        return "cross_cutting", ""
    if scope.startswith("brand:"):
        ref = scope[len("brand:"):]
        if not ref:
            raise ValueError(f"empty brand ref: {scope!r}")
        return "brand", ref
    for prefix in ("industry/", "arena/", "company/"):
        if scope.startswith(prefix):
            ref = scope[len(prefix):]
            if not ref:
                raise ValueError(f"empty ref: {scope!r}")
            return prefix.rstrip("/"), ref
    raise ValueError(f"invalid scope: {scope!r}")


def join_scope(scope_type: str, scope_ref: str) -> str:
    if scope_type == "cross_cutting":
        return "cross_cutting"
    if scope_type == "brand":
        return f"brand:{scope_ref}"
    if scope_type in {"industry", "arena", "company"}:
        return f"{scope_type}/{scope_ref}"
    raise ValueError(f"invalid scope_type: {scope_type!r}")


def is_valid_scope(scope: str) -> bool:
    try:
        split_scope(scope)
        return True
    except ValueError:
        return False
