"""Pure integer capacity calculations; no timetable or teacher assumptions."""

from .models import Dataset, GroupResult
from .validation import validate_data


def calculate_group_count(student_count: int, limit: int) -> int:
    if not isinstance(student_count, int) or isinstance(student_count, bool) or student_count < 0:
        raise ValueError("student_count must be a non-negative integer")
    if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
        raise ValueError("limit must be a positive integer")
    return (student_count + limit - 1) // limit


def calculate_groups(dataset: Dataset, use_preferred: bool = True) -> list[GroupResult]:
    errors = validate_data(dataset)
    if errors:
        raise ValueError("Invalid input data:\n" + "\n".join(errors))
    rules = {rule.subject_id: rule for rule in dataset.subject_rules}
    results = []
    for row in sorted(dataset.enrolments, key=lambda r: (
        r.academic_year, r.level, r.block_id, r.band_id, r.subject_id
    )):
        rule = rules[row.subject_id]
        limit = rule.preferred_max_size if use_preferred else rule.hard_max_size
        groups = calculate_group_count(row.student_count, limit)
        results.append(GroupResult(
            row.academic_year, row.level, row.block_id, row.band_id, row.subject_id,
            rule.subject_name, row.student_count, limit, groups,
            groups * limit - row.student_count,
            use_preferred and rule.preferred_max_size < rule.hard_max_size,
        ))
    return results
