"""macro 输入登记表（macro_inputs.yaml）CRUD + 机制纪律 validator。零 LLM。"""
import shutil
import tempfile
from pathlib import Path

import pytest

from prism.scripts import macro_registry as mr

SLUG = "global-macro-rates-liquidity"
VARIANT = "opus4.8"


@pytest.fixture
def reg_env(monkeypatch):
    tmpdir = Path(tempfile.mkdtemp())
    monkeypatch.setattr("prism.scripts.macro_registry._PRISM_ROOT", tmpdir)
    (tmpdir / "topics" / SLUG / VARIANT).mkdir(parents=True)
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


def test_create_and_read_roundtrip(reg_env):
    path = mr.create_registry(SLUG, VARIANT)
    assert path.exists()
    data = mr.read_registry(SLUG, VARIANT)
    assert data["slug"] == SLUG
    assert data["variant"] == VARIANT
    assert data["inputs"] == []
