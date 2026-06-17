# Technology Stack

Ported from `.kiro/steering/tech-stack.md` (Kiro `inclusion: always`).

## Core Technologies
- Python 3.10+ with type hints and dataclasses
- AWS Bedrock for LLM interactions
- boto3 for AWS SDK
- pytest + hypothesis for testing

## Code Quality Tools
- black (100 char line length — project-specific)
- isort (black profile)
- flake8 (E203, W503 ignored)
- mypy (strict type checking)
- bandit (security scanning)

> NOTE: this project intentionally uses the **black/isort/flake8** toolchain, not ruff.
> Line length is **100** (not the 120 default). These are preserved per the migration's
> merge rule — do not "upgrade" them to ruff/120.

## Preferred Libraries
- dataclasses for models (not pydantic unless needed)
- logging (not print)
- pathlib (not os.path)
- typing for all type hints

## Virtual Environment
All commands must execute inside the activated venv. No execution without an activated
venv.

**CRITICAL — Windows Environment:**
- Virtual environment location: `venv/`
- Activation command (Windows cmd): `venv\Scripts\activate`
- Activation command (PowerShell): `venv\Scripts\Activate.ps1`
- For any pip or python commands, prepend with venv activation using `&` syntax
- Example: `venv\Scripts\activate & pip install package-name`

## Project-Specific Configuration
- Line length: 100 characters (not 120)
- Package name: `bestehorn-llmmanager`
- Source directory: `src/bestehorn_llmmanager/`
- Auto-generated version file: `src/bestehorn_llmmanager/_version.py` (ALWAYS exclude
  from checks)
