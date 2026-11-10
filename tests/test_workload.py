"""Component 3 verifies weekly workload independently from window concurrency."""

from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from curriculum_planner.calculation import calculate_groups
from curriculum_planner.loading import load_data
from curriculum_planner.models import Block, Dataset, Enrolment, SubjectRule
from curriculum_planner.scheduling.calculation import run_scenario
from curriculum_planner.scheduling.groups import generate_teaching_groups
from curriculum_planner.scheduling.loading import load_scheduling
from curriculum_planner.workload.calculation import calculate_workload
from curriculum_planner.workload.comparison import compare_period_scenarios
from curriculum_planner.workload.loading import load_workload_data
from curriculum_planner.workload.models import CurriculumRequirement, PeriodScenario, WorkloadData
from curriculum_planner.workload.periods import convert_minutes
from curriculum_planner.workload.validation import validate_workload_data


DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def dataset_for(count=40):
    return Dataset(
        [Block(2027, "Sec3", "A", count)],
        [Enrolment(2027, "Sec3", "A", "Science", "BIO", count)],
        [SubjectRule("BIO", "Biology", 40, 40)],
    )


def workload_data(minutes=150, duration=30):
    return WorkloadData(
        [CurriculumRequirement(2027, "Sec3", "BIO", Decimal(str(minutes)), "SYNTHETIC test")],
        [PeriodScenario("test", "Test period duration", Decimal(str(duration)))],
    )


def cohort_summary(result):
    return next(row for row in result.summaries if row.scope == "level")


@pytest.mark.parametrize(
    "minutes,duration,periods,scheduled,excess",
    [(150, 15, 10, 150, 0), (150, 20, 8, 160, 10),
     (150, 30, 5, 150, 0), (150, 35, 5, 175, 25), (0, 20, 0, 0, 0)],
)
def test_minutes_round_up_per_group(minutes, duration, periods, scheduled, excess):
    converted = convert_minutes(minutes, duration)
    assert converted.required_periods == periods
    assert converted.scheduled_minutes == scheduled
    assert converted.excess_minutes == excess


def test_fractional_minutes_and_nonstandard_positive_period_lengths():
    converted = convert_minutes(Decimal("150.1"), Decimal("22.5"))
    assert converted.required_periods == 7
    assert converted.scheduled_minutes == Decimal("157.5")
    assert converted.excess_minutes == Decimal("7.4")


def test_high_precision_minimum_just_above_period_boundary_rounds_up():
    converted = convert_minutes(Decimal("150.00000000000000000000000001"), Decimal(30))
    assert converted.required_periods == 6
    assert converted.scheduled_minutes == Decimal(180)
    assert converted.excess_minutes == Decimal("29.99999999999999999999999999")
    assert converted.excess_minutes >= 0


@pytest.mark.parametrize("duration", [0, -1, Decimal("NaN"), Decimal("Infinity")])
def test_invalid_period_lengths_are_rejected(duration):
    with pytest.raises(ValueError):
        convert_minutes(150, duration)


@pytest.mark.parametrize("minutes", [-1, Decimal("NaN"), Decimal("Infinity")])
def test_invalid_minimum_minutes_are_rejected(minutes):
    with pytest.raises(ValueError):
        convert_minutes(minutes, 30)


def test_biology_worked_examples_leave_unknown_cohort_workload_explicit():
    dataset = load_data(DATA_DIR)
    data = load_workload_data(DATA_DIR)
    results = compare_period_scenarios(dataset, data, ["p15", "p20", "p30", "p35"])
    summaries = [cohort_summary(result) for result in results]
    assert [row.known_required_teacher_periods for row in summaries] == [40, 32, 20, 20]
    assert [row.known_scheduled_teacher_minutes for row in summaries] == [600, 640, 600, 700]
    assert [row.known_excess_teacher_minutes for row in summaries] == [0, 40, 0, 100]
    assert all(row.known_minimum_teacher_minutes == 600 for row in summaries)
    for result, summary in zip(results, summaries):
        assert "synthetic" in summary.requirement_sources.lower()
        assert len(result.group_workload) == summary.teaching_group_count == 70
        assert summary.calculated_group_count == 4
        assert summary.uncalculated_group_count == len(result.completeness) == 66
        assert summary.total_required_teacher_periods is None
        assert summary.total_scheduled_teacher_minutes is None
        assert "partial" in summary.assessment_completeness.lower()
        known = [row for row in result.group_workload if row.required_periods is not None]
        assert len(known) == 4
        assert all(row.minimum_weekly_minutes == 150 for row in known)
        assert all("synthetic" in row.requirement_source.lower() for row in known)
        unknown = [row for row in result.group_workload if row.required_periods is None]
        assert all(row.minimum_weekly_minutes is None and row.scheduled_minutes is None for row in unknown)


