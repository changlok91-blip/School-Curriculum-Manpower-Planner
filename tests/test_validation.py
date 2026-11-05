from pathlib import Path

import pytest

from curriculum_planner.calculation import calculate_groups
from curriculum_planner.loading import DataLoadError, load_data
from curriculum_planner.models import Block, Dataset, Enrolment, SubjectRule
from curriculum_planner.validation import validate_data


DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def valid_dataset():
    return Dataset(
        blocks=[Block(2027, "Sec3", "A", 40)],
        enrolments=[Enrolment(2027, "Sec3", "A", "English", "ENG", 40)],
        subject_rules=[SubjectRule("ENG", "English", 40, 40)],
    )


def write_csv_inputs(directory, *, blocks=None, enrolments=None, subject_rules=None):
    directory.mkdir(exist_ok=True)
    contents = {
        "blocks.csv": blocks or "academic_year,level,block_id,student_count,form_classes\n2027,Sec3,A,40,\n",
        "enrolments.csv": enrolments or "academic_year,level,block_id,band_id,subject_id,student_count\n2027,Sec3,A,English,ENG,40\n",
        "subject_rules.csv": subject_rules or "subject_id,subject_name,hard_max_size,preferred_max_size\nENG,English,40,40\n",
    }
    for filename, content in contents.items():
        (directory / filename).write_text(content, encoding="utf-8")


def test_historical_data_is_valid():
    dataset = load_data(DATA_DIR)
    assert validate_data(dataset) == []
    assert len(dataset.blocks) == 2
    assert len(dataset.enrolments) == 44


def test_seed_data_preserves_actual_component_counts_and_subject_distinctions():
    dataset = load_data(DATA_DIR)
    actual = {
        (row.block_id, row.band_id, row.subject_id): row.student_count
        for row in dataset.enrolments
    }
    assert actual[("A", "Science", "G3_PURE_CHEMISTRY")] == 29
    assert actual[("A", "Science", "G3_SCIENCE_CHEM")] == 86
    assert actual[("A", "Science", "G3_PURE_PHYSICS")] == 15
    assert actual[("A", "Science", "G3_PURE_BIOLOGY")] == 14
    assert actual[("B", "Mathematics", "G1_MATHEMATICS")] == 37
    assert sum(
        count for (block, band, _), count in actual.items()
        if block == "B" and band == "Elective 2"
    ) == 38
    assert {(row.academic_year, row.level) for row in dataset.enrolments} == {(2027, "Sec3")}
    assert {row.block_id: row.student_count for row in dataset.blocks} == {"A": 115, "B": 145}
    assert next(row for row in dataset.blocks if row.block_id == "A").form_classes == "3A;3B;3C"


def test_negative_enrolments_are_flagged_and_calculation_refuses_them():
    dataset = valid_dataset()
    dataset.enrolments[:] = [Enrolment(2027, "Sec3", "A", "English", "ENG", -1)]
    assert validate_data(dataset)
    with pytest.raises(ValueError):
        calculate_groups(dataset)


def test_missing_subject_rule_is_flagged():
    dataset = valid_dataset()
    dataset.subject_rules.clear()
    assert validate_data(dataset)
    with pytest.raises(ValueError):
        calculate_groups(dataset)


def test_duplicate_enrolment_identity_is_flagged_even_if_counts_differ():
    dataset = valid_dataset()
    dataset.enrolments.append(Enrolment(2027, "Sec3", "A", "English", "ENG", 10))
    errors = validate_data(dataset)
    assert errors
    assert any("duplicate" in error.lower() for error in errors)


def test_component_sums_can_exceed_unique_block_population():
    dataset = Dataset(
        blocks=[Block(2027, "Sec3", "A", 40)],
        enrolments=[
            Enrolment(2027, "Sec3", "A", "Science", "CHEM", 40),
            Enrolment(2027, "Sec3", "A", "Science", "PHY", 40),
        ],
        subject_rules=[
            SubjectRule("CHEM", "Science (Chem)", 40, 40),
            SubjectRule("PHY", "Science (Phy)", 40, 40),
        ],
    )
    assert validate_data(dataset) == []
    assert sum(row.groups_required for row in calculate_groups(dataset)) == 2


@pytest.mark.parametrize("hard,preferred", [(0, 20), (-1, 20), (20, 0), (20, -1), (20, 40)])
def test_invalid_group_limits_are_flagged(hard, preferred):
    dataset = valid_dataset()
    dataset.subject_rules[:] = [SubjectRule("ENG", "English", hard, preferred)]
    assert validate_data(dataset)


def test_unknown_block_is_flagged():
    dataset = valid_dataset()
    dataset.enrolments[:] = [Enrolment(2027, "Sec3", "missing", "English", "ENG", 10)]
    assert validate_data(dataset)


def test_repeated_block_and_rule_ids_are_flagged():
    dataset = valid_dataset()
    dataset.blocks.append(dataset.blocks[0])
    dataset.subject_rules.append(dataset.subject_rules[0])
    errors = validate_data(dataset)
    assert len(errors) >= 2


def test_missing_form_classes_column_is_allowed(tmp_path):
    write_csv_inputs(
        tmp_path,
        blocks="academic_year,level,block_id,student_count\n2027,Sec3,A,40\n",
    )
    dataset = load_data(tmp_path)
    assert validate_data(dataset) == []
    assert dataset.blocks[0].form_classes == ""


def test_missing_required_column_is_reported(tmp_path):
    write_csv_inputs(tmp_path, enrolments="academic_year,level,block_id,band_id,student_count\n2027,Sec3,A,English,40\n")
    with pytest.raises(DataLoadError):
        load_data(tmp_path)


def test_non_integer_enrolment_is_reported(tmp_path):
    write_csv_inputs(tmp_path, enrolments="academic_year,level,block_id,band_id,subject_id,student_count\n2027,Sec3,A,English,ENG,forty\n")
    with pytest.raises(DataLoadError):
        load_data(tmp_path)


def test_missing_file_is_reported(tmp_path):
    with pytest.raises(DataLoadError):
        load_data(tmp_path)
