import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent


def test_notebook_is_executed_and_has_markdown_before_code():
    notebook=json.loads((ROOT/"notebooks/dashboard.ipynb").read_text())
    for index,cell in enumerate(notebook["cells"]):
        if cell["cell_type"]=="code":
            assert index and notebook["cells"][index-1]["cell_type"]=="markdown"
            assert cell["execution_count"] is not None and cell["outputs"]


def test_required_reports_and_visuals_exist():
    reports=["profile.md","bronze_report.md","dq_report.md","load_report.md","stream_report.md","dw_report.md","marts_report.md","failure_tests.md"]
    assert all((ROOT/"outputs"/name).exists() for name in reports)
    assert len(list((ROOT/"outputs/dashboard").glob("*.png")))==5
