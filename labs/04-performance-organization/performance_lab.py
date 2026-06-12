"""Performance, bottleneck, rework, and handover analysis."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from labs.common import load_variant_lab


ROLE_BY_ACTIVITY = {
    "Receive": "Sales",
    "Check": "Risk",
    "Clarify": "Sales",
    "Approve": "Risk",
    "Reject": "Risk",
    "Pack": "Warehouse",
    "Rework": "Quality",
    "Ship": "Logistics",
}


def analyze_performance(events: pd.DataFrame):
    completed = events.query("lifecycle == 'complete'").sort_values(["case_id", "timestamp"]).copy()
    completed["role"] = completed["activity"].map(ROLE_BY_ACTIVITY)
    completed["next_role"] = completed.groupby("case_id")["role"].shift(-1)
    completed["handover"] = completed["role"] != completed["next_role"]

    activity = (
        completed.groupby("activity")
        .agg(events=("activity", "size"), median_hours=("duration_hours", "median"), p90_hours=("duration_hours", lambda series: series.quantile(0.9)))
        .sort_values("p90_hours", ascending=False)
        .reset_index()
    )

    cases = (
        completed.groupby("case_id")
        .agg(
            start=("timestamp", "min"),
            end=("timestamp", "max"),
            activities=("activity", "size"),
            rework=("activity", lambda values: int(values.duplicated().sum())),
            handovers=("handover", "sum"),
            channel=("channel", "first"),
            product_type=("product_type", "first"),
            outcome=("outcome", lambda values: values.dropna().iloc[-1]),
        )
        .reset_index()
    )
    cases["cycle_hours"] = (cases["end"] - cases["start"]).dt.total_seconds() / 3600

    handovers: Counter = Counter(
        zip(
            completed.loc[completed["next_role"].notna(), "role"],
            completed.loc[completed["next_role"].notna(), "next_role"],
        )
    )
    handover_frame = pd.DataFrame(
        [{"source": source, "target": target, "count": count} for (source, target), count in handovers.most_common()]
    )
    cohorts = (
        cases.groupby(["channel", "product_type"], dropna=False)
        .agg(cases=("case_id", "size"), median_cycle=("cycle_hours", "median"), adverse_rate=("outcome", lambda values: (values == "adverse").mean()))
        .reset_index()
        .sort_values("median_cycle", ascending=False)
    )
    return activity, cases, handover_frame, cohorts


def plot_activity(activity: pd.DataFrame, output: Path | None = None):
    figure, axis = plt.subplots(figsize=(8.2, 4.8))
    ordered = activity.sort_values("p90_hours")
    axis.barh(ordered["activity"], ordered["p90_hours"], color="#008f95")
    axis.set(xlabel="90th percentile service time (hours)", title="Activity bottleneck profile")
    figure.tight_layout()
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(output, dpi=180)
    return figure


def run_lab(output_dir: Path):
    results = analyze_performance(load_variant_lab().generate_event_log())
    activity, cases, handovers, cohorts = results
    output_dir.mkdir(parents=True, exist_ok=True)
    activity.to_csv(output_dir / "activity_performance.csv", index=False)
    cases.to_csv(output_dir / "case_performance.csv", index=False)
    handovers.to_csv(output_dir / "handover_network.csv", index=False)
    cohorts.to_csv(output_dir / "cohort_performance.csv", index=False)
    plot_activity(activity, output_dir / "activity_bottlenecks.png")
    plt.close("all")
    return results


def check_lab() -> None:
    activity, cases, handovers, cohorts = analyze_performance(load_variant_lab().generate_event_log())
    assert len(cases) == 240
    assert activity["p90_hours"].gt(0).all()
    assert cases["rework"].gt(0).any()
    assert not handovers.empty and not cohorts.empty
    print(f"Performance lab passed: {len(activity)} activities, {len(handovers)} handover relations.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).with_name("outputs"))
    args = parser.parse_args()
    if args.check:
        check_lab()
    else:
        for frame in run_lab(args.output_dir):
            print(frame.head().to_string(index=False), "\n")


if __name__ == "__main__":
    main()
