"""Measure real end-to-end positioning on the dedicated safe surface."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import statistics
import time

from mousse_controler.command_client import invoke


DEFAULT_CONFIG = Path(r"C:\ProgramData\MousseControler\controller.json")
POINTS = ((900, 380), (1000, 400), (1100, 420), (1000, 440), (900, 420))


def percentile_nearest_rank(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(percentile * len(ordered)) - 1)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--cycles", type=int, default=20)
    args = parser.parse_args()
    if not 1 <= args.cycles <= 100:
        raise SystemExit("cycles must be between 1 and 100")

    steps = [
        {
            "zone": {"type": "rectangle", "x": x, "y": y, "width": 8, "height": 8},
            "wait_mode": "automatic",
            "wait_seconds": 0.0,
        }
        for x, y in POINTS
    ]
    started = time.perf_counter()
    results = []
    status = None
    for cycle in range(args.cycles):
        arguments = {
            "seed": 20261120 + cycle,
            "trajectory": {
                "spacing_px": 28.0,
                "curvature": 0.08,
                "speed_variation": 0.02,
                "micro_variation_px": 1,
                "minimum_points": 3,
            },
            "steps": steps,
        }
        invoke(args.config, "sequence_start", arguments)
        deadline = time.monotonic() + 30.0
        while time.monotonic() < deadline:
            status = invoke(args.config, "sequence_status")
            if status["state"] in {"COMPLETED", "ERROR", "STOPPED"}:
                break
            time.sleep(0.05)
        if status is None or status["state"] not in {"COMPLETED", "ERROR", "STOPPED"}:
            raise TimeoutError("performance qualification timed out")
        results.extend(status["results"])
        if status["state"] != "COMPLETED":
            break
    arrived = [item for item in results if item["state"] == "ARRIVED"]
    latencies = [(item["finished_at"] - item["started_at"]) * 1000.0 for item in arrived]
    errors = [
        math.dist(item["target"], item["measured_position"])
        for item in arrived
    ]
    corrections = [int(item.get("metrics", {}).get("corrections", 0)) for item in arrived]
    transport_ms = [float(item.get("metrics", {}).get("transport_ms", 0.0)) for item in arrived]
    feedback_ms = [float(item.get("metrics", {}).get("feedback_wait_ms", 0.0)) for item in arrived]
    expected = len(steps) * args.cycles
    output = {
        "schema": 1,
        "matrix": {"points": len(POINTS), "cycles": args.cycles, "expected_moves": expected},
        "state": status["state"],
        "completed_moves": len(arrived),
        "success_rate_percent": round(len(arrived) * 100.0 / expected, 3),
        "elapsed_ms": round((time.perf_counter() - started) * 1000.0, 3),
        "latency_ms": {
            "mean": round(statistics.fmean(latencies), 3) if latencies else None,
            "median": round(statistics.median(latencies), 3) if latencies else None,
            "p95": round(percentile_nearest_rank(latencies, 0.95), 3) if latencies else None,
            "max": round(max(latencies), 3) if latencies else None,
        },
        "error_px": {
            "mean": round(statistics.fmean(errors), 3) if errors else None,
            "max": round(max(errors), 3) if errors else None,
        },
        "corrections": {
            "mean": round(statistics.fmean(corrections), 3) if corrections else None,
            "max": max(corrections) if corrections else None,
        },
        "stage_totals_ms": {
            "transport": round(sum(transport_ms), 3),
            "feedback_wait": round(sum(feedback_ms), 3),
        },
        "failure": status.get("error"),
        "transport_after": invoke(args.config, "transport_status"),
    }
    print(json.dumps(output, indent=2))
    return 0 if status["state"] == "COMPLETED" and len(arrived) == expected else 1


if __name__ == "__main__":
    raise SystemExit(main())
