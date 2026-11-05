"""Read editable CSV files without mixing parsing and school validation."""

import csv
from pathlib import Path

from .models import Block, Dataset, Enrolment, SubjectRule


class DataLoadError(ValueError):
    """A file cannot be read or has an invalid CSV schema or value."""


def _read_rows(path: Path, required: tuple[str, ...], optional: tuple[str, ...] = ()):
    try:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle, strict=True)
            headers = reader.fieldnames
            if not headers:
                raise DataLoadError(f"{path.name}: missing CSV header")
            missing = set(required) - set(headers)
            unknown = set(headers) - set(required + optional)
            if missing or unknown or len(headers) != len(set(headers)):
                raise DataLoadError(
                    f"{path.name}: invalid columns; missing={sorted(missing)}, "
                    f"unknown={sorted(unknown)}; duplicate headers are not allowed"
                )
            for row in reader:
                line = reader.line_num
                if None in row or any(value is None for value in row.values()):
                    raise DataLoadError(f"{path.name}: row {line}: incorrect number of fields")
                clean = {key: value.strip() for key, value in row.items()}
                for field in required:
                    if not clean[field]:
                        raise DataLoadError(f"{path.name}: row {line}: {field} is required")
                for field in ("academic_year", "student_count", "hard_max_size", "preferred_max_size"):
                    if field in clean:
                        try:
                            clean[field] = int(clean[field])
                        except ValueError as exc:
                            raise DataLoadError(
                                f"{path.name}: row {line}: {field} must be an integer"
                            ) from exc
                yield clean
    except (OSError, UnicodeError, csv.Error) as exc:
        raise DataLoadError(f"{path.name}: {exc}") from exc


def load_data(data_dir: str | Path) -> Dataset:
    """Load all files; call validate_data separately for semantic errors."""
    data_dir = Path(data_dir)
    blocks = [Block(**row) for row in _read_rows(
        data_dir / "blocks.csv",
        ("academic_year", "level", "block_id", "student_count"), ("form_classes",),
    )]
    enrolments = [Enrolment(**row) for row in _read_rows(
        data_dir / "enrolments.csv",
        ("academic_year", "level", "block_id", "band_id", "subject_id", "student_count"),
    )]
    rules = [SubjectRule(**row) for row in _read_rows(
        data_dir / "subject_rules.csv",
        ("subject_id", "subject_name", "hard_max_size", "preferred_max_size"),
    )]
    return Dataset(blocks, enrolments, rules)
