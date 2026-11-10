"""Curriculum time contracts; Decimal minutes keep fractional periods exact."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class CurriculumRequirement:
    academic_year: int
    level: str
    subject_id: str
    minimum_weekly_minutes: Decimal
    requirement_source: str = "user supplied; unverified"
    requirement_scope: str = "component"


@dataclass(frozen=True)
class PeriodScenario:
    period_scenario_id: str
    scenario_name: str
    period_duration_minutes: Decimal


@dataclass(frozen=True)
class WorkloadData:
    curriculum_requirements: list[CurriculumRequirement]
    period_scenarios: list[PeriodScenario]


@dataclass(frozen=True)
class PeriodConversion:
    required_periods: int
    scheduled_minutes: Decimal
    excess_minutes: Decimal


@dataclass(frozen=True)
class GroupWorkload:
    period_scenario_id: str
    scenario_name: str
    period_duration_minutes: Decimal
    teaching_scenario_id: str
    window_id: str
    teacher_pool_id: str
    academic_year: int
    level: str
    block_id: str
    band_id: str
    subject_id: str
    subject_name: str
    teaching_group_id: str
    minimum_weekly_minutes: Decimal | None
    required_periods: int | None
    scheduled_minutes: Decimal | None
    excess_minutes: Decimal | None
    requirement_source: str
    calculation_status: str


@dataclass(frozen=True)
class CompletenessRow:
    period_scenario_id: str
    teaching_scenario_id: str
    academic_year: int
    level: str
    block_id: str
    band_id: str
    subject_id: str
    subject_name: str
    teaching_group_id: str
    reason: str


@dataclass(frozen=True)
class WorkloadSummary:
    scope: str
    period_scenario_id: str
    scenario_name: str
    period_duration_minutes: Decimal
    teaching_scenario_id: str
    academic_year: int
    level: str
    block_id: str
    band_id: str
    subject_id: str
    subject_name: str
    teaching_group_count: int
    calculated_group_count: int
    uncalculated_group_count: int
    known_required_teacher_periods: int
    known_scheduled_teacher_minutes: Decimal
    known_minimum_teacher_minutes: Decimal
    known_excess_teacher_minutes: Decimal
    total_required_teacher_periods: int | None
    total_scheduled_teacher_minutes: Decimal | None
    assessment_completeness: str
    requirement_sources: str = ""


@dataclass(frozen=True)
class WorkloadResult:
    scenario: PeriodScenario
    group_workload: list[GroupWorkload]
    summaries: list[WorkloadSummary]
    completeness: list[CompletenessRow]
    validation_issues: list[str]
