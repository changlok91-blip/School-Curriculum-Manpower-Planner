"""Thin command-line interface around the independent Component 1 APIs."""

import argparse
import sys
from pathlib import Path

from .calculation import calculate_groups
from .loading import DataLoadError, load_data
from .reporting import export_results, format_report, summarize
from .validation import validate_data


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="School Curriculum & Manpower Planner — Component 1")
    commands = parser.add_subparsers(dest="command", required=True)
    for command, description in (
        ("validate", "Validate all editable input files"),
        ("calculate", "Display provisional subject-component group instances"),
        ("export", "Export detailed results and all summaries to CSV"),
    ):
        sub = commands.add_parser(command, help=description)
        sub.add_argument("--data-dir", type=Path, default=Path("data"), help="Input CSV directory (default: data)")
        if command != "validate":
            sub.add_argument("--use-hard-max", action="store_true", help="Plan using hard limits instead of preferred limits")
        if command == "export":
            sub.add_argument("--output-dir", type=Path, default=Path("output"), help="Export directory (default: output)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        dataset = load_data(args.data_dir)
        errors = validate_data(dataset)
        if errors:
            print("Input validation failed:\n" + "\n".join(f"- {error}" for error in errors), file=sys.stderr)
            return 1
        if args.command == "validate":
            print(f"Validation passed: {len(dataset.blocks)} blocks, {len(dataset.enrolments)} enrolment records, "
                  f"{len(dataset.subject_rules)} subject rules.")
            return 0
        results = calculate_groups(dataset, use_preferred=not args.use_hard_max)
        summaries = summarize(dataset, results)
        if args.command == "calculate":
            print(format_report(results, summaries))
        else:
            paths = export_results(results, summaries, args.output_dir)
            print("Exported provisional subject-component group instances:")
            for path in paths:
                print(path)
        return 0
    except (DataLoadError, ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
