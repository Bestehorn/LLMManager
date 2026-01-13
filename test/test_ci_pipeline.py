"""
Integration test for CI pipeline health.

This test verifies that all CI checks pass locally before release.
"""

import subprocess
from pathlib import Path
from typing import List, Tuple

import pytest


class TestCIPipeline:
    """Test suite for CI pipeline health checks."""

    @pytest.fixture(scope="class")
    def project_root(self) -> Path:
        """Get the project root directory."""
        return Path(__file__).parent.parent

    def _run_command(self, command: str, cwd: Path) -> Tuple[int, str, str]:
        """
        Run a shell command and return the result.

        Args:
            command: Command to execute
            cwd: Working directory

        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
        )
        return result.returncode, result.stdout, result.stderr

    def test_black_formatting(self, project_root: Path) -> None:
        """
        Test that black formatting check passes.

        Validates: Requirements 5.1, 5.4
        """
        command = (
            "venv\\Scripts\\activate & black src/ test/ --check "
            '--extend-exclude="src/bestehorn_llmmanager/_version.py"'
        )
        returncode, stdout, stderr = self._run_command(command=command, cwd=project_root)

        assert returncode == 0, (
            f"Black formatting check failed.\n"
            f"stdout: {stdout}\n"
            f"stderr: {stderr}\n"
            f"Run: black src/ test/ --extend-exclude='src/bestehorn_llmmanager/_version.py'"
        )

    def test_isort_imports(self, project_root: Path) -> None:
        """
        Test that isort import sorting check passes.

        Validates: Requirements 5.1, 5.4
        """
        command = (
            "venv\\Scripts\\activate & isort src/ test/ --check-only "
            '--skip="src/bestehorn_llmmanager/_version.py"'
        )
        returncode, stdout, stderr = self._run_command(command=command, cwd=project_root)

        assert returncode == 0, (
            f"isort import sorting check failed.\n"
            f"stdout: {stdout}\n"
            f"stderr: {stderr}\n"
            f"Run: isort src/ test/ --skip='src/bestehorn_llmmanager/_version.py'"
        )

    def test_flake8_linting(self, project_root: Path) -> None:
        """
        Test that flake8 linting check passes.

        Validates: Requirements 5.1, 5.4
        """
        command = (
            "venv\\Scripts\\activate & flake8 src/ test/ "
            '--exclude="src/bestehorn_llmmanager/_version.py"'
        )
        returncode, stdout, stderr = self._run_command(command=command, cwd=project_root)

        assert returncode == 0, (
            f"flake8 linting check failed.\n"
            f"stdout: {stdout}\n"
            f"stderr: {stderr}\n"
            f"Run: flake8 src/ test/ --exclude='src/bestehorn_llmmanager/_version.py'"
        )

    def test_mypy_type_checking(self, project_root: Path) -> None:
        """
        Test that mypy type checking passes.

        Validates: Requirements 5.1, 5.4
        """
        command = 'venv\\Scripts\\activate & mypy --exclude="_version" src/'
        returncode, stdout, stderr = self._run_command(command=command, cwd=project_root)

        assert returncode == 0, (
            f"mypy type checking failed.\n"
            f"stdout: {stdout}\n"
            f"stderr: {stderr}\n"
            f"Run: mypy --exclude='_version' src/"
        )

    def test_bandit_security_scan(self, project_root: Path) -> None:
        """
        Test that bandit security scanning passes.

        Validates: Requirements 5.1, 5.4
        """
        command = (
            "venv\\Scripts\\activate & bandit -r src/ " '-x "src/bestehorn_llmmanager/_version.py"'
        )
        returncode, stdout, stderr = self._run_command(command=command, cwd=project_root)

        assert returncode == 0, (
            f"bandit security scan failed.\n"
            f"stdout: {stdout}\n"
            f"stderr: {stderr}\n"
            f"Run: bandit -r src/ -x 'src/bestehorn_llmmanager/_version.py'"
        )

    def test_pytest_suite(self, project_root: Path) -> None:
        """
        Test that pytest test suite passes.

        Validates: Requirements 5.1, 5.2, 5.5
        """
        command = "venv\\Scripts\\activate & pytest test/ -v"
        returncode, stdout, stderr = self._run_command(command=command, cwd=project_root)

        assert returncode == 0, (
            f"pytest test suite failed.\n"
            f"stdout: {stdout}\n"
            f"stderr: {stderr}\n"
            f"Run: pytest test/ -v"
        )

    def test_all_ci_checks_pass(self, project_root: Path) -> None:
        """
        Comprehensive test that all CI checks pass together.

        This test runs all CI checks in sequence and reports any failures.

        Validates: Requirements 5.1, 5.2, 5.4, 5.5
        """
        checks: List[Tuple[str, str]] = [
            (
                "black",
                "venv\\Scripts\\activate & black src/ test/ --check "
                '--extend-exclude="src/bestehorn_llmmanager/_version.py"',
            ),
            (
                "isort",
                "venv\\Scripts\\activate & isort src/ test/ --check-only "
                '--skip="src/bestehorn_llmmanager/_version.py"',
            ),
            (
                "flake8",
                "venv\\Scripts\\activate & flake8 src/ test/ "
                '--exclude="src/bestehorn_llmmanager/_version.py"',
            ),
            ("mypy", 'venv\\Scripts\\activate & mypy --exclude="_version" src/'),
            (
                "bandit",
                "venv\\Scripts\\activate & bandit -r src/ "
                '-x "src/bestehorn_llmmanager/_version.py"',
            ),
            ("pytest", "venv\\Scripts\\activate & pytest test/ -v"),
        ]

        failures: List[str] = []

        for name, command in checks:
            returncode, stdout, stderr = self._run_command(command=command, cwd=project_root)
            if returncode != 0:
                failures.append(
                    f"{name} check failed (exit code {returncode}):\n"
                    f"  stdout: {stdout[:200]}\n"
                    f"  stderr: {stderr[:200]}"
                )

        assert (
            len(failures) == 0
        ), f"CI pipeline has {len(failures)} failing check(s):\n" + "\n".join(failures)
