# Curriculum time and workload CSV contract

This contract lets another application exchange curriculum time requirements and results with Component 3. It does not depend on, import code from, or merge with a separate period simulator.

## File conventions and units

Use comma-separated CSV with a header row, standard CSV quoting, and UTF-8 encoding. A UTF-8 byte-order mark is accepted; exports include it for spreadsheet compatibility. Preserve identifier spelling and case. Empty output numeric fields mean **unknown or not calculated**, never zero.

Write numeric values without units or thousands separators: `150`, `22.5`, and `0` are examples. Minutes and durations use finite decimal values; `NaN` and infinity are invalid. Weekly curriculum minutes must be nonnegative. Period duration must be strictly positive. Required period counts are nonnegative integers.

`minimum_weekly_minutes`, `scheduled_minutes`, and `excess_minutes` in group rows are minutes **per teaching group per week**. Summed values are **teacher-minutes per week**. A teacher-period is one group receiving one period of teaching; it is not an elapsed school timetable period. For example, three simultaneous groups receiving five periods each consume 15 teacher-periods, regardless of only five periods elapsing concurrently.

## Curriculum requirements import

File: `curriculum_requirements.csv`.

The minimum accepted header and a synthetic example are:

```csv
academic_year,level,subject_id,minimum_weekly_minutes
2027,Sec3,G3_PURE_BIOLOGY,150
```

The unique key is `(academic_year, level, subject_id)`. Duplicate keys are invalid even when their values agree. Subject IDs must already exist in Component 1's subject rules, and year/level references must match existing input cohorts. A subject component can have different requirements in different years or levels. The time rule is reused for that component's teaching-group instances across blocks, without merging the groups.

Two optional columns preserve provenance and prevent unreliable component allocations:

| Column | Default when omitted | Meaning |
| --- | --- | --- |
| `requirement_source` | `user supplied; unverified` | Descriptive provenance carried into group workload exports; no automatic claim of official approval |
| `requirement_scope` | `component` | `component` applies to the named subject component; `combined_unallocated` flags an unallocated combined-subject requirement that must not be used for component workload |

The provided file includes both optional columns. Its three rules are labelled **`SYNTHETIC EXAMPLE - not official`**, each at 150 minutes. They cover the four historical Biology groups because G3 Science (Bio) occurs in both blocks. These are not MOE curriculum requirements.

Pure Chemistry and Science (Chem), (Phy), and (Bio) keep their separate existing IDs. Social Studies and Humanities electives likewise need explicit component rules. The calculator does not copy a combined subject's time allowance onto each component, divide a larger allowance by guessed proportions, or infer a rule from similar subject names. If only a combined total is known, leave component rules missing, or mark the relevant rule `combined_unallocated`, until a reliable component allocation is supplied. A new, unknown combined-subject ID is flagged as an invalid reference and never used as an alias for existing components.

## Period scenarios import

File: `period_scenarios.csv`.

```csv
period_scenario_id,scenario_name,period_duration_minutes
p15,15-minute periods,15
p20,20-minute periods,20
p30,30-minute periods,30
p35,35-minute periods,35
```

`period_scenario_id` is the unique key. Add another row for any positive finite period duration; fractional durations are supported. These IDs are a separate namespace from Component 2's teaching-window scenario IDs.

## Teaching-group workload export

File: `teaching_group_workload.csv`.

```csv
period_scenario_id,scenario_name,period_duration_minutes,teaching_scenario_id,window_id,teacher_pool_id,academic_year,level,block_id,band_id,subject_id,subject_name,teaching_group_id,minimum_weekly_minutes,required_periods,scheduled_minutes,excess_minutes,requirement_source,calculation_status
```

Each row identifies one generated teaching-group instance under one period-duration scenario. Never enter group counts a second time: Component 1 calculates them and Component 2's group expansion supplies their stable identifiers. Group IDs contain URL-encoded year, level, block, band, subject ID, and a one-based ordinal, for example `2027/Sec3/A/Science/G3_PURE_BIOLOGY/1`.

For a valid requirement, the calculation is:

```text
required_periods = ceiling(minimum_weekly_minutes / period_duration_minutes)
scheduled_minutes = required_periods × period_duration_minutes
excess_minutes = scheduled_minutes − minimum_weekly_minutes
```

Rounding occurs for each group before aggregation. Missing or invalid rules produce an explicit `calculation_status`, blank calculated numeric fields, and a matching data-completeness record. Missing requirements are not zero-minute rules.

When a Component 2 scenario is selected, `teaching_scenario_id`, `window_id`, and `teacher_pool_id` retain its assignment metadata. Unassigned groups still appear; their window and pool fields are blank. If no teaching scenario is selected, those three fields are blank. Moving a group between abstract windows does not change its curriculum requirement or weekly workload. A computed five-period requirement does not mean five weekly lessons have been scheduled.

## Workload summaries and comparison

Files:

- `subject_workload_summary.csv`: subject totals within a year and level.
- `block_workload_summary.csv`: block totals and separate subject-band breakdown rows.
- `cohort_workload_summary.csv`: year/level totals for each selected period scenario.
- `period_duration_comparison.csv`: year/level summaries across the selected period-duration scenarios.

These files share this summary header:

```csv
scope,period_scenario_id,scenario_name,period_duration_minutes,teaching_scenario_id,academic_year,level,block_id,band_id,subject_id,subject_name,teaching_group_count,calculated_group_count,uncalculated_group_count,known_required_teacher_periods,known_scheduled_teacher_minutes,known_minimum_teacher_minutes,known_excess_teacher_minutes,total_required_teacher_periods,total_scheduled_teacher_minutes,assessment_completeness,requirement_sources
```

`scope` identifies subject, band, block, or level aggregation. Identity fields outside that scope are blank. Band rows retain their block; subject summaries aggregate already calculated group workloads without pooling pupils into larger teaching groups.

`requirement_sources` preserves the distinct source labels of the calculated groups contributing to the summary, so a synthetic subtotal remains visibly synthetic when exported without its group-detail file. A blank source list means no calculated source was available.

`known_*` fields are subtotals for groups with usable component requirements only. `calculated_group_count` and `uncalculated_group_count` state their coverage. `total_required_teacher_periods` and `total_scheduled_teacher_minutes` remain blank when the corresponding total cannot be claimed complete; consult `assessment_completeness` and validation issues. Do not combine block and band rows as independent totals, since band rows break down the same blocks.

The supplied partial Biology demonstration has four calculated groups and 66 uncalculated groups out of the 70-instance preferred-size inventory. Its known minimum requirement is 600 teacher-minutes weekly. The whole-cohort workload remains unknown, even though the four known groups have complete synthetic requirements.

## Completeness and validation exports

`data_completeness.csv` identifies each group whose workload cannot be calculated, with the period scenario, optional teaching scenario, source identity and reason:

```csv
period_scenario_id,teaching_scenario_id,academic_year,level,block_id,band_id,subject_id,subject_name,teaching_group_id,reason
```

`validation_issues.csv` lists input problems with the header `period_scenario_id,issue`. The command-line `validate` action returns a failure status when required curriculum data is missing or invalid. Workload runs and exports can still produce explicitly partial, known subtotals; a successful export is not evidence that the input set or whole-cohort workload is complete.

## Boundaries of exchanged results

The files contain no individual teacher deployment, teacher qualifications, teacher workload limits, student-level selections, full weekly timetable, or staffing sufficiency recommendation. Component 2's concurrency demand and Component 3's weekly teacher-period demand measure different things. Neither calculation alone establishes whole-school feasibility.
