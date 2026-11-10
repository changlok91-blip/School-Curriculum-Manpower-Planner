# School Curriculum & Manpower Planner

Component 1 is a command-line Python application for checking curriculum input data and estimating **subject-component group instances** for a Singapore secondary school. It reads editable CSV files, calculates each subject component within its own band and block, and produces detailed results and summaries.

These are preliminary mathematical requirements. They do not establish actual teaching-group arrangements, timetables, or teacher allocations. This component includes no timetable solver, teacher allocator, simulation, or optimisation engine. An optional Streamlit interface displays the same Component 1 calculations. Calculation needs no database, paid API, cloud service, or external data source.

## Run with Streamlit

The web entry file is **`streamlit_app.py`**, in the repository root.

After creating the virtual environment as described below, run these commands from the repository folder on Windows:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev,web]"
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

For Streamlit Community Cloud, select this GitHub repository, branch `main`, and main file path **`streamlit_app.py`**. Choose Python 3.11 or newer in advanced settings. The root `requirements.txt` installs Streamlit automatically. No secrets are required.

Use the sidebar **Page** selector to switch between **Teaching groups (Component 1)**, **Concurrency scenarios (Component 2)**, and the Component 3 curriculum workload page. Component 1 reads the three historical CSV files and shows cohort calculations. Component 2 also reads the four scenario CSV files: choose a scheduling scenario to view teacher-pool peaks and shortages, window demand, unscheduled groups, and a comparison of all configured scenarios. The workload page selects a period duration and optionally retains a Component 2 scenario's window metadata; it shows known workload, missing requirements, and CSV downloads. The pages support preferred or hard group limits and CSV downloads. Scenario assessments cover the full generated inventory across the input cohorts. Edit the CSV files in the repository to change inputs; the web interface does not save data edits.

After pulling updates, the deployment entry file remains `streamlit_app.py` on `main`. Streamlit Community Cloud normally picks up pushed changes automatically; if it still displays the previous interface, reboot the app from its management menu. No new secrets or dependencies are required for the Component 2 or Component 3 pages.

## Install on Windows

