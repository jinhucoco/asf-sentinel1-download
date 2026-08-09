@echo off
setlocal
rem ==== path config (config.env) ====
for /f "usebackq tokens=1,* delims==" %%a in ("%~dp0config.env") do set %%a=%%b
cd /d %WORK_DIR%
"%ENVI_IDL%" -quiet -e "print,'ENVI-IDL-WORKS' & exit" > envi_idl_out.txt 2>&1
echo EXITCODE=%ERRORLEVEL% >> envi_idl_out.txt
