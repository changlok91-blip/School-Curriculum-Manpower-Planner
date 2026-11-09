"""Component 2 tests: abstract concurrency, never full timetable feasibility."""

from dataclasses import replace
import json
from pathlib import Path

import pytest

from curriculum_planner.calculation import calculate_groups
from curriculum_planner.loading import DataLoadError, load_data
from curriculum_planner.models import Block, Enrolment, GroupResult
from curriculum_planner.scheduling.calculation import compare_scenarios, run_scenario
from curriculum_planner.scheduling.groups import generate_teaching_groups
from curriculum_planner.scheduling.loading import load_scheduling
from curriculum_planner.scheduling.models import (
    GroupAssignment, Scenario, SchedulingData, TeacherPool, TeachingWindow,
)
from curriculum_planner.scheduling.validation import validate_scheduling


DATA_DIR = Path(__file__).resolve().parents[1] / "data"


@pytest.fixture
def historical_groups():
    return generate_teaching_groups(calculate_groups(load_data(DATA_DIR)))


def synthetic_groups():
    return generate_teaching_groups([
        GroupResult(2027, "Sec3", "A", "Science", "BIO", "Biology", 20, 40, 1, 20, False),
        GroupResult(2027, "Sec3", "B", "Science", "CHEM", "Chemistry", 20, 40, 1, 20, False),
    ])


def simple_scenario(groups, *, independent_pools=False, availability=1):
    pools = [TeacherPool("s", "shared", "Shared teachers", availability)]
    if independent_pools:
        pools.append(TeacherPool("s", "other", "Independent teachers", availability))
    assignments = [
        GroupAssignment("s", "w", group.teaching_group_id,
                        "other" if independent_pools and index else "shared")
        for index, group in enumerate(groups)
    ]
    return SchedulingData(
        [Scenario("s", "Test scenario")],
        [TeachingWindow("s", "w", "Window")],
        assignments,
        pools,
    )


def test_biology_demo_has_four_groups_in_both_scenarios(historical_groups):
    scheduling = load_scheduling(DATA_DIR)
    simultaneous = run_scenario(historical_groups, scheduling, "simultaneous_science")
    separate = run_scenario(historical_groups, scheduling, "separate_science")
    assert len(historical_groups) == 70
    first = simultaneous.resource_pool_summary[0]
    second = separate.resource_pool_summary[0]
    assert first.available_teacher_count == second.available_teacher_count == 2
    assert first.peak_simultaneous_demand == 4
    assert first.maximum_shortage == 2
    assert "violated" in first.concurrency_status.lower()
    assert second.peak_simultaneous_demand == 2
    assert second.maximum_shortage == 0
    assert "satisfied" in second.concurrency_status.lower()
    assert {row.concurrent_demand for row in separate.window_summary} == {2}
    assert sum(row.group_count for row in simultaneous.window_summary) == 4
    assert sum(row.group_count for row in separate.window_summary) == 4
    assert simultaneous.comparison.windows_used == 1
    assert separate.comparison.windows_used == 2
    assert simultaneous.comparison.concurrency_violations == 1
    assert separate.comparison.concurrency_violations == 0


def test_partial_demo_reports_sixty_six_unassessed_groups(historical_groups):
    data = load_scheduling(DATA_DIR)
    for scenario_id in ("simultaneous_science", "separate_science"):
        result = run_scenario(historical_groups, data, scenario_id)
        comparison = result.comparison
        assert comparison.total_group_instances == 70
        assert comparison.scheduled_group_instances == 4
        assert comparison.unscheduled_group_instances == 66
        assert len(result.unscheduled_groups) == 66
        assert "partial" in comparison.assessment_completeness.lower()
        assert comparison.full_timetable_feasibility == "not yet assessed"
        assert comparison.student_compatibility == "unverified"
        assert comparison.shared_teacher_capacity == "not validated"
        assert comparison.weekly_teaching_capacity == "not assessed"
        assigned = {a.teaching_group_id for a in data.assignments if a.scenario_id == scenario_id}
        unassigned = {g.teaching_group_id for g in result.unscheduled_groups}
        assert not assigned & unassigned
        assert assigned | unassigned == {g.teaching_group_id for g in historical_groups}


