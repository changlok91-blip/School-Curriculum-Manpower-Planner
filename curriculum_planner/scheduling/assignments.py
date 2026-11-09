"""Resolve manually selected groups into windows; this does not generate a schedule."""

from collections import defaultdict

from .models import SchedulingData, TeachingGroup
from .validation import validate_scheduling


def assign_groups(
    groups: list[TeachingGroup], data: SchedulingData, scenario_id: str,
) -> dict[tuple[str, str], list[TeachingGroup]]:
    errors = validate_scheduling(data, groups)
    if errors:
        raise ValueError("Invalid scenario input:\n" + "\n".join(errors))
    if scenario_id not in {scenario.scenario_id for scenario in data.scenarios}:
        raise ValueError(f"Unknown scenario: {scenario_id}")
    inventory = {group.teaching_group_id: group for group in groups}
    placements = defaultdict(list)
    for row in data.assignments:
        if row.scenario_id == scenario_id:
            placements[(row.window_id, row.teacher_pool_id)].append(inventory[row.teaching_group_id])
    return {key: sorted(value, key=lambda group: group.teaching_group_id)
            for key, value in sorted(placements.items())}
