"""Calculate weekly workload independently for every generated teaching group."""

from collections import defaultdict
from dataclasses import replace

from ..calculation import calculate_groups
from ..models import Dataset
from ..scheduling.assignments import assign_groups
from ..scheduling.groups import generate_teaching_groups
from ..scheduling.models import SchedulingData
from .models import (
    CompletenessRow, GroupWorkload, WorkloadData, WorkloadResult, WorkloadSummary,
)
from .periods import convert_minutes, normalized_minutes, sum_minutes
from .validation import requirement_issues, validate_workload_data


def calculate_workload(
    dataset: Dataset, data: WorkloadData, period_scenario_id: str, *,
    use_preferred: bool = True, scheduling: SchedulingData | None = None,
    teaching_scenario_id: str | None = None, academic_year: int | None = None,
    level: str | None = None,
) -> WorkloadResult:
    """Keep missing requirements unknown and abstract windows as metadata only.

    Requirements are component-specific. No combined-subject total is inherited
    and no component enrolments are summed to infer unique student populations.
    """
    matching = [s for s in data.period_scenarios if s.period_scenario_id == period_scenario_id]
    if len(matching) != 1:
        raise ValueError(f"Period scenario must exist exactly once: {period_scenario_id}")
    scenario = matching[0]
    if not scenario.period_scenario_id.strip() or not scenario.scenario_name.strip():
        raise ValueError("Period scenario ID and name are required")
    # Conversion validates that duration is finite and strictly positive.
    convert_minutes(0, scenario.period_duration_minutes)
    scenario = replace(scenario, period_duration_minutes=normalized_minutes(scenario.period_duration_minutes))
    all_groups = generate_teaching_groups(calculate_groups(dataset, use_preferred=use_preferred))
    assignment_by_group = {}
    if (scheduling is None) != (teaching_scenario_id is None):
        raise ValueError("Provide both scheduling data and a teaching scenario ID, or neither")
    if scheduling is not None:
        placements = assign_groups(all_groups, scheduling, teaching_scenario_id)
        assignment_by_group = {
            group.teaching_group_id: (window_id, pool_id)
            for (window_id, pool_id), groups in placements.items() for group in groups
        }

    def selected(record):
        return ((academic_year is None or record.academic_year == academic_year)
                and (level is None or record.level == level))

    selected_blocks = [block for block in dataset.blocks if selected(block)]
    if not selected_blocks:
        raise ValueError("No curriculum blocks match the selected academic year and level")
    groups = [group for group in all_groups if selected(group)]
    issues = validate_workload_data(dataset, data, include_missing=False)
    invalid_rules = requirement_issues(dataset, data)
    requirements = defaultdict(list)
    for rule in data.curriculum_requirements:
        requirements[(rule.academic_year, rule.level, rule.subject_id)].append(rule)

    workload = []
    completeness = []
    for group in groups:
        key = (group.academic_year, group.level, group.subject_id)
        candidates = requirements.get(key, [])
        minimum = None
        conversion = None
        if not candidates:
            status = "missing requirement"
            reason = "Missing component-level curriculum time requirement; no minutes assumed"
        elif key in invalid_rules or len(candidates) != 1:
            status = "invalid requirement"
            reason = "; ".join(invalid_rules.get(key, ["Duplicate or conflicting curriculum rules"]))
        else:
            status = "calculated"
            minimum = normalized_minutes(candidates[0].minimum_weekly_minutes)
            conversion = convert_minutes(minimum, scenario.period_duration_minutes)
        window_id, pool_id = assignment_by_group.get(group.teaching_group_id, ("", ""))
        source = "; ".join(sorted({rule.requirement_source for rule in candidates}))
        workload.append(GroupWorkload(
            scenario.period_scenario_id, scenario.scenario_name, scenario.period_duration_minutes,
            teaching_scenario_id or "", window_id, pool_id,
            group.academic_year, group.level, group.block_id, group.band_id,
            group.subject_id, group.subject_name, group.teaching_group_id, minimum,
            conversion.required_periods if conversion else None,
            conversion.scheduled_minutes if conversion else None,
            conversion.excess_minutes if conversion else None, source, status,
        ))
        if conversion is None:
            completeness.append(CompletenessRow(
                scenario.period_scenario_id, teaching_scenario_id or "", group.academic_year,
                group.level, group.block_id, group.band_id, group.subject_id,
                group.subject_name, group.teaching_group_id, reason,
            ))
    summaries = _summarize_workload(workload, selected_blocks, scenario, teaching_scenario_id, issues)
    return WorkloadResult(scenario, workload, summaries, completeness, issues)


def _summarize_workload(workload, blocks, scenario, teaching_scenario_id, issues):
    buckets = defaultdict(list)
    for block in blocks:
        buckets[("block", block.academic_year, block.level, block.block_id, "", "", "")]
        buckets[("level", block.academic_year, block.level, "", "", "", "")]
    for row in workload:
        for key in (
            ("subject", row.academic_year, row.level, "", "", row.subject_id, row.subject_name),
            ("band", row.academic_year, row.level, row.block_id, row.band_id, "", ""),
            ("block", row.academic_year, row.level, row.block_id, "", "", ""),
            ("level", row.academic_year, row.level, "", "", "", ""),
        ):
            buckets[key].append(row)
    summaries = []
    for key, rows in sorted(buckets.items()):
        scope, year, level, block_id, band_id, subject_id, subject_name = key
        known = [row for row in rows if row.calculation_status == "calculated"]
        periods = sum(row.required_periods for row in known)
        scheduled = sum_minutes(row.scheduled_minutes for row in known)
        minimum = sum_minutes(row.minimum_weekly_minutes for row in known)
        excess = sum_minutes(row.excess_minutes for row in known)
        uncalculated = len(rows) - len(known)
        complete = not uncalculated and not issues
        status = "complete for configured requirements" if complete else (
            f"partial ({len(known)} of {len(rows)} groups calculated)"
            + ("; input validation issues present" if issues else "")
        )
        summaries.append(WorkloadSummary(
            scope, scenario.period_scenario_id, scenario.scenario_name,
            scenario.period_duration_minutes, teaching_scenario_id or "", year, level,
            block_id, band_id, subject_id, subject_name, len(rows), len(known), uncalculated,
            periods, scheduled, minimum, excess,
            periods if complete else None, scheduled if complete else None, status,
            "; ".join(sorted({row.requirement_source for row in known if row.requirement_source})),
        ))
    return summaries
