@echo off
setlocal
rem ==== path config (config.env) ====
for /f "usebackq tokens=1,* delims==" %%a in ("%~dp0..\..\config.env") do set %%a=%%b
cd /d %WORK_DIR%
"%IDL_EXE%" -quiet -e "print,'IDL-FROM-BAT' & exit" > idl_bat_out.txt 2>&1
echo EXITCODE=%ERRORLEVEL% >> idl_bat_out.txt
