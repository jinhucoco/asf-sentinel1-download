@echo off
setlocal
rem ==== path config (config.env) ====
for /f "usebackq tokens=1,* delims==" %%a in ("%~dp0config.env") do set %%a=%%b
cd /d %WORK_DIR%
"%ENVI_IDL%" -quiet -e "openw,u,'%WORK_DIR%\envi_idl_test.txt',/get_lun & printf,u,'ENVI-IDL-WRITE-OK' & free_lun,u & exit" 2>nul
