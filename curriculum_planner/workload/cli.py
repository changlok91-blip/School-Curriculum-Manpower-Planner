"""CLI for time requirements, independent period scenarios and weekly workload."""

from pathlib import Path

from ..calculation import calculate_groups
from ..loading import load_data
from ..reporting import _table
from ..scheduling.groups import generate_teaching_groups
from ..scheduling.loading import load_scheduling
from .calculation import calculate_workload
from .comparison import compare_period_scenarios
from .loading import load_workload_data
from .reporting import export_workload_results, format_comparison, format_workload
from .validation import validate_workload_data


def register_commands(commands):
    root = commands.add_parser("workload", help="Component 3: weekly curriculum time and teacher-periods")
    actions = root.add_subparsers(dest="workload_command", required=True)
    for action, help_text in (
        ("list", "List period-duration scenarios"),
        ("validate", "Flag invalid or missing curriculum time requirements"),
        ("run", "Calculate known workload for one period scenario"),
        ("compare", "Compare workload for two or more period scenarios"),
        ("export", "Export all workload reports for one or more period scenarios"),
    ):
        parser = actions.add_parser(action, help=help_text)
        parser.add_argument("--data-dir", type=Path, default=Path("data"))
        if action != "list":
            parser.add_argument("--use-hard-max", action="store_true")
            parser.add_argument("--academic-year", type=int)
            parser.add_argument("--level")
            parser.add_argument("--teaching-scenario", help="Optional Component 2 scenario: retain window metadata only")
        if action == "run":
            parser.add_argument("period_scenario_id")
        if action in {"compare", "export"}:
            parser.add_argument("period_scenario_ids", nargs="+")
        if action == "export":
            parser.add_argument("--output-dir", type=Path, default=Path("output/workload"))


def run_command(args) -> int:
    data = load_workload_data(args.data_dir)
    action = args.workload_command
    if action == "list":
        print(_table(
            ["Period scenario ID", "Name", "Minutes per period"],
            [[s.period_scenario_id, s.scenario_name, str(s.period_duration_minutes)]
             for s in data.period_scenarios],
        ))
        return 0
    dataset = load_data(args.data_dir)
    scheduling = load_scheduling(args.data_dir) if args.teaching_scenario else None
    options = dict(use_preferred=not args.use_hard_max, scheduling=scheduling,
                   teaching_scenario_id=args.teaching_scenario, academic_year=args.academic_year,
                   level=args.level)
    if action == "validate":
        issues = validate_workload_data(dataset, data, include_missing=False)
        groups = generate_teaching_groups(calculate_groups(dataset, use_preferred=not args.use_hard_max))
        groups = [g for g in groups if (args.academic_year is None or g.academic_year == args.academic_year)
                  and (args.level is None or g.level == args.level)]
        if not any((args.academic_year is None or b.academic_year == args.academic_year)
                   and (args.level is None or b.level == args.level) for b in dataset.blocks):
            raise ValueError("No curriculum blocks match the selected academic year and level")
        if scheduling is not None:
            from ..scheduling.assignments import assign_groups
            assign_groups(generate_teaching_groups(calculate_groups(dataset, use_preferred=not args.use_hard_max)),
                          scheduling, args.teaching_scenario)
        keys = {(r.academic_year, r.level, r.subject_id) for r in data.curriculum_requirements}
        issues.extend(f"Missing curriculum requirement for teaching group {g.teaching_group_id}"
                      for g in groups if (g.academic_year, g.level, g.subject_id) not in keys)
        if issues:
            print("Curriculum workload validation issues:\n" + "\n".join(f"- {issue}" for issue in issues))
            return 1
        print("Curriculum workload validation passed for the selected groups.")
        return 0
    if action == "run":
        print(format_workload(calculate_workload(dataset, data, args.period_scenario_id, **options)))
        return 0
    if action == "compare":
        print(format_comparison(compare_period_scenarios(dataset, data, args.period_scenario_ids, **options)))
        return 0
    if len(set(args.period_scenario_ids)) != len(args.period_scenario_ids):
        raise ValueError("Export requires distinct period scenario IDs")
    results = [calculate_workload(dataset, data, identifier, **options)
               for identifier in args.period_scenario_ids]
    print(format_comparison(results))
    for path in export_workload_results(results, args.output_dir):
        print(f"Exported: {path}")
    return 0
