@echo off
setlocal
rem ==== path config (config.env) ====
for /f "usebackq tokens=1,* delims==" %%a in ("%~dp0config.env") do set %%a=%%b
cd /d %WORK_DIR%
"%ENVI_IDL%" -quiet -e "!PATH=!PATH+';'+'%SARSCAPE_LIB%\envi_extensions\idl\lib'+';'+'%SARSCAPE_LIB%\envi_extensions\idl\lib\hook'+';'+'%SARSCAPE_LIB%\envi_extensions\envi\sarscape_local_sav' & resolve_routine,'sarscape_batch_init',/COMPILE_FULL_FILE & SARscape_Batch_Init,Temp_Directory='%WORK_DIR%\sar\tmp' & openw,u,'%SAR_MODULES%',/get_lun & o=obj_new('SARscapeBatch',Module='ToolsGeoid') & printf,u,'OBJ:',byte(OBJ_VALID(o)) & a=o.SetParam('input_file_name','%WORK_DIR%\sar\dem\yanjiuqu.dat_envi') & b=o.SetParam('output_file_name','%WORK_DIR%\sar\dem\yanjiuqu_dem') & c=o.SetParam('geoid_operation','SUBTRACT') & printf,u,'OP:',byte(c) & d=o.SetParam('geoid_type','EGM96') & printf,u,'TYPE:',byte(d) & r=o.Execute() & printf,u,'EXECUTE:',byte(r) & free_lun,u & exit" > sarbatch_err25.txt 2>&1
echo EXIT=%ERRORLEVEL% >> sarbatch_err25.txt