def test_demo_assigns_the_four_actual_biology_components(historical_groups):
    data = load_scheduling(DATA_DIR)
    expected = {
        ("A", "G3_PURE_BIOLOGY", 14), ("A", "G3_SCIENCE_BIO", 34),
        ("B", "G3_SCIENCE_BIO", 17), ("B", "G2_SCIENCE_BIO", 40),
    }
    for scenario_id in ("simultaneous_science", "separate_science"):
        assigned = {row.teaching_group_id for row in data.assignments if row.scenario_id == scenario_id}
        components = {(g.block_id, g.subject_id, g.component_student_count)
                      for g in historical_groups if g.teaching_group_id in assigned}
        assert components == expected
        assert len(assigned) == 4


def test_different_subjects_in_shared_pool_add_to_concurrent_demand():
    groups = synthetic_groups()
    result = run_scenario(groups, simple_scenario(groups), "s")
    pool = result.resource_pool_summary[0]
    assert pool.peak_simultaneous_demand == 2
    assert pool.maximum_shortage == 1
    assert {row.concurrent_demand for row in result.window_summary} == {2}
    assert result.comparison.concurrency_violations == 1
    assert json.loads(result.comparison.peak_concurrent_demand_by_pool) == {"shared": 2}


def test_independent_pools_keep_their_own_concurrency():
    groups = synthetic_groups()
    result = run_scenario(groups, simple_scenario(groups, independent_pools=True), "s")
    assert {pool.teacher_pool_id: pool.peak_simultaneous_demand
            for pool in result.resource_pool_summary} == {"shared": 1, "other": 1}
    assert all(pool.maximum_shortage == 0 for pool in result.resource_pool_summary)
    assert result.comparison.concurrency_violations == 0
    # Complete placement is still only a concurrency assessment, not a timetable.
    assert result.comparison.unscheduled_group_instances == 0
    assert result.comparison.full_timetable_feasibility == "not yet assessed"
    assert "concurrency" in result.comparison.assessment_completeness.lower()


def test_adding_block_c_requires_only_data_changes():
    dataset = load_data(DATA_DIR)
    dataset.blocks.append(Block(2027, "Sec3", "C", 41))
    dataset.enrolments.append(Enrolment(2027, "Sec3", "C", "New band", "G3_ENGLISH", 41))
    groups = generate_teaching_groups(calculate_groups(dataset))
    new_groups = [g for g in groups if g.block_id == "C"]
    assert len(new_groups) == 2
    data = simple_scenario(new_groups, availability=2)
    result = run_scenario(groups, data, "s")
    assert result.resource_pool_summary[0].peak_simultaneous_demand == 2
    assert result.comparison.scheduled_group_instances == 2
    assert result.comparison.unscheduled_group_instances == 70
    assert {row.block_id for row in result.window_summary} == {"C"}


def test_each_component_group_has_distinct_stable_identity(historical_groups):
    poa = [g for g in historical_groups if g.subject_id == "G3_PRINCIPLES_OF_ACCOUNTS"]
    assert len(poa) == 2
    assert {g.group_number for g in poa} == {1, 2}
    assert len({g.teaching_group_id for g in historical_groups}) == 70
    results = calculate_groups(load_data(DATA_DIR))
    reordered = generate_teaching_groups(list(reversed(results)))
    assert {g.teaching_group_id for g in reordered} == {g.teaching_group_id for g in historical_groups}
    grown = generate_teaching_groups(results + [
        GroupResult(2027, "Sec3", "C", "New", "NEW", "New subject", 1, 40, 1, 39, False),
    ])
    assert {g.teaching_group_id for g in historical_groups} < {g.teaching_group_id for g in grown}


def test_group_identifiers_escape_delimiters_and_include_full_identity():
    row = GroupResult(2027, "Sec3", "A/B", "Band %", "S/1", "Subject", 1, 40, 1, 39, False)
    rows = [row, replace(row, block_id="A", band_id="B/Band %"),
            replace(row, academic_year=2028), replace(row, level="Sec4")]
    groups = generate_teaching_groups(rows)
    assert len({g.teaching_group_id for g in groups}) == 4
    assert all(len(g.teaching_group_id.split("/")) == 6 for g in groups)
    assert any("%2F" in g.teaching_group_id for g in groups)
    assert all(" " not in g.teaching_group_id for g in groups)


