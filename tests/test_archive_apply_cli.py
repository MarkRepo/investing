import json
from argparse import Namespace

from scripts import ingest_qa as qa


def _writes(action="append"):
    return {
        "source_id": "src-001",
        "writes": [
            {
                "fact_id": "fact-001",
                "fact_payload": {"fact_id": "fact-001", "fact_text": "事实"},
                "final_targets": [
                    {
                        "archive_path": "archive/layer8/company/SSE_600519/moat.jsonl",
                        "action": action,
                    }
                ],
            }
        ],
    }


def test_check_archive_writes_rejects_update_action():
    warnings = qa.check_archive_writes_shape(_writes(action="update"))

    assert warnings[0]["rule"] == "archive_invalid_action"
    assert warnings[0]["severity"] == "error"


def test_cmd_archive_apply_appends_fact_payload(tmp_path):
    pending = tmp_path / "archive-writes-src-001.json"
    pending.write_text(json.dumps(_writes()), encoding="utf-8")

    rc = qa.cmd_archive_apply(Namespace(pending=str(pending), base=str(tmp_path)))

    assert rc == 0
    target = tmp_path / "archive" / "layer8" / "company" / "SSE_600519" / "moat.jsonl"
    rows = target.read_text(encoding="utf-8").splitlines()
    assert json.loads(rows[0]) == {"fact_id": "fact-001", "fact_text": "事实"}
