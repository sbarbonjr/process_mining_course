"""Leakage-safe predictive process monitoring with prefix encodings."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, brier_score_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from labs.common import load_variant_lab


def build_prefix_table(events: pd.DataFrame, prefix_length: int = 3) -> pd.DataFrame:
    completed = events.query("lifecycle == 'complete'").sort_values(["case_id", "timestamp"])
    rows = []
    for case_id, group in completed.groupby("case_id", sort=True):
        if len(group) <= prefix_length:
            continue
        prefix = group.iloc[:prefix_length]
        outcome = group["outcome"].dropna().iloc[-1]
        counts = prefix["activity"].value_counts()
        rows.append(
            {
                "case_id": case_id,
                "start_time": group["timestamp"].min(),
                "current_activity": prefix["activity"].iloc[-1],
                "channel": group["channel"].iloc[0],
                "product_type": group["product_type"].iloc[0],
                "priority": group["priority"].iloc[0],
                "amount": group["amount"].iloc[0],
                "elapsed_hours": (prefix["timestamp"].iloc[-1] - prefix["timestamp"].iloc[0]).total_seconds() / 3600,
                "activities_seen": len(prefix),
                "check_count": int(counts.get("Check", 0)),
                "clarify_count": int(counts.get("Clarify", 0)),
                "target": int(outcome == "adverse"),
            }
        )
    return pd.DataFrame(rows).sort_values("start_time").reset_index(drop=True)


def evaluate_models(prefixes: pd.DataFrame):
    split = int(len(prefixes) * 0.70)
    train = prefixes.iloc[:split]
    test = prefixes.iloc[split:]
    features = [
        "current_activity",
        "channel",
        "product_type",
        "priority",
        "amount",
        "elapsed_hours",
        "activities_seen",
        "check_count",
        "clarify_count",
    ]
    categorical = ["current_activity", "channel", "product_type", "priority"]
    numeric = [column for column in features if column not in categorical]

    preprocessing = ColumnTransformer(
        [
            (
                "categorical",
                Pipeline(
                    [
                        ("impute", SimpleImputer(strategy="most_frequent")),
                        ("encode", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                categorical,
            ),
            (
                "numeric",
                Pipeline(
                    [
                        ("impute", SimpleImputer(strategy="median")),
                        ("scale", StandardScaler()),
                    ]
                ),
                numeric,
            ),
        ]
    )
    model = Pipeline(
        [
            ("preprocess", preprocessing),
            ("model", LogisticRegression(max_iter=1000, class_weight="balanced")),
        ]
    )
    model.fit(train[features], train["target"])
    probabilities = model.predict_proba(test[features])[:, 1]
    predictions = (probabilities >= 0.5).astype(int)

    baseline = DummyClassifier(strategy="prior")
    baseline.fit(np.zeros((len(train), 1)), train["target"])
    baseline_probabilities = baseline.predict_proba(np.zeros((len(test), 1)))[:, 1]

    metrics = pd.DataFrame(
        [
            {
                "model": "prefix logistic regression",
                "roc_auc": roc_auc_score(test["target"], probabilities),
                "brier": brier_score_loss(test["target"], probabilities),
                "balanced_accuracy": balanced_accuracy_score(test["target"], predictions),
            },
            {
                "model": "base-rate baseline",
                "roc_auc": roc_auc_score(test["target"], baseline_probabilities),
                "brier": brier_score_loss(test["target"], baseline_probabilities),
                "balanced_accuracy": balanced_accuracy_score(
                    test["target"], np.zeros(len(test), dtype=int)
                ),
            },
        ]
    )
    predictions_frame = test[["case_id", "start_time", "target"]].copy()
    predictions_frame["risk"] = probabilities
    return model, metrics, predictions_frame


def plot_calibration(predictions: pd.DataFrame, output: Path | None = None):
    bins = pd.cut(predictions["risk"], bins=np.linspace(0, 1, 6), include_lowest=True)
    calibration = predictions.groupby(bins, observed=False).agg(
        predicted=("risk", "mean"), observed=("target", "mean"), cases=("target", "size")
    ).dropna()
    figure, axis = plt.subplots(figsize=(6.2, 5.0))
    axis.plot([0, 1], [0, 1], "--", color="#6f7787")
    axis.plot(calibration["predicted"], calibration["observed"], "o-", color="#008f95")
    axis.set(xlabel="Mean predicted risk", ylabel="Observed adverse rate", title="Temporal holdout calibration")
    axis.grid(alpha=0.2)
    figure.tight_layout()
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(output, dpi=180)
    return figure


def run_lab(output_dir: Path):
    prefixes = build_prefix_table(load_variant_lab().generate_event_log())
    model, metrics, predictions = evaluate_models(prefixes)
    output_dir.mkdir(parents=True, exist_ok=True)
    prefixes.to_csv(output_dir / "prefix_table.csv", index=False)
    metrics.to_csv(output_dir / "predictive_metrics.csv", index=False)
    predictions.to_csv(output_dir / "holdout_predictions.csv", index=False)
    plot_calibration(predictions, output_dir / "calibration.png")
    plt.close("all")
    return prefixes, model, metrics, predictions


def check_lab() -> None:
    prefixes = build_prefix_table(load_variant_lab().generate_event_log())
    _, metrics, predictions = evaluate_models(prefixes)
    assert len(prefixes) > 200
    assert predictions["start_time"].min() >= prefixes.iloc[int(len(prefixes) * 0.70)]["start_time"]
    assert metrics["roc_auc"].between(0, 1).all()
    assert metrics.loc[metrics["model"] == "prefix logistic regression", "roc_auc"].item() > 0.5
    print(f"Predictive lab passed: {len(prefixes)} prefixes, holdout AUC {metrics.iloc[0]['roc_auc']:.3f}.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).with_name("outputs"))
    args = parser.parse_args()
    if args.check:
        check_lab()
    else:
        _, _, metrics, _ = run_lab(args.output_dir)
        print(metrics.to_string(index=False))


if __name__ == "__main__":
    main()
