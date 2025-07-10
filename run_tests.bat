@echo off
REM Batch script for running tests on Windows
REM This provides the same functionality as run_tests.py but for Windows users

setlocal enabledelayedexpansion

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    exit /b 1
)

REM Default to running all tests with coverage
set "PYTEST_ARGS=test/ --cov=src --cov-report=term-missing --cov-report=json:coverage.json"

REM Parse command line arguments
:parse_args
if "%~1"=="" goto run_tests
if "%~1"=="--unit" set "PYTEST_ARGS=-m unit test/ --cov=src --cov-report=term-missing --cov-report=json:coverage.json"
if "%~1"=="--integration" set "PYTEST_ARGS=-m integration test/ --cov=src --cov-report=term-missing --cov-report=json:coverage.json"
if "%~1"=="--fast" set "PYTEST_ARGS=-m 'not slow' test/ --cov=src --cov-report=term-missing --cov-report=json:coverage.json"
if "%~1"=="--no-coverage" set "PYTEST_ARGS=test/"
if "%~1"=="--html" set "PYTEST_ARGS=test/ --cov=src --cov-report=html:htmlcov --html=test_results.html --self-contained-html --cov-report=term-missing --cov-report=json:coverage.json"
if "%~1"=="--parallel" set "PYTEST_ARGS=%PYTEST_ARGS% -n auto"
if "%~1"=="--verbose" set "PYTEST_ARGS=%PYTEST_ARGS% -v"
if "%~1"=="--install-deps" (
    echo Installing test dependencies...
    python -m pip install -r requirements-test.txt
    if %errorlevel% neq 0 (
        echo ERROR: Failed to install dependencies
        exit /b 1
    )
)
if "%~1"=="--help" (
    echo Usage: run_tests.bat [options]
    echo.
    echo Options:
    echo   --unit           Run only unit tests
    echo   --integration    Run only integration tests
    echo   --fast           Skip slow tests
    echo   --no-coverage    Run without coverage
    echo   --html           Generate HTML reports
    echo   --parallel       Run tests in parallel
    echo   --verbose        Verbose output
    echo   --install-deps   Install dependencies first
    echo   --help           Show this help
    echo.
    exit /b 0
)
shift
goto parse_args

:run_tests
echo Running tests with pytest...
echo Command: python -m pytest %PYTEST_ARGS%
echo.

python -m pytest %PYTEST_ARGS%
set "TEST_RESULT=%errorlevel%"

if %TEST_RESULT% equ 0 (
    echo.
    echo ✅ All tests completed successfully!
) else (
    echo.
    echo ❌ Tests failed!
)

exit /b %TEST_RESULT%
