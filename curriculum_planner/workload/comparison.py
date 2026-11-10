"""Compare period durations without altering group placement or teacher demand."""

from .calculation import calculate_workload


def compare_period_scenarios(dataset, data, scenario_ids: list[str], **kwargs):
    if len(scenario_ids) < 2 or len(set(scenario_ids)) != len(scenario_ids):
        raise ValueError("Comparison requires at least two distinct period scenario IDs")
    return [calculate_workload(dataset, data, identifier, **kwargs) for identifier in scenario_ids]
