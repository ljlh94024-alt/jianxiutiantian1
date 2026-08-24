"""Post-execution verification contract and fixed test identifiers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class VerificationResult:
    passed: bool
    tests: tuple[str, ...]
    details: str = ""


class VerificationBackend(Protocol):
    def run_test(self, test_name: str) -> bool: ...


class Verifier:
    def __init__(self, backend: VerificationBackend | None = None):
        self.backend = backend

    def verify(self, tests: tuple[str, ...]) -> VerificationResult:
        if not tests:
            return VerificationResult(False, (), "No verification tests declared")
        if self.backend is None:
            return VerificationResult(False, tests, "Verification backend is not configured")
        outcomes = [self.backend.run_test(test) for test in tests]
        return VerificationResult(all(outcomes), tests, "all tests passed" if all(outcomes) else "verification failed")