@pytest.mark.parametrize("change", ["unknown_group", "duplicate_placement", "unknown_window", "unknown_pool"])
def test_invalid_group_placement_is_flagged_and_refused(change):
    groups = synthetic_groups()
    data = simple_scenario(groups)
    if change == "unknown_group":
        data.assignments[0] = replace(data.assignments[0], teaching_group_id="not-a-group")
    elif change == "duplicate_placement":
        data.windows.append(TeachingWindow("s", "w2", "Another window"))
        data.assignments.append(replace(data.assignments[0], window_id="w2"))
    elif change == "unknown_window":
        data.assignments[0] = replace(data.assignments[0], window_id="missing")
    else:
        data.assignments[0] = replace(data.assignments[0], teacher_pool_id="missing")
    assert validate_scheduling(data, groups)
    with pytest.raises(ValueError):
        run_scenario(groups, data, "s")


@pytest.mark.parametrize("kind", ["scenario", "window", "pool"])
def test_duplicate_configuration_identifiers_are_flagged(kind):
    groups = synthetic_groups()
    data = simple_scenario(groups)
    collection = {"scenario": data.scenarios, "window": data.windows, "pool": data.teacher_pools}[kind]
    collection.append(collection[0])
    assert validate_scheduling(data, groups)


def test_negative_pool_availability_is_invalid_but_zero_is_valid():
    groups = synthetic_groups()
    data = simple_scenario(groups, availability=-1)
    assert validate_scheduling(data, groups)
    data.teacher_pools[0] = replace(data.teacher_pools[0], available_teacher_count=0)
    assert validate_scheduling(data, groups) == []
    result = run_scenario(groups, data, "s")
    assert result.resource_pool_summary[0].maximum_shortage == 2


def test_idle_windows_and_pools_have_zero_demand():
    groups = synthetic_groups()
    data = simple_scenario(groups, availability=2)
    data.windows.append(TeachingWindow("s", "idle", "Unused window"))
    data.teacher_pools.append(TeacherPool("s", "idle", "Unused pool", 0))
    result = run_scenario(groups, data, "s")
    assert result.comparison.teaching_windows == 2
    assert result.comparison.windows_used == 1
    unused_pool = next(pool for pool in result.resource_pool_summary if pool.teacher_pool_id == "idle")
    assert unused_pool.peak_simultaneous_demand == 0
    assert unused_pool.maximum_shortage == 0
    assert all(row.concurrent_demand == 0 for row in result.window_summary if row.window_id == "idle")


def test_no_placements_reports_all_groups_unassessed():
    groups = synthetic_groups()
    data = simple_scenario(groups)
    data.assignments.clear()
    result = run_scenario(groups, data, "s")
    assert result.comparison.scheduled_group_instances == 0
    assert result.comparison.unscheduled_group_instances == 2
    assert result.comparison.windows_used == 0
    assert len(result.unscheduled_groups) == 2
    assert "partial" in result.comparison.assessment_completeness.lower()
    assert "no configured groups assessed" in result.comparison.concurrency_status.lower()
    assert result.resource_pool_summary[0].peak_simultaneous_demand == 0
    assert "no configured groups assessed" in result.resource_pool_summary[0].concurrency_status.lower()


def test_empty_inventory_is_not_reported_as_successful_assessment():
    data = simple_scenario([])
    result = run_scenario([], data, "s")
    assert result.comparison.total_group_instances == 0
    assert result.comparison.scheduled_group_instances == 0
    assert result.comparison.unscheduled_group_instances == 0
    assert result.unscheduled_groups == []
    assert "nothing assessed" in result.comparison.assessment_completeness.lower()
    assert "no configured groups assessed" in result.comparison.concurrency_status.lower()
    assert result.comparison.full_timetable_feasibility == "not yet assessed"


def test_scenario_without_windows_or_pools_is_an_unscheduled_plan():
    groups = synthetic_groups()
    data = SchedulingData([Scenario("s", "Not configured yet")], [], [], [])
    assert validate_scheduling(data, groups) == []
    result = run_scenario(groups, data, "s")
    assert result.comparison.teaching_windows == result.comparison.windows_used == 0
    assert result.comparison.unscheduled_group_instances == 2
    assert result.window_summary == result.resource_pool_summary == []
    assert result.comparison.full_timetable_feasibility == "not yet assessed"


