"""Check component-specific time rules; never allocate combined-subject minutes."""

from collections import defaultdict

from ..calculation import calculate_groups
from ..models import Dataset
from ..scheduling.groups import generate_teaching_groups
from ..validation import validate_data
from .models import WorkloadData
from .periods import normalized_minutes


def requirement_issues(dataset: Dataset, data: WorkloadData) -> dict[tuple, list[str]]:
    issues = defaultdict(list)
    seen = set()
    subjects = {rule.subject_id for rule in dataset.subject_rules}
    cohorts = {(block.academic_year, block.level) for block in dataset.blocks}
    for row in data.curriculum_requirements:
        key = (row.academic_year, row.level, row.subject_id)
        if key in seen:
            issues[key].append("Duplicate or conflicting curriculum requirements")
        seen.add(key)
        if (not isinstance(row.academic_year, int) or isinstance(row.academic_year, bool)
                or row.academic_year <= 0):
            issues[key].append("Academic year must be a positive integer")
        if not row.level.strip() or not row.subject_id.strip():
            issues[key].append("Level and subject_id are required")
        if (row.academic_year, row.level) not in cohorts:
            issues[key].append("Unknown academic year / level in existing blocks")
        if row.subject_id not in subjects:
            issues[key].append("Unknown subject_id; combined-subject time is not allocated to components")
        try:
            normalized_minutes(row.minimum_weekly_minutes)
        except ValueError as exc:
            issues[key].append(f"Invalid minimum_weekly_minutes: {exc}")
        if row.requirement_scope != "component":
            issues[key].append("Component allocation unknown: requirement_scope must be component; "
                               "combined-subject minutes cannot be copied or allocated automatically")
    return dict(issues)


def validate_workload_data(
    dataset: Dataset, data: WorkloadData, *, include_missing: bool = True,
) -> list[str]:
    base_errors = validate_data(dataset)
    errors = list(base_errors)
    issues = requirement_issues(dataset, data)
    for key, reasons in issues.items():
        errors.extend(f"curriculum_requirements.csv {key}: {reason}" for reason in reasons)
    seen = set()
    if not data.period_scenarios:
        errors.append("period_scenarios.csv: at least one period scenario is required")
    for index, scenario in enumerate(data.period_scenarios, 2):
        label = f"period_scenarios.csv row {index} ({scenario.period_scenario_id})"
        if not scenario.period_scenario_id.strip() or not scenario.scenario_name.strip():
            errors.append(f"{label}: period_scenario_id and scenario_name are required")
        if scenario.period_scenario_id in seen:
            errors.append(f"{label}: duplicate period_scenario_id")
        seen.add(scenario.period_scenario_id)
        try:
            if normalized_minutes(scenario.period_duration_minutes) <= 0:
                raise ValueError("Period duration must be positive")
        except ValueError as exc:
            errors.append(f"{label}: invalid period duration: {exc}")
    if include_missing and not base_errors:
        keys = {(r.academic_year, r.level, r.subject_id) for r in data.curriculum_requirements}
        for group in generate_teaching_groups(calculate_groups(dataset)):
            key = (group.academic_year, group.level, group.subject_id)
            if key not in keys:
                errors.append(f"Missing curriculum requirement for teaching group {group.teaching_group_id}")
    return errors
