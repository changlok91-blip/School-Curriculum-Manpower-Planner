"""Validate records without assuming that components contain distinct students."""

from .models import Dataset


def _integer(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def validate_data(dataset: Dataset) -> list[str]:
    """Return all semantic errors. Empty enrolments are valid; blocks are required."""
    errors: list[str] = []
    blocks = {}
    rules = {}
    if not dataset.blocks:
        errors.append("blocks.csv: at least one block is required")
    for number, block in enumerate(dataset.blocks, 2):
        label = f"blocks.csv row {number} ({block.block_id})"
        key = (block.academic_year, block.level, block.block_id)
        if key in blocks:
            errors.append(f"{label}: duplicate block record")
        blocks[key] = block
        if not _integer(block.academic_year) or block.academic_year <= 0:
            errors.append(f"{label}: academic_year must be a positive integer")
        if not block.level.strip() or not block.block_id.strip():
            errors.append(f"{label}: level and block_id are required")
        if not _integer(block.student_count) or block.student_count < 0:
            errors.append(f"{label}: student_count must be a non-negative integer")
    for number, rule in enumerate(dataset.subject_rules, 2):
        label = f"subject_rules.csv row {number} ({rule.subject_id})"
        if rule.subject_id in rules:
            errors.append(f"{label}: duplicate subject rule")
        rules[rule.subject_id] = rule
        if not rule.subject_id.strip() or not rule.subject_name.strip():
            errors.append(f"{label}: subject_id and subject_name are required")
        hard_valid = _integer(rule.hard_max_size) and rule.hard_max_size > 0
        preferred_valid = _integer(rule.preferred_max_size) and rule.preferred_max_size > 0
        if not hard_valid:
            errors.append(f"{label}: hard_max_size must be a positive integer")
        if not preferred_valid:
            errors.append(f"{label}: preferred_max_size must be a positive integer")
        if hard_valid and preferred_valid and rule.preferred_max_size > rule.hard_max_size:
            errors.append(f"{label}: preferred_max_size cannot exceed hard_max_size")
    seen = set()
    for number, row in enumerate(dataset.enrolments, 2):
        label = f"enrolments.csv row {number} ({row.block_id}/{row.band_id}/{row.subject_id})"
        block_key = (row.academic_year, row.level, row.block_id)
        key = (*block_key, row.band_id, row.subject_id)
        if key in seen:
            errors.append(f"{label}: duplicate enrolment record")
        seen.add(key)
        if not _integer(row.academic_year) or row.academic_year <= 0:
            errors.append(f"{label}: academic_year must be a positive integer")
        if not all(field.strip() for field in (row.level, row.block_id, row.band_id, row.subject_id)):
            errors.append(f"{label}: level, block_id, band_id and subject_id are required")
        count_valid = _integer(row.student_count) and row.student_count >= 0
        if not count_valid:
            errors.append(f"{label}: student_count must be a non-negative integer")
        if row.subject_id not in rules:
            errors.append(f"{label}: missing subject rule for {row.subject_id}")
        if block_key not in blocks:
            errors.append(f"{label}: unknown block for academic_year and level")
        elif count_valid:
            population = blocks[block_key].student_count
            if _integer(population) and row.student_count > population:
                errors.append(f"{label}: single component enrolment exceeds block student_count")
        # Never sum components to validate population: pupils can take several.
    return errors
