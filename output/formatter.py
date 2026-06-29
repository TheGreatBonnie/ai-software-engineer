"""Formatter module for log analyzer — generates human-readable reports."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, Sequence

from analyzer import Anomaly, LogStats
from reader import LogEntry


def format_report(
    stats: LogStats,
    anomalies: Optional[List[Anomaly]] = None,
    entries: Optional[Sequence[LogEntry]] = None,
    verbose: bool = False,
) -> str:
    """Generate a full analysis report.

    Args:
        stats: Computed log statistics.
        anomalies: Detected anomalies.
        entries: Original log entries (used for verbose output).
        verbose: Whether to include sample entries.

    Returns:
        Formatted report string.
    """
    sections = [
        _header(),
        _summary_section(stats),
        _level_breakdown(stats),
        _time_distribution(stats),
        _top_sources(stats),
        _top_patterns(stats),
    ]

    if anomalies:
        sections.append(_anomalies_section(anomalies))

    if verbose and entries:
        sections.append(_sample_errors_section(stats))
        sections.append(_recent_entries_section(entries))

    return "\n".join(sections)


def _header() -> str:
    """Generate report header."""
    width = 70
    return "\n".join([
        "=" * width,
        "LOG ANALYSIS REPORT".center(width),
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".center(width),
        "=" * width,
    ])


def _summary_section(stats: LogStats) -> str:
    """Generate summary section."""
    lines = [
        "",
        "--- SUMMARY ---",
        f"  Total entries:     {stats.total_entries:,}",
        f"  Unique sources:    {stats.unique_sources}",
        f"  Errors:            {stats.entries_by_level.get('ERROR', 0):,}",
        f"  Critical:          {stats.entries_by_level.get('CRITICAL', 0):,}",
    ]

    if stats.time_range:
        start, end = stats.time_range
        duration = end - start
        lines.append(f"  Time range:        {start} -> {end}")
        lines.append(f"  Duration:          {duration}")

    if stats.errors_per_minute > 0:
        lines.append(f"  Errors/minute:     {stats.errors_per_minute:.2f}")

    return "\n".join(lines)


def _level_breakdown(stats: LogStats) -> str:
    """Generate level breakdown section."""
    if not stats.entries_by_level:
        return ""

    lines = ["", "--- LOG LEVELS ---"]
    max_count = max(stats.entries_by_level.values()) if stats.entries_by_level else 1

    for level, count in sorted(stats.entries_by_level.items(), key=lambda x: -x[1]):
        bar_len = int(30 * count / max_count)
        bar = "#" * bar_len
        pct = (count / stats.total_entries * 100) if stats.total_entries > 0 else 0
        lines.append(f"  {level:<12} {count:>7,}  {bar}  ({pct:.1f}%)")

    return "\n".join(lines)


def _time_distribution(stats: LogStats) -> str:
    """Generate hourly distribution section."""
    if not stats.entries_by_hour:
        return ""

    lines = ["", "--- HOURLY DISTRIBUTION ---"]
    max_count = max(stats.entries_by_hour.values()) if stats.entries_by_hour else 1

    for hour in range(24):
        count = stats.entries_by_hour.get(hour, 0)
        bar_len = int(25 * count / max_count) if max_count > 0 else 0
        bar = "#" * bar_len
        lines.append(f"  {hour:02d}:00  {count:>6,}  {bar}")

    return "\n".join(lines)


def _top_sources(stats: LogStats) -> str:
    """Generate top sources section."""
    if not stats.entries_by_source:
        return ""

    lines = ["", "--- TOP SOURCES ---"]
    for source, count in list(stats.entries_by_source.items())[:10]:
        lines.append(f"  {source:<30} {count:>7,}")

    return "\n".join(lines)


def _top_patterns(stats: LogStats) -> str:
    """Generate top message patterns section."""
    if not stats.top_patterns:
        return ""

    lines = ["", "--- TOP MESSAGE PATTERNS ---"]
    for pattern, count in stats.top_patterns[:10]:
        display = pattern[:60] + "..." if len(pattern) > 60 else pattern
        lines.append(f"  [{count:>5,}x] {display}")

    return "\n".join(lines)


def _anomalies_section(anomalies: List[Anomaly]) -> str:
    """Generate anomalies section."""
    lines = [
        "",
        "--- ANOMALIES DETECTED ---",
        f"  Total: {len(anomalies)}",
        "",
    ]

    for i, anomaly in enumerate(anomalies, 1):
        severity_marker = {"CRITICAL": "[!]", "WARNING": "[*]", "[INFO]": "[i]"}.get(anomaly.severity, "[?]")
        lines.append(f"  {i}. {severity_marker} [{anomaly.type}] {anomaly.description}")

    return "\n".join(lines)


def _sample_errors_section(stats: LogStats) -> str:
    """Generate sample error entries section."""
    if not stats.error_messages:
        return ""

    lines = ["", "--- SAMPLE ERROR ENTRIES ---"]
    for entry in stats.error_messages[:5]:
        ts = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S") if entry.timestamp else "N/A"
        msg = entry.message[:80] + "..." if len(entry.message) > 80 else entry.message
        lines.append(f"  [{ts}] [{entry.level}] {msg}")

    return "\n".join(lines)


def _recent_entries_section(entries: Sequence[LogEntry]) -> str:
    """Generate recent entries section."""
    lines = ["", "--- RECENT ENTRIES (last 10) ---"]
    for entry in entries[-10:]:
        ts = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S") if entry.timestamp else "N/A"
        msg = entry.message[:80] + "..." if len(entry.message) > 80 else entry.message
        lines.append(f"  [{ts}] [{entry.level:<8}] {msg}")

    return "\n".join(lines)


def format_csv(entries: Sequence[LogEntry]) -> str:
    """Format log entries as CSV.

    Args:
        entries: Log entries to format.

    Returns:
        CSV-formatted string.
    """
    lines = ["timestamp,level,source,message"]
    for entry in entries:
        ts = entry.timestamp.isoformat() if entry.timestamp else ""
        msg = entry.message.replace('"', '""')
        lines.append(f'{ts},{entry.level},{entry.source},"{msg}"')
    return "\n".join(lines)


def format_json(entries: Sequence[LogEntry]) -> str:
    """Format log entries as JSON.

    Args:
        entries: Log entries to format.

    Returns:
        JSON-formatted string.
    """
    import json

    records = []
    for entry in entries:
        record = {
            "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
            "level": entry.level,
            "source": entry.source,
            "message": entry.message,
        }
        if entry.metadata:
            record["metadata"] = entry.metadata
        records.append(record)

    return json.dumps(records, indent=2)
