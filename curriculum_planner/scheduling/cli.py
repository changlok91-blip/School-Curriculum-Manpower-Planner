"""CLI adapter for Component 2; existing Component 1 commands stay unchanged."""

from pathlib import Path

from ..calculation import calculate_groups
from ..loading import load_data
from ..reporting import _table
from .calculation import compare_scenarios, run_scenario
from .groups import generate_teaching_groups
from .loading import load_scheduling
from .reporting import (
    export_scenario_results, export_teaching_groups, format_comparison, format_scenario,
    format_teaching_groups,
)
from .validation import validate_scheduling


def register_commands(commands):
    root = commands.add_parser("scenarios", help="Component 2: teaching-window concurrency")
    actions = root.add_subparsers(dest="scenario_command", required=True)
    for action, help_text in (
        ("list", "List editable scheduling scenarios"),
        ("validate", "Validate scenario files against generated teaching-group IDs"),
        ("groups", "List or export the generated teaching-group inventory"),
        ("run", "Assess one scenario"),
        ("compare", "Compare two or more scenarios"),
        ("export", "Export reports for one or more scenarios"),
    ):
        parser = actions.add_parser(action, help=help_text)
        parser.add_argument("--data-dir", type=Path, default=Path("data"),
                            help="Directory containing Component 1 and Component 2 CSVs")
        parser.add_argument("--use-hard-max", action="store_true",
                            help="Generate the group inventory using hard rather than preferred sizes")
        if action == "run":
            parser.add_argument("scenario_id")
        if action in {"compare", "export"}:
            parser.add_argument("scenario_ids", nargs="+")
        if action == "groups":
            parser.add_argument("--output", type=Path, help="Optional CSV inventory destination")
        if action == "export":
            parser.add_argument("--output-dir", type=Path, default=Path("output/scenarios"))


def run_command(args) -> int:
    action = args.scenario_command
    if action == "list":
        data = load_scheduling(args.data_dir)
        print(_table(
            ["Scenario ID", "Name", "Description"],
            [[s.scenario_id, s.scenario_name, s.description] for s in data.scenarios],
        ))
        return 0
    groups = generate_teaching_groups(calculate_groups(
        load_data(args.data_dir), use_preferred=not args.use_hard_max,
    ))
    if action == "groups":
        print(format_teaching_groups(groups))
        if args.output:
            print(f"Exported inventory: {export_teaching_groups(groups, args.output)}")
        return 0
    data = load_scheduling(args.data_dir)
    errors = validate_scheduling(data, groups)
    if errors:
        raise ValueError("Scenario validation failed:\n" + "\n".join(f"- {error}" for error in errors))
    if action == "validate":
        print(f"Scenario validation passed: {len(data.scenarios)} scenarios, {len(groups)} generated groups, "
              f"{len(data.assignments)} placements across scenarios.")
        print("Input validation does not establish staffing or timetable feasibility.")
    elif action == "run":
        print(format_scenario(run_scenario(groups, data, args.scenario_id)))
    elif action == "compare":
        print(format_comparison(compare_scenarios(groups, data, args.scenario_ids)))
    else:
        if len(set(args.scenario_ids)) != len(args.scenario_ids):
            raise ValueError("Export requires distinct scenario IDs")
        results = [run_scenario(groups, data, scenario_id) for scenario_id in args.scenario_ids]
        print(format_comparison(results))
        for path in export_scenario_results(results, groups, args.output_dir):
            print(f"Exported: {path}")
    return 0
