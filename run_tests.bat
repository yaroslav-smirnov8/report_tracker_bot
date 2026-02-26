@echo off
setlocal
python -m pip show pytest >nul 2>&1
if errorlevel 1 python -m pip install pytest
python -m pytest -q
if errorlevel 1 exit /b 1
echo OK
