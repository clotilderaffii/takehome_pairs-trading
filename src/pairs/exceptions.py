"""Custom exception classes for expected failure states (e.g. DataFetchError)."""

from __future__ import annotations


class PairsError(Exception):
    """Base class for all expected errors raised by the pairs package."""


class DataFetchError(PairsError):
    """Raised when input data is missing, unreadable or does not have the expected shape."""


class InsufficientDataError(PairsError):
    """Raised when there is not enough data before a cutoff to estimate or evaluate something."""
