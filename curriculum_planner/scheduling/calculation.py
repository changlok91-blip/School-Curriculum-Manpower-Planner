"""Count simultaneous group demand without generating a timetable."""

from collections import defaultdict
from dataclasses import asdict
import json

from .assignments import assign_groups
from .models import (
    PoolSummary, ScenarioComparison, ScenarioResult, SchedulingData,
    TeachingGroup, UnscheduledGroup, WindowSummary,
)
from .validation import validate_scheduling


VIOLATED = "Concurrent staffing constraint violated"
SATISFIED = "Concurrent staffing constraint satisfied for the configured groups"


def run_scenario(
    groups: list[TeachingGroup], data: SchedulingData, scenario_id: str,
) -> ScenarioResult:
    """Assess manually placed groups; each group draws one teacher per window.

    Separate windows are assumed non-overlapping. Pool availability is an
    explicit modelling input, not inferred from subject names or qualifications.
    """
    errors = validate_scheduling(data, groups)
    if errors:
        raise ValueError("Invalid scheduling data:\n" + "\n".join(errors))
    scenarios = {scenario.scenario_id: scenario for scenario in data.scenarios}
    if scenario_id not in scenarios:
        raise ValueError(f"Unknown scenario: {scenario_id}")
    scenario = scenarios[scenario_id]
    windows = sorted(
        (window for window in data.windows if window.scenario_id == scenario_id),
        key=lambda window: window.window_id,
    )
    pools = sorted(
        (pool for pool in data.teacher_pools if pool.scenario_id == scenario_id),
        key=lambda pool: pool.teacher_pool_id,
    )
    placements = assign_groups(groups, data, scenario_id)
    placed_ids = {
        group.teaching_group_id for assigned in placements.values() for group in assigned
    }
    window_summary = []
    resource_summary = []
    peaks = {}
    violations = 0

    for pool in pools:
        peak = 0
        for window in windows:
            assigned = placements.get((window.window_id, pool.teacher_pool_id), [])
            demand = len(assigned)
            peak = max(peak, demand)
            shortage = max(0, demand - pool.available_teacher_count)
            violations += int(shortage > 0)
            slices = defaultdict(list)
            for group in assigned:
                slices[(group.academic_year, group.level, group.block_id, group.band_id)].append(group)
            # Include configured idle pool/window combinations in the report.
            if not slices:
                slices[(None, "", "", "")] = []
            for (year, level, block_id, band_id), subset in sorted(slices.items()):
                window_summary.append(WindowSummary(
                    scenario_id, scenario.scenario_name, window.window_id,
                    window.window_name, year, level, block_id, band_id,
                    pool.teacher_pool_id, pool.pool_name,
                    ";".join(sorted(group.teaching_group_id for group in subset)),
                    len(subset), demand, pool.available_teacher_count, shortage,
                ))
        peaks[pool.teacher_pool_id] = peak
        maximum_shortage = max(0, peak - pool.available_teacher_count)
        resource_summary.append(PoolSummary(
            scenario_id, scenario.scenario_name, pool.teacher_pool_id,
            pool.pool_name, pool.available_teacher_count, peak, maximum_shortage,
            VIOLATED if maximum_shortage else (
                SATISFIED if peak else "No configured groups assessed"
            ),
        ))

    window_summary.sort(key=lambda row: (
        row.window_id, row.teacher_pool_id,
        row.academic_year if row.academic_year is not None else -1,
        row.level, row.block_id, row.band_id,
    ))
    unscheduled = [
        UnscheduledGroup(scenario_id, scenario.scenario_name, **asdict(group))
        for group in sorted(groups, key=lambda group: group.teaching_group_id)
        if group.teaching_group_id not in placed_ids
    ]
    if not groups:
        completeness = "no teaching groups available; nothing assessed"
    elif unscheduled:
        completeness = f"partial ({len(placed_ids)} of {len(groups)} groups placed)"
    else:
        completeness = "all groups placed; concurrency checks only"
    comparison = ScenarioComparison(
        scenario_id, scenario.scenario_name, len(windows),
        len({window_id for (window_id, _), assigned in placements.items() if assigned}),
        len(groups), len(placed_ids), len(unscheduled),
        json.dumps(peaks, sort_keys=True), violations,
        VIOLATED if violations else (
            SATISFIED if placed_ids else "No configured groups assessed"
        ),
        completeness,
    )
    return ScenarioResult(
        scenario, window_summary, resource_summary, unscheduled, comparison,
    )


def compare_scenarios(
    groups: list[TeachingGroup], data: SchedulingData, scenario_ids: list[str],
) -> list[ScenarioResult]:
    """Compare two or more distinct scenarios against the same group inventory."""
    if len(scenario_ids) < 2 or len(set(scenario_ids)) != len(scenario_ids):
        raise ValueError("Comparison requires at least two distinct scenario IDs")
    return [run_scenario(groups, data, scenario_id) for scenario_id in scenario_ids]
