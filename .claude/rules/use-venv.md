# Always Work Inside the Virtual Environment

ALWAYS run Python, pip, pytest, and the quality tools (ruff, mypy) inside the project
venv at `venv/`. No execution outside an activated venv.

- Windows cmd: `venv\Scripts\activate`
- PowerShell: `venv\Scripts\Activate.ps1`
- Prepend activation to commands with `&`: `venv\Scripts\activate & pytest test/`
- In a bash shell on Windows: `source venv/Scripts/activate`

If `venv/` is missing or broken, recreate it before doing anything else:
```bash
python -m venv venv
venv\Scripts\activate & pip install -e ".[dev]"
```
Never `pip install` into the global interpreter. Migrated from `.clinerules/venv-only.md`
and `.amazonq/rules/use-venv.md`; see also `.claude/rules/tech-stack.md`.
