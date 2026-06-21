#!/usr/bin/env python3
"""Release smoke test for the bestehorn-llmmanager built artifact (issue #46).

This script verifies that an **installed** ``bestehorn_llmmanager`` (a wheel or sdist
installed into a clean environment — NOT the editable source tree) is healthy:

1. the package imports and exposes a non-empty ``__version__`` (optionally matching an
   expected release version);
2. every name in ``__all__`` is importable from the top-level package;
3. core objects construct with no AWS credentials or network access; and
4. the bundled catalog JSON ships and loads offline through the public loader.

It is run by ``.github/workflows/release.yml`` (gating the prod-PyPI publish) and by the
``ci.yml`` build job (catching packaging regressions on PRs). Run it from a directory that
is NOT the repo root, against a venv where the built artifact is installed::

    python release_smoke_test.py --expected-version 0.8.5

Exit code 0 = all checks passed; non-zero = a check failed (the failure is printed).
"""

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional


class SmokeTestError(Exception):
    """Raised when a release smoke-test check fails."""


@dataclass(frozen=True)
class CheckResult:
    """Outcome of a single smoke check."""

    name: str
    passed: bool
    detail: str = ""


def assert_installed_not_editable(module_file: Optional[str] = None) -> None:
    """Verify the imported package is a real install, not the repo ``src/`` tree.

    The whole point of a release smoke test is to exercise the *installed artifact*. An
    editable install (or running with the repo ``src/`` on ``sys.path``) would silently
    test the source tree instead, defeating the smoke test. We reject any import whose
    file lives under a ``src/`` directory or an ``__editable__``/``.pth`` shim.

    Args:
        module_file: Path to the imported package's ``__init__.py``. Defaults to the
            installed ``bestehorn_llmmanager.__file__``.

    Raises:
        SmokeTestError: If the package appears to be imported from a repo source tree
            or an editable install rather than an installed artifact.
    """
    if module_file is None:
        import bestehorn_llmmanager

        module_file = bestehorn_llmmanager.__file__ or ""

    resolved = Path(module_file).resolve()
    parts = {p.lower() for p in resolved.parts}

    if "src" in parts:
        raise SmokeTestError(
            f"Package imported from a 'src/' tree ({resolved}); the smoke test must run "
            f"against an INSTALLED artifact, not the editable source tree."
        )
    if "__editable__" in resolved.name or "__editable__" in str(resolved):
        raise SmokeTestError(f"Package appears to be an editable install ({resolved}).")
    if "site-packages" not in parts and "dist-packages" not in parts:
        # Not fatal on every layout, but in CI the install goes to site-packages; warn loudly.
        print(
            f"WARNING: imported package path is not under site-packages ({resolved}). "
            f"Ensure this runs against an installed artifact in a clean environment.",
            file=sys.stderr,
        )


def check_import_and_version(expected_version: Optional[str] = None) -> str:
    """Import the package and validate ``__version__``.

    Args:
        expected_version: If provided, the package ``__version__`` must equal it.

    Returns:
        The imported ``__version__`` string.

    Raises:
        SmokeTestError: If the import fails, the version is empty, or it does not match
            ``expected_version``.
    """
    try:
        import bestehorn_llmmanager
    except Exception as exc:  # noqa: BLE001 - surface any import failure as a smoke failure
        raise SmokeTestError(f"`import bestehorn_llmmanager` failed: {exc}") from exc

    version = getattr(bestehorn_llmmanager, "__version__", "")
    if not isinstance(version, str) or not version:
        raise SmokeTestError(f"__version__ is empty or not a string: {version!r}")

    if expected_version is not None and version != expected_version:
        raise SmokeTestError(
            f"__version__ {version!r} does not match expected release version {expected_version!r}"
        )
    return version


def check_public_surface() -> List[str]:
    """Import every name declared in the package's ``__all__``.

    Returns:
        The list of successfully imported public names.

    Raises:
        SmokeTestError: If ``__all__`` is missing/empty or any name is not importable.
    """
    import bestehorn_llmmanager

    public_names = getattr(bestehorn_llmmanager, "__all__", None)
    if not public_names:
        raise SmokeTestError("Package __all__ is missing or empty.")

    missing = [name for name in public_names if not hasattr(bestehorn_llmmanager, name)]
    if missing:
        raise SmokeTestError(f"Names in __all__ not importable from the package: {missing}")
    return list(public_names)


