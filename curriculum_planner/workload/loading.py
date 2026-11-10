"""Read the exchangeable curriculum-time and period-scenario CSV inputs."""

import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path

from ..loading import DataLoadError
from .models import CurriculumRequirement, PeriodScenario, WorkloadData


def _records(path, required, optional=()):
    try:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle, strict=True)
            headers = reader.fieldnames or []
            if (not set(required) <= set(headers) or set(headers) - set(required + optional)
                    or len(headers) != len(set(headers))):
                raise DataLoadError(f"{path.name}: invalid columns; required: {', '.join(required)}")
            for row in reader:
                label = f"{path.name} row {reader.line_num}"
                if None in row or any(value is None for value in row.values()):
                    raise DataLoadError(f"{label}: incorrect number of fields")
                clean = {key: value.strip() for key, value in row.items()}
                for field in required:
                    if not clean[field]:
                        raise DataLoadError(f"{label}: {field} is required")
                if "academic_year" in clean:
                    try:
                        clean["academic_year"] = int(clean["academic_year"])
                    except ValueError as exc:
                        raise DataLoadError(f"{label}: academic_year must be an integer") from exc
                for field in ("minimum_weekly_minutes", "period_duration_minutes"):
                    if field in clean:
                        try:
                            clean[field] = Decimal(clean[field])
                        except InvalidOperation as exc:
                            raise DataLoadError(f"{label}: {field} must be numeric minutes") from exc
                yield clean
    except (OSError, UnicodeError, csv.Error) as exc:
        raise DataLoadError(f"{path.name}: {exc}") from exc


def load_workload_data(data_dir: str | Path) -> WorkloadData:
    path = Path(data_dir)
    requirements = [CurriculumRequirement(**row) for row in _records(
        path / "curriculum_requirements.csv",
        ("academic_year", "level", "subject_id", "minimum_weekly_minutes"),
        ("requirement_source", "requirement_scope"),
    )]
    scenarios = [PeriodScenario(**row) for row in _records(
        path / "period_scenarios.csv",
        ("period_scenario_id", "scenario_name", "period_duration_minutes"),
    )]
    return WorkloadData(requirements, scenarios)
