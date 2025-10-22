# Python Environment Rules
- ALWAYS activate the virtual environment before running any Python or pip commands or any other command-line actions
- Virtual environment location: venv/
- Activation command (Windows cmd): venv\Scripts\activate
- Activation command (PowerShell): venv\Scripts\Activate.ps1
- For any pip or python commands, prepend with venv activation using && syntax
- Example: venv\Scripts\activate && pip install package-name