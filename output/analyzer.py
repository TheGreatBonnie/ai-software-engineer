"""Analyzer module for log analyzer — computes statistics and detects anomalies."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Sequence, Tuple

from reader import LogEntry


@dataclass
class LogStats:
    """Container for log analysis statistics."""

    total_entries: int = 0
    entries_by_level: Dict[str, int] = field(default_factory=dict)
    entries_by_source: Dict[str, int] = field(default_factory=dict)
    entries_by_hour: Dict[int, int] = field(default_factory=dict)
    time_range: Optional[Tuple[datetime, datetime]] = None
    error_messages: List[LogEntry] = field(default_factory=list)
    top_patterns: List[Tuple[str, int]] = field(default_factory=list)
    unique_sources: int = 0
    errors_per_minute: float = 0.0


@dataclass
class Anomaly:
    """Represents a detected anomaly in the log data."""

    type: str
    description: str
    severity: str = "WARNING"
    timestamp: Optional[datetime] = None
    related_entries: List[LogEntry] = field(default_factory=list)


def compute_stats(entries: Sequence[LogEntry]) -> LogStats:
    """Compute comprehensive statistics from log entries.

    Args:
        entries: Sequence of LogEntry objects to analyze.

    Returns:
        LogStats with all computed metrics.
    """
    stats = LogStats(total_entries=len(entries))

    if not entries:
        return stats

    level_counter: Counter = Counter()
    source_counter: Counter = Counter()
    hour_counter: Counter = Counter()
    timestamps: List[datetime] = []
    error_entries: List[LogEntry] = []

    for entry in entries:
        level_counter[entry.level] += 1

        if entry.source:
            source_counter[entry.source] += 1

        if entry.timestamp:
            timestamps.append(entry.timestamp)
            hour_counter[entry.timestamp.hour] += 1

        if entry.level in ("ERROR", "CRITICAL", "FATAL"):
            error_entries.append(entry)

    stats.entries_by_level = dict(level_counter.most_common())
    stats.entries_by_source = dict(source_counter.most_common(20))
    stats.entries_by_hour = dict(sorted(hour_counter.items()))
    stats.error_messages = error_entries[:100]
    stats.unique_sources = len(source_counter)

    if timestamps:
        stats.time_range = (min(timestamps), max(timestamps))
        duration = (stats.time_range[1] - stats.time_range[0]).total_seconds() / 60
        if duration > 0:
            stats.errors_per_minute = len(error_entries) / duration

    # Extract common message patterns
    pattern_counter = Counter()
    for entry in entries:
        pattern = _generalize_message(entry.message)
        if pattern:
            pattern_counter[pattern] += 1
    stats.top_patterns = pattern_counter.most_common(10)

    return stats


def _generalize_message(message: str) -> str:
    """Replace variable parts of a message with placeholders to find patterns."""
    if not message:
        return ""
    # Replace numbers, hex strings, UUIDs, IPs, and quoted strings
    generalized = re.sub(r'\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b', '<UUID>', message)
    generalized = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '<IP>', generalized)
    generalized = re.sub(r'\b0x[0-9a-fA-F]+\b', '<HEX>', generalized)
    generalized = re.sub(r'"[^"]*"', '"<STR>"', generalized)
    generalized = re.sub(r"'[^']*'", "'<STR>'", generalized)
    generalized = re.sub(r'\b\d+\b', '<N>', generalized)
    return generalized


def detect_anomalies(entries: Sequence[LogEntry], stats: Optional[LogStats] = None) -> List[Anomaly]:
    """Detect anomalies in log entries.

    Args:
        entries: Sequence of LogEntry objects.
        stats: Pre-computed LogStats (will compute if not provided).

    Returns:
        List of detected Anomaly objects.
    """
    if stats is None:
        stats = compute_stats(entries)

    anomalies: List[Anomaly] = []

    anomalies.extend(_detect_error_spikes(entries, stats))
    anomalies.extend(_detect_unusual_hours(entries, stats))
    anomalies.extend(_detect_bursts(entries))
    anomalies.extend(_detect_repeated_errors(entries))

    return anomalies


def _detect_error_spikes(entries: Sequence[LogEntry], stats: LogStats) -> List[Anomaly]:
    """Detect periods with abnormally high error rates."""
    anomalies = []
    if not stats.time_range or len(entries) < 10:
        return anomalies

    # Divide the time range into 5-minute windows
    window = timedelta(minutes=5)
    current = stats.time_range[0]
    error_entries = [e for e in entries if e.level in ("ERROR", "CRITICAL", "FATAL") and e.timestamp]

    while current <= stats.time_range[1]:
        window_end = current + window
        count = sum(1 for e in error_entries if current <= e.timestamp < window_end)
        if count >= 5:
            anomalies.append(Anomaly(
                type="error_spike",
                description=f"{count} errors in 5-minute window starting {current}",
                severity="CRITICAL" if count >= 10 else "WARNING",
                timestamp=current,
            ))
        current = window_end

    return anomalies


def _detect_unusual_hours(entries: Sequence[LogEntry], stats: LogStats) -> List[Anomaly]:
    """Detect activity during unusual hours (outside 9-17)."""
    anomalies = []
    off_hours = {h: count for h, count in stats.entries_by_hour.items() if h < 6 or h > 22}
    if off_hours:
        total_off = sum(off_hours.values())
        anomalies.append(Anomaly(
            type="off_hours_activity",
            description=f"{total_off} log entries during off-hours (late night/early morning)",
            severity="INFO",
        ))
    return anomalies


def _detect_bursts(entries: Sequence[LogEntry]) -> List[Anomaly]:
    """Detect sudden bursts of log activity (>50 entries in 1 minute)."""
    anomalies = []
    timed_entries = sorted(
        [e for e in entries if e.timestamp],
        key=lambda e: e.timestamp,
    )

    if len(timed_entries) < 50:
        return anomalies

    i = 0
    while i < len(timed_entries):
        window_end = timed_entries[i].timestamp + timedelta(minutes=1)
        j = i
        while j < len(timed_entries) and timed_entries[j].timestamp <= window_end:
            j += 1
        count = j - i
        if count >= 50:
            anomalies.append(Anomaly(
                type="burst",
                description=f"{count} log entries in 1 minute starting {timed_entries[i].timestamp}",
                severity="WARNING",
                timestamp=timed_entries[i].timestamp,
            ))
        i = j if j > i else i + 1

    return anomalies


def _detect_repeated_errors(entries: Sequence[LogEntry]) -> List[Anomaly]:
    """Detect repeated identical error messages."""
    anomalies = []
    error_patterns: Counter = Counter()

    for entry in entries:
        if entry.level in ("ERROR", "CRITICAL", "FATAL"):
            pattern = _generalize_message(entry.message)
            error_patterns[pattern] += 1

    for pattern, count in error_patterns.items():
        if count >= 10:
            anomalies.append(Anomaly(
                type="repeated_error",
                description=f"Error pattern repeated {count} times: {pattern[:100]}",
                severity="WARNING",
            ))

    return anomalies


def filter_entries(
    entries: Sequence[LogEntry],
    level: Optional[str] = None,
    source: Optional[str] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    search: Optional[str] = None,
) -> List[LogEntry]:
    """Filter log entries by various criteria.

    Args:
        entries: Sequence of LogEntry objects.
        level: Filter by log level (exact match, case-insensitive).
        source: Filter by source (substring match).
        since: Only entries at or after this timestamp.
        until: Only entries at or before this timestamp.
        search: Substring search in the message field.

    Returns:
        Filtered list of LogEntry objects.
    """
    result = list(entries)

    if level:
        level_upper = level.upper()
        result = [e for e in result if e.level == level_upper]

    if source:
        result = [e for e in result if source.lower() in e.source.lower()]

    if since:
        result = [e for e in result if e.timestamp and e.timestamp >= since]

    if until:
        result = [e for e in result if e.timestamp and e.timestamp <= until]

    if search:
        search_lower = search.lower()
        result = [e for e in result if search_lower in e.message.lower()]

    return result
