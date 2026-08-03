@echo off
setlocal

REM Pulls the latest code from GitHub and rebuilds the Docker containers.

echo Fetching latest changes from GitHub...
git fetch origin
if errorlevel 1 (
    echo Failed to fetch from GitHub. Check your internet connection.
    pause
    exit /b 1
)

for /f "delims=" %%b in ('git rev-parse --abbrev-ref HEAD') do set BRANCH=%%b

git reset --hard origin/%BRANCH%
if errorlevel 1 (
    echo Failed to update to the latest version.
    pause
    exit /b 1
)

echo Rebuilding and restarting the app...
docker compose up --build --force-recreate

start "" "http://localhost:8501"

endlocal
