"""
LithKhoj: Automated Smoke Test Runner for Continuous Integration & Multi-District Verification.
Validates rapid evaluation mode across all supported Indian pegmatite cratons.
"""

import os
import sys
import time
import argparse
from typing import List, Dict, Any

# Ensure project root is on sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from demo_pipeline import run_pipeline
from src.geospatial.district_profiles import DISTRICT_REGISTRY, list_supported_districts


def run_smoke_suite(districts: List[str] = None) -> bool:
    """Runs fast pipeline evaluation across specified or all registered districts."""
    target_districts = districts or list(DISTRICT_REGISTRY.keys())
    print("=" * 80)
    print("  LITHKHOJ: MULTI-DISTRICT CI SMOKE TEST RUNNER")
    print(f"  Target Districts ({len(target_districts)}): {', '.join(target_districts)}")
    print("=" * 80)

    results: Dict[str, Dict[str, Any]] = {}
    suite_start = time.time()
    all_passed = True

    for dist_id in target_districts:
        print(f"\n>>> Running Smoke Test for District: [{dist_id}]")
        t0 = time.time()
        try:
            deliverables = run_pipeline(district=dist_id, fast=True)
            elapsed = time.time() - t0

            # Verify deliverables exist on disk and have non-zero size
            missing_or_empty = []
            for k, fpath in deliverables.items():
                if not os.path.exists(fpath):
                    missing_or_empty.append(f"{k}: missing ({fpath})")
                elif os.path.getsize(fpath) == 0:
                    missing_or_empty.append(f"{k}: empty (0 bytes)")

            # Also verify .tfw world file
            geotiff_path = deliverables.get("geotiff")
            if geotiff_path:
                tfw_path = os.path.splitext(geotiff_path)[0] + ".tfw"
                if not os.path.exists(tfw_path) or os.path.getsize(tfw_path) == 0:
                    missing_or_empty.append(f"world_file: missing/empty ({tfw_path})")

            passed = len(missing_or_empty) == 0
            if not passed:
                all_passed = False

            results[dist_id] = {
                "status": "PASS" if passed else "FAIL",
                "duration_sec": elapsed,
                "issues": missing_or_empty,
                "deliverables_count": len(deliverables),
            }
        except Exception as exc:
            elapsed = time.time() - t0
            all_passed = False
            results[dist_id] = {
                "status": "ERROR",
                "duration_sec": elapsed,
                "issues": [str(exc)],
                "deliverables_count": 0,
            }

    total_duration = time.time() - suite_start
    print("\n" + "=" * 80)
    print("  SMOKE SUITE EXECUTION SUMMARY")
    print("=" * 80)
    print(f"  {'District':<25} | {'Status':<8} | {'Duration (s)':<12} | {'Artifacts':<10} | Notes")
    print("  " + "-" * 76)
    for dist_id, res in results.items():
        notes = "OK" if res["status"] == "PASS" else "; ".join(res["issues"])[:40]
        print(f"  {dist_id:<25} | {res['status']:<8} | {res['duration_sec']:<12.2f} | {res['deliverables_count']:<10} | {notes}")
    print("  " + "-" * 76)
    print(f"  Total Test Time: {total_duration:.2f}s | Result: {'SUCCESS (ALL PASSED)' if all_passed else 'FAILURE'}")
    print("=" * 80)

    return all_passed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LithKhoj CI Smoke Test Runner")
    parser.add_argument(
        "--districts",
        nargs="+",
        default=None,
        help="List of district IDs to run (default: all registered cratons)",
    )
    args = parser.parse_args()
    success = run_smoke_suite(districts=args.districts)
    sys.exit(0 if success else 1)
