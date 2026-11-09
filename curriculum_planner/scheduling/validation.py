"""Validate explicit references, capacities and single group placement per scenario."""

from .models import SchedulingData, TeachingGroup


def validate_scheduling(data: SchedulingData, groups: list[TeachingGroup]) -> list[str]:
    errors = []
    scenario_ids = set()
    windows = set()
    pools = set()
    placements = set()
    group_ids = {group.teaching_group_id for group in groups}
    if len(group_ids) != len(groups):
        errors.append("Teaching-group inventory contains duplicate identifiers")
    if not data.scenarios:
        errors.append("scenarios.csv: at least one scenario is required")
    for number, scenario in enumerate(data.scenarios, 2):
        label = f"scenarios.csv row {number}"
        if not scenario.scenario_id.strip() or not scenario.scenario_name.strip():
            errors.append(f"{label}: scenario_id and scenario_name are required")
        if scenario.scenario_id in scenario_ids:
            errors.append(f"{label}: duplicate scenario_id {scenario.scenario_id}")
        scenario_ids.add(scenario.scenario_id)
    for number, window in enumerate(data.windows, 2):
        label = f"teaching_windows.csv row {number}"
        key = (window.scenario_id, window.window_id)
        if not all(s.strip() for s in (window.scenario_id, window.window_id, window.window_name)):
            errors.append(f"{label}: scenario_id, window_id and window_name are required")
        if window.scenario_id not in scenario_ids:
            errors.append(f"{label}: unknown scenario {window.scenario_id}")
        if key in windows:
            errors.append(f"{label}: duplicate window {key}")
        windows.add(key)
    for number, pool in enumerate(data.teacher_pools, 2):
        label = f"teacher_pools.csv row {number}"
        key = (pool.scenario_id, pool.teacher_pool_id)
        if not all(s.strip() for s in (pool.scenario_id, pool.teacher_pool_id, pool.pool_name)):
            errors.append(f"{label}: scenario_id, teacher_pool_id and pool_name are required")
        if pool.scenario_id not in scenario_ids:
            errors.append(f"{label}: unknown scenario {pool.scenario_id}")
        if key in pools:
            errors.append(f"{label}: duplicate teacher pool {key}")
        pools.add(key)
        count = pool.available_teacher_count
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            errors.append(f"{label}: available_teacher_count must be a non-negative integer")
    for number, assignment in enumerate(data.assignments, 2):
        label = f"group_assignments.csv row {number}"
        if not all(s.strip() for s in (
            assignment.scenario_id, assignment.window_id,
            assignment.teaching_group_id, assignment.teacher_pool_id,
        )):
            errors.append(f"{label}: every assignment field is required")
        if assignment.scenario_id not in scenario_ids:
            errors.append(f"{label}: unknown scenario {assignment.scenario_id}")
        if (assignment.scenario_id, assignment.window_id) not in windows:
            errors.append(f"{label}: unknown teaching window {assignment.window_id}")
        if (assignment.scenario_id, assignment.teacher_pool_id) not in pools:
            errors.append(f"{label}: unknown teacher pool {assignment.teacher_pool_id}")
        if assignment.teaching_group_id not in group_ids:
            errors.append(f"{label}: unknown teaching-group identifier {assignment.teaching_group_id}")
        key = (assignment.scenario_id, assignment.teaching_group_id)
        if key in placements:
            errors.append(f"{label}: duplicate placement for {assignment.teaching_group_id}")
        placements.add(key)
    return errors
