import csv
import json
from pathlib import Path
import subprocess
import sys

from curriculum_planner.calculation import calculate_groups
from curriculum_planner.loading import load_data
from curriculum_planner.scheduling.calculation import compare_scenarios
from curriculum_planner.scheduling.groups import generate_teaching_groups
from curriculum_planner.scheduling.loading import load_scheduling
from curriculum_planner.scheduling.reporting import export_scenario_results


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
SCENARIOS = ["simultaneous_science", "separate_science"]


def run_cli(*arguments):
    return subprocess.run(
        [sys.executable, "-m", "curriculum_planner", "scenarios", *map(str, arguments)],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )


def read_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def test_export_reports_have_baseline_results_and_unscheduled_inventory(tmp_path):
    groups = generate_teaching_groups(calculate_groups(load_data(DATA_DIR)))
    results = compare_scenarios(groups, load_scheduling(DATA_DIR), SCENARIOS)
    paths = export_scenario_results(results, groups, tmp_path)
    assert {path.name for path in paths} == {
        "window_summary.csv", "resource_pool_summary.csv", "unscheduled_groups.csv",
        "scenario_comparison.csv", "teaching_groups.csv",
    }
    pools = read_csv(tmp_path / "resource_pool_summary.csv")
    assert [int(row["peak_simultaneous_demand"]) for row in pools] == [4, 2]
    assert [int(row["maximum_shortage"]) for row in pools] == [2, 0]
    comparison = read_csv(tmp_path / "scenario_comparison.csv")
    assert [row["unscheduled_group_instances"] for row in comparison] == ["66", "66"]
    assert [json.loads(row["peak_concurrent_demand_by_pool"]) for row in comparison] == [
        {"BIOLOGY": 4}, {"BIOLOGY": 2},
    ]
    assert all(row["full_timetable_feasibility"] == "not yet assessed" for row in comparison)
    unscheduled = read_csv(tmp_path / "unscheduled_groups.csv")
    assert len(unscheduled) == 132
    assert len(read_csv(tmp_path / "teaching_groups.csv")) == 70
    # Repeated exports replace the same report set and keep deterministic content.
    before = {path.name: path.read_bytes() for path in paths}
    export_scenario_results(results, groups, tmp_path)
    assert {path.name: path.read_bytes() for path in paths} == before


def test_cli_lists_and_validates_scenarios():
    listed = run_cli("list")
    assert listed.returncode == 0, listed.stderr
    assert all(identifier in listed.stdout for identifier in SCENARIOS)
    validated = run_cli("validate")
    assert validated.returncode == 0, validated.stderr


def test_cli_runs_and_compares_with_explicit_limitations():
    result = run_cli("run", "separate_science")
    assert result.returncode == 0, result.stderr
    assert "66" in result.stdout
    assert "unverified" in result.stdout.lower()
    assert "not yet assessed" in result.stdout.lower()
    comparison = run_cli("compare", *SCENARIOS)
    assert comparison.returncode == 0, comparison.stderr
    assert all(identifier in comparison.stdout for identifier in SCENARIOS)
    assert "Simultaneous Science groups" in comparison.stdout
    assert "Separate Science windows" in comparison.stdout


def test_cli_exports_comparison_and_generated_group_ids(tmp_path):
    exported = run_cli("export", *SCENARIOS, "--output-dir", tmp_path / "reports")
    assert exported.returncode == 0, exported.stderr
    assert len(read_csv(tmp_path / "reports" / "scenario_comparison.csv")) == 2
    inventory = tmp_path / "teaching_groups.csv"
    generated = run_cli("groups", "--output", inventory)
    assert generated.returncode == 0, generated.stderr
    assert len(read_csv(inventory)) == 70


def test_cli_rejects_unknown_scenario_and_insufficient_comparison():
    for arguments in [("run", "missing"), ("compare", SCENARIOS[0])]:
        result = run_cli(*arguments)
        assert result.returncode != 0
        assert "traceback" not in (result.stdout + result.stderr).lower()
