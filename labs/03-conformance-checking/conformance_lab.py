"""Alignment-style conformance diagnostics against a reference process."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import sys

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from labs.common import load_variant_lab


REFERENCE_TRACES = (
    ("Receive", "Check", "Approve", "Ship"),
    ("Receive", "Check", "Clarify", "Check", "Approve", "Ship"),
    ("Receive", "Check", "Reject"),
)


def alignment_moves(observed: tuple[str, ...], expected: tuple[str, ...]):
    rows = len(observed) + 1
    columns = len(expected) + 1
    cost = [[0] * columns for _ in range(rows)]
    back = [[None] * columns for _ in range(rows)]
    for i in range(1, rows):
        cost[i][0] = i
        back[i][0] = "log"
    for j in range(1, columns):
        cost[0][j] = j
        back[0][j] = "model"
    for i in range(1, rows):
        for j in range(1, columns):
            options = [
                (cost[i - 1][j] + 1, "log"),
                (cost[i][j - 1] + 1, "model"),
                (cost[i - 1][j - 1] + (observed[i - 1] != expected[j - 1]), "sync" if observed[i - 1] == expected[j - 1] else "replace"),
            ]
            cost[i][j], back[i][j] = min(options, key=lambda item: item[0])

    i, j = len(observed), len(expected)
    moves = []
    while i or j:
        move = back[i][j]
        if move == "sync":
            moves.append(("sync", observed[i - 1], expected[j - 1]))
            i -= 1
            j -= 1
        elif move == "replace":
            moves.append(("replace", observed[i - 1], expected[j - 1]))
            i -= 1
            j -= 1
        elif move == "log":
            moves.append(("log", observed[i - 1], None))
            i -= 1
        else:
            moves.append(("model", None, expected[j - 1]))
            j -= 1
    return cost[-1][-1], list(reversed(moves))


def best_alignment(trace: tuple[str, ...]):
    candidates = [
        (alignment_moves(trace, reference)[0], reference, alignment_moves(trace, reference)[1])
        for reference in REFERENCE_TRACES
    ]
    return min(candidates, key=lambda item: item[0])


def conformance_report(events: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    traces = load_variant_lab().encode_traces(events, "control_flow")
    rows = []
    deviations: Counter = Counter()
    for case_id, trace in traces.items():
        cost, reference, moves = best_alignment(trace)
        denominator = max(len(trace), len(reference), 1)
        rows.append(
            {
                "case_id": case_id,
                "trace": " > ".join(trace),
                "reference": " > ".join(reference),
                "alignment_cost": cost,
                "conformance": 1.0 - cost / denominator,
                "deviation_moves": sum(move[0] != "sync" for move in moves),
            }
        )
        for move, observed, expected in moves:
            if move != "sync":
                deviations[(move, observed or "-", expected or "-")] += 1
    deviation_frame = pd.DataFrame(
        [
            {"move": move, "observed": observed, "expected": expected, "count": count}
            for (move, observed, expected), count in deviations.most_common()
        ]
    )
    return pd.DataFrame(rows), deviation_frame


def run_lab(output_dir: Path):
    events = load_variant_lab().generate_event_log()
    cases, deviations = conformance_report(events)
    output_dir.mkdir(parents=True, exist_ok=True)
    cases.to_csv(output_dir / "case_conformance.csv", index=False)
    deviations.to_csv(output_dir / "deviation_summary.csv", index=False)
    return cases, deviations


def check_lab() -> None:
    cases, deviations = conformance_report(load_variant_lab().generate_event_log())
    assert len(cases) == 240
    assert cases["conformance"].between(0, 1).all()
    assert (cases["alignment_cost"] > 0).any()
    assert {"log", "model", "replace"} & set(deviations["move"])
    print(f"Conformance lab passed: {(cases['alignment_cost'] > 0).sum()} deviating cases.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).with_name("outputs"))
    args = parser.parse_args()
    if args.check:
        check_lab()
    else:
        cases, deviations = run_lab(args.output_dir)
        print(cases.describe().to_string())
        print(deviations.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
