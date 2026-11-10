"""Streamlit entry point for teaching-group and concurrency assessments."""

import csv
from dataclasses import asdict, fields
from io import StringIO
from pathlib import Path

import streamlit as st

from curriculum_planner import (
    DataLoadError, Dataset, GroupResult, SummaryRow,
    calculate_groups, load_data, summarize, validate_data,
)
from curriculum_planner.scheduling.calculation import run_scenario
from curriculum_planner.scheduling.groups import generate_teaching_groups
from curriculum_planner.scheduling.loading import load_scheduling
from curriculum_planner.scheduling.models import (
    PoolSummary, ScenarioComparison, TeachingGroup, UnscheduledGroup, WindowSummary,
)
from curriculum_planner.scheduling.reporting import ASSESSMENT_LIMITS
from curriculum_planner.scheduling.validation import validate_scheduling


def csv_download(rows, row_type):
    buffer = StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=[field.name for field in fields(row_type)])
    writer.writeheader()
    writer.writerows(asdict(row) for row in rows)
    return buffer.getvalue().encode("utf-8-sig")


def show_scenarios(data):
    st.caption("Component 2 · Teaching-window concurrency")
    use_preferred = st.sidebar.checkbox("Use preferred group sizes", value=True)
    try:
        groups = generate_teaching_groups(calculate_groups(data, use_preferred=use_preferred))
        scheduling = load_scheduling(Path(__file__).resolve().parent / "data")
        errors = validate_scheduling(scheduling, groups)
        if errors:
            raise ValueError("\n".join(errors))
        names = {s.scenario_id: s.scenario_name for s in scheduling.scenarios}
        scenario_id = st.sidebar.selectbox(
            "Scheduling scenario", list(names),
            format_func=lambda identifier: f"{names[identifier]} ({identifier})",
        )
        assessments = [run_scenario(groups, scheduling, identifier) for identifier in names]
    except (DataLoadError, ValueError) as exc:
        st.error(f"Correct the scenario input files before assessing concurrency: {exc}")
        st.stop()
    result = next(item for item in assessments if item.scenario.scenario_id == scenario_id)
    comparison = result.comparison
    st.subheader(result.scenario.scenario_name)
    st.write(result.scenario.description)
    scheduled, unscheduled, windows, violations = st.columns(4)
    scheduled.metric("Groups scheduled", comparison.scheduled_group_instances)
    unscheduled.metric("Groups unscheduled / unassessed", comparison.unscheduled_group_instances)
    windows.metric("Windows used", comparison.windows_used)
    violations.metric("Pool/window violations", comparison.concurrency_violations)
    st.caption(f"{comparison.total_group_instances} total subject-component group instances; "
               f"{comparison.teaching_windows} windows configured. Abstract windows are not weekly periods.")
    if comparison.unscheduled_group_instances:
        st.warning(f"Partial assessment: {comparison.unscheduled_group_instances} groups remain unassessed. "
                   "This does not establish whole-cohort scheduling feasibility.")
    if comparison.concurrency_violations:
        st.error(comparison.concurrency_status)
    elif comparison.scheduled_group_instances:
        st.success(comparison.concurrency_status)
    else:
        st.warning(comparison.concurrency_status)
    for limitation in ASSESSMENT_LIMITS:
        st.caption(limitation)

    tabs = st.tabs(["Teacher pools", "Teaching windows", "Unscheduled groups", "Compare scenarios"])
    reports = [
        (tabs[0], result.resource_pool_summary, PoolSummary, "resource_pool_summary.csv"),
        (tabs[1], result.window_summary, WindowSummary, "window_summary.csv"),
        (tabs[2], result.unscheduled_groups, UnscheduledGroup, "unscheduled_groups.csv"),
        (tabs[3], [item.comparison for item in assessments], ScenarioComparison, "scenario_comparison.csv"),
    ]
    for tab, rows, row_type, filename in reports:
        with tab:
            if row_type is WindowSummary:
                st.caption("group_count counts the block/band slice. concurrent_demand and shortage "
                           "repeat the entire pool/window total; do not sum those repeated values.")
            st.dataframe([asdict(row) for row in rows], use_container_width=True, hide_index=True)
            st.download_button("Download CSV", csv_download(rows, row_type),
                               file_name=filename, mime="text/csv", key=filename)
    st.download_button("Download teaching-group inventory", csv_download(groups, TeachingGroup),
                       file_name="teaching_groups.csv", mime="text/csv")
    st.sidebar.caption("Edit the scenario CSV files in data/ to change windows, placements or teacher pools.")


