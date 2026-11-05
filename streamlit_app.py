"""Streamlit entry point for the Component 1 calculator."""

import csv
from dataclasses import asdict, fields
from io import StringIO
from pathlib import Path

import streamlit as st

from curriculum_planner import (
    DataLoadError, Dataset, GroupResult, SummaryRow,
    calculate_groups, load_data, summarize, validate_data,
)


def csv_download(rows, row_type):
    buffer = StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=[field.name for field in fields(row_type)])
    writer.writeheader()
    writer.writerows(asdict(row) for row in rows)
    return buffer.getvalue().encode("utf-8-sig")


def main():
    st.set_page_config(page_title="School Curriculum Planner", layout="wide")
    st.title("School Curriculum & Manpower Planner")
    st.caption("Component 1 · Teaching group calculator")
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
