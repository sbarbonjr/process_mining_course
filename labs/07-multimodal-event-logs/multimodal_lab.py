"""Evaluate whether event-text payload adds stable predictive evidence."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.feature_extraction.text import TfidfVectorizer

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from labs.common import load_variant_lab


def multimodal_case_table(events: pd.DataFrame) -> pd.DataFrame:
    cases = load_variant_lab().build_case_table(events)
    cases["customer_note"] = cases["customer_note"].fillna("")
    cases["target"] = (cases["outcome"] == "adverse").astype(int)
    return cases.sort_values("start_time").reset_index(drop=True)


def _structured_preprocessor():
    categorical = ["channel", "product_type", "priority"]
    numeric = ["amount"]
    return ColumnTransformer(
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


def evaluate_modalities(cases: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    split = int(len(cases) * 0.70)
    train, test = cases.iloc[:split], cases.iloc[split:]
    structured_columns = ["channel", "product_type", "priority", "amount"]
    rows = []
    predictions = test[["case_id", "target", "start_time"]].copy()

    models = {
        "structured": Pipeline(
            [
                ("features", _structured_preprocessor()),
                ("model", LogisticRegression(max_iter=1000, class_weight="balanced")),
            ]
        ),
        "text": Pipeline(
            [
                ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=2)),
                ("model", LogisticRegression(max_iter=1000, class_weight="balanced")),
            ]
        ),
        "combined": Pipeline(
            [
                (
                    "features",
                    ColumnTransformer(
                        [
                            ("structured", _structured_preprocessor(), structured_columns),
                            ("text", TfidfVectorizer(ngram_range=(1, 2), min_df=2), "customer_note"),
                        ]
                    ),
                ),
                ("model", LogisticRegression(max_iter=1000, class_weight="balanced")),
            ]
        ),
    }

    for name, model in models.items():
        if name == "text":
            model.fit(train["customer_note"], train["target"])
            probability = model.predict_proba(test["customer_note"])[:, 1]
        elif name == "structured":
            model.fit(train[structured_columns], train["target"])
            probability = model.predict_proba(test[structured_columns])[:, 1]
        else:
            model.fit(train[structured_columns + ["customer_note"]], train["target"])
            probability = model.predict_proba(test[structured_columns + ["customer_note"]])[:, 1]
        predictions[f"{name}_risk"] = probability
        rows.append(
            {
                "modality": name,
                "roc_auc": roc_auc_score(test["target"], probability),
                "brier": brier_score_loss(test["target"], probability),
            }
        )

    metrics = pd.DataFrame(rows)
    structured_auc = metrics.loc[metrics["modality"] == "structured", "roc_auc"].item()
    metrics["auc_gain_over_structured"] = metrics["roc_auc"] - structured_auc
    return metrics, predictions


def run_lab(output_dir: Path):
    cases = multimodal_case_table(load_variant_lab().generate_event_log())
    metrics, predictions = evaluate_modalities(cases)
    output_dir.mkdir(parents=True, exist_ok=True)
    cases.to_csv(output_dir / "multimodal_cases.csv", index=False)
    metrics.to_csv(output_dir / "modality_metrics.csv", index=False)
    predictions.to_csv(output_dir / "modality_predictions.csv", index=False)
    return cases, metrics, predictions


def check_lab() -> None:
    cases = multimodal_case_table(load_variant_lab().generate_event_log())
    metrics, predictions = evaluate_modalities(cases)
    assert set(metrics["modality"]) == {"structured", "text", "combined"}
    assert metrics["roc_auc"].between(0, 1).all()
    assert len(predictions) > 60
    assert cases["customer_note"].str.len().gt(0).any()
    print(f"Multimodal lab passed: combined AUC {metrics.loc[metrics['modality'] == 'combined', 'roc_auc'].item():.3f}.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).with_name("outputs"))
    args = parser.parse_args()
    if args.check:
        check_lab()
    else:
        _, metrics, _ = run_lab(args.output_dir)
        print(metrics.to_string(index=False))


if __name__ == "__main__":
    main()
