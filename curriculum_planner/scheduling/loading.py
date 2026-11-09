"""Parse scenario CSVs; cross-record validation lives in validation.py."""

import csv
from dataclasses import fields
from pathlib import Path

from ..loading import DataLoadError
from .models import GroupAssignment, Scenario, SchedulingData, TeacherPool, TeachingWindow


def _load_records(path, record_type):
    expected = [field.name for field in fields(record_type)]
    records = []
    try:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle, strict=True)
            headers = reader.fieldnames or []
            if set(headers) != set(expected) or len(headers) != len(expected):
                raise DataLoadError(f"{path.name}: expected CSV columns: {', '.join(expected)}")
            for row in reader:
                location = f"{path.name} row {reader.line_num}"
                if None in row or any(value is None for value in row.values()):
                    raise DataLoadError(f"{location}: incorrect number of fields")
                clean = {key: value.strip() for key, value in row.items()}
                for name, value in clean.items():
                    if not value and name != "description":
                        raise DataLoadError(f"{location}: {name} is required")
                if "available_teacher_count" in clean:
                    try:
                        clean["available_teacher_count"] = int(clean["available_teacher_count"])
                    except ValueError as exc:
                        raise DataLoadError(f"{location}: available_teacher_count must be an integer") from exc
                records.append(record_type(**clean))
    except (OSError, UnicodeError, csv.Error) as exc:
        raise DataLoadError(f"{path.name}: {exc}") from exc
    return records


def load_scheduling(data_dir: str | Path) -> SchedulingData:
    path = Path(data_dir)
    return SchedulingData(
        _load_records(path / "scenarios.csv", Scenario),
        _load_records(path / "teaching_windows.csv", TeachingWindow),
        _load_records(path / "group_assignments.csv", GroupAssignment),
        _load_records(path / "teacher_pools.csv", TeacherPool),
    )
