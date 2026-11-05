# School Curriculum & Manpower Planner

Component 1 is a command-line Python application for checking curriculum input data and estimating **subject-component group instances** for a Singapore secondary school. It reads editable CSV files, calculates each subject component within its own band and block, and produces detailed results and summaries.

These are preliminary mathematical requirements. They do not establish actual teaching-group arrangements, timetables, or teacher allocations. This component includes no timetable solver, teacher allocator, simulation, optimisation engine, or dashboard. It uses no database, paid API, cloud service, or external data source.

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
│   └── cli.py
├── data/
│   ├── blocks.csv
│   ├── enrolments.csv
│   └── subject_rules.csv
├── tests/
├── .gitignore
├── pyproject.toml
└── README.md
```

Data loading, validation, calculation, and reporting are separate from the CLI. A future interface can call those modules without embedding the calculation in a screen or command handler. This implementation stops at Component 1.
