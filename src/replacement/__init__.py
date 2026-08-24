"""Read-only replacement recommendation engine."""

from .loader import load_replacement_data
from .matcher import ReplacementMatcher

__all__ = ["ReplacementMatcher", "load_replacement_data"]

