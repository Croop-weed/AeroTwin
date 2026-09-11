"""Compatibility entrypoint for the live AeroTwin dashboard demo.

The old API demo used an in-process fallback and only printed a few snapshots,
so it could not drive the browser dashboard. Keep this filename usable for
existing commands while sharing the paced HTTP producer with dashboard_demo.
"""

from __future__ import annotations

import argparse

from dashboard_demo import run_demo


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AeroTwin live dashboard demo")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of AeroTwin API")
    parser.add_argument("--uav", default="UAV-001", help="UAV ID shown by the dashboard")
    parser.add_argument("--delay", type=float, default=0.35, help="Delay between streamed steps in seconds")
    parser.add_argument("--continuous", action="store_true", help="Repeat the scenario continuously")
    args = parser.parse_args()
    run_demo(args.url, args.uav, args.delay, args.continuous)
