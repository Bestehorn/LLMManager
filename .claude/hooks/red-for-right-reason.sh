#!/usr/bin/env bash
# red-for-right-reason.sh — verify a captured "RED" test run failed for the RIGHT
# reason (a genuine assertion / property falsification), not because the test could
# not even load (import/collection/syntax/fixture errors).
#
# Usage:  red-for-right-reason.sh <path-to-evidence/red/<task>.txt>
# Exit 0: red for the right reason (a real assertion failure, no load errors).
# Exit 1: NOT red for the right reason (load error dominates, or no failure/assertion
#         signal present). The caller (conductor / spec-implementer) must fix the test.
#
# This is a helper invoked by the conductor during the IMPLEMENT_LOOP TEST step and by
# the adversarial-verifier's red audit. It reads a file (complete captured output),
# never truncates, and is test-runner aware for pytest/Hypothesis (the project's
# default) with generic fallbacks.

set -u

capture="${1:-}"
if [[ -z "$capture" || ! -f "$capture" ]]; then
  echo "red-for-right-reason: capture file not found: '$capture'" >&2
  exit 1
fi

content="$(cat "$capture")"

# 1. There must be evidence of a FAILED test at all (not an all-green run).
if ! grep -qiE 'failed|FAILED|error|Falsifying example|AssertionError' <<<"$content"; then
  echo "red-for-right-reason: no failure detected — the test did not fail (it must be RED before implementing)." >&2
  exit 1
fi

# 2. Load/collection errors mean the test could not even run → WRONG reason.
#    pytest reports these as collection errors / ERRORS rather than assertion FAILUREs.
wrong_reason_re='ModuleNotFoundError|ImportError|cannot import name|SyntaxError|IndentationError|errors during collection|ERROR collecting|fixture .* not found|NameError|no tests ran'
if grep -qiE "$wrong_reason_re" <<<"$content"; then
  # A load error is present. Only acceptable if there is ALSO a genuine assertion
  # failure AND no pytest collection-error banner (i.e. the import error is incidental
  # output, not the cause). Be strict: if a collection error banner is present, reject.
  if grep -qiE 'errors during collection|ERROR collecting' <<<"$content"; then
    echo "red-for-right-reason: collection/import error dominates — test failed because it could not load, not on an assertion. Make the symbols importable (stub the signature) so the test fails on its assertion instead." >&2
    exit 1
  fi
fi

# 3. There must be a genuine assertion / property-falsification signal.
right_reason_re='AssertionError|assert |Falsifying example|FAILED .*::|hypothesis\.errors|self\.assert'
if grep -qiE "$right_reason_re" <<<"$content"; then
  echo "red-for-right-reason: OK — failure is a genuine assertion/property falsification."
  exit 0
fi

echo "red-for-right-reason: a failure was reported but no assertion/property-falsification signal was found; cannot confirm the test is red for the right reason." >&2
exit 1
