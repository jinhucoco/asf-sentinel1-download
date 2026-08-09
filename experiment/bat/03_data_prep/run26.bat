@echo off
setlocal
rem ==== path config (config.env) ====
for /f "usebackq tokens=1,* delims==" %%a in ("%~dp0..\..\config.env") do set %%a=%%b
cd /d %WORK_DIR%
"%ENVI_IDL%" -quiet -e "!PATH=!PATH+';'+'%SARSCAPE_LIB%\envi_extensions\idl\lib'+';'+'%SARSCAPE_LIB%\envi_extensions\idl\lib\hook'+';'+'%SARSCAPE_LIB%\envi_extensions\envi\sarscape_local_sav' & resolve_routine,'sarscape_batch_init',/COMPILE_FULL_FILE & SARscape_Batch_Init,Temp_Directory='%WORK_DIR%\sar\tmp' & openw,u,'%SAR_MODULES%',/get_lun & o=obj_new('SARscapeBatch',Module='ToolsGeoid') & v1=o.SetParam('geoid_operation','SUBTRACT') & printf,u,'SUBTRACT:',byte(v1) & v2=o.SetParam('geoid_operation','subtract') & printf,u,'subtract:',byte(v2) & v3=o.SetParam('geoid_operation','SubtractGeoid') & printf,u,'SubtractGeoid:',byte(v3) & v4=o.SetParam('geoid_operation','0') & printf,u,'0:',byte(v4) & v5=o.SetParam('geoid_operation','Subtract') & printf,u,'Subtract:',byte(v5) & free_lun,u & exit" > sarbatch_err24.txt 2>&1
echo EXIT=%ERRORLEVEL% >> sarbatch_err24.txt
