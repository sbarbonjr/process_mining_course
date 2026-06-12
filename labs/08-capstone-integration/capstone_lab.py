"""Integrate all course practices into one reproducible evidence package."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from labs.common import load_module, load_variant_lab


LABS = {
    "discovery": "labs/02-discovery-model-quality/discovery_quality_lab.py",
    "conformance": "labs/03-conformance-checking/conformance_lab.py",
    "performance": "labs/04-performance-organization/performance_lab.py",
    "prediction": "labs/05-predictive-monitoring/predictive_monitoring_lab.py",
    "objects": "labs/06-object-centric-analysis/object_centric_lab.py",
    "multimodal": "labs/07-multimodal-event-logs/multimodal_lab.py",
}


def build_evidence_package() -> dict[str, pd.DataFrame]:
    variant = load_variant_lab()
    modules = {
        name: load_module(f"capstone_{name}", REPO_ROOT / relative_path)
        for name, relative_path in LABS.items()
    }
    events = variant.generate_event_log()
    payload = variant.profile_payload(events)
    variant_candidates, _ = variant.evaluate_variant_candidates(events)
    discovery = modules["discovery"].discover_candidates(events)
    case_conformance, deviations = modules["conformance"].conformance_report(events)
    activity, cases, handovers, cohorts = modules["performance"].analyze_performance(events)
    prefixes = modules["prediction"].build_prefix_table(events)
    _, predictive_metrics, predictions = modules["prediction"].evaluate_models(prefixes)
    flattening, _ = modules["objects"].compare_flattening(events)
    multimodal_cases = modules["multimodal"].multimodal_case_table(events)
    modality_metrics, _ = modules["multimodal"].evaluate_modalities(multimodal_cases)

    scorecard = pd.DataFrame(
        [
            {"evidence": "Cases analyzed", "value": events["case_id"].nunique(), "interpretation": "Population size"},
            {"evidence": "Variant Pareto candidates", "value": int(variant_candidates["pareto"].sum()), "interpretation": "Encoding/threshold shortlist"},
            {"evidence": "Discovery Pareto candidates", "value": int(discovery["pareto"].sum()), "interpretation": "Model shortlist"},
            {"evidence": "Deviating cases", "value": int((case_conformance["alignment_cost"] > 0).sum()), "interpretation": "Requires explanation or model review"},
            {"evidence": "Largest activity p90", "value": round(float(activity["p90_hours"].max()), 2), "interpretation": "Service-time bottleneck in hours"},
            {"evidence": "Predictive holdout AUC", "value": round(float(predictive_metrics.iloc[0]["roc_auc"]), 3), "interpretation": "Temporal discrimination"},
            {"evidence": "Item flattening duplication", "value": round(float(flattening.loc[flattening["case_notion"] == "item", "duplication_factor"].item()), 3), "interpretation": "Representation distortion"},
            {"evidence": "Text AUC gain", "value": round(float(modality_metrics.loc[modality_metrics["modality"] == "text", "auc_gain_over_structured"].item()), 3), "interpretation": "Incremental modality evidence"},
        ]
    )

    return {
        "events": events,
        "payload_profile": payload,
        "variant_candidates": variant_candidates,
        "discovery_candidates": discovery,
        "case_conformance": case_conformance,
        "deviations": deviations,
        "activity_performance": activity,
        "case_performance": cases,
        "handovers": handovers,
        "cohorts": cohorts,
        "predictive_metrics": predictive_metrics,
        "predictions": predictions,
        "flattening": flattening,
        "modality_metrics": modality_metrics,
        "scorecard": scorecard,
    }


def run_lab(output_dir: Path) -> dict[str, pd.DataFrame]:
    package = build_evidence_package()
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, frame in package.items():
        frame.to_csv(output_dir / f"{name}.csv", index=False)
    return package


def check_lab() -> None:
    package = build_evidence_package()
    assert len(package["scorecard"]) == 8
    assert package["events"]["case_id"].nunique() == 240
    assert package["predictive_metrics"]["roc_auc"].between(0, 1).all()
    assert package["variant_candidates"]["pareto"].any()
    print(f"Capstone lab passed: {len(package)} evidence tables, {len(package['scorecard'])} scorecard items.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).with_name("outputs"))
    args = parser.parse_args()
    if args.check:
        check_lab()
    else:
        package = run_lab(args.output_dir)
        print(package["scorecard"].to_string(index=False))


if __name__ == "__main__":
    main()
