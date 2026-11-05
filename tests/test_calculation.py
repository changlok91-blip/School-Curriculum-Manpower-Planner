from pathlib import Path

import pytest

from curriculum_planner.calculation import calculate_group_count, calculate_groups
from curriculum_planner.loading import load_data
from curriculum_planner.models import Block, Dataset, Enrolment, SubjectRule
from curriculum_planner.reporting import summarize


DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def dataset_for(student_count=37, *, block_id="A", subject_id="G1_MATHEMATICS"):
    return Dataset(
        blocks=[Block(2027, "Sec3", block_id, student_count)],
        enrolments=[
            Enrolment(2027, "Sec3", block_id, "Mathematics", subject_id, student_count)
        ],
        subject_rules=[SubjectRule(subject_id, "G1 Mathematics", 40, 20)],
    )


@pytest.mark.parametrize(
    ("student_count", "limit", "expected"),
    [(0, 40, 0), (40, 40, 1), (41, 40, 2), (21, 20, 2)],
)
def test_group_count_rounds_up(student_count, limit, expected):
    assert calculate_group_count(student_count, limit) == expected


@pytest.mark.parametrize(
    ("student_count", "limit"),
    [(-1, 40), (20, 0), (20, -1), (1.5, 40), (True, 40), (20, False)],
)
def test_group_count_rejects_invalid_counts_and_limits(student_count, limit):
    with pytest.raises(ValueError):
        calculate_group_count(student_count, limit)


def test_zero_enrolment_has_no_groups_or_unused_places():
    result = calculate_groups(dataset_for(0))[0]
    assert result.groups_required == 0
    assert result.unused_places == 0


def test_preferred_limit_is_default_and_hard_limit_is_selectable():
    dataset = dataset_for()
    preferred = calculate_groups(dataset)[0]
    hard = calculate_groups(dataset, use_preferred=False)[0]
    assert preferred.student_count == 37
    assert preferred.planning_max_size == 20
    assert preferred.groups_required == 2
    assert preferred.unused_places == 3
    assert preferred.preferred_size_applied is True
    assert hard.planning_max_size == 40
    assert hard.groups_required == 1
    assert hard.unused_places == 3
    assert hard.preferred_size_applied is False


def test_hard_limit_of_twenty_cannot_be_relaxed():
    dataset = Dataset(
        blocks=[Block(2027, "Sec3", "A", 21)],
        enrolments=[Enrolment(2027, "Sec3", "A", "Elective 1", "DNT", 21)],
        subject_rules=[SubjectRule("DNT", "Design & Technology", 20, 20)],
    )
    for use_preferred in (True, False):
        result = calculate_groups(dataset, use_preferred=use_preferred)[0]
        assert result.groups_required == 2
        assert result.unused_places == 19
        assert result.planning_max_size == 20
        assert result.preferred_size_applied is False


def test_limits_come_from_editable_rules():
    dataset = dataset_for(37, subject_id="NEW_SUBJECT")
    dataset.subject_rules[:] = [SubjectRule("NEW_SUBJECT", "New subject", 15, 12)]
    result = calculate_groups(dataset)[0]
    assert result.planning_max_size == 12
    assert result.groups_required == 4
    assert result.unused_places == 11


def test_different_blocks_keep_their_own_groups():
    dataset = Dataset(
        blocks=[Block(2027, "Sec3", "A", 20), Block(2027, "Sec3", "B", 20)],
        enrolments=[
            Enrolment(2027, "Sec3", block, "English", "ENGLISH", 20)
            for block in ("A", "B")
        ],
        subject_rules=[SubjectRule("ENGLISH", "English", 40, 40)],
    )
    results = calculate_groups(dataset)
    assert {result.block_id for result in results} == {"A", "B"}
    assert len(results) == 2
    assert sum(result.groups_required for result in results) == 2
    subject = next(
        row for row in summarize(dataset, results) if row.summary_type == "subject"
    )
    assert subject.groups_required == 2