def test_window_and_pool_identifiers_are_scoped_to_scenario():
    groups = synthetic_groups()
    data = simple_scenario(groups, availability=2)
    data.scenarios.append(Scenario("other", "Other scenario"))
    data.windows.append(TeachingWindow("other", "w", "Other window"))
    data.teacher_pools.append(TeacherPool("other", "shared", "Other pool", 0))
    data.assignments.append(GroupAssignment("other", "w", groups[0].teaching_group_id, "shared"))
    assert validate_scheduling(data, groups) == []
    first = run_scenario(groups, data, "s")
    other = run_scenario(groups, data, "other")
    assert first.resource_pool_summary[0].available_teacher_count == 2
    assert first.resource_pool_summary[0].peak_simultaneous_demand == 2
    assert first.resource_pool_summary[0].maximum_shortage == 0
    assert other.resource_pool_summary[0].available_teacher_count == 0
    assert other.resource_pool_summary[0].peak_simultaneous_demand == 1
    assert other.resource_pool_summary[0].maximum_shortage == 1
    assert other.comparison.unscheduled_group_instances == 1


@pytest.mark.parametrize("kind", ["window", "pool", "assignment"])
def test_configuration_references_to_missing_scenario_are_rejected(kind):
    groups = synthetic_groups()
    data = simple_scenario(groups)
    collection = {"window": data.windows, "pool": data.teacher_pools,
                  "assignment": data.assignments}[kind]
    collection[0] = replace(collection[0], scenario_id="missing")
    errors = validate_scheduling(data, groups)
    assert any("unknown scenario" in error.lower() for error in errors)
    with pytest.raises(ValueError):
        run_scenario(groups, data, "s")


def test_duplicate_generated_inventory_cannot_be_counted_twice():
    groups = synthetic_groups()
    data = simple_scenario(groups)
    groups.append(groups[0])
    assert any("duplicate" in error.lower() for error in validate_scheduling(data, groups))
    with pytest.raises(ValueError):
        run_scenario(groups, data, "s")


def test_unknown_scenario_and_invalid_comparisons_are_rejected(historical_groups):
    data = load_scheduling(DATA_DIR)
    with pytest.raises(ValueError):
        run_scenario(historical_groups, data, "missing")
    for identifiers in (["simultaneous_science"], ["simultaneous_science"] * 2,
                        ["simultaneous_science", "missing"]):
        with pytest.raises(ValueError):
            compare_scenarios(historical_groups, data, identifiers)


def test_component_one_baseline_is_unchanged_after_running_scenarios():
    dataset = load_data(DATA_DIR)
    before = calculate_groups(dataset)
    groups = generate_teaching_groups(before)
    compare_scenarios(groups, load_scheduling(DATA_DIR), ["simultaneous_science", "separate_science"])
    assert calculate_groups(dataset) == before
    assert sum(row.groups_required for row in before) == 70


def write_scheduling_csvs(directory, *, teacher_count="2"):
    files = {
        "scenarios.csv": "scenario_id,scenario_name,description\ns,Scenario,\n",
        "teaching_windows.csv": "scenario_id,window_id,window_name\ns,w,Window\n",
        "group_assignments.csv": "scenario_id,window_id,teaching_group_id,teacher_pool_id\n",
        "teacher_pools.csv": "scenario_id,teacher_pool_id,pool_name,available_teacher_count\n"
                             f"s,p,Teachers,{teacher_count}\n",
    }
    for name, content in files.items():
        (directory / name).write_text(content, encoding="utf-8")


def test_csv_loader_accepts_empty_description_and_no_assignments(tmp_path):
    write_scheduling_csvs(tmp_path)
    data = load_scheduling(tmp_path)
    assert data.scenarios[0].description == ""
    assert data.teacher_pools[0].available_teacher_count == 2
    assert data.assignments == []


@pytest.mark.parametrize("teacher_count", ["two", "1.5", ""])
def test_csv_loader_rejects_invalid_teacher_count(tmp_path, teacher_count):
    write_scheduling_csvs(tmp_path, teacher_count=teacher_count)
    with pytest.raises(DataLoadError):
        load_scheduling(tmp_path)


def test_csv_loader_reports_missing_file(tmp_path):
    with pytest.raises(DataLoadError):
        load_scheduling(tmp_path)
