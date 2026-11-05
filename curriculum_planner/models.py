"""Data contracts shared by the CLI and future interfaces."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Block:
    academic_year: int
    level: str
    block_id: str
    student_count: int
    form_classes: str = ""


@dataclass(frozen=True)
class Enrolment:
    academic_year: int
    level: str
    block_id: str
    band_id: str
    subject_id: str
    student_count: int


@dataclass(frozen=True)
class SubjectRule:
    subject_id: str
    subject_name: str
    hard_max_size: int
    preferred_max_size: int


@dataclass(frozen=True)
class Dataset:
    blocks: list[Block]
    enrolments: list[Enrolment]
    subject_rules: list[SubjectRule]


@dataclass(frozen=True)
class GroupResult:
    academic_year: int
    level: str
    block_id: str
    band_id: str
    subject_id: str
    subject_name: str
    student_count: int
    planning_max_size: int
    groups_required: int
    unused_places: int
    preferred_size_applied: bool


@dataclass(frozen=True)
class SummaryRow:
    summary_type: str
    academic_year: int
    level: str
    block_id: str
    band_id: str
    subject_id: str
    subject_name: str
    unique_students: int | None
    component_enrolments: int
    groups_required: int
    unused_places: int