def test_enrolment_growth_automatically_doubles_group_workload():
    data = workload_data()
    one = calculate_workload(dataset_for(40), data, "test")
    two = calculate_workload(dataset_for(41), data, "test")
    assert len(one.group_workload) == 1
    assert len(two.group_workload) == 2
    assert cohort_summary(one).total_required_teacher_periods == 5
    assert cohort_summary(two).total_required_teacher_periods == 10
    assert cohort_summary(two).total_scheduled_teacher_minutes == 300
    assert two.group_workload[0].teaching_group_id == one.group_workload[0].teaching_group_id


def test_rounding_occurs_for_each_group_before_aggregation():
    result = calculate_workload(dataset_for(81), workload_data(duration=20), "test")
    assert len(result.group_workload) == 3
    assert [row.required_periods for row in result.group_workload] == [8, 8, 8]
    assert cohort_summary(result).total_required_teacher_periods == 24
    assert cohort_summary(result).total_scheduled_teacher_minutes == 480


def test_zero_enrolment_produces_zero_groups_and_zero_workload():
    result = calculate_workload(dataset_for(0), workload_data(), "test")
    assert result.group_workload == []
    assert result.completeness == []
    summary = cohort_summary(result)
    assert summary.teaching_group_count == 0
    assert summary.known_required_teacher_periods == summary.known_scheduled_teacher_minutes == 0
    assert summary.total_required_teacher_periods == summary.total_scheduled_teacher_minutes == 0


def test_zero_groups_do_not_require_a_curriculum_rule():
    data = workload_data()
    data.curriculum_requirements.clear()
    result = calculate_workload(dataset_for(0), data, "test")
    assert result.group_workload == result.completeness == []
    assert cohort_summary(result).total_required_teacher_periods == 0


def test_explicit_zero_minutes_is_distinct_from_a_missing_requirement():
    result = calculate_workload(dataset_for(), workload_data(minutes=0), "test")
    assert result.group_workload[0].required_periods == 0
    assert result.group_workload[0].minimum_weekly_minutes == 0
    assert result.completeness == []
    assert cohort_summary(result).total_required_teacher_periods == 0


def test_windows_preserve_context_without_changing_weekly_workload():
    dataset = load_data(DATA_DIR)
    data = load_workload_data(DATA_DIR)
    scheduling = load_scheduling(DATA_DIR)
    first = calculate_workload(dataset, data, "p30", scheduling=scheduling,
                               teaching_scenario_id="simultaneous_science")
    second = calculate_workload(dataset, data, "p30", scheduling=scheduling,
                                teaching_scenario_id="separate_science")
    assert cohort_summary(first).known_required_teacher_periods == 20
    assert cohort_summary(second).known_required_teacher_periods == 20
    assert cohort_summary(first).known_scheduled_teacher_minutes == 600
    assert cohort_summary(second).known_scheduled_teacher_minutes == 600
    first_biology = [row for row in first.group_workload if row.required_periods is not None]
    second_biology = [row for row in second.group_workload if row.required_periods is not None]
    assert {row.window_id for row in first_biology} == {"SCIENCE_ALL"}
    assert {row.window_id for row in second_biology} == {"SCIENCE_A", "SCIENCE_B"}
    assert {row.teacher_pool_id for row in second_biology} == {"BIOLOGY"}
    assert {row.block_id for row in second_biology} == {"A", "B"}
    assert {row.band_id for row in second_biology} == {"Science"}
    groups = generate_teaching_groups(calculate_groups(dataset))
    assert run_scenario(groups, scheduling, "simultaneous_science").resource_pool_summary[0].peak_simultaneous_demand == 4
    assert run_scenario(groups, scheduling, "separate_science").resource_pool_summary[0].peak_simultaneous_demand == 2


def test_subject_and_band_and_block_summaries_aggregate_separate_group_rows():
    result = calculate_workload(load_data(DATA_DIR), load_workload_data(DATA_DIR), "p30")
    assert {row.scope for row in result.summaries} == {"subject", "band", "block", "level"}
    science_bands = [row for row in result.summaries if row.scope == "band" and row.band_id == "Science"]
    assert {row.block_id: row.known_required_teacher_periods for row in science_bands} == {"A": 10, "B": 10}
    block_rows = [row for row in result.summaries if row.scope == "block"]
    assert {row.block_id: row.known_scheduled_teacher_minutes for row in block_rows} == {"A": 300, "B": 300}


