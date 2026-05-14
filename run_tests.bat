@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "PYEXE=python"
if exist "%~dp0venv\Scripts\python.exe" set "PYEXE=%~dp0venv\Scripts\python.exe"

"%PYEXE%" -m pip show pytest >nul 2>&1
if errorlevel 1 "%PYEXE%" -m pip install pytest
"%PYEXE%" -m pip show colorama >nul 2>&1
if errorlevel 1 "%PYEXE%" -m pip install colorama

echo.
echo Running tests from: %CD%
echo Python: %PYEXE%
echo.

"%PYEXE%" -m pytest tests -v --tb=short --color=yes
set "ERR=%ERRORLEVEL%"

echo.
if "%ERR%"=="0" (
  echo All tests passed.
) else (
  echo Some tests failed (exit code %ERR%^).
)
echo.
pause
endlocal & exit /b %ERR%