def check_no_aws_construction() -> None:
    """Construct core objects that must work with no AWS credentials or network.

    Raises:
        SmokeTestError: If any no-AWS construction path fails.
    """
    try:
        from bestehorn_llmmanager import (
            RolesEnum,
            create_user_message,
            get_all_regions,
        )

        # MessageBuilder fluent build (pure, no AWS).
        message = create_user_message().add_text("smoke test").build()
        if not message:
            raise SmokeTestError("create_user_message().add_text(...).build() returned falsy.")

        # Enum access.
        _ = RolesEnum.USER

        # Region utility (static data, no network).
        regions = get_all_regions()
        if not regions:
            raise SmokeTestError("get_all_regions() returned no regions.")
    except SmokeTestError:
        raise
    except Exception as exc:  # noqa: BLE001 - any failure here is a smoke failure
        raise SmokeTestError(f"No-AWS construction failed: {exc}") from exc


def check_bundled_catalog_loads() -> None:
    """Load the bundled catalog JSON offline via the public loader.

    A packaging gap that dropped ``bedrock/package_data/bedrock_catalog_bundled.json``
    would install cleanly but fail here — exactly the class of defect this smoke test
    exists to catch.

    Raises:
        SmokeTestError: If the bundled catalog cannot be located or loaded.
    """
    try:
        from bestehorn_llmmanager.bedrock.catalog.bundled_loader import BundledDataLoader

        catalog = BundledDataLoader.load_bundled_catalog()
        if catalog is None:
            raise SmokeTestError("BundledDataLoader.load_bundled_catalog() returned None.")
    except SmokeTestError:
        raise
    except Exception as exc:  # noqa: BLE001 - any failure here is a smoke failure
        raise SmokeTestError(
            f"Bundled catalog failed to load from the installed package: {exc}"
        ) from exc


def run_smoke_checks(expected_version: Optional[str] = None) -> List[CheckResult]:
    """Run all smoke checks in order, returning one CheckResult per check.

    The first failing check raises ``SmokeTestError`` (fail fast), so a returned list
    means every check passed.

    Args:
        expected_version: Optional release version the package must report.

    Returns:
        A list of passed :class:`CheckResult` (one per check).

    Raises:
        SmokeTestError: On the first failing check.
    """
    assert_installed_not_editable()

    checks: List[tuple[str, Callable[[], object]]] = [
        ("import", lambda: check_import_and_version(expected_version=expected_version)),
        ("public_surface", check_public_surface),
        ("no_aws_construction", check_no_aws_construction),
        ("bundled_catalog", check_bundled_catalog_loads),
    ]

    results: List[CheckResult] = []
    for name, fn in checks:
        fn()
        results.append(CheckResult(name=name, passed=True))
        print(f"  [PASS] {name}")
    return results


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point. Returns 0 if all checks pass, 1 otherwise."""
    parser = argparse.ArgumentParser(description="Release smoke test for bestehorn-llmmanager.")
    parser.add_argument(
        "--expected-version",
        default=None,
        help="Release version the installed package must report (e.g. 0.8.5).",
    )
    parser.add_argument(
        "--skip-install-check",
        action="store_true",
        help="Skip the installed-not-editable guard (for local invocation from a venv).",
    )
    args = parser.parse_args(argv)

    print("Running release smoke test for bestehorn_llmmanager...")
    try:
        if args.skip_install_check:
            # Run the checks without the clean-env guard (local convenience only).
            check_import_and_version(expected_version=args.expected_version)
            print("  [PASS] import")
            check_public_surface()
            print("  [PASS] public_surface")
            check_no_aws_construction()
            print("  [PASS] no_aws_construction")
            check_bundled_catalog_loads()
            print("  [PASS] bundled_catalog")
        else:
            run_smoke_checks(expected_version=args.expected_version)
    except SmokeTestError as exc:
        print(f"\nSMOKE TEST FAILED: {exc}", file=sys.stderr)
        return 1

    print("\nSMOKE TEST PASSED: installed artifact is importable and healthy.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
