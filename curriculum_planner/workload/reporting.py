"""Export workload units and unknown totals with an explicit CSV contract."""

import csv
from dataclasses import asdict, fields
from pathlib import Path

from ..reporting import _table
from .models import CompletenessRow, GroupWorkload, WorkloadSummary


ASSESSMENT_LIMITS = (
    "Known subtotals cover calculated groups only; blank total fields mean the full workload is unknown.",
    "Teacher-periods are summed teaching commitments, not elapsed school timetable periods.",
    "Abstract teaching windows retain concurrency context; calculated periods have not been placed in a weekly timetable.",
    "No teacher deployment, workload limits, staffing sufficiency or timetable feasibility is assessed.",
    "Curriculum requirements retain their supplied source labels; synthetic examples are not official MOE requirements.",
)


def _write_csv(path, row_type, rows):
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=[field.name for field in fields(row_type)])
        writer.writeheader()
        writer.writerows(asdict(row) for row in rows)


def export_workload_results(results, output_dir):
    """Write all report schemas, including headers for empty detail/error lists."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    summaries = [row for result in results for row in result.summaries]
    reports = (
        ("teaching_group_workload.csv", GroupWorkload,
         [row for result in results for row in result.group_workload]),
        ("subject_workload_summary.csv", WorkloadSummary,
         [row for row in summaries if row.scope == "subject"]),
        ("block_workload_summary.csv", WorkloadSummary,
         [row for row in summaries if row.scope in {"block", "band"}]),
        ("cohort_workload_summary.csv", WorkloadSummary,
         [row for row in summaries if row.scope == "level"]),
        ("period_duration_comparison.csv", WorkloadSummary,
         [row for row in summaries if row.scope == "level"]),
        ("data_completeness.csv", CompletenessRow,
         [row for result in results for row in result.completeness]),
    )
    paths = []
    for filename, row_type, rows in reports:
        path = output_dir / filename
        _write_csv(path, row_type, rows)
        paths.append(path)
    issues_path = output_dir / "validation_issues.csv"
    with issues_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=["period_scenario_id", "issue"])
        writer.writeheader()
        for result in results:
            writer.writerows({"period_scenario_id": result.scenario.period_scenario_id, "issue": issue}
                            for issue in result.validation_issues)
    paths.append(issues_path)
    return paths


def format_comparison(results):
    rows = [row for result in results for row in result.summaries if row.scope == "level"]
    return "\n".join([
        "Period-duration workload comparison — known subtotals, not staffing sufficiency",
        _table(
            ["Scenario ID", "Scenario", "Year", "Level", "Minutes/period", "Groups calculated/total",
             "Known teacher-periods", "Known scheduled teacher-minutes", "Known minimum teacher-minutes",
             "Known excess teacher-minutes", "Full teacher-period total", "Completeness"],
            [[row.period_scenario_id, row.scenario_name, str(row.academic_year), row.level, str(row.period_duration_minutes),
              f"{row.calculated_group_count}/{row.teaching_group_count}",
              str(row.known_required_teacher_periods), str(row.known_scheduled_teacher_minutes),
              str(row.known_minimum_teacher_minutes), str(row.known_excess_teacher_minutes),
              str(row.total_required_teacher_periods) if row.total_required_teacher_periods is not None else "unknown",
              row.assessment_completeness] for row in rows],
        ),
        *(f"- {limit}" for limit in ASSESSMENT_LIMITS),
    ])


def format_workload(result):
    source_labels = sorted({row.requirement_source for row in result.group_workload if row.requirement_source})
    sections = [
        f"Period scenario: {result.scenario.scenario_name} ({result.scenario.period_scenario_id})",
        f"Requirement sources: {'; '.join(source_labels) if source_labels else 'none available'}",
        format_comparison([result]),
        f"Groups with missing or invalid curriculum time: {len(result.completeness)}",
    ]
    if result.validation_issues:
        sections.extend(["Input validation issues:", *(f"- {issue}" for issue in result.validation_issues)])
    sections.extend([
        "Subject and block/band workload (known subtotals):",
        _table(
            ["Scope", "Year", "Level", "Block", "Band", "Subject", "Groups calculated/total",
             "Teacher-periods", "Scheduled teacher-minutes", "Completeness"],
            [[row.scope, str(row.academic_year), row.level, row.block_id, row.band_id, row.subject_name,
              f"{row.calculated_group_count}/{row.teaching_group_count}",
              str(row.known_required_teacher_periods), str(row.known_scheduled_teacher_minutes),
              row.assessment_completeness] for row in result.summaries if row.scope != "level"],
        ),
    ])
    return "\n".join(sections)
