"""Expand Component 1 results without recalculating or pooling teaching groups."""

from urllib.parse import quote

from ..models import GroupResult
from .models import TeachingGroup


def generate_teaching_groups(results: list[GroupResult]) -> list[TeachingGroup]:
    """Identity is year/level/block/band/subject/ordinal, independent of row order.

    Percent-encoding individual segments prevents collisions when identifiers
    contain slashes, percent signs or other separators. Ordinals do not imply
    an actual distribution of students within a component.
    """
    groups = []
    seen = set()
    for row in results:
        key = (row.academic_year, row.level, row.block_id, row.band_id, row.subject_id)
        if key in seen:
            raise ValueError(f"Duplicate Component 1 result identity: {key}")
        seen.add(key)
        for number in range(1, row.groups_required + 1):
            identifier = "/".join(quote(str(part), safe="") for part in (*key, number))
            groups.append(TeachingGroup(
                identifier, row.academic_year, row.level, row.block_id, row.band_id,
                row.subject_id, row.subject_name, number, row.planning_max_size,
                row.student_count,
            ))
    return sorted(groups, key=lambda group: (
        group.academic_year, group.level, group.block_id, group.band_id,
        group.subject_id, group.group_number,
    ))
