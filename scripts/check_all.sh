#!/usr/bin/env bash
# Runs the checks of .github/workflows/checks.yml locally, with the same commands in the same
# order; the container test runs only with --all, which also measures the presentation.
set -uo pipefail
cd "$(dirname "$0")/.."

run_all=0
[[ "${1:-}" == "--all" ]] && run_all=1

failures=0
step() {
  local name="$1"; shift
  printf '\n\033[1m── %s\033[0m\n' "$name"
  if "$@"; then
    printf '   \033[32mpassed\033[0m\n'
  else
    printf '   \033[31mfailed\033[0m\n'
    failures=$((failures + 1))
  fi
}

step "ruff — lint"                          python3 -m ruff check .
step "ruff — format check"                  python3 -m ruff format --check .
step "mypy — type check"                    python3 -m mypy src
step "bandit — security scan"               python3 -m bandit -c pyproject.toml -r src scripts packaging -q
step "pip-audit — known vulnerabilities"    python3 -m pip_audit --disable-pip --no-deps --requirement constraints.txt
step "pytest — tests without models"        python3 -m pytest -m "not slow and not network and not container" -q
step "Parity of Python and browser walkthrough" python3 scripts/check_parity.py --runs 400
step "Rule set and legal bases"             python3 scripts/check_rule_set.py
step "Web page catalogs"                    python3 scripts/check_web_locales.py
step "Every catalog key is read somewhere"  python3 scripts/find_unused_catalog_keys.py

if [[ $run_all -eq 1 ]]; then
  step "pytest — container without network" python3 -m pytest -m container -q
  step "Presentation — does everything fit?" python3 scripts/build_presentation.py --measure
fi

printf '\n'
if [[ $failures -eq 0 ]]; then
  printf '\033[32mAll checks passed.\033[0m\n'
else
  printf '\033[31m%d checks failed.\033[0m\n' "$failures"
fi
exit $failures
