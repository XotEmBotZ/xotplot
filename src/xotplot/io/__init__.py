"""Data ingestion and coordinate normalization for xotplot."""

from xotplot.io.canonical import canonicalize_coordinates
from xotplot.io.detector import detect_file_format

__all__ = [
    "canonicalize_coordinates",
    "detect_file_format",
]
