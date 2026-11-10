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


def test_web_concurrency_scenarios_and_comparison():
    app = AppTest.from_file(str(APP)).run(timeout=20)
    app.sidebar.radio[0].set_value("Concurrency scenarios (Component 2)").run()
    assert not app.exception
    assert [metric.value for metric in app.metric] == ["4", "66", "1", "1"]
    assert app.dataframe[0].value.iloc[0].peak_simultaneous_demand == 4
    assert app.dataframe[0].value.iloc[0].maximum_shortage == 2
    assert len(app.dataframe[2].value) == 66
    assert len(app.error) == 1
    assert "violated" in app.error[0].value

    app.sidebar.selectbox[0].set_value("separate_science").run()
    assert not app.exception
    assert not app.error
    assert [metric.value for metric in app.metric] == ["4", "66", "2", "0"]
    assert app.dataframe[0].value.iloc[0].peak_simultaneous_demand == 2
    comparison = app.dataframe[3].value
    assert list(comparison.unscheduled_group_instances) == [66, 66]
    assert set(comparison.full_timetable_feasibility) == {"not yet assessed"}
    assert len(app.get("download_button")) == 5
    assert any("Partial assessment" in item.value for item in app.warning)

    app.sidebar.checkbox[0].uncheck().run()
    assert not app.exception
    assert [metric.value for metric in app.metric] == ["4", "63", "2", "0"]


def test_web_scenario_validation_errors_are_displayed(monkeypatch):
    from curriculum_planner.scheduling import loading
    data = loading.load_scheduling(APP.parent / "data")
    data.assignments.append(data.assignments[0])
    monkeypatch.setattr(loading, "load_scheduling", lambda path: data)
    app = AppTest.from_file(str(APP)).run(timeout=20)
    app.sidebar.radio[0].set_value("Concurrency scenarios (Component 2)").run()
    assert not app.exception
    assert "duplicate placement" in app.error[0].value.lower()
    assert len(app.metric) == 0
