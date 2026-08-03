@echo off
setlocal

REM Downloads the latest version of the app from GitHub (no git required)
REM and rebuilds the Docker containers.
REM
REM .streamlit/secrets.toml and src/quick_wins/config/crowdstrike_config.json
REM are gitignored, so they are never part of the GitHub download and are
REM left completely untouched by this update.

set REPO_ZIP_URL=https://github.com/MaxRijnberg/lbh-quick-wins/archive/refs/heads/main.zip
set TEMP_ZIP=%TEMP%\lbh-quick-wins-update.zip
set TEMP_DIR=%TEMP%\lbh-quick-wins-update
set APP_DIR=%~dp0
if "%APP_DIR:~-1%"=="\" set APP_DIR=%APP_DIR:~0,-1%

echo Downloading latest version from GitHub...
powershell -NoProfile -Command "try { Invoke-WebRequest -Uri '%REPO_ZIP_URL%' -OutFile '%TEMP_ZIP%' -UseBasicParsing } catch { exit 1 }"
if errorlevel 1 (
    echo Failed to download update. Check your internet connection.
    pause
    exit /b 1
)

if exist "%TEMP_DIR%" rmdir /s /q "%TEMP_DIR%"

echo Extracting update...
powershell -NoProfile -Command "Expand-Archive -Path '%TEMP_ZIP%' -DestinationPath '%TEMP_DIR%' -Force"
if errorlevel 1 (
    echo Failed to extract update.
    pause
    exit /b 1
)

REM The zip extracts into a single subfolder, e.g. lbh-quick-wins-main
set EXTRACTED=
for /d %%d in ("%TEMP_DIR%\*") do set EXTRACTED=%%d

if "%EXTRACTED%"=="" (
    echo Could not find extracted files.
    pause
    exit /b 1
)

echo Applying update...
REM /XF update.bat: never overwrite the script that is currently running,
REM to avoid corrupting it mid-execution.
robocopy "%EXTRACTED%" "%APP_DIR%" /E /XF update.bat secrets.toml crowdstrike_config.json /NFL /NDL /NJH /NJS
if %errorlevel% GEQ 8 (
    echo Failed to copy update files.
    pause
    exit /b 1
)

del /q "%TEMP_ZIP%" >nul 2>&1
rmdir /s /q "%TEMP_DIR%" >nul 2>&1

echo Rebuilding and restarting the app...
docker compose up --build --force-recreate

start "" "http://localhost:8501"

endlocal
