"""Reader module for log analyzer — handles file I/O operations."""

from __future__ import annotations

import gzip
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterator, List, Optional, Union


@dataclass
class LogEntry:
    """Represents a single parsed log line."""

    timestamp: Optional[datetime] = None
    level: str = "UNKNOWN"
    source: str = ""
    message: str = ""
    raw: str = ""
    metadata: dict = field(default_factory=dict)


# Common log format patterns
_PATTERNS = [
    # Apache/Nginx combined log format
    re.compile(
        r'(?P<ip>\S+) \S+ \S+ \[(?P<timestamp>[^\]]+)\] '
        r'"(?P<method>\S+) (?P<path>\S+) \S+" (?P<status>\d{3}) (?P<size>\S+)'
    ),
    # Syslog format: "Jan  1 12:00:00 hostname process[pid]: message"
    re.compile(
        r'(?P<timestamp>\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}) '
        r'(?P<hostname>\S+) (?P<source>\S+?)(?:\[\d+\])?: (?P<message>.+)'
    ),
    # ISO timestamp format: "2024-01-01T12:00:00 LEVEL source: message"
    re.compile(
        r'(?P<timestamp>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)'
        r'\s+(?P<level>\w+)\s+(?P<message>.+)'
    ),
    # Simple format: "[2024-01-01 12:00:00] [LEVEL] message"
    re.compile(
        r'\[(?P<timestamp>[^\]]+)\]\s+\[(?P<level>\w+)\]\s+(?P<message>.+)'
    ),
]

_TIMESTAMP_FORMATS = [
    "%d/%b/%Y:%H:%M:%S %z",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%S.%f%z",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M:%S.%f",
    "%b %d %H:%M:%S",
]

# Pattern to extract source from "source: message" or [source] message format
_SOURCE_RE = re.compile(r'^(?P<source>[a-zA-Z][\w.]*?):\s+(?P<rest>.+)')


def _parse_timestamp(ts_str: str) -> Optional[datetime]:
    """Attempt to parse a timestamp string using known formats."""
    ts_str = ts_str.strip()
    for fmt in _TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(ts_str, fmt)
        except ValueError:
            continue
    return None


def parse_line(line: str) -> LogEntry:
    """Parse a single log line into a LogEntry."""
    line = line.strip()
    if not line:
        return LogEntry(raw=line)

    for pattern in _PATTERNS:
        match = pattern.match(line)
        if match:
            groups = match.groupdict()
            entry = LogEntry(raw=line, message=groups.get("message", ""))

            if "level" in groups:
                entry.level = groups["level"].upper()
            if "timestamp" in groups:
                entry.timestamp = _parse_timestamp(groups["timestamp"])
            if "source" in groups:
                entry.source = groups["source"]
            elif "hostname" in groups:
                entry.source = groups["hostname"]

            known = {"level", "timestamp", "source", "hostname", "message", "ip", "method", "path", "status", "size"}
            for key, value in groups.items():
                if key not in known and value is not None:
                    entry.metadata[key] = value

            if not entry.message and "message" not in groups:
                entry.message = line

            # Try to extract source from "source: message" pattern
            if not entry.source and entry.message:
                src_match = _SOURCE_RE.match(entry.message)
                if src_match:
                    entry.source = src_match.group("source")
                    entry.message = src_match.group("rest")

            return entry

    return LogEntry(raw=line, message=line)


def read_file(path: Union[str, Path], encoding: str = "utf-8") -> str:
    """Read the entire contents of a text file."""
    with open(path, "r", encoding=encoding) as f:
        return f.read()


def read_lines(path: Union[str, Path], encoding: str = "utf-8") -> List[str]:
    """Read a text file and return its lines."""
    with open(path, "r", encoding=encoding) as f:
        return [line.rstrip("\n") for line in f]


def read_log_entries(path: Union[str, Path], encoding: str = "utf-8") -> List[LogEntry]:
    """Read a log file and parse each line into a LogEntry."""
    path = Path(path)
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding=encoding) as f:
            lines = [line.rstrip("\n") for line in f]
    else:
        lines = read_lines(path, encoding)
    return [parse_line(line) for line in lines]


def stream_log_entries(path: Union[str, Path], encoding: str = "utf-8") -> Iterator[LogEntry]:
    """Stream log entries from a file one at a time (memory-efficient)."""
    path = Path(path)
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding=encoding) as f:
            for line in f:
                yield parse_line(line.rstrip("\n"))
    else:
        for line in read_lines(path, encoding):
            yield parse_line(line)


def find_log_files(directory: Union[str, Path], pattern: str = "*.log*") -> List[Path]:
    """Find log files in a directory."""
    return sorted(Path(directory).glob(pattern))
