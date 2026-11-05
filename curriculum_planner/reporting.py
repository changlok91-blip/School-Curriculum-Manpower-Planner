"""Aggregate computed group instances and render/export their results."""

import csv
from collections import defaultdict
from dataclasses import asdict, fields
from pathlib import Path

from .models import Dataset, GroupResult, SummaryRow


def summarize(dataset: Dataset, results: list[GroupResult]) -> list[SummaryRow]:
    """Sum already computed groups, never regroup pupils across blocks or bands.

    Unique populations are known only for blocks and cohorts. Component totals
    can count a pupil more than once, including within a single band.
    """
    buckets = defaultdict(list)
    populations = defaultdict(int)
    for block in dataset.blocks:
        block_key = ("block", block.academic_year, block.level, block.block_id, "", "", "")
        cohort_key = ("cohort", block.academic_year, block.level, "", "", "", "")
        buckets[block_key]
        buckets[cohort_key]
        populations[block_key] += block.student_count
        populations[cohort_key] += block.student_count
    for row in results:
        keys = [
            ("subject", row.academic_year, row.level, "", "", row.subject_id, row.subject_name),
            ("band", row.academic_year, row.level, row.block_id, row.band_id, "", ""),
            ("block", row.academic_year, row.level, row.block_id, "", "", ""),
            ("cohort", row.academic_year, row.level, "", "", "", ""),
        ]
        for key in keys:
            buckets[key].append(row)
    return [SummaryRow(
        *key, populations[key] if key[0] in {"block", "cohort"} else None,
        sum(row.student_count for row in rows),
        sum(row.groups_required for row in rows),
        sum(row.unused_places for row in rows),
    ) for key, rows in sorted(buckets.items())]


def _write_csv(path: Path, row_type: type, rows: list) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[field.name for field in fields(row_type)])
        writer.writeheader()
        writer.writerows(asdict(row) for row in rows)


def export_results(
    results: list[GroupResult], summaries: list[SummaryRow], output_dir: str | Path
) -> tuple[Path, Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    details_path = output_dir / "group_results.csv"
    summaries_path = output_dir / "summaries.csv"
    _write_csv(details_path, GroupResult, results)
    _write_csv(summaries_path, SummaryRow, summaries)
    return details_path, summaries_path


def _table(headers: list[str], rows: list[list[str]]) -> str:
    widths = [max(len(header), *(len(row[i]) for row in rows)) if rows else len(header)
              for i, header in enumerate(headers)]
    def render(row):
        return " | ".join(value.ljust(width) for value, width in zip(row, widths))
    return "\n".join([render(headers), "-+-".join("-" * width for width in widths),
                       *(render(row) for row in rows)])


def format_report(results: list[GroupResult], summaries: list[SummaryRow]) -> str:
    sections = [
        "Provisional subject-component group instances",
        "Mathematical capacity targets; actual timetable and teacher allocation are not established.",
        "Component enrolments may overlap; only block/cohort unique_students are student populations.",
        "\nDetail (one row per year, level, block, band and subject component):",
        _table(
            ["Year", "Level", "Block", "Band", "Subject", "Students", "Max size", "Groups", "Unused", "Preferred"],
            [[str(r.academic_year), r.level, r.block_id, r.band_id, r.subject_name,
              str(r.student_count), str(r.planning_max_size), str(r.groups_required),
              str(r.unused_places), "yes" if r.preferred_size_applied else "no"] for r in results],
        ),
    ]
    for kind in ("subject", "band", "block", "cohort"):
        sections.append(f"\n{kind.capitalize()} summary — subject-component group instances:")
        sections.append(_table(
            ["Year", "Level", "Block", "Band", "Subject", "Unique students", "Component enrolments", "Groups", "Unused"],
            [[str(r.academic_year), r.level, r.block_id, r.band_id, r.subject_name,
              str(r.unique_students) if r.unique_students is not None else "unknown",
              str(r.component_enrolments), str(r.groups_required), str(r.unused_places)]
             for r in summaries if r.summary_type == kind],
        ))
    return "\n".join(sections)