def test_new_block_and_band_are_processed_without_code_changes():
    dataset = load_data(DATA_DIR)
    dataset.blocks.append(Block(2027, "Sec3", "C", 41))
    dataset.enrolments.append(
        Enrolment(2027, "Sec3", "C", "New curriculum band", "G3_ENGLISH", 41)
    )
    results = calculate_groups(dataset)
    block_c = [row for row in results if row.block_id == "C"]
    assert len(block_c) == 1
    assert block_c[0].band_id == "New curriculum band"
    assert block_c[0].groups_required == 2
    assert sum(row.groups_required for row in results) == 72


def test_same_subject_in_distinct_bands_is_not_merged():
    dataset = dataset_for(20)
    dataset.enrolments.append(
        Enrolment(2027, "Sec3", "A", "Additional band", "G1_MATHEMATICS", 20)
    )
    results = calculate_groups(dataset)
    assert len(results) == 2
    assert sum(row.groups_required for row in results) == 2


def test_identical_block_labels_in_different_cohorts_remain_separate():
    dataset = Dataset(
        blocks=[
            Block(2027, "Sec3", "A", 20),
            Block(2028, "Sec3", "A", 21),
            Block(2027, "Sec4", "A", 22),
        ],
        enrolments=[
            Enrolment(block.academic_year, block.level, "A", "English", "ENG", block.student_count)
            for block in [
                Block(2027, "Sec3", "A", 20),
                Block(2028, "Sec3", "A", 21),
                Block(2027, "Sec4", "A", 22),
            ]
        ],
        subject_rules=[SubjectRule("ENG", "English", 40, 40)],
    )
    results = calculate_groups(dataset)
    assert len(results) == 3
    cohorts = [row for row in summarize(dataset, results) if row.summary_type == "cohort"]
    assert {(row.academic_year, row.level, row.unique_students, row.groups_required) for row in cohorts} == {
        (2027, "Sec3", 20, 1),
        (2028, "Sec3", 21, 1),
        (2027, "Sec4", 22, 1),
    }


def test_historical_baseline_by_block_and_band():
    dataset = load_data(DATA_DIR)
    results = calculate_groups(dataset)
    actual = {}
    for row in results:
        key = row.block_id, row.band_id
        actual[key] = actual.get(key, 0) + row.groups_required
    assert actual == {
        ("A", "English"): 3,
        ("A", "Mathematics"): 3,
        ("A", "Science"): 9,
        ("A", "Humanities"): 7,
        ("A", "Elective 1"): 5,
        ("B", "English"): 6,
        ("B", "Mathematics"): 6,
        ("B", "Science"): 11,
        ("B", "Humanities"): 10,
        ("B", "Elective 1"): 7,
        ("B", "Elective 2"): 3,
    }
    assert sum(row.groups_required for row in results if row.block_id == "A") == 27
    assert sum(row.groups_required for row in results if row.block_id == "B") == 43
    assert sum(row.groups_required for row in results) == 70
    assert sum(row.preferred_size_applied for row in results) == 3


def test_hard_maximum_scenario_uses_sixty_seven_group_instances():
    results = calculate_groups(load_data(DATA_DIR), use_preferred=False)
    assert sum(row.groups_required for row in results) == 67
    assert not any(row.preferred_size_applied for row in results)


def test_summaries_keep_component_enrolments_and_unique_students_distinct():
    dataset = load_data(DATA_DIR)
    results = calculate_groups(dataset)
    summaries = summarize(dataset, results)
    science_a = next(
        row
        for row in summaries
        if row.summary_type == "band" and row.block_id == "A" and row.band_id == "Science"
    )
    assert science_a.component_enrolments == 230
    assert science_a.unique_students is None
    block_a = next(
        row for row in summaries if row.summary_type == "block" and row.block_id == "A"
    )
    assert block_a.unique_students == 115
    cohort = next(row for row in summaries if row.summary_type == "cohort")
    assert cohort.unique_students == 260
    assert cohort.groups_required == 70
    assert cohort.component_enrolments == sum(row.student_count for row in results)
    assert {row.summary_type for row in summaries} == {"subject", "band", "block", "cohort"}
