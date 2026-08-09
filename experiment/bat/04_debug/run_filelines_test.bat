@echo off
setlocal
rem ==== path config (config.env) ====
for /f "usebackq tokens=1,* delims==" %%a in ("%~dp0..\..\config.env") do set %%a=%%b
cd /d %WORK_DIR%
"%ENVI_IDL%" -quiet -e "openw,u,'%SAR_MODULES%',/get_lun & d=file_lines('%WORK_DIR%\sar\gacos_dates.txt') & printf,u,'TYPE:',size(d,/type),'N:',n_elements(d) & printf,u,'FIRST:',d[0] & printf,u,'LAST:',d[n_elements(d)-1] & free_lun,u & exit" > sarbatch_fl.txt 2>&1
echo EXIT=%ERRORLEVEL% >> sarbatch_fl.txt