def main():
    st.set_page_config(page_title="School Curriculum Planner", layout="wide")
    st.title("School Curriculum & Manpower Planner")
    page = st.sidebar.radio("Page", ["Teaching groups (Component 1)", "Concurrency scenarios (Component 2)",
                                     "Curriculum workload (Component 3)"])
    st.info(
        "Results are provisional subject-component group instances. "
        "They do not establish a timetable or teacher allocation."
    )

    try:
        data = load_data(Path(__file__).resolve().parent / "data")
    except DataLoadError as exc:
        st.error(f"Unable to load input files: {exc}")
        st.stop()
    errors = validate_data(data)
    if errors:
        st.error("Correct the input CSV files before calculating.")
        for error in errors:
            st.error(error)
        st.stop()

    if page == "Concurrency scenarios (Component 2)":
        show_scenarios(data)
        return
    if page == "Curriculum workload (Component 3)":
        from curriculum_planner.workload.web import render_workload_page
        render_workload_page(data, Path(__file__).resolve().parent / "data")
        return
    st.caption("Component 1 · Teaching group calculator")
    cohorts = sorted({(block.academic_year, block.level) for block in data.blocks})
    year, level = st.sidebar.selectbox(
        "Cohort", cohorts, format_func=lambda cohort: f"{cohort[0]} · {cohort[1]}"
    )
    use_preferred = st.sidebar.checkbox("Use preferred group sizes", value=True)
    st.sidebar.caption(
        "Preferred limits apply by default. Uncheck to use hard maximum sizes. "
        "Edit the three files in data/ to change enrolments, blocks or subject rules."
    )
    selected = Dataset(
        [b for b in data.blocks if (b.academic_year, b.level) == (year, level)],
        [e for e in data.enrolments if (e.academic_year, e.level) == (year, level)],
        data.subject_rules,
    )
    results = calculate_groups(selected, use_preferred=use_preferred)
    summaries = summarize(selected, results)
    cohort = next(row for row in summaries if row.summary_type == "cohort")
    st.success(f"Input validation passed · {year} {level}")
    students, groups, unused = st.columns(3)
    students.metric("Unique students", cohort.unique_students)
    groups.metric("Subject-component group instances", cohort.groups_required)
    unused.metric("Unused component places", cohort.unused_places)
    st.caption(
        "Science and Humanities components may overlap. Component enrolments "
        "are not unique student populations. Groups remain separate between blocks."
    )

    detail_tab, band_tab, block_tab, subject_tab, cohort_tab = st.tabs(
        ["Subject details", "By band", "By block", "By subject", "Whole cohort"]
    )
    with detail_tab:
        st.dataframe([asdict(row) for row in results], use_container_width=True, hide_index=True)
    for tab, kind in ((band_tab, "band"), (block_tab, "block"),
                      (subject_tab, "subject"), (cohort_tab, "cohort")):
        with tab:
            st.dataframe(
                [asdict(row) for row in summaries if row.summary_type == kind],
                use_container_width=True, hide_index=True,
            )

    st.download_button(
        "Download detailed results", csv_download(results, GroupResult),
        file_name="group_results.csv", mime="text/csv",
    )
    st.download_button(
        "Download all summaries", csv_download(summaries, SummaryRow),
        file_name="summaries.csv", mime="text/csv",
    )
    with st.expander("View input data"):
        for title, rows in (("Blocks", selected.blocks), ("Enrolments", selected.enrolments),
                            ("Subject rules", selected.subject_rules)):
            st.write(title)
            st.dataframe([asdict(row) for row in rows], use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
