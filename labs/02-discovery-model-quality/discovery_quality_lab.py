"""Lightweight process discovery and Pareto-based model-quality comparison."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from labs.common import load_variant_lab


def completed_traces(events: pd.DataFrame) -> dict[str, tuple[str, ...]]:
    completed = events.query("lifecycle == 'complete'").sort_values(["case_id", "timestamp"])
    return {
        str(case_id): tuple(group["activity"].astype(str))
        for case_id, group in completed.groupby("case_id", sort=True)
    }


def directly_follows_counts(traces: dict[str, tuple[str, ...]]) -> Counter:
    counts: Counter = Counter()
    for trace in traces.values():
        counts.update(zip(trace, trace[1:]))
    return counts


def discover_candidates(events: pd.DataFrame) -> pd.DataFrame:
    cases = (
        events.groupby("case_id", as_index=False)["timestamp"]
        .min()
        .sort_values("timestamp")
        .reset_index(drop=True)
    )
    split = int(len(cases) * 0.65)
    train_ids = set(cases.iloc[:split]["case_id"])
    test_ids = set(cases.iloc[split:]["case_id"])

    traces = completed_traces(events)
    train = {key: value for key, value in traces.items() if key in train_ids}
    test = {key: value for key, value in traces.items() if key in test_ids}
    train_edges = directly_follows_counts(train)
    early_edges = directly_follows_counts(
        dict(list(train.items())[: max(len(train) // 2, 1)])
    )
    late_edges = directly_follows_counts(
        dict(list(train.items())[max(len(train) // 2, 1) :])
    )
    all_edges = set(train_edges)
    max_count = max(train_edges.values())
    rows = []

    for threshold_share in (0.00, 0.03, 0.08, 0.15, 0.25):
        minimum = max(1, int(np.ceil(max_count * threshold_share)))
        model_edges = {edge for edge, count in train_edges.items() if count >= minimum}

        def trace_fitness(trace: tuple[str, ...]) -> float:
            edges = list(zip(trace, trace[1:]))
            return 1.0 if not edges else sum(edge in model_edges for edge in edges) / len(edges)

        fitness = float(np.mean([trace_fitness(trace) for trace in test.values()]))
        precision = float(
            sum(train_edges[edge] for edge in model_edges) / sum(train_edges.values())
        )
        simplicity = float(1.0 - (len(model_edges) - 1) / max(len(all_edges) - 1, 1))
        early_total = sum(early_edges[edge] for edge in model_edges)
        late_total = sum(late_edges[edge] for edge in model_edges)
        frequency_shift = sum(
            abs(
                early_edges[edge] / max(early_total, 1)
                - late_edges[edge] / max(late_total, 1)
            )
            for edge in model_edges
        )
        stability = float(1.0 - 0.5 * frequency_shift)
        rows.append(
            {
                "candidate": f"frequency >= {threshold_share:.0%}",
                "threshold_share": threshold_share,
                "edges": len(model_edges),
                "fitness": fitness,
                "precision": precision,
                "simplicity": simplicity,
                "stability": stability,
            }
        )

    frame = pd.DataFrame(rows)
    frame["pareto"] = pareto_mask(
        frame, ("fitness", "precision", "simplicity", "stability")
    )
    equivalent = frame[
        ["fitness", "precision", "simplicity", "stability"]
    ].round(12).duplicated(keep="first")
    frame.loc[equivalent, "pareto"] = False
    return frame


def discover_edge_sets(events: pd.DataFrame) -> dict[float, set[tuple[str, str]]]:
    """Directly-follows edges kept at each frequency threshold.

    Mirrors the train split and thresholds used by ``discover_candidates`` so
    the same candidate models can be rendered as process diagrams (e.g. with
    PM4Py) without duplicating the scoring logic.
    """
    cases = (
        events.groupby("case_id", as_index=False)["timestamp"]
        .min()
        .sort_values("timestamp")
        .reset_index(drop=True)
    )
    split = int(len(cases) * 0.65)
    train_ids = set(cases.iloc[:split]["case_id"])
    train = {
        key: value
        for key, value in completed_traces(events).items()
        if key in train_ids
    }
    train_edges = directly_follows_counts(train)
    max_count = max(train_edges.values())
    return {
        threshold_share: {
            edge
            for edge, count in train_edges.items()
            if count >= max(1, int(np.ceil(max_count * threshold_share)))
        }
        for threshold_share in (0.00, 0.03, 0.08, 0.15, 0.25)
    }


def pareto_mask(frame: pd.DataFrame, objectives: tuple[str, ...]) -> np.ndarray:
    values = frame.loc[:, objectives].to_numpy(float)
    keep = np.ones(len(values), dtype=bool)
    for index, point in enumerate(values):
        dominated = np.all(values >= point, axis=1) & np.any(values > point, axis=1)
        keep[index] = not dominated.any()
    return keep


def plot_candidates(candidates: pd.DataFrame, output: Path | None = None):
    fig, axis = plt.subplots(figsize=(8.2, 5.0))
    axis.scatter(
        candidates["simplicity"],
        candidates["fitness"],
        c=candidates["threshold_share"],
        cmap="viridis",
        s=100,
    )
    front = candidates[candidates["pareto"]]
    axis.scatter(
        front["simplicity"],
        front["fitness"],
        facecolors="none",
        edgecolors="#ef5b5b",
        s=220,
        linewidths=2,
        label="4D Pareto front",
    )
    plotted_models = (
        candidates.groupby(["simplicity", "fitness"], as_index=False)
        .agg(
            thresholds=(
                "threshold_share",
                lambda values: ", ".join(f"{value:.0%}" for value in values),
            )
        )
    )
    for row in plotted_models.itertuples():
        axis.annotate(
            row.thresholds,
            (row.simplicity, row.fitness),
            xytext=(5, 5),
            textcoords="offset points",
        )
    axis.set(
        xlabel="Simplicity",
        ylabel="Held-out edge fitness",
        title="Discovery thresholds: model-quality trade-offs",
    )
    axis.grid(alpha=0.2)
    axis.legend(frameon=False)
    fig.tight_layout()
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output, dpi=180)
    return fig


def run_lab(output_dir: Path) -> pd.DataFrame:
    events = load_variant_lab().generate_event_log()
    candidates = discover_candidates(events)
    output_dir.mkdir(parents=True, exist_ok=True)
    candidates.to_csv(output_dir / "model_quality_candidates.csv", index=False)
    plot_candidates(candidates, output_dir / "model_quality_pareto.png")
    plt.close("all")
    return candidates


def check_lab() -> None:
    candidates = discover_candidates(load_variant_lab().generate_event_log())
    assert len(candidates) == 5
    assert candidates["edges"].is_monotonic_decreasing
    assert candidates["pareto"].any()
    assert candidates[["fitness", "precision", "simplicity", "stability"]].apply(
        lambda column: column.between(0, 1).all()
    ).all()
    print(f"Discovery lab passed: {len(candidates)} models, {candidates['pareto'].sum()} Pareto candidates.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).with_name("outputs"))
    args = parser.parse_args()
    if args.check:
        check_lab()
    else:
        print(run_lab(args.output_dir).to_string(index=False))


if __name__ == "__main__":
    main()
