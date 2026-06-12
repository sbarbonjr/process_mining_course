"""Object-centric analysis and quantified flattening distortions."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from labs.common import load_variant_lab


def build_object_centric_log(events: pd.DataFrame):
    cases = load_variant_lab().build_case_table(events)
    object_rows = []
    relation_rows = []
    event_rows = []
    event_object_rows = []

    for case_index, case in cases.iterrows():
        order_id = f"O-{case_index + 1:04d}"
        item_count = 1 + int(case["product_type"] == "custom") + int(case_index % 5 == 0)
        item_ids = [f"I-{case_index + 1:04d}-{number + 1}" for number in range(item_count)]
        shipment_id = f"S-{case_index // 2 + 1:04d}"  # Some shipments are shared.
        invoice_id = f"V-{case_index + 1:04d}"

        object_rows.extend(
            [{"object_id": order_id, "object_type": "order"}]
            + [{"object_id": item_id, "object_type": "item"} for item_id in item_ids]
            + [
                {"object_id": shipment_id, "object_type": "shipment"},
                {"object_id": invoice_id, "object_type": "invoice"},
            ]
        )
        relation_rows.extend(
            [{"source": order_id, "target": item_id, "relation": "contains"} for item_id in item_ids]
            + [{"source": item_id, "target": shipment_id, "relation": "shipped_in"} for item_id in item_ids]
            + [{"source": order_id, "target": invoice_id, "relation": "invoiced_by"}]
        )

        case_events = events.query("case_id == @case.case_id and lifecycle == 'complete'").sort_values("timestamp")
        for event_index, event in enumerate(case_events.itertuples()):
            event_id = f"E-{case_index + 1:04d}-{event_index + 1:02d}"
            event_rows.append({"event_id": event_id, "activity": event.activity, "timestamp": event.timestamp})
            related = [order_id]
            if event.activity in {"Check", "Clarify", "Approve", "Rework"}:
                related += item_ids
            if event.activity in {"Pack", "Ship"}:
                related += [shipment_id] + item_ids
            if event.activity in {"Approve", "Reject"}:
                related.append(invoice_id)
            event_object_rows.extend(
                [{"event_id": event_id, "object_id": object_id} for object_id in dict.fromkeys(related)]
            )

    objects = pd.DataFrame(object_rows).drop_duplicates()
    relations = pd.DataFrame(relation_rows).drop_duplicates()
    oc_events = pd.DataFrame(event_rows)
    event_objects = pd.DataFrame(event_object_rows).drop_duplicates()
    return oc_events, objects, event_objects, relations


def flatten_by_type(oc_events, objects, event_objects, object_type: str) -> pd.DataFrame:
    ids = set(objects.loc[objects["object_type"] == object_type, "object_id"])
    links = event_objects[event_objects["object_id"].isin(ids)]
    return links.merge(oc_events, on="event_id").rename(columns={"object_id": "case_id"})


def compare_flattening(events: pd.DataFrame):
    oc_events, objects, event_objects, relations = build_object_centric_log(events)
    summaries = []
    for object_type in ("order", "item", "shipment"):
        flat = flatten_by_type(oc_events, objects, event_objects, object_type)
        summaries.append(
            {
                "case_notion": object_type,
                "cases": flat["case_id"].nunique(),
                "rows": len(flat),
                "unique_events": flat["event_id"].nunique(),
                "duplication_factor": len(flat) / max(flat["event_id"].nunique(), 1),
                "median_trace_length": flat.groupby("case_id").size().median(),
            }
        )
    return pd.DataFrame(summaries), (oc_events, objects, event_objects, relations)


def run_lab(output_dir: Path):
    summary, tables = compare_flattening(load_variant_lab().generate_event_log())
    output_dir.mkdir(parents=True, exist_ok=True)
    summary.to_csv(output_dir / "flattening_comparison.csv", index=False)
    for name, table in zip(("events", "objects", "event_objects", "relations"), tables):
        table.to_csv(output_dir / f"ocel_{name}.csv", index=False)
    return summary, tables


def check_lab() -> None:
    summary, tables = compare_flattening(load_variant_lab().generate_event_log())
    assert set(summary["case_notion"]) == {"order", "item", "shipment"}
    assert summary.loc[summary["case_notion"] == "item", "duplication_factor"].item() > 1
    assert tables[1]["object_type"].nunique() == 4
    print(f"Object-centric lab passed: {len(tables[1])} objects, {len(tables[2])} event-object links.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).with_name("outputs"))
    args = parser.parse_args()
    if args.check:
        check_lab()
    else:
        summary, _ = run_lab(args.output_dir)
        print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
