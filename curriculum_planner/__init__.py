"""Component 1: independent CSV data, validation, calculation and reporting APIs."""

from .calculation import calculate_group_count, calculate_groups
from .loading import DataLoadError, load_data
from .models import Block, Dataset, Enrolment, GroupResult, SubjectRule, SummaryRow
from .reporting import summarize
from .validation import validate_data

__all__ = [
    "Block", "Dataset", "Enrolment", "GroupResult", "SubjectRule", "SummaryRow",
    "DataLoadError", "load_data", "validate_data", "calculate_group_count",
    "calculate_groups", "summarize",
]
