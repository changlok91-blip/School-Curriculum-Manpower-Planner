import csv
from decimal import Decimal
from pathlib import Path
import subprocess
import sys

import pytest

from curriculum_planner.loading import DataLoadError, load_data
from curriculum_planner.workload.comparison import compare_period_scenarios
from curriculum_planner.workload.loading import load_workload_data
from curriculum_planner.workload.reporting import export_workload_results


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
PERIODS = ["p15", "p20", "p30", "p35"]


def write_inputs(path, *, minimum="150", duration="22.5"):
    (path / "curriculum_requirements.csv").write_text(
        "academic_year,level,subject_id,minimum_weekly_minutes\n"
        f"2027,Sec3,BIO,{minimum}\n", encoding="utf-8",
    )
    (path / "period_scenarios.csv").write_text(
        "period_scenario_id,scenario_name,period_duration_minutes\n"
        f"custom,Custom duration,{duration}\n", encoding="utf-8",
    )


def read_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def run_cli(*arguments):
    return subprocess.run(
        [sys.executable, "-m", "curriculum_planner", "workload", *map(str, arguments)],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )


def test_loader_supports_minimal_csv_contract_and_fractional_minutes(tmp_path):
    write_inputs(tmp_path, minimum="150.1")
    data = load_workload_data(tmp_path)
    assert data.curriculum_requirements[0].minimum_weekly_minutes == Decimal("150.1")
    assert data.curriculum_requirements[0].requirement_scope == "component"
    assert data.period_scenarios[0].period_duration_minutes == Decimal("22.5")


def test_loader_requires_both_input_files(tmp_path):
    with pytest.raises(DataLoadError):
        load_workload_data(tmp_path)


def test_loader_reports_missing_required_columns(tmp_path):
    write_inputs(tmp_path)
    (tmp_path / "curriculum_requirements.csv").write_text(
        "academic_year,level,minimum_weekly_minutes\n2027,Sec3,150\n", encoding="utf-8",
    )
    with pytest.raises(DataLoadError):
        load_workload_data(tmp_path)


def test_loader_does_not_silently_accept_nonnumeric_minutes(tmp_path):
    write_inputs(tmp_path, minimum="one hundred")
    with pytest.raises(DataLoadError):
        load_workload_data(tmp_path)


def test_loader_rejects_missing_subject_identifier(tmp_path):
    write_inputs(tmp_path)
    (tmp_path / "curriculum_requirements.csv").write_text(
        "academic_year,level,subject_id,minimum_weekly_minutes\n2027,Sec3,,150\n",
        encoding="utf-8",
    )
    with pytest.raises(DataLoadError):
        load_workload_data(tmp_path)


def test_exports_preserve_unknown_values_and_partial_comparison(tmp_path):
    results = compare_period_scenarios(load_data(DATA_DIR), load_workload_data(DATA_DIR), PERIODS)
    paths = export_workload_results(results, tmp_path)
    assert {path.name for path in paths} == {
        "teaching_group_workload.csv", "subject_workload_summary.csv", "block_workload_summary.csv",
        "cohort_workload_summary.csv", "period_duration_comparison.csv", "data_completeness.csv",
        "validation_issues.csv",
    }
    comparison = read_csv(tmp_path / "period_duration_comparison.csv")
    assert [int(row["known_required_teacher_periods"]) for row in comparison] == [40, 32, 20, 20]
    assert [Decimal(row["known_scheduled_teacher_minutes"]) for row in comparison] == [600, 640, 600, 700]
    assert all(row["total_required_teacher_periods"] == "" for row in comparison)
    assert all(row["uncalculated_group_count"] == "66" for row in comparison)
    detail = read_csv(tmp_path / "teaching_group_workload.csv")
    assert len(detail) == 280
    assert sum(row["required_periods"] == "" for row in detail) == 264
    assert len(read_csv(tmp_path / "data_completeness.csv")) == 264
    before = {path.name: path.read_bytes() for path in paths}
    export_workload_results(results, tmp_path)
    assert {path.name: path.read_bytes() for path in paths} == before


def test_cli_lists_scenarios_and_flags_missing_historical_requirements():
    listed = run_cli("list")
    assert listed.returncode == 0, listed.stderr
    assert all(identifier in listed.stdout for identifier in PERIODS)
    validation = run_cli("validate")
    assert validation.returncode != 0
    assert "missing" in (validation.stdout + validation.stderr).lower()


def test_cli_partial_run_and_comparison_remain_useful():
    result = run_cli("run", "p30", "--teaching-scenario", "separate_science")
    assert result.returncode == 0, result.stderr
    assert "partial" in result.stdout.lower()
    assert "66" in result.stdout
    comparison = run_cli("compare", *PERIODS)
    assert comparison.returncode == 0, comparison.stderr
    assert "640" in comparison.stdout
    assert "700" in comparison.stdout


def test_cli_exports_reports_and_rejects_unknown_periods(tmp_path):
    exported = run_cli("export", *PERIODS, "--output-dir", tmp_path)
    assert exported.returncode == 0, exported.stderr
    assert len(read_csv(tmp_path / "period_duration_comparison.csv")) == 4
    invalid = run_cli("run", "unknown")
    assert invalid.returncode != 0
    assert "traceback" not in (invalid.stdout + invalid.stderr).lower()
