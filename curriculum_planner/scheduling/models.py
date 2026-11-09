"""Data contracts for abstract windows and explicitly configured resource pools."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    scenario_name: str
    description: str = ""


@dataclass(frozen=True)
class TeachingWindow:
    scenario_id: str
    window_id: str
    window_name: str


@dataclass(frozen=True)
class GroupAssignment:
    scenario_id: str
    window_id: str
    teaching_group_id: str
    teacher_pool_id: str


@dataclass(frozen=True)
class TeacherPool:
    scenario_id: str
    teacher_pool_id: str
    pool_name: str
    available_teacher_count: int


@dataclass(frozen=True)
class SchedulingData:
    scenarios: list[Scenario]
    windows: list[TeachingWindow]
    assignments: list[GroupAssignment]
    teacher_pools: list[TeacherPool]


@dataclass(frozen=True)
class TeachingGroup:
    teaching_group_id: str
    academic_year: int
    level: str
    block_id: str
    band_id: str
    subject_id: str
    subject_name: str
    group_number: int
    planning_max_size: int
    component_student_count: int


@dataclass(frozen=True)
class WindowSummary:
    scenario_id: str
    scenario_name: str
    window_id: str
    window_name: str
    academic_year: int | None
    level: str
    block_id: str
    band_id: str
    teacher_pool_id: str
    pool_name: str
    teaching_group_ids: str
    group_count: int
    concurrent_demand: int
    available_teacher_count: int
    shortage: int


@dataclass(frozen=True)
class PoolSummary:
    scenario_id: str
    scenario_name: str
    teacher_pool_id: str
    pool_name: str
    available_teacher_count: int
    peak_simultaneous_demand: int
    maximum_shortage: int
    concurrency_status: str


@dataclass(frozen=True)
class UnscheduledGroup:
    scenario_id: str
    scenario_name: str
    teaching_group_id: str
    academic_year: int
    level: str
    block_id: str
    band_id: str
    subject_id: str
    subject_name: str
    group_number: int
    planning_max_size: int
    component_student_count: int


@dataclass(frozen=True)
class ScenarioComparison:
    scenario_id: str
    scenario_name: str
    teaching_windows: int
    windows_used: int
    total_group_instances: int
    scheduled_group_instances: int
    unscheduled_group_instances: int
    peak_concurrent_demand_by_pool: str
    concurrency_violations: int
    concurrency_status: str
    assessment_completeness: str
    full_timetable_feasibility: str = "not yet assessed"
    student_compatibility: str = "unverified"
    shared_teacher_capacity: str = "not validated"
    weekly_teaching_capacity: str = "not assessed"


@dataclass(frozen=True)
class ScenarioResult:
    scenario: Scenario
    window_summary: list[WindowSummary]
    resource_pool_summary: list[PoolSummary]
    unscheduled_groups: list[UnscheduledGroup]
    comparison: ScenarioComparison
