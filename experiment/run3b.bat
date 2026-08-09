@echo off
setlocal
rem ==== path config (config.env) ====
for /f "usebackq tokens=1,* delims==" %%a in ("%~dp0config.env") do set %%a=%%b
cd /d %WORK_DIR%
"%ENVI_IDL%" -quiet -e ".run %WORK_DIR%\test_sarbatch" > sarbatch_err.txt 2>&1
echo EXIT=%ERRORLEVEL% >> sarbatch_err.txt