1. Install Python 3.11 or newer from [python.org](https://www.python.org/downloads/windows/). Enable the Python launcher during installation.
2. Download or clone this repository, then open PowerShell in its folder. You should see `pyproject.toml` and the `data` folder.
3. Create a virtual environment and install the application with its test tools:

```powershell
py -3 --version
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Check that the first command reports Python 3.11 or newer. The commands below use the virtual environment's Python directly, so PowerShell script activation is unnecessary. Installation needs Internet access to obtain Python packages; normal calculation runs entirely locally.

On macOS or Linux, use `python3 -m venv .venv`, then substitute `.venv/bin/python` for `.\.venv\Scripts\python.exe` in the commands below.

## Run the application

Run these commands from the repository folder.

Validate the three input files:

```powershell
.\.venv\Scripts\python.exe -m curriculum_planner validate
```

Calculate and display detailed group requirements and summaries:

```powershell
.\.venv\Scripts\python.exe -m curriculum_planner calculate
```

Export results to CSV:

```powershell
.\.venv\Scripts\python.exe -m curriculum_planner export --output-dir output
```

The export creates `output/group_results.csv` and `output/summaries.csv`. Open them in Excel or another spreadsheet application.

To use another folder containing the three input CSV files, add `--data-dir` after the command:

```powershell
.\.venv\Scripts\python.exe -m curriculum_planner validate --data-dir "C:\School\planning-data"
.\.venv\Scripts\python.exe -m curriculum_planner calculate --data-dir "C:\School\planning-data"
.\.venv\Scripts\python.exe -m curriculum_planner export --data-dir "C:\School\planning-data" --output-dir output
```

Preferred size limits apply by default. To calculate with the editable hard maximum instead, use `--use-hard-max` with `calculate` or `export`:

```powershell
.\.venv\Scripts\python.exe -m curriculum_planner calculate --use-hard-max
```

This simply selects a size limit; it performs no optimisation or predictive simulation. Use `--help` after any command to see its options. Validation failures must be corrected before calculation or export.

## Edit the input data

Keep the CSV header names unchanged. Save files as UTF-8 CSV. Subject IDs, band IDs, and block IDs are identifiers, so use them consistently across files. New blocks, bands, and subjects require data changes only; their names and number are not fixed in the calculation engine.

### `data/blocks.csv`

```csv
academic_year,level,block_id,student_count,form_classes
2027,Sec3,A,115,3A;3B;3C
2027,Sec3,B,145,
```

Each `(academic_year, level, block_id)` identifies one block. `student_count` is the block's unique student population. `form_classes` is optional descriptive text and has no effect on calculation. The sample uses semicolons between class names so the field remains simple CSV text.

### `data/enrolments.csv`

```csv
academic_year,level,block_id,band_id,subject_id,student_count
2027,Sec3,A,Science,G3_PURE_CHEMISTRY,29
2027,Sec3,A,Science,G3_SCIENCE_CHEM,86
```

Each row records enrolment in one subject component within a band and block. The duplicate-record key is `(academic_year, level, block_id, band_id, subject_id)`. A repeated key is an error, even if its count differs. Add the correct total to a single row instead of duplicating it.

Every enrolment must refer to a defined block and subject rule. Counts must be nonnegative integers. A zero count is valid and requires zero groups.

Bands are recorded independently from subjects: `band_id` belongs to the enrolment, while subject limits belong to `subject_rules.csv`. The same subject can therefore appear in different bands or blocks without changing its rule.

### `data/subject_rules.csv`

```csv
subject_id,subject_name,hard_max_size,preferred_max_size
G1_MATHEMATICS,G1 Mathematics,40,20
G2_DESIGN_AND_TECHNOLOGY,G2 Design & Technology,20,20
```

Each subject ID has one rule. Limits must be positive integers, and a preferred limit cannot exceed its hard maximum. Edit these limits in the CSV; they are not hard-coded into the engine.

The supplied school rules are:

| Subject | Hard maximum | Preferred maximum |
| --- | ---: | ---: |
| Design & Technology, Nutrition and Food Science, Computing, Essentials of Business Skills | 20 | 20 |
| G1 English, G1 Mathematics, G1 Science | 40 | 20 |
| All other supplied subjects | 40 | 40 |

When adding a new subject, add its explicit rule as well as its enrolment records. The engine does not infer limits from subject names.

## What the results mean

Each detailed row contains the year, level, block, band, and subject identifiers, plus:

| Field | Meaning |
| --- | --- |
| `student_count` | Enrolment in that subject component |
| `planning_max_size` | Preferred size by default, or hard maximum when selected |
| `groups_required` | Enrolment divided by the planning maximum, rounded up |
| `unused_places` | `groups_required × planning_max_size − student_count` |
| `preferred_size_applied` | Whether a smaller preferred limit was selected (including for zero enrolment) |

For example, 37 G1 Mathematics students use a preferred maximum of 20, giving two subject-component group instances and three unused places. These unused places are arithmetic capacity within that component; they are not a pool that can automatically be shared with another component or block.

The summaries aggregate by subject, band, block, and cohort. Subject summaries combine results for the same subject within a year and level after calculating every block separately. Band summaries retain their block. Block and cohort summaries report `unique_students` from `blocks.csv`; subject and band rows leave it blank because the data does not establish their distinct student populations. `component_enrolments` counts enrolment records' student totals and must not be interpreted as unique students.

Important modelling limits:

- Pure Chemistry and Science (Chem) are separate subject components.
- One student may take several Science or Humanities components. Their enrolment totals can exceed the block population.
- Elective 2 need not cover every student in a block.
- Students in different blocks do not share calculated groups.
- The data contains component counts, not individual student identities. It cannot establish student overlap, timetable compatibility, or the number of teachers needed.

## Supplied historical baseline

The sample data represents **2027 Secondary 3**: Block A has 115 students and Block B has 145 students, giving 260 unique students in total. Block A's recorded form classes are 3A, 3B, and 3C; no form classes were supplied for Block B.

With preferred limits enabled, the expected subject-component group instances are:

| Subject band | Block A | Block B | Combined |
| --- | ---: | ---: | ---: |
| English | 3 | 6 | 9 |
| Mathematics | 3 | 6 | 9 |
| Science components | 9 | 11 | 20 |
| Humanities components | 7 | 10 | 17 |
| Elective 1 | 5 | 7 | 12 |
| Elective 2 | — | 3 | 3 |
| **Total** | **27** | **43** | **70** |

The dash means no Elective 2 enrolment records were supplied for Block A. With `--use-hard-max`, Block B's G1 English, Mathematics, and Science each require one fewer group, giving totals of 27 for A, 40 for B, and 67 overall.

The completion checklist mentions a “2026 baseline,” but all provided historical figures are labelled 2027. No 2026 dataset was supplied, so the baseline is retained and tested as 2027. To calculate 2026, provide its actual CSV records rather than relabelling the 2027 figures.

## Run automated tests

```powershell
.\.venv\Scripts\python.exe -m pytest
```

The tests cover rounding boundaries, zero enrolment, preferred limits, separate blocks, adding Block C, invalid input, overlapping component counts, and the historical baseline.

## Repository structure

```text
School-Curriculum-Manpower-Planner/
├── curriculum_planner/
│   ├── __init__.py
│   ├── __main__.py
│   ├── models.py
│   ├── loading.py
│   ├── validation.py
│   ├── calculation.py
│   ├── reporting.py
│   ├── cli.py
│   ├── scheduling/
│   │   ├── models.py
│   │   ├── groups.py
│   │   ├── loading.py
│   │   ├── validation.py
│   │   ├── assignments.py
│   │   ├── calculation.py
│   │   ├── reporting.py
│   │   └── cli.py
│   └── workload/
│       ├── models.py
│       ├── loading.py
│       ├── validation.py
│       ├── periods.py
│       ├── calculation.py
│       ├── comparison.py
│       ├── reporting.py
│       ├── cli.py
│       └── web.py
├── data/
│   ├── blocks.csv
│   ├── enrolments.csv
│   ├── subject_rules.csv
│   ├── scenarios.csv
│   ├── teaching_windows.csv
│   ├── group_assignments.csv
│   ├── teacher_pools.csv
│   ├── curriculum_requirements.csv
│   └── period_scenarios.csv
├── docs/
│   └── workload_csv_contract.md
├── tests/
├── streamlit_app.py
├── requirements.txt
├── .gitignore
├── pyproject.toml
└── README.md
```

Data loading, validation, calculation, and reporting are separate from the CLI. A future interface can call those modules without embedding the calculation in a screen or command handler. Component 2 adds a separate scheduling package and leaves the Component 1 calculation and Streamlit interface intact. Component 3 adds a separate workload package using the same generated teaching groups. Development stops at Component 3.

## Component 2: teaching-window concurrency

Component 2 places selected Component 1 teaching-group instances into manually configured, abstract teaching windows. Activities in the same window are simultaneous; different windows are treated as non-overlapping. The number and names of blocks, bands, scenarios, windows, and teacher pools are editable data, not fixed engine rules.

Each placed group requires one teacher from its assigned resource pool. A pool's demand in a window is the number of groups assigned to that pool and window, including groups from different subjects or blocks. Its peak simultaneous demand is the **maximum across windows**, never their sum. A concurrency violation occurs when a pool's demand in one window exceeds its configured available teacher count.

Windows are not weekly timetable periods. This component does not generate timetables, calculate teaching periods, allocate named teachers, or optimise assignments. Use the Streamlit sidebar's **Concurrency scenarios (Component 2)** page or the CLI below to view the assessments.

### Run Component 2 on Windows

Use the same virtual environment and installation described above. No additional dependencies are needed. Run these commands from the repository folder:

```powershell
# List the configured scenarios.
.\.venv\Scripts\python.exe -m curriculum_planner scenarios list

# Validate Component 1 inputs and all scenario inputs.
.\.venv\Scripts\python.exe -m curriculum_planner scenarios validate

# See every generated teaching-group identifier, or export the inventory.
.\.venv\Scripts\python.exe -m curriculum_planner scenarios groups
.\.venv\Scripts\python.exe -m curriculum_planner scenarios groups --output output/teaching_groups.csv

# Run either Biology demonstration.
.\.venv\Scripts\python.exe -m curriculum_planner scenarios run simultaneous_science
.\.venv\Scripts\python.exe -m curriculum_planner scenarios run separate_science

# Compare two or more distinct scenarios.
.\.venv\Scripts\python.exe -m curriculum_planner scenarios compare simultaneous_science separate_science

# Export one or more scenarios and their comparison.
.\.venv\Scripts\python.exe -m curriculum_planner scenarios export simultaneous_science separate_science --output-dir output/scenarios
```

For an alternative set of inputs, add `--data-dir "C:\School\planning-data"` after the leaf command (for example, after `run separate_science`). That directory must contain the three Component 1 CSVs and the four Component 2 CSVs. The `--use-hard-max` option selects Component 1's hard-limit calculation for the generated group inventory; preferred limits remain the default. Revalidate assignments after changing limits or enrolments because some previously generated group IDs may no longer exist.

### Edit the scenario files

The original `blocks.csv`, `enrolments.csv`, and `subject_rules.csv` remain the source of teaching-group counts. Do not enter those counts again in the scheduling data. Generate the inventory with `scenarios groups` and copy the appropriate IDs into assignments.

The four additional editable CSVs have these headers:

| File | Columns |
| --- | --- |
| `scenarios.csv` | `scenario_id,scenario_name,description` |
| `teaching_windows.csv` | `scenario_id,window_id,window_name` |
| `group_assignments.csv` | `scenario_id,window_id,teaching_group_id,teacher_pool_id` |
| `teacher_pools.csv` | `scenario_id,teacher_pool_id,pool_name,available_teacher_count` |

Keep the headers unchanged and save UTF-8 CSV. Description may be blank. Teacher counts must be nonnegative integers; zero availability is valid and makes every positive demand a shortage. Window and pool identifiers are scoped to their scenario, so another scenario can reuse them. Each group can be placed at most once per scenario, even if its second placement names a different window or pool. Unknown groups, windows, pools, or scenarios and duplicate placements must be corrected before simulation.

A teaching-group ID contains the year, level, block, band, subject ID, and a one-based group number. For example:

```text
2027/Sec3/A/Science/G3_PURE_BIOLOGY/1
```

Each segment is URL-encoded so identifiers containing reserved characters do not collide. IDs remain stable when CSV rows are reordered, display names change, or unrelated blocks and subjects are added. If a component grows from two groups to three, the existing first and second IDs remain and a third is added. Renaming an identity field or reducing the calculated number of groups can invalidate assignments, which validation reports. Generated `component_student_count` is the whole subject-component enrolment, **not** the number of students in each individual group; this component does not invent a pupil distribution among groups.

Resource pool membership is explicit in each assignment. By assigning a group to a pool, the user asserts that the pool is qualified and available for that group. The engine does not infer qualifications from a subject name, and does not treat all Science teachers as interchangeable. For the demonstration only, the Biology pool is assumed to contain two teachers qualified for all four selected Biology groups.

### Biology demonstration results

The four supplied groups are:

| Block | Subject component | Students | Group instances |
| --- | --- | ---: | ---: |
| A | G3 Pure Biology | 14 | 1 |
| A | G3 Science (Bio) | 34 | 1 |
| B | G3 Science (Bio) | 17 | 1 |
| B | G2 Science (Bio) | 40 | 1 |

These are the existing **2027 Sec 3** records. The Component 2 request calls them 2026, but no 2026 dataset was supplied. The historical year and all original input values are preserved.

| Scenario ID | Windows used | Groups scheduled | Groups unscheduled | Biology teachers available | Peak demand | Maximum shortage | Pool-window violations |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `simultaneous_science` | 1 | 4 | 66 | 2 | 4 | 2 | 1 |
| `separate_science` | 2 | 4 | 66 | 2 | 2 | 0 | 0 |

The simultaneous scenario places all four groups in one window and violates the configured concurrency constraint. The separate scenario places Block A's two groups in one window and Block B's two in another: each window requires two teachers. It satisfies the concurrency constraint **for those four configured groups only**. Both scenarios still contain four Biology groups, and the baseline inventory remains 70 group instances (27 for A and 43 for B).

### Exported reports

`scenarios export` writes these files in the selected output directory:

| Report | Contents |
| --- | --- |
| `window_summary.csv` | Scenario, window, block, band, group IDs, resource pool, demand, availability, and shortage |
| `resource_pool_summary.csv` | Each pool's available teachers, peak simultaneous demand, maximum shortage, and concurrency status |
| `unscheduled_groups.csv` | Every group not placed in each selected scenario, with its source component identity |
| `scenario_comparison.csv` | Defined/used windows, scheduled/unscheduled counts, peak demand by pool, violation count, and assessment limitations |
| `teaching_groups.csv` | Generated Component 1 group inventory, including stable IDs for editing assignments |

The window report retains block and band context: one row represents a window/pool/year/level/block/band slice. `teaching_group_ids` lists its IDs separated by semicolons, and `group_count` is that slice's group count. `concurrent_demand` and `shortage` describe the **entire pool in the window**, so they can repeat across block/band rows. Do not sum repeated demand or shortage values; use `group_count` for slice totals and the resource-pool report for peaks. Configured empty window/pool combinations have zero demand.

In the comparison, `teaching_windows` counts all configured windows and `windows_used` counts those with assigned groups. `concurrency_violations` counts distinct over-capacity pool/window combinations. `peak_concurrent_demand_by_pool` is a JSON object keyed by pool ID. A partially scheduled scenario is marked partial; placing every group still means only the concurrency checks have been assessed.

### What this assessment cannot establish

- **Other groups:** the Biology examples place 4 of 70 group instances. The remaining 66 are explicitly unscheduled and unassessed, so neither result establishes whole-cohort or whole-school scheduling feasibility.
- **Student conflicts:** individual student subject selections are unavailable. A student may appear in more than one component, and student-level timetable compatibility remains unverified.
- **Shared teachers:** pool membership is manually configured. If one teacher belongs to two pools, the engine cannot detect or prevent that person's capacity being counted twice. Cross-subject teacher sharing is not validated.
- **Weekly capacity:** passing a concurrency check does not show that teachers have enough total weekly teaching capacity or suitable individual availability.
- **Finite timetable:** more abstract windows can lower peak demand, but those windows must eventually fit into a finite school timetable. Full timetable feasibility is not yet assessed, even when every group has been placed.

Before Component 2 changes, all **43 existing tests passed**. After implementation, all **80 tests passed** (the original 43 plus 37 Component 2 tests). Run the full suite with `.\.venv\Scripts\python.exe -m pytest` to check Component 1 and Component 2 together. Those results record the Component 2 implementation stage; Component 3 is described below.

## Component 3: curriculum time and weekly teaching workload

Component 3 converts each generated teaching group's curriculum minutes into required weekly periods, then sums the resulting teacher workload by subject, band, block, and level. It reads Component 1's calculated group instances through the existing Component 2 group expansion; there is no second database of group numbers. If a component grows from 40 to 41 students with a maximum size of 40, its second group automatically contributes another group's workload.

The supplied curriculum minutes are **synthetic demonstration values, not official MOE requirements**. Only three Biology subject components have a time rule. They cover four of the historical 70 teaching-group instances; the remaining **66 groups have missing time requirements**. The historical data remains **2027 Sec 3**. The request mentions 2026, but no 2026 figures were supplied, so the existing year and original enrolments are preserved.

### Run Component 3 on Windows

Use the existing virtual environment. No additional dependencies are required. Run from the repository folder:

```powershell
# List the editable period-duration scenarios.
.\.venv\Scripts\python.exe -m curriculum_planner workload list

# Check curriculum requirements and report missing time data.
.\.venv\Scripts\python.exe -m curriculum_planner workload validate

# Calculate weekly workload under 30-minute periods.
.\.venv\Scripts\python.exe -m curriculum_planner workload run p30

# Retain an existing Component 2 scenario's teaching-window metadata.
.\.venv\Scripts\python.exe -m curriculum_planner workload run p30 --teaching-scenario separate_science

# Compare all four initial period lengths.
.\.venv\Scripts\python.exe -m curriculum_planner workload compare p15 p20 p30 p35

# Export detailed, summary, comparison, and completeness reports.
.\.venv\Scripts\python.exe -m curriculum_planner workload export p15 p20 p30 p35 --output-dir output/workload
```

For the supplied demonstration, `workload validate` intentionally reports missing requirements and returns a nonzero exit status. Its known Biology rules can still be calculated: `run`, `compare`, and `export` produce clearly labelled partial results. Missing curriculum data must be supplied before claiming a complete cohort workload.

Add options after the leaf command or scenario IDs:

- `--data-dir "C:\School\planning-data"` selects another input folder.
- `--academic-year 2027 --level Sec3` restricts the reported cohort.
- `--use-hard-max` generates groups using Component 1's hard sizes instead of preferred sizes.
- `--teaching-scenario separate_science` retains that Component 2 scenario's assignment metadata. Its scenario CSV files are needed only when this option is used.

Changing teaching-window placement does not change weekly curriculum minutes or teacher-periods. All generated groups remain in the workload assessment, including those without a window assignment. Windows identify possible simultaneous commitments; they do not place the calculated weekly lessons into a timetable.

In Streamlit, open the Component 3 workload page from the sidebar, select a period scenario and optional teaching-window scenario, and review the data-completeness warning before using a subtotal. The existing launch file is still `streamlit_app.py`.

### Edit curriculum time requirements

`data/curriculum_requirements.csv` uses a unique `(academic_year, level, subject_id)` key:

```csv
academic_year,level,subject_id,minimum_weekly_minutes,requirement_source,requirement_scope
2027,Sec3,G3_PURE_BIOLOGY,150,SYNTHETIC EXAMPLE - not official,component
2027,Sec3,G3_SCIENCE_BIO,150,SYNTHETIC EXAMPLE - not official,component
2027,Sec3,G2_SCIENCE_BIO,150,SYNTHETIC EXAMPLE - not official,component
```

The first four columns are required. `requirement_source` and `requirement_scope` are optional; their defaults are `user supplied; unverified` and `component`. Provenance is retained in the group report and in each summary's `requirement_sources` field, including the explicit synthetic-example label. Weekly minutes must be finite, nonnegative numeric values. Fractional minutes are supported. A missing rule is unknown, not zero; an explicit valid zero-minute rule has zero required periods.

Subject IDs reference existing Component 1 subject rules, and year/level references identify existing cohorts. Duplicate or conflicting keys are invalid. Unknown subject IDs, negative minutes, and invalid component rules are flagged; affected groups cannot contribute a calculated workload.

Pure Chemistry, Science (Chem), Science (Phy), and Science (Bio) remain distinct components, as do Social Studies and Humanities electives. Give each component its own reliably allocated time requirement. A full combined-subject requirement is never copied onto every component. If an allocation is unknown, keep those component rules missing or flag the relevant record with `requirement_scope=combined_unallocated`. The calculator reports that component workload cannot yet be calculated reliably and does not invent a split. Component enrolments can overlap and remain unrelated to unique student population totals.

### Edit period-duration scenarios

`data/period_scenarios.csv` contains:

```csv
period_scenario_id,scenario_name,period_duration_minutes
p15,15-minute periods,15
p20,20-minute periods,20
p30,30-minute periods,30
p35,35-minute periods,35
```

Add rows for other strictly positive, finite period durations, including fractional durations. Period-duration scenario IDs are separate from Component 2's teaching-window scenario IDs. Invalid or duplicate selected period scenarios are rejected.

For every teaching group, the calculator rounds up independently:

```text
required_periods = ceiling(minimum_weekly_minutes / period_duration_minutes)
scheduled_minutes = required_periods × period_duration_minutes
excess_minutes = scheduled_minutes − minimum_weekly_minutes
```

Aggregating follows this per-group rounding. Three groups receiving five periods each consume **15 teacher-periods**, even if they run concurrently for only five elapsed timetable periods. Scheduled minutes are the minutes implied by the rounded curriculum requirement; they are not evidence that lessons have been placed into an actual weekly schedule.

### Four-group Biology worked example

Each of the four Biology groups used in Component 2 has a **synthetic 150-minute weekly requirement**. The G3 Science (Bio) rule applies to its separate groups in Blocks A and B, giving a known minimum of **600 teacher-minutes per week**.

| Period scenario | Period duration (minutes) | Required periods per group | Known total teacher-periods | Known scheduled teacher-minutes | Known excess teacher-minutes |
| --- | ---: | ---: | ---: | ---: | ---: |
| `p15` | 15 | 10 | 40 | 600 | 0 |
| `p20` | 20 | 8 | 32 | 640 | 40 |
| `p30` | 30 | 5 | 20 | 600 | 0 |
| `p35` | 35 | 5 | 20 | 700 | 100 |

These subtotals cover **4 of 70 groups**. They do not represent the whole cohort's weekly workload. The other 66 groups, covering 34 subject components without time rules, are listed in the completeness report rather than assigned guessed minutes. Component 2's simultaneous and separate Biology windows retain their different concurrent demands of four and two teachers; their weekly workload is the same for a given period duration.

### Workload CSV reports

The export command writes:

| File | Contents |
| --- | --- |
| `teaching_group_workload.csv` | Every generated group, its identity and optional window/pool metadata, curriculum minutes, period conversion, provenance, and calculation status |
| `subject_workload_summary.csv` | Group counts and workload subtotals by subject within year and level |
| `block_workload_summary.csv` | Workload by block, plus separate band breakdown rows |
| `cohort_workload_summary.csv` | Workload and coverage by year and level for each selected period scenario |
| `period_duration_comparison.csv` | The same cohort measures compared across the selected period durations |
| `data_completeness.csv` | Each group whose workload is unknown because a requirement is missing or invalid |
| `validation_issues.csv` | Input problems associated with the selected period scenarios |

`known_required_teacher_periods`, `known_scheduled_teacher_minutes`, `known_minimum_teacher_minutes`, and `known_excess_teacher_minutes` cover calculated groups only. `calculated_group_count` and `uncalculated_group_count` identify coverage. Complete-total fields such as `total_required_teacher_periods` and `total_scheduled_teacher_minutes` stay blank when the total cannot be claimed complete. Blank values mean unknown, not zero. Read `assessment_completeness` before interpreting a summary. Zero teaching groups produce zero workload.

The [CSV import/export contract](docs/workload_csv_contract.md) documents headers, units, keys, optional provenance, and missing-data meanings for eventual exchange with another period simulator. No other repository is imported or merged.

### Scope and validation evidence

All **82 existing tests passed before Component 3 changes**. After implementation, all **127 tests passed**, including the original tests and 45 new workload and interface tests. Run `.\.venv\Scripts\python.exe -m pytest` to verify the complete current suite, including the existing Streamlit, grouping, and concurrency checks.

Component 3 calculates weekly curriculum workload, not individual teacher deployment or staffing sufficiency. It does not apply teacher workload limits, infer qualifications, allocate student combinations, generate a full timetable, or optimise blocks. Student compatibility, shared teachers across resource pools, and actual weekly lesson placement remain unverified. Development stops after Component 3.
