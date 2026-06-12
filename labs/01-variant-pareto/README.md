# Lab 01: Trace Variants and Pareto Selection

This lab connects four course ideas:

1. A trace variant depends on its encoding.
2. Event payload must be profiled before it is used.
3. Rare-variant filtering creates trade-offs rather than one correct threshold.
4. Pareto analysis makes those trade-offs explicit.

## Learning objectives

After the lab, participants can:

- compare control-flow, lifecycle, time-aware, and payload-aware trace encodings;
- identify payload leakage, missingness, cardinality, and temporal drift;
- detect exact and approximate variants using edit similarity;
- evaluate configurations using coverage, compactness, decision relevance, and
  temporal stability;
- inspect and justify a non-dominated configuration instead of choosing a
  threshold by convention.

## Files

- `variant_pareto_lab.ipynb`: guided teaching notebook.
- `variant_pareto_lab.py`: reusable implementation and verification entry point.
- `requirements.txt`: minimal dependencies for this lab.
- `outputs/`: generated artifacts; this directory is intentionally ignored.

## Run

From the repository root:

```bash
python3 labs/01-variant-pareto/variant_pareto_lab.py
```

To run the automated checks without creating output files:

```bash
make lab-check
```

The lab deliberately does not require PM4Py. Its generated event table follows
the familiar case/activity/timestamp structure and can be converted to a PM4Py
event log as an optional extension.

## Teaching sequence

1. Inspect the event and case populations.
2. Profile payload and identify why `outcome` is unavailable at prediction time.
3. Compare the number and meaning of variants under each encoding.
4. Vary edit-similarity and rare-variant thresholds.
5. Build the four-objective Pareto front.
6. Inspect representative traces before making a final selection.

## Discussion

- Which objective would you constrain rather than optimize?
- Does payload improve decision relevance or simply fragment the population?
- Which configuration remains stable when the process drifts?
- What information would be unavailable in a live monitoring system?
