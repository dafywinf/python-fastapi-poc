# Python Development Standards

## Style & Formatting

- Formatter/Linter: Ruff (88 chars).
- Naming: Snake_case for functions, PascalCase for classes.
- Documentation: Google-style docstrings.

## Type Hinting (Mandatory)

- No `Any`. Use explicit types for all parameters and return values.
- Use Pydantic v2 for all data validation and configuration.

## Testing (Pytest + Allure)

- All tests must be decorated with `@allure.feature` and `@allure.story`.
- Use `allure.step` for complex test steps.
- Run command: `pytest --alluredir=allure-results`.
- Coverage: Use `pytest-cov`, minimum 80% coverage required for new features.

## Tooling

- Dependency management: `venv` + `pip`. (See project CLAUDE.md for the venv location.)
- Static Analysis: Run `basedpyright backend/` before finalizing any PR.

## Virtual Environment Execution

- **Do not use `source .venv/bin/activate`** — Claude Code runs each shell command in a fresh shell, so activation does not persist between tool calls.
- **Always use the absolute path** to the venv binary instead:
  ```bash
  ./engines/python-advisor/.venv/bin/python -m pytest tests/
  ./engines/python-advisor/.venv/bin/pip install -r requirements.txt
  ```
- This ensures the correct interpreter and packages are used regardless of shell state.
