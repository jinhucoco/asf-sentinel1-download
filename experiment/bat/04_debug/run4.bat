@echo off
setlocal
rem ==== path config (config.env) ====
for /f "usebackq tokens=1,* delims==" %%a in ("%~dp0..\..\config.env") do set %%a=%%b
cd /d %WORK_DIR%
"%ENVI_IDL%" -quiet -e ".compile %WORK_DIR%\test_sarbatch & test_sarbatch & exit" > sarbatch_err2.txt 2>&1
echo EXIT=%ERRORLEVEL% >> sarbatch_err2.txt
