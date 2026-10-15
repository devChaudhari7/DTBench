# DTBench: business rules with ground-truth decision tables

DTBench is a small benchmark for evaluating how well large language models (LLMs) turn
natural-language business rules into **decision tables** and **decision-table test cases**.
It accompanies the STQA term paper *LLM-Based Generation and Validation of Decision Table Test Cases*.

Each of the 12 specifications contains:

| Field | Meaning |
|---|---|
| `rules_text` | the business rules exactly as given to the LLM |
| `inputs`, `output`, `constraint` | the data dictionary (names, types, domains, allowed outputs) |
| `ground_truth_table` | a limited-entry decision table: conditions are boolean expressions over the inputs, rules map each condition to true/false/don't care and give the output |
| `infeasible_rules` | combinations of condition values that no valid input can reach (S01 only) |
| `reference_implementation` | an independently written Python function `decide(**inputs)` used as the test oracle |
| `probes` (separate file) | the evaluation inputs used to compare tables and test cases with the ground truth |

## Specifications

| ID | Name | Category | Inputs | Conditions | Rules | Probes |
|---|---|---|---|---|---|---|
| S01 | Triangle classification | Textbook | 3 | 6 | 8 | 35582 |
| S02 | NextDate | Textbook | 3 | 8 | 22 | 8174 |
| S03 | Order discount | Business rules (authored) | 3 | 6 | 17 | 4003 |
| S04 | BMI level | GPT-DMN | 3 | 4 | 7 | 5241 |
| S05 | Pet adoption | GPT-DMN | 4 | 5 | 8 | 24 |
| S06 | Driver's licence | GPT-DMN | 6 | 6 | 7 | 4616 |
| S07 | Vacation days | GPT-DMN | 2 | 5 | 6 | 1540 |
| S08 | Mode of transportation | GPT-DMN | 3 | 7 | 12 | 3953 |
| S09 | Scholarship eligibility | GPT-DMN | 3 | 3 | 4 | 4073 |
| S10 | Login with lockout and OTP | Business rules (authored) | 5 | 5 | 6 | 160 |
| S11 | UPI transfer screening | Business rules (authored) | 3 | 5 | 8 | 4052 |
| S12 | Personal-loan screening | Business rules (authored) | 4 | 5 | 6 | 6400 |

Totals: 12 specifications, 111 feasible ground-truth rules, 77818 evaluation probes.

## How the ground truth was built and checked

The ground-truth tables were derived manually following the decision-table procedure in
Jorgensen (2013, ch. 7): one rule per distinct case stated in the specification, with a
"don't care" entry only where the specification makes a condition irrelevant. Each table
was then checked automatically (`scripts/verify_benchmark.py`): on every evaluation probe
exactly one rule fires and its output equals the independent reference implementation,
every rule is reached by at least one probe, and no probe reaches an infeasible rule.

## Sources and licence

* S01, S02: classic textbook problems (Jorgensen 2013; Myers et al. 2011), rules re-worded.
* S04 to S09: descriptions from the GPT-DMN data set of Goossens, Vandevelde, Vanthienen and
  Vennekens, "GPT-3 for Decision Logic Modeling", RuleML+RR 2023 (CEUR-WS Vol. 3485),
  https://gitlab.com/EAVISE/sva/GPT-DMN . They are reproduced with attribution for research use;
  S07 originates from the DMCommunity challenge of January 2016 (J. Vanthienen). Changes are
  listed per specification in the `clarifications` field (S08 boundary wording; data dictionaries added).
* S03, S10, S11, S12: written for this benchmark. S11 is a simplified illustration, not an official
  NPCI rule set.

Content written for DTBench (rules S03, S10 to S12, all data dictionaries, ground-truth tables,
reference implementations and probes) is released under CC BY 4.0. The GPT-DMN descriptions remain
under the terms of their original authors.

## Files

```
dtbench_specs.json          all specifications in one file
specs/Sxx_<name>.json       one file per specification
dtbench_summary.csv         one row per specification
ground_truth_tables.md      the ground-truth tables in readable T/F/- form
reference/sxx_<name>.py     reference implementations
probes/Sxx.jsonl            evaluation probes with ground-truth rule and expected output
```
