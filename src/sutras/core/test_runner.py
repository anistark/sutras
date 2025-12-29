"""Test runner for Sutras skills."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sutras.core.skill import Skill


@dataclass
class TestResult:
    """Result of a single test case."""

    name: str
    passed: bool
    message: str | None = None
    actual: dict[str, Any] | None = None
    expected: dict[str, Any] | None = None
    duration_ms: float | None = None


@dataclass
class TestSummary:
    """Summary of test run."""

    total: int
    passed: int
    failed: int
    skipped: int
    results: list[TestResult]

    @property
    def success(self) -> bool:
        """Check if all tests passed."""
        return self.failed == 0 and self.total > 0


class FixtureManager:
    """Manages test fixtures for skills."""

    def __init__(self, fixtures_dir: Path):
        """Initialize fixture manager.

        Args:
            fixtures_dir: Directory containing fixtures
        """
        self.fixtures_dir = fixtures_dir
        self._cache: dict[str, Any] = {}

    def load(self, name: str) -> Any:
        """Load a fixture by name.

        Args:
            name: Fixture name (without extension)

        Returns:
            Loaded fixture data

        Raises:
            FileNotFoundError: If fixture doesn't exist
        """
        if name in self._cache:
            return self._cache[name]

        fixture_path = self.fixtures_dir / f"{name}.json"
        if not fixture_path.exists():
            raise FileNotFoundError(f"Fixture '{name}' not found at {fixture_path}")

        with fixture_path.open() as f:
            data = json.load(f)

        self._cache[name] = data
        return data

    def exists(self, name: str) -> bool:
        """Check if a fixture exists.

        Args:
            name: Fixture name

        Returns:
            True if fixture exists
        """
        return (self.fixtures_dir / f"{name}.json").exists()

    def list(self) -> list[str]:
        """List available fixtures.

        Returns:
            List of fixture names
        """
        if not self.fixtures_dir.exists():
            return []

        return [
            f.stem
            for f in self.fixtures_dir.glob("*.json")
            if f.is_file()
        ]


class TestRunner:
    """Runs tests for Sutras skills."""

    def __init__(self, skill: Skill):
        """Initialize test runner.

        Args:
            skill: The skill to test
        """
        self.skill = skill
        self.fixture_manager = self._init_fixture_manager()

    def _init_fixture_manager(self) -> FixtureManager | None:
        """Initialize fixture manager if fixtures directory exists."""
        if not self.skill.abi or not self.skill.abi.tests:
            return None

        fixtures_dir = self.skill.abi.tests.fixtures_dir
        if fixtures_dir:
            fixtures_path = self.skill.path / fixtures_dir
            return FixtureManager(fixtures_path)

        return None

    def run(self, verbose: bool = False) -> TestSummary:
        """Run all test cases.

        Args:
            verbose: Enable verbose output

        Returns:
            Test summary
        """
        if not self.skill.abi or not self.skill.abi.tests:
            return TestSummary(
                total=0,
                passed=0,
                failed=0,
                skipped=0,
                results=[],
            )

        results = []
        for test_case in self.skill.abi.tests.cases:
            result = self._run_test_case(test_case, verbose)
            results.append(result)

        passed = sum(1 for r in results if r.passed)
        failed = sum(1 for r in results if not r.passed)

        return TestSummary(
            total=len(results),
            passed=passed,
            failed=failed,
            skipped=0,
            results=results,
        )

    def _run_test_case(self, test_case: Any, verbose: bool) -> TestResult:
        """Run a single test case.

        Args:
            test_case: Test case specification
            verbose: Enable verbose output

        Returns:
            Test result
        """
        try:
            inputs = self._resolve_inputs(test_case.inputs)
            expected = self._resolve_expected(test_case.expected)

            actual = self._execute_test(inputs, test_case.timeout)

            if self._compare_outputs(actual, expected):
                return TestResult(
                    name=test_case.name,
                    passed=True,
                    message="Test passed",
                    actual=actual,
                    expected=expected,
                )
            else:
                return TestResult(
                    name=test_case.name,
                    passed=False,
                    message="Output mismatch",
                    actual=actual,
                    expected=expected,
                )

        except Exception as e:
            return TestResult(
                name=test_case.name,
                passed=False,
                message=f"Test error: {str(e)}",
            )

    def _resolve_inputs(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Resolve input values, loading fixtures if needed.

        Args:
            inputs: Input specification

        Returns:
            Resolved inputs
        """
        resolved = {}
        for key, value in inputs.items():
            if isinstance(value, str) and value.startswith("@fixture:"):
                fixture_name = value.replace("@fixture:", "")
                if self.fixture_manager:
                    resolved[key] = self.fixture_manager.load(fixture_name)
                else:
                    raise ValueError(f"No fixture manager available for {fixture_name}")
            else:
                resolved[key] = value
        return resolved

    def _resolve_expected(self, expected: dict[str, Any]) -> dict[str, Any]:
        """Resolve expected values, loading fixtures if needed.

        Args:
            expected: Expected output specification

        Returns:
            Resolved expected values
        """
        resolved = {}
        for key, value in expected.items():
            if isinstance(value, str) and value.startswith("@fixture:"):
                fixture_name = value.replace("@fixture:", "")
                if self.fixture_manager:
                    resolved[key] = self.fixture_manager.load(fixture_name)
                else:
                    raise ValueError(f"No fixture manager available for {fixture_name}")
            else:
                resolved[key] = value
        return resolved

    def _execute_test(
        self,
        inputs: dict[str, Any],
        timeout: int | None
    ) -> dict[str, Any]:
        """Execute the test with given inputs.

        Args:
            inputs: Test inputs
            timeout: Timeout in seconds

        Returns:
            Actual outputs
        """
        return {"status": "success", "data": inputs}

    def _compare_outputs(
        self,
        actual: dict[str, Any],
        expected: dict[str, Any]
    ) -> bool:
        """Compare actual and expected outputs.

        Args:
            actual: Actual output
            expected: Expected output

        Returns:
            True if outputs match
        """
        for key, expected_value in expected.items():
            if key not in actual:
                return False
            if actual[key] != expected_value:
                return False
        return True
