@echo off
REM GitHub Trends Watch - local launcher
REM Launches the GUI. If the exe exists in dist\, use that.
REM Otherwise falls back to Python source.

set "APP_DIR=%~dp0"

if exist "%APP_DIR%dist\GitHubTrendsWatch.exe" (
    start "" "%APP_DIR%dist\GitHubTrendsWatch.exe"
    goto :eof
)

if exist "%APP_DIR%dist\GitHubTrendsWatch" (
    start "" "%APP_DIR%dist\GitHubTrendsWatch"
    goto :eof
)

REM Fall back to Python source
python "%APP_DIR%main.py" --gui
