#!/usr/bin/env python3
"""CLI entry point for the log analyzer."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from analyzer import compute_stats, detect_anomalies, filter_entries
from formatter import format_csv, format_json, format_report
from reader import read_log_entries, find_log_files


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="log-analyzer",
        description="Analyze log files and generate reports.",
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Log file(s) to analyze. Supports .log, .txt, and .gz files.",
    )
    parser.add_argument(
        "-o", "--output",
        choices=["report", "csv", "json"],
        default="report",
        help="Output format (default: report).",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Include sample entries in report.",
    )
    parser.add_argument(
        "--level",
        help="Filter by log level (e.g., ERROR, WARN, INFO).",
    )
    parser.add_argument(
        "--source",
        help="Filter by source (substring match).",
    )
    parser.add_argument(
        "--search",
        help="Search for a pattern in log messages.",
    )
    parser.add_argument(
        "--since",
        help="Only show entries after this timestamp (ISO format).",
    )
    parser.add_argument(
        "--until",
        help="Only show entries before this timestamp (ISO format).",
    )
    parser.add_argument(
        "--anomalies",
        action="store_true",
        help="Only show detected anomalies.",
    )
    parser.add_argument(
        "--no-anomalies",
        action="store_true",
        help="Skip anomaly detection.",
    )

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if not args.files:
        print("Error: No log files specified.", file=sys.stderr)
        print("Usage: log-analyzer <file1> [file2] ...", file=sys.stderr)
        return 1

    # Read and parse all log files
    all_entries = []
    for filepath in args.files:
        path = Path(filepath)
        if not path.exists():
            print(f"Error: File not found: {filepath}", file=sys.stderr)
            return 1
        try:
            entries = read_log_entries(filepath)
            all_entries.extend(entries)
        except Exception as e:
            print(f"Error reading {filepath}: {e}", file=sys.stderr)
            return 1

    if not all_entries:
        print("No log entries found.", file=sys.stderr)
        return 0

    # Apply filters
    from datetime import datetime as dt

    since = dt.fromisoformat(args.since) if args.since else None
    until = dt.fromisoformat(args.until) if args.until else None

    filtered = filter_entries(
        all_entries,
        level=args.level,
        source=args.source,
        since=since,
        until=until,
        search=args.search,
    )

    if not filtered:
        print("No log entries match the specified filters.", file=sys.stderr)
        return 0

    # Compute stats and anomalies
    stats = compute_stats(filtered)
    anomalies = [] if args.no_anomalies else detect_anomalies(filtered, stats)

    # Output
    if args.anomalies:
        if anomalies:
            for a in anomalies:
                marker = {"CRITICAL": "[!]", "WARNING": "[*]", "[INFO]": "[i]"}.get(a.severity, "[?]")
                print(f"{marker} [{a.type}] {a.description}")
        else:
            print("No anomalies detected.")
    elif args.output == "csv":
        print(format_csv(filtered))
    elif args.output == "json":
        print(format_json(filtered))
    else:
        report = format_report(stats, anomalies, filtered, verbose=args.verbose)
        print(report)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
