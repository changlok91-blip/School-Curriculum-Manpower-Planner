from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest


APP = Path(__file__).resolve().parents[1] / "streamlit_app.py"


def test_web_baseline_and_hard_limits(monkeypatch, tmp_path):
    # Data paths must work even when the launch directory differs from the repo.
    monkeypatch.chdir(tmp_path)
    app = AppTest.from_file(str(APP)).run(timeout=20)
    assert not app.exception
    assert not app.error
    assert [metric.value for metric in app.metric] == ["260", "70", "737"]
    assert len(app.dataframe[0].value) == 44
    block_summary = app.dataframe[2].value
    assert dict(zip(block_summary.block_id, block_summary.groups_required)) == {"A": 27, "B": 43}

    app.sidebar.checkbox[0].uncheck().run()
    assert not app.exception
    assert [metric.value for metric in app.metric] == ["260", "67", "737"]
