#!/bin/sh
# Runs every web app check with all external APIs mocked. Needs webapp/requirements.txt + httpx.
cd "$(dirname "$0")/.." || exit 1
fail=0
for t in tests/test_*.py; do
  out=$(python "$t" 2>&1)
  echo "$t: $(echo "$out" | grep -c '^PASS') passed"
  echo "$out" | grep -E '^FAIL|Traceback|Error' && fail=1
done
exit $fail
