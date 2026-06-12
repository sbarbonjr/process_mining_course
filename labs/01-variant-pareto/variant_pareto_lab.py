"""Trace-variant analysis with payload profiling and Pareto selection."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import normalized_mutual_info_score


ACTIVITY_HOURS = {
    "Receive": 0.3,
    "Check": 1.2,
    "Clarify": 5.0,
    "Approve": 0.8,
    "Reject": 0.4,
    "Pack": 2.0,
    "Rework": 7.0,
    "Ship": 3.0,
}

PATHS = {
    "normal": ("Receive", "Check", "Approve", "Ship"),
    "clarify": ("Receive", "Check", "Clarify", "Check", "Approve", "Ship"),
    "reject": ("Receive", "Check", "Reject"),
    "expedite": ("Receive", "Check", "Approve", "Pack", "Ship"),
    "rework": ("Receive", "Check", "Approve", "Rework", "Approve", "Ship"),
}

PAYLOAD_AVAILABILITY = {
    "channel": "case start",
    "product_type": "case start",
    "priority": "case start",
    "amount": "case start",
    "customer_note": "case start",
    "outcome": "case completion only",
}


def _choose_path(
    rng: np.random.Generator,
    product_type: str | None,
    priority: str,
    late_period: bool,
) -> str:
    probabilities = np.array([0.55, 0.18, 0.10, 0.10, 0.07], dtype=float)

    if product_type == "custom":
        probabilities += np.array([-0.20, 0.12, -0.01, 0.01, 0.08])
    if priority == "high":
        probabilities += np.array([-0.10, -0.04, -0.01, 0.15, 0.00])
    if late_period:
        probabilities += np.array([-0.07, 0.03, 0.00, 0.00, 0.04])

    probabilities = np.clip(probabilities, 0.01, None)
    probabilities /= probabilities.sum()
    return str(rng.choice(list(PATHS), p=probabilities))


def generate_event_log(n_cases: int = 240, seed: int = 17) -> pd.DataFrame:
    """Generate a deterministic event log with lifecycle and payload attributes."""
    rng = np.random.default_rng(seed)
    rows: list[dict[str, object]] = []
    origin = pd.Timestamp("2025-01-06 08:00:00")

    for index in range(n_cases):
        case_id = f"C-{index + 1:04d}"
        late_period = index >= n_cases // 2
        start_time = origin + pd.Timedelta(hours=18 * index + rng.uniform(0, 8))

        channel_weights = [0.55, 0.28, 0.17] if not late_period else [0.42, 0.38, 0.20]
        channel = str(rng.choice(["web", "partner", "direct"], p=channel_weights))
        product_type: str | None = str(
            rng.choice(["standard", "custom", "service"], p=[0.58, 0.27, 0.15])
        )
        if rng.random() < 0.05:
            product_type = None

        priority = str(rng.choice(["normal", "high"], p=[0.78, 0.22]))
        path_name = _choose_path(rng, product_type, priority, late_period)
        activities = PATHS[path_name]

        amount = float(rng.lognormal(mean=6.1, sigma=0.65))
        if rng.random() < 0.04:
            amount = np.nan

        note_templates = {
            "standard": "standard request",
            "custom": "custom dimensions require review",
            "service": "service activation request",
            None: None,
        }
        customer_note = note_templates[product_type]
        if rng.random() < 0.22:
            customer_note = None

        bad_path = path_name in {"clarify", "reject", "rework"}
        adverse_probability = 0.70 if bad_path else 0.10
        if channel == "partner":
            adverse_probability += 0.08
        outcome = "adverse" if rng.random() < min(adverse_probability, 0.95) else "good"

        current_time = start_time
        for activity_index, activity in enumerate(activities):
            base_hours = ACTIVITY_HOURS[activity]
            duration = base_hours * float(rng.lognormal(mean=0.0, sigma=0.32))
            if product_type == "custom" and activity in {"Check", "Clarify", "Rework"}:
                duration *= 1.35
            if priority == "high" and activity in {"Pack", "Ship"}:
                duration *= 0.72

            event_payload = {
                "case_id": case_id,
                "channel": channel,
                "product_type": product_type,
                "priority": priority,
                "amount": amount,
                "customer_note": customer_note,
                "path_name": path_name,
                "late_period": late_period,
            }

            rows.append(
                {
                    **event_payload,
                    "activity": activity,
                    "lifecycle": "start",
                    "timestamp": current_time,
                    "duration_hours": np.nan,
                    "outcome": None,
                }
            )

            if (
                activity == "Check"
                and path_name in {"clarify", "rework"}
                and rng.random() < 0.55
            ):
                suspend_time = current_time + pd.Timedelta(hours=duration * 0.35)
                resume_time = current_time + pd.Timedelta(hours=duration * 0.62)
                rows.append(
                    {
                        **event_payload,
                        "activity": activity,
                        "lifecycle": "suspend",
                        "timestamp": suspend_time,
                        "duration_hours": np.nan,
                        "outcome": None,
                    }
                )
                rows.append(
                    {
                        **event_payload,
                        "activity": activity,
                        "lifecycle": "resume",
                        "timestamp": resume_time,
                        "duration_hours": np.nan,
                        "outcome": None,
                    }
                )

            current_time += pd.Timedelta(hours=duration)
            is_final_event = activity_index == len(activities) - 1
            rows.append(
                {
                    **event_payload,
                    "activity": activity,
                    "lifecycle": "complete",
                    "timestamp": current_time,
                    "duration_hours": duration,
                    "outcome": outcome if is_final_event else None,
                }
            )
            current_time += pd.Timedelta(minutes=float(rng.uniform(5, 45)))

    events = pd.DataFrame(rows).sort_values(["case_id", "timestamp", "lifecycle"])
    return events.reset_index(drop=True)


def build_case_table(events: pd.DataFrame) -> pd.DataFrame:
    """Create one row per case without using the outcome before completion."""
    ordered = events.sort_values(["case_id", "timestamp"])
    rows = []
    for case_id, case_events in ordered.groupby("case_id", sort=True):
        completed = case_events[case_events["lifecycle"] == "complete"]
        outcome_values = case_events["outcome"].dropna()
        rows.append(
            {
                "case_id": case_id,
                "start_time": case_events["timestamp"].min(),
                "end_time": case_events["timestamp"].max(),
                "channel": case_events["channel"].iloc[0],
                "product_type": case_events["product_type"].iloc[0],
                "priority": case_events["priority"].iloc[0],
                "amount": case_events["amount"].iloc[0],
                "customer_note": case_events["customer_note"].iloc[0],
                "path_name": case_events["path_name"].iloc[0],
                "outcome": outcome_values.iloc[-1],
                "completed_events": len(completed),
            }
        )

    cases = pd.DataFrame(rows).sort_values("start_time").reset_index(drop=True)
    split = len(cases) // 2
    cases["period"] = np.where(cases.index < split, "early", "late")
    return cases


def _categorical_drift(early: pd.Series, late: pd.Series) -> float:
    early_distribution = early.fillna("<missing>").astype(str).value_counts(normalize=True)
    late_distribution = late.fillna("<missing>").astype(str).value_counts(normalize=True)
    categories = early_distribution.index.union(late_distribution.index)
    p = early_distribution.reindex(categories, fill_value=0.0)
    q = late_distribution.reindex(categories, fill_value=0.0)
    return float(0.5 * np.abs(p - q).sum())


def _numeric_drift(early: pd.Series, late: pd.Series) -> float:
    combined = pd.concat([early, late]).dropna()
    if combined.empty:
        return 0.0
    scale = float(combined.quantile(0.75) - combined.quantile(0.25))
    if scale == 0:
        return 0.0
    return float(min(abs(early.median() - late.median()) / scale, 1.0))


def profile_payload(events: pd.DataFrame) -> pd.DataFrame:
    """Profile payload availability, missingness, cardinality, and temporal drift."""
    cases = build_case_table(events)
    profile_rows = []

    for column, availability in PAYLOAD_AVAILABILITY.items():
        series = cases[column]
        early = cases.loc[cases["period"] == "early", column]
        late = cases.loc[cases["period"] == "late", column]
        if pd.api.types.is_numeric_dtype(series):
            drift = _numeric_drift(early, late)
        else:
            drift = _categorical_drift(early, late)

        profile_rows.append(
            {
                "payload": column,
                "available": availability,
                "missing_rate": float(series.isna().mean()),
                "cardinality": int(series.nunique(dropna=True)),
                "drift_score": drift,
                "leakage_risk": column == "outcome",
            }
        )

    return pd.DataFrame(profile_rows)


def _duration_bucket(value: float) -> str:
    if value <= 1.0:
        return "fast"
    if value <= 4.0:
        return "typical"
    return "slow"


def encode_traces(events: pd.DataFrame, encoding: str) -> pd.Series:
    """Encode each case as a tuple suitable for exact or approximate variants."""
    ordered = events.sort_values(["case_id", "timestamp"])
    traces: dict[str, tuple[str, ...]] = {}

    for case_id, case_events in ordered.groupby("case_id", sort=True):
        completed = case_events[case_events["lifecycle"] == "complete"]

        if encoding == "control_flow":
            tokens = completed["activity"].astype(str).tolist()
        elif encoding == "lifecycle":
            tokens = (
                case_events["activity"].astype(str)
                + ":"
                + case_events["lifecycle"].astype(str)
            ).tolist()
        elif encoding == "time":
            tokens = [
                f"{row.activity}@{_duration_bucket(float(row.duration_hours))}"
                for row in completed.itertuples()
            ]
        elif encoding == "payload":
            channel = str(case_events["channel"].iloc[0])
            product = case_events["product_type"].iloc[0]
            product = "<missing>" if pd.isna(product) else str(product)
            tokens = [
                f"{activity}|{channel}|{product}"
                for activity in completed["activity"].astype(str)
            ]
        else:
            raise ValueError(f"Unknown encoding: {encoding}")

        traces[str(case_id)] = tuple(tokens)

    return pd.Series(traces, name=encoding)


def _edit_distance(left: tuple[str, ...], right: tuple[str, ...]) -> int:
    previous = list(range(len(right) + 1))
    for left_index, left_token in enumerate(left, start=1):
        current = [left_index]
        for right_index, right_token in enumerate(right, start=1):
            insertion = current[right_index - 1] + 1
            deletion = previous[right_index] + 1
            substitution = previous[right_index - 1] + (left_token != right_token)
            current.append(min(insertion, deletion, substitution))
        previous = current
    return previous[-1]


def _trace_similarity(left: tuple[str, ...], right: tuple[str, ...]) -> float:
    denominator = max(len(left), len(right), 1)
    return 1.0 - (_edit_distance(left, right) / denominator)


def cluster_trace_variants(traces: pd.Series, similarity_threshold: float) -> pd.Series:
    """Greedily cluster frequent traces using normalized edit similarity."""
    frequencies = Counter(traces.tolist())
    representatives: list[tuple[str, ...]] = []
    assignment: dict[tuple[str, ...], int] = {}

    for trace, _ in frequencies.most_common():
        assigned_cluster = None
        for cluster_id, representative in enumerate(representatives):
            if _trace_similarity(trace, representative) >= similarity_threshold:
                assigned_cluster = cluster_id
                break
        if assigned_cluster is None:
            assigned_cluster = len(representatives)
            representatives.append(trace)
        assignment[trace] = assigned_cluster

    return traces.map(lambda trace: f"V{assignment[trace]:03d}")


def _temporal_stability(labels: pd.Series, periods: pd.Series) -> float:
    frame = pd.DataFrame({"label": labels.to_numpy(), "period": periods.to_numpy()})
    early = frame.loc[frame["period"] == "early", "label"].value_counts(normalize=True)
    late = frame.loc[frame["period"] == "late", "label"].value_counts(normalize=True)
    categories = early.index.union(late.index)
    p = early.reindex(categories, fill_value=0.0).to_numpy(dtype=float)
    q = late.reindex(categories, fill_value=0.0).to_numpy(dtype=float)
    midpoint = 0.5 * (p + q)

    def kl_divergence(a: np.ndarray, b: np.ndarray) -> float:
        mask = a > 0
        return float(np.sum(a[mask] * np.log2(a[mask] / b[mask])))

    js_divergence = 0.5 * kl_divergence(p, midpoint) + 0.5 * kl_divergence(q, midpoint)
    return float(1.0 - np.sqrt(max(js_divergence, 0.0)))


def evaluate_variant_candidates(events: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, pd.Series]]:
    """Evaluate encoding, similarity, and rare-cutoff configurations."""
    cases = build_case_table(events).set_index("case_id")
    candidate_rows = []
    labels_by_candidate: dict[str, pd.Series] = {}

    encodings = ("control_flow", "lifecycle", "time", "payload")
    thresholds = (1.00, 0.80, 0.65)
    rare_cutoffs = (1, 6, 20)

    for encoding in encodings:
        traces = encode_traces(events, encoding).reindex(cases.index)
        for threshold in thresholds:
            clustered = cluster_trace_variants(traces, threshold)
            counts = clustered.value_counts()
            for cutoff in rare_cutoffs:
                candidate_id = f"{encoding}|sim={threshold:.2f}|min={cutoff}"
                retained = clustered.map(counts).ge(cutoff)
                labels = clustered.where(retained, "OTHER")
                retained_variants = int(labels[labels != "OTHER"].nunique())

                coverage = float(retained.mean())
                compactness = float(
                    1.0 - min(max(retained_variants - 1, 0) / max(len(cases) - 1, 1), 1.0)
                )
                relevance = float(
                    normalized_mutual_info_score(cases["outcome"], labels)
                )
                stability = _temporal_stability(labels, cases["period"])

                candidate_rows.append(
                    {
                        "candidate_id": candidate_id,
                        "encoding": encoding,
                        "similarity_threshold": threshold,
                        "rare_cutoff": cutoff,
                        "coverage": coverage,
                        "compactness": compactness,
                        "decision_relevance": relevance,
                        "temporal_stability": stability,
                        "retained_variants": retained_variants,
                    }
                )
                labels_by_candidate[candidate_id] = labels

    candidates = pd.DataFrame(candidate_rows)
    candidates["evidence_score"] = candidates[
        ["coverage", "decision_relevance", "temporal_stability"]
    ].mean(axis=1)
    candidates["pareto"] = pareto_mask(
        candidates,
        objectives=("coverage", "compactness", "decision_relevance", "temporal_stability"),
    )
    objective_columns = [
        "coverage",
        "compactness",
        "decision_relevance",
        "temporal_stability",
    ]
    equivalent = candidates[objective_columns].round(12).duplicated(keep="first")
    candidates.loc[equivalent, "pareto"] = False
    return candidates.sort_values(
        ["pareto", "evidence_score", "compactness"], ascending=False
    ).reset_index(drop=True), labels_by_candidate


def pareto_mask(frame: pd.DataFrame, objectives: tuple[str, ...]) -> np.ndarray:
    """Return True for candidates not dominated on maximize-all objectives."""
    values = frame.loc[:, objectives].to_numpy(dtype=float)
    non_dominated = np.ones(len(values), dtype=bool)

    for index, point in enumerate(values):
        no_worse = np.all(values >= point, axis=1)
        strictly_better = np.any(values > point, axis=1)
        if np.any(no_worse & strictly_better):
            non_dominated[index] = False

    return non_dominated


def plot_pareto_candidates(candidates: pd.DataFrame, output_path: Path | None = None):
    """Plot a readable 2D projection of the four-objective Pareto comparison."""
    colors = {
        "control_flow": "#ef5b5b",
        "lifecycle": "#008f95",
        "time": "#e5a92f",
        "payload": "#17233f",
    }
    fig, axis = plt.subplots(figsize=(9.2, 5.4))

    for encoding, group in candidates.groupby("encoding"):
        axis.scatter(
            group["compactness"],
            group["evidence_score"],
            label=encoding.replace("_", " "),
            color=colors[encoding],
            alpha=0.45,
            s=48,
        )

    front = candidates[candidates["pareto"]]
    axis.scatter(
        front["compactness"],
        front["evidence_score"],
        facecolors="none",
        edgecolors="#008f95",
        linewidths=2.2,
        s=150,
        label="4D Pareto front",
    )

    compact_candidates = front[
        front["compactness"].eq(front["compactness"].max())
    ]
    archetypes = [
        ("balanced", front.nlargest(1, "evidence_score").iloc[0], (0.40, 0.92)),
        (
            "relevance",
            front.nlargest(1, "decision_relevance").iloc[0],
            (0.40, 0.80),
        ),
        (
            "compact",
            compact_candidates.nlargest(1, "evidence_score").iloc[0],
            (0.40, 0.68),
        ),
        (
            "stable",
            front.nlargest(1, "temporal_stability").iloc[0],
            (0.40, 0.52),
        ),
    ]
    annotated: set[str] = set()
    for role, row, offset in archetypes:
        if row["candidate_id"] in annotated:
            continue
        annotated.add(str(row["candidate_id"]))
        axis.annotate(
            (
                f"{role}: {row['encoding']}\n"
                f"sim {row['similarity_threshold']:.2f}, min {int(row['rare_cutoff'])}"
            ),
            (row["compactness"], row["evidence_score"]),
            xytext=offset,
            textcoords="axes fraction",
            fontsize=8,
            arrowprops={"arrowstyle": "-", "color": "#6f7787", "lw": 0.8},
            bbox={"boxstyle": "round,pad=0.2", "fc": "white", "ec": "none", "alpha": 0.9},
        )

    axis.set(
        xlabel="Compactness (higher is fewer retained variants)",
        ylabel="Evidence projection: mean(coverage, relevance, stability)",
        title="Trace-variant configurations: 2D view of a 4-objective Pareto front",
    )
    axis.grid(alpha=0.18)
    axis.legend(frameon=False, ncol=3, loc="lower left")
    fig.tight_layout()

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=180, bbox_inches="tight")
    return fig, axis


def run_lab(output_dir: Path) -> dict[str, object]:
    """Run the complete lab and save reproducible artifacts."""
    output_dir.mkdir(parents=True, exist_ok=True)
    events = generate_event_log()
    payload = profile_payload(events)
    candidates, labels = evaluate_variant_candidates(events)

    events.to_csv(output_dir / "synthetic_event_log.csv", index=False)
    payload.to_csv(output_dir / "payload_profile.csv", index=False)
    candidates.to_csv(output_dir / "variant_candidates.csv", index=False)
    candidates[candidates["pareto"]].to_csv(output_dir / "pareto_front.csv", index=False)
    plot_pareto_candidates(candidates, output_dir / "pareto_front.png")
    plt.close("all")

    return {
        "events": events,
        "payload": payload,
        "candidates": candidates,
        "labels": labels,
    }


def check_lab() -> None:
    """Run lightweight assertions used by the Makefile verification target."""
    events = generate_event_log()
    payload = profile_payload(events)
    candidates, _ = evaluate_variant_candidates(events)

    assert events["case_id"].nunique() == 240
    assert {"start", "complete", "suspend", "resume"} <= set(events["lifecycle"])
    assert payload.loc[payload["payload"] == "outcome", "leakage_risk"].item()
    assert len(candidates) == 36
    assert candidates["pareto"].sum() >= 2
    assert candidates[["coverage", "compactness", "decision_relevance", "temporal_stability"]].apply(
        lambda column: column.between(0.0, 1.0).all()
    ).all()

    front = candidates[candidates["pareto"]]
    assert front["coverage"].min() < 1.0
    assert front["coverage"].max() == 1.0
    assert front["compactness"].nunique() >= 3
    print(
        f"Lab check passed: {len(events):,} events, "
        f"{events['case_id'].nunique()} cases, "
        f"{len(candidates)} candidates, {len(front)} Pareto candidates."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).with_name("outputs"),
        help="Directory for generated CSV and PNG artifacts.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Run assertions without writing artifacts.",
    )
    args = parser.parse_args()

    if args.check:
        check_lab()
    else:
        results = run_lab(args.output_dir)
        front = results["candidates"].query("pareto")
        print(f"Wrote lab artifacts to {args.output_dir}")
        print(front.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
