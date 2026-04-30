import json
from argparse import Namespace

from scripts import ingest_qa as qa


def _pending(path):
    rows = [
        {
            "candidate_id": "arena-001",
            "slug": "cn-power-cable-polymer-material",
            "name": "电缆高分子材料",
            "battleground_focus": "高压电缆材料国产化",
            "core_participants": ["SSE_600522"],
            "merge_suggestions": [],
        }
    ]
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")


def test_arena_approve_creates_skeleton_and_archives_pending(tmp_path):
    pending = tmp_path / "data" / "pending" / "arenas-src-001.jsonl"
    pending.parent.mkdir(parents=True)
    _pending(pending)

    rc = qa.cmd_arena_approve(Namespace(pending=str(pending), base=str(tmp_path), id="arena-001"))

    assert rc == 0
    arena_dir = tmp_path / "arenas" / "cn-power-cable-polymer-material"
    assert (arena_dir / "name.yaml").exists()
    assert (arena_dir / "battleground_focus.md").read_text(encoding="utf-8") == "高压电缆材料国产化\n"
    assert "SSE_600522" in (arena_dir / "core_participants.yaml").read_text(encoding="utf-8")
    assert not pending.exists()
    assert (tmp_path / "data" / "pending" / "archive" / "arenas-src-001.jsonl").exists()


def test_arena_reject_archives_pending_with_rejected_marker(tmp_path):
    pending = tmp_path / "data" / "pending" / "arenas-src-001.jsonl"
    pending.parent.mkdir(parents=True)
    _pending(pending)

    rc = qa.cmd_arena_reject(Namespace(pending=str(pending), base=str(tmp_path), id="arena-001"))

    assert rc == 0
    archived = tmp_path / "data" / "pending" / "archive" / "arenas-src-001.jsonl"
    row = json.loads(archived.read_text(encoding="utf-8").splitlines()[0])
    assert row["candidate_id"] == "arena-001"
    assert row["decision"] == "rejected"


def test_arena_merge_archives_pending_with_target(tmp_path):
    pending = tmp_path / "data" / "pending" / "arenas-src-001.jsonl"
    pending.parent.mkdir(parents=True)
    _pending(pending)

    rc = qa.cmd_arena_merge(Namespace(pending=str(pending), base=str(tmp_path), id="arena-001", target_slug="existing-arena"))

    assert rc == 0
    archived = tmp_path / "data" / "pending" / "archive" / "arenas-src-001.jsonl"
    row = json.loads(archived.read_text(encoding="utf-8").splitlines()[0])
    assert row["decision"] == "merged"
    assert row["merge_target"] == "existing-arena"
