"""Streamlit views over the Component 3 calculation APIs."""

import csv
from dataclasses import asdict, fields
from io import StringIO
from pathlib import Path

import streamlit as st

from ..loading import DataLoadError
from ..models import Dataset
from ..scheduling.loading import load_scheduling
from .calculation import calculate_workload
from .loading import load_workload_data
from .models import CompletenessRow, GroupWorkload, WorkloadSummary
from .reporting import ASSESSMENT_LIMITS


def _csv_bytes(rows, row_type):
    buffer = StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=[field.name for field in fields(row_type)])
    writer.writeheader()
    writer.writerows(asdict(row) for row in rows)
    return buffer.getvalue().encode("utf-8-sig")


def _issues_csv(result):
    buffer = StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=["period_scenario_id", "issue"])
    writer.writeheader()
    writer.writerows({"period_scenario_id": result.scenario.period_scenario_id, "issue": issue}
                    for issue in result.validation_issues)
    return buffer.getvalue().encode("utf-8-sig")


def render_workload_page(dataset: Dataset, data_dir: Path) -> None:
    st.caption("Component 3 · Curriculum time and teaching workload")
    try:
        data = load_workload_data(data_dir)
        if not data.period_scenarios:
            raise ValueError("At least one period-duration scenario is required")
        cohorts = sorted({(block.academic_year, block.level) for block in dataset.blocks})
        year, level = st.sidebar.selectbox(
            "Workload cohort", cohorts, format_func=lambda cohort: f"{cohort[0]} · {cohort[1]}"
        )
        period_ids = [scenario.period_scenario_id for scenario in data.period_scenarios]
        names = {scenario.period_scenario_id: scenario.scenario_name for scenario in data.period_scenarios}
        period_id = st.sidebar.selectbox(
            "Period-duration scenario", period_ids,
            index=period_ids.index("p30") if "p30" in period_ids else 0,
            format_func=lambda identifier: f"{names[identifier]} ({identifier})",
        )
        use_preferred = st.sidebar.checkbox("Use preferred group sizes", value=True)
        retain_windows = st.sidebar.checkbox("Retain teaching-window assignments", value=False)
        scheduling = None
        teaching_id = None
        if retain_windows:
            scheduling = load_scheduling(data_dir)
            teaching_names = {scenario.scenario_id: scenario.scenario_name for scenario in scheduling.scenarios}
            if not teaching_names:
                raise ValueError("No teaching-window scenarios are configured")
            teaching_id = st.sidebar.selectbox(
                "Teaching-window scenario", list(teaching_names),
                format_func=lambda identifier: f"{teaching_names[identifier]} ({identifier})",
            )
        options = dict(use_preferred=use_preferred, scheduling=scheduling,
                       teaching_scenario_id=teaching_id, academic_year=year, level=level)
        result = calculate_workload(dataset, data, period_id, **options)
    except (DataLoadError, ValueError) as exc:
        st.error(f"Unable to calculate curriculum workload: {exc}")
        st.stop()

    cohort = next(row for row in result.summaries if row.scope == "level")
    st.subheader(result.scenario.scenario_name)
    periods, minutes, calculated, missing = st.columns(4)
    periods.metric("Known teacher-periods", cohort.known_required_teacher_periods)
    minutes.metric("Known scheduled teacher-minutes", str(cohort.known_scheduled_teacher_minutes))
    calculated.metric("Groups calculated", cohort.calculated_group_count)
    missing.metric("Groups with unknown workload", cohort.uncalculated_group_count)
    st.caption(f"Calculated {cohort.calculated_group_count} of {cohort.teaching_group_count} "
               f"subject-component group instances for {year} {level}. "
               f"Known minimum requirement: {cohort.known_minimum_teacher_minutes} teacher-minutes weekly; "
               f"known excess: {cohort.known_excess_teacher_minutes} teacher-minutes weekly.")
    if result.completeness or result.validation_issues:
        st.warning("Incomplete curriculum-time data: displayed figures are known subtotals only. "
                   "The complete cohort workload is unknown; missing values are not zero.")
    sources = sorted({row.requirement_source for row in result.group_workload if row.requirement_source})
    if any("synthetic" in source.lower() for source in sources):
        st.warning("Synthetic demonstration requirements are in use. They are not official MOE curriculum requirements.")
    st.caption("Requirement sources: " + ("; ".join(sources) if sources else "none supplied"))
    for limitation in ASSESSMENT_LIMITS:
        st.caption(limitation)
    if result.validation_issues:
        with st.expander("Input validation issues", expanded=True):
            for issue in result.validation_issues:
                st.write(issue)

    try:
        comparisons = [calculate_workload(dataset, data, identifier, **options) for identifier in period_ids]
        comparison_rows = [row for assessment in comparisons for row in assessment.summaries
                           if row.scope == "level"]
        comparison_error = None
    except ValueError as exc:
        comparison_rows = []
        comparison_error = str(exc)

    tabs = st.tabs(["Group workload", "By subject", "By block and band", "Whole cohort",
                    "Compare period durations", "Missing or invalid requirements"])
    reports = [
        (tabs[0], result.group_workload, GroupWorkload, "teaching_group_workload.csv"),
        (tabs[1], [row for row in result.summaries if row.scope == "subject"],
         WorkloadSummary, "subject_workload_summary.csv"),
        (tabs[2], [row for row in result.summaries if row.scope in {"block", "band"}],
         WorkloadSummary, "block_workload_summary.csv"),
        (tabs[3], [cohort], WorkloadSummary, "cohort_workload_summary.csv"),
        (tabs[4], comparison_rows, WorkloadSummary, "period_duration_comparison.csv"),
        (tabs[5], result.completeness, CompletenessRow, "data_completeness.csv"),
    ]
    for tab, rows, row_type, filename in reports:
        with tab:
            if filename == "period_duration_comparison.csv" and comparison_error:
                st.error(f"Fix period scenarios before comparing: {comparison_error}")
                continue
            st.dataframe([asdict(row) for row in rows], use_container_width=True, hide_index=True)
            st.download_button("Download CSV", _csv_bytes(rows, row_type),
                               file_name=filename, mime="text/csv", key=f"workload_{filename}")
    st.download_button("Download validation issues", _issues_csv(result),
                       file_name="validation_issues.csv", mime="text/csv")
    st.sidebar.caption("Edit curriculum_requirements.csv and period_scenarios.csv in data/ to change "
                       "time inputs. Teaching-window assignments are context, not scheduled weekly lessons.")
