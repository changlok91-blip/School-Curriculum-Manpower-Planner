from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest


APP = Path(__file__).resolve().parents[1] / "streamlit_app.py"


def workload_app():
    app = AppTest.from_file(str(APP)).run(timeout=20)
    app.sidebar.radio[0].set_value("Curriculum workload (Component 3)").run()
    return app


def test_web_workload_biology_comparison_and_unknown_totals():
    app = workload_app()
    assert not app.exception
    assert not app.error
    assert [metric.value for metric in app.metric] == ["20", "600", "4", "66"]
    detail = app.dataframe[0].value
    assert len(detail) == 70
    assert detail.teaching_group_id.nunique() == 70
    assert sum(detail.calculation_status == "calculated") == 4
    cohort = app.dataframe[3].value.iloc[0]
    assert cohort.total_required_teacher_periods is None
    assert cohort.total_scheduled_teacher_minutes is None
    comparison = app.dataframe[4].value
    assert list(comparison.known_required_teacher_periods) == [40, 32, 20, 20]
    assert list(comparison.known_scheduled_teacher_minutes) == [600, 640, 600, 700]
    assert list(comparison.uncalculated_group_count) == [66] * 4
    assert len(app.dataframe[5].value) == 66
    assert len(app.get("download_button")) == 7
    assert any("not official MOE" in warning.value for warning in app.warning)
    assert any("known subtotals" in warning.value for warning in app.warning)

    app.sidebar.selectbox[1].set_value("p20").run()
    assert not app.exception
    assert [metric.value for metric in app.metric] == ["32", "640", "4", "66"]


def test_web_window_context_retains_ids_without_changing_workload():
    app = workload_app()
    app.sidebar.checkbox[1].check().run()
    assert not app.exception
    assert not app.error
    assert [metric.value for metric in app.metric] == ["20", "600", "4", "66"]
    detail = app.dataframe[0].value
    assert set(detail.teaching_scenario_id) == {"simultaneous_science"}
    assert sum(detail.window_id != "") == 4
    assert set(detail.loc[detail.window_id != "", "window_id"]) == {"SCIENCE_ALL"}
    app.sidebar.selectbox[2].set_value("separate_science").run()
    assert not app.exception
    assert [metric.value for metric in app.metric] == ["20", "600", "4", "66"]
    detail = app.dataframe[0].value
    assert set(detail.loc[detail.window_id != "", "window_id"]) == {"SCIENCE_A", "SCIENCE_B"}


def test_web_workload_load_errors_are_shown(monkeypatch):
    from curriculum_planner.workload import loading
    from curriculum_planner.loading import DataLoadError

    def missing_file(path):
        raise DataLoadError("curriculum_requirements.csv: missing input")

    monkeypatch.setattr(loading, "load_workload_data", missing_file)
    # Workload web imports the loader once, so patch its binding too if already imported.
    import curriculum_planner.workload.web as web
    monkeypatch.setattr(web, "load_workload_data", missing_file)
    app = workload_app()
    assert not app.exception
    assert "missing input" in app.error[0].value
    assert len(app.metric) == 0
