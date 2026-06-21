"""
Tests for the release smoke-test script (issue #46).

`scripts/release_smoke_test.py` runs against an INSTALLED `bestehorn_llmmanager` (in CI it
runs in a clean env where only the installed wheel/sdist is importable) and verifies the
package imports, exposes its public surface, constructs no-AWS objects, and loads its
bundled catalog data. These tests exercise the script's check functions directly (the test
environment has the package importable via the editable install, which is sufficient to
prove the check logic; the clean-env guard is unit-tested separately with a fake module).
"""

import importlib.util
from pathlib import Path

import pytest

# Load the script as a module by path (it lives in scripts/, not in the package).
_SCRIPT = Path(__file__).parent.parent / "scripts" / "release_smoke_test.py"
_spec = importlib.util.spec_from_file_location("release_smoke_test", _SCRIPT)
assert _spec and _spec.loader
release_smoke_test = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(release_smoke_test)


class TestSmokeChecksPassOnInstalledPackage:
    """The individual smoke checks succeed against the importable package."""

    def test_check_import_and_version(self):
        version = release_smoke_test.check_import_and_version()
        assert isinstance(version, str)
        assert version  # non-empty

    def test_check_import_and_version_matches_expected(self):
        version = release_smoke_test.check_import_and_version()
        # When an expected version is supplied and matches, it must not raise.
        release_smoke_test.check_import_and_version(expected_version=version)

    def test_check_import_and_version_rejects_mismatch(self):
        with pytest.raises(release_smoke_test.SmokeTestError):
            release_smoke_test.check_import_and_version(expected_version="999.999.999")

    def test_check_public_surface(self):
        """Every name in __all__ is importable from the top-level package."""
        imported = release_smoke_test.check_public_surface()
        assert "LLMManager" in imported
        assert "MessageBuilder" in imported
        assert "VideoFormatEnum" in imported

    def test_check_no_aws_construction(self):
        """Constructing message-builder objects / enums / regions needs no AWS or network."""
        release_smoke_test.check_no_aws_construction()  # must not raise

    def test_check_bundled_catalog_loads(self):
        """The bundled catalog JSON loads offline via the public loader."""
        release_smoke_test.check_bundled_catalog_loads()  # must not raise

    def test_run_smoke_checks_all_pass(self, monkeypatch):
        """The aggregate runner returns a passed CheckResult per check.

        The test environment is an editable install, so the clean-env guard would
        (correctly) reject it; we bypass only that guard here and assert the four
        functional checks all pass. The guard itself is covered by TestCleanEnvGuard.
        """
        monkeypatch.setattr(release_smoke_test, "assert_installed_not_editable", lambda: None)
        results = release_smoke_test.run_smoke_checks()
        names = {r.name for r in results}
        assert {"import", "public_surface", "no_aws_construction", "bundled_catalog"} <= names
        assert all(r.passed for r in results)


class TestCleanEnvGuard:
    """The clean-env guard detects an editable / repo-src import."""

    def test_rejects_module_loaded_from_repo_src(self, tmp_path):
        """A module whose __file__ is under a repo `src/` tree must be rejected."""
        fake_src = tmp_path / "src" / "bestehorn_llmmanager" / "__init__.py"
        fake_src.parent.mkdir(parents=True)
        fake_src.write_text("")
        with pytest.raises(release_smoke_test.SmokeTestError):
            release_smoke_test.assert_installed_not_editable(module_file=str(fake_src))

    def test_accepts_module_loaded_from_site_packages(self, tmp_path):
        """A module under a site-packages path is accepted (installed artifact)."""
        sp = tmp_path / "venv" / "lib" / "site-packages" / "bestehorn_llmmanager" / "__init__.py"
        sp.parent.mkdir(parents=True)
        sp.write_text("")
        # Must not raise.
        release_smoke_test.assert_installed_not_editable(module_file=str(sp))


class TestCliEntryPoint:
    """The script's main() returns 0 on success and is invocable."""

    def test_main_returns_zero_on_success(self):
        # --skip-install-check runs the functional checks without the clean-env guard,
        # which is the correct mode for this editable test environment.
        rc = release_smoke_test.main(argv=["--skip-install-check"])
        assert rc == 0

    def test_main_rejects_version_mismatch(self):
        rc = release_smoke_test.main(
            argv=["--skip-install-check", "--expected-version", "999.999.999"]
        )
        assert rc != 0

    def test_main_rejects_editable_install_without_skip(self):
        """Without --skip-install-check, main() fails in this editable env (guard fires)."""
        rc = release_smoke_test.main(argv=[])
        assert rc != 0
