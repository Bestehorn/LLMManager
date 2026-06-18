# Technology Stack

Ported from `.kiro/steering/tech-stack.md` (Kiro `inclusion: always`).

## Core Technologies
- Python 3.10+ with type hints and dataclasses
- AWS Bedrock for LLM interactions
- boto3 for AWS SDK
- pytest + hypothesis for testing

## Code Quality Tools
- ruff format (100 char line length — project-specific)
- ruff check (lint: E/F/W + isort I + bandit S + bugbear B)
- mypy (strict type checking)

> NOTE: this project uses the **ruff** toolchain (`ruff format` + `ruff check`) at
> line-length **100** (not the 120 default), plus mypy and pytest. Keep the line length
> at 100 — do not "upgrade" it to 120.

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