def test_missing_requirement_is_flagged_and_never_assumed_zero():
    data = workload_data()
    data.curriculum_requirements.clear()
    assert validate_workload_data(dataset_for(), data)
    result = calculate_workload(dataset_for(), data, "test")
    assert len(result.completeness) == 1
    assert "missing" in result.completeness[0].reason.lower()
    assert result.group_workload[0].required_periods is None
    assert cohort_summary(result).total_required_teacher_periods is None


@pytest.mark.parametrize("failure", ["negative", "duplicate", "conflicting", "combined"])
def test_invalid_component_rules_are_flagged_without_calculating_them(failure):
    data = workload_data()
    rule = data.curriculum_requirements[0]
    if failure == "negative":
        data.curriculum_requirements[0] = replace(rule, minimum_weekly_minutes=Decimal(-1))
    elif failure == "duplicate":
        data.curriculum_requirements.append(rule)
    elif failure == "conflicting":
        data.curriculum_requirements.append(replace(rule, minimum_weekly_minutes=Decimal(200)))
    else:
        data.curriculum_requirements[0] = replace(rule, requirement_scope="combined_unallocated")
    assert validate_workload_data(dataset_for(), data)
    result = calculate_workload(dataset_for(), data, "test")
    assert result.group_workload[0].required_periods is None
    assert len(result.completeness) == 1
    assert cohort_summary(result).total_required_teacher_periods is None


def test_combined_science_rule_is_not_inherited_by_component_subjects():
    dataset = Dataset(
        [Block(2027, "Sec3", "A", 40)],
        [Enrolment(2027, "Sec3", "A", "Science", subject, 40) for subject in ("CHEM", "PHY")],
        [SubjectRule(subject, subject, 40, 40) for subject in ("CHEM", "PHY")],
    )
    data = workload_data()
    data.curriculum_requirements[:] = [
        CurriculumRequirement(2027, "Sec3", "COMBINED_SCIENCE", Decimal(300),
                              "SYNTHETIC test", "combined_unallocated")
    ]
    assert validate_workload_data(dataset, data)
    result = calculate_workload(dataset, data, "test")
    assert len(result.completeness) == 2
    assert all(row.required_periods is None for row in result.group_workload)


def test_same_subject_time_requirements_are_scoped_by_level():
    dataset = dataset_for()
    dataset.blocks.append(Block(2027, "Sec4", "A", 40))
    dataset.enrolments.append(Enrolment(2027, "Sec4", "A", "Science", "BIO", 40))
    data = workload_data()
    data.curriculum_requirements.append(CurriculumRequirement(2027, "Sec4", "BIO", Decimal(180)))
    result = calculate_workload(dataset, data, "test")
    assert {row.level: row.required_periods for row in result.group_workload} == {"Sec3": 5, "Sec4": 6}
    selected = calculate_workload(dataset, data, "test", academic_year=2027, level="Sec4")
    assert len(selected.group_workload) == 1
    assert cohort_summary(selected).total_required_teacher_periods == 6


def test_unknown_and_ambiguous_period_scenarios_are_rejected():
    data = workload_data()
    with pytest.raises(ValueError):
        calculate_workload(dataset_for(), data, "missing")
    data.period_scenarios.append(data.period_scenarios[0])
    with pytest.raises(ValueError):
        calculate_workload(dataset_for(), data, "test")


def test_invalid_selected_period_duration_is_rejected():
    data = workload_data(duration=0)
    assert validate_workload_data(dataset_for(), data)
    with pytest.raises(ValueError):
        calculate_workload(dataset_for(), data, "test")


def test_comparison_requires_two_distinct_period_scenarios():
    dataset = load_data(DATA_DIR)
    data = load_workload_data(DATA_DIR)
    for identifiers in (["p30"], ["p30", "p30"], ["p30", "unknown"]):
        with pytest.raises(ValueError):
            compare_period_scenarios(dataset, data, identifiers)


def test_scheduling_context_requires_scenario_and_valid_assignment_references():
    dataset = load_data(DATA_DIR)
    data = load_workload_data(DATA_DIR)
    scheduling = load_scheduling(DATA_DIR)
    with pytest.raises(ValueError):
        calculate_workload(dataset, data, "p30", teaching_scenario_id="separate_science")
    with pytest.raises(ValueError):
        calculate_workload(dataset, data, "p30", scheduling=scheduling)
    scheduling.assignments[0] = replace(scheduling.assignments[0], window_id="UNKNOWN")
    with pytest.raises(ValueError):
        calculate_workload(dataset, data, "p30", scheduling=scheduling,
                           teaching_scenario_id="simultaneous_science")
