import csv
from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"


def run_cli(*arguments):
    return subprocess.run(
        [sys.executable, "-m", "curriculum_planner", *map(str, arguments)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_validate_command_succeeds():
    result = run_cli("validate", "--data-dir", DATA_DIR)
    assert result.returncode == 0, result.stderr


def test_calculate_command_names_provisional_group_instances():
    result = run_cli("calculate", "--data-dir", DATA_DIR)
    assert result.returncode == 0, result.stderr
    assert "subject-component group instance" in result.stdout.lower()
    assert "70" in result.stdout
    assert "Science" in result.stdout


def test_export_command_writes_details_and_all_summary_levels(tmp_path):
    output_dir = tmp_path / "exports"
    result = run_cli("export", "--data-dir", DATA_DIR, "--output-dir", output_dir)
    assert result.returncode == 0, result.stderr
    with (output_dir / "group_results.csv").open(encoding="utf-8-sig", newline="") as stream:
        detail = list(csv.DictReader(stream))
    with (output_dir / "summaries.csv").open(encoding="utf-8-sig", newline="") as stream:
        summaries = list(csv.DictReader(stream))
    assert len(detail) == 44
    assert sum(int(row["groups_required"]) for row in detail) == 70
    assert {row["summary_type"] for row in summaries} == {"subject", "band", "block", "cohort"}
    cohort = next(row for row in summaries if row["summary_type"] == "cohort")
    assert cohort["groups_required"] == "70"
    assert cohort["unique_students"] == "260"


def test_invalid_input_returns_failure_without_traceback(tmp_path):
    result = run_cli("validate", "--data-dir", tmp_path)
    assert result.returncode != 0
    assert "traceback" not in (result.stdout + result.stderr).lower()
