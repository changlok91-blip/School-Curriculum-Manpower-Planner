"""Human-readable and CSV concurrency reports, with explicit assessment limits."""

import csv
from dataclasses import asdict, fields
from pathlib import Path

from ..reporting import _table
from .models import (
    PoolSummary, ScenarioComparison, ScenarioResult, TeachingGroup,
    UnscheduledGroup, WindowSummary,
)


ASSESSMENT_LIMITS = (
    "Student-level timetable compatibility remains unverified: components may share students.",
    "Cross-subject teacher sharing is not validated; pool capacity must not double-count real teachers.",
    "Total weekly teaching capacity and individual teacher availability are not assessed.",
    "Full timetable feasibility is not yet assessed: abstract windows must eventually fit a finite school timetable.",
)


def _write_csv(path: Path, row_type: type, rows: list) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=[field.name for field in fields(row_type)])
        writer.writeheader()
        writer.writerows(asdict(row) for row in rows)


def export_teaching_groups(groups: list[TeachingGroup], output_path: str | Path) -> Path:
    """Save generated identifiers for use in editable assignment CSV files."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_csv(path, TeachingGroup, groups)
    return path


def format_teaching_groups(groups: list[TeachingGroup]) -> str:
    """Show the group inventory without implying per-group student allocations."""
    return "\n".join([
        f"Generated subject-component group instances: {len(groups)}",
        _table(
            ["Teaching group ID", "Year", "Level", "Block", "Band", "Subject", "Group number"],
            [[group.teaching_group_id, str(group.academic_year), group.level,
              group.block_id, group.band_id, group.subject_name, str(group.group_number)]
             for group in groups],
        ),
        "Group ordinals identify instances; no actual distribution of students among groups is established.",
    ])


def export_scenario_results(
    results: list[ScenarioResult], groups: list[TeachingGroup], output_dir: str | Path,
) -> list[Path]:
    """Export all report levels and the generated inventory, even for empty rows.

    Window rows describe a block/band slice. `group_count` counts that slice;
    `concurrent_demand` and `shortage` describe the entire pool in that window
    and repeat across slices. Do not sum those repeated pool/window values.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    reports = (
        ("window_summary.csv", WindowSummary,
         [row for result in results for row in result.window_summary]),
        ("resource_pool_summary.csv", PoolSummary,
         [row for result in results for row in result.resource_pool_summary]),
        ("unscheduled_groups.csv", UnscheduledGroup,
         [row for result in results for row in result.unscheduled_groups]),
        ("scenario_comparison.csv", ScenarioComparison,
         [result.comparison for result in results]),
        ("teaching_groups.csv", TeachingGroup, groups),
    )
    paths = []
    for filename, row_type, rows in reports:
        path = output_dir / filename
        _write_csv(path, row_type, rows)
        paths.append(path)
    return paths


def format_scenario(result: ScenarioResult) -> str:
    """Render one scenario without claiming cohort or timetable feasibility."""
    comparison = result.comparison
    sections = [
        f"Scenario: {result.scenario.scenario_name} ({result.scenario.scenario_id})",
        result.scenario.description,
        f"Teaching windows: {comparison.teaching_windows} configured; {comparison.windows_used} used.",
        f"Subject-component group instances: {comparison.scheduled_group_instances} scheduled; "
        f"{comparison.unscheduled_group_instances} unscheduled / not yet assessed "
        f"(total {comparison.total_group_instances}).",
        f"Assessment completeness: {comparison.assessment_completeness}.",
        "\nConcurrent demand by teaching window and pool:",
    ]
    # Pool/window totals appear once in this compact view. The detailed CSV
    # retains the block and band slices as well as their teaching-group IDs.
    unique_windows = {}
    for row in result.window_summary:
        key = row.window_id, row.teacher_pool_id
        unique_windows[key] = row
    sections.append(_table(
        ["Window", "Resource pool", "Demand", "Available", "Shortage"],
        [[row.window_name, row.pool_name, str(row.concurrent_demand),
          str(row.available_teacher_count), str(row.shortage)]
         for _, row in sorted(unique_windows.items())],
    ))
    sections.extend([
        "\nResource pool peaks (maximum across windows, not their sum):",
        _table(
            ["Resource pool", "Available", "Peak demand", "Maximum shortage", "Status"],
            [[row.pool_name, str(row.available_teacher_count),
              str(row.peak_simultaneous_demand), str(row.maximum_shortage), row.concurrency_status]
             for row in result.resource_pool_summary],
        ),
        f"Concurrency violations: {comparison.concurrency_violations} pool/window combinations.",
        f"Concurrency status: {comparison.concurrency_status}.",
        "\nAssessment limits:",
        *(f"- {limit}" for limit in ASSESSMENT_LIMITS),
    ])
    return "\n".join(section for section in sections if section)


def format_comparison(results: list[ScenarioResult]) -> str:
    """Render scenario differences and preserve the limits of partial scheduling."""
    return "\n".join([
        "Scenario comparison — abstract teaching-window concurrency only",
        _table(
            ["Scenario ID", "Scenario", "Windows configured/used", "Scheduled", "Unscheduled",
             "Peak demand by pool", "Violations", "Assessment completeness"],
            [[result.scenario.scenario_id, result.scenario.scenario_name,
              f"{result.comparison.teaching_windows}/{result.comparison.windows_used}",
              str(result.comparison.scheduled_group_instances),
              str(result.comparison.unscheduled_group_instances),
              result.comparison.peak_concurrent_demand_by_pool,
              str(result.comparison.concurrency_violations),
              result.comparison.assessment_completeness] for result in results],
        ),
        "Violations count pool/window combinations whose demand exceeds availability.",
        "Unscheduled groups have not yet been assessed; no whole-cohort feasibility is established.",
        *(f"- {limit}" for limit in ASSESSMENT_LIMITS),
    ])
