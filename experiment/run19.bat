@echo off
setlocal
rem ==== path config (config.env) ====
for /f "usebackq tokens=1,* delims==" %%a in ("%~dp0config.env") do set %%a=%%b
cd /d %WORK_DIR%
"%ENVI_IDL%" -quiet -e "!PATH=!PATH+';'+'%SARSCAPE_LIB%\envi_extensions\idl\lib'+';'+'%SARSCAPE_LIB%\envi_extensions\idl\lib\hook'+';'+'%SARSCAPE_LIB%\envi_extensions\envi\sarscape_local_sav' & resolve_routine,'sarscape_batch_init',/COMPILE_FULL_FILE & SARscape_Batch_Init,Temp_Directory='%WORK_DIR%\sar_tmp' & openw,u,'%SAR_MODULES%',/get_lun & printf,u,'OPEN-OK' & o=obj_new('SARscapeBatch',Module='ToolsDemExtractionSrtm1') & printf,u,'OBJ:',byte(OBJ_VALID(o)) & ok=o.SetParam('output_file_dem_val','%WORK_DIR%\sar_out\gulang_dem') & printf,u,'SETPARAM-OUT:',byte(ok) & ok2=o.SetParam('east_start_val',102.0) & printf,u,'SETPARAM-E:',byte(ok2) & ok3=o.SetParam('east_end_val',104.0) & ok4=o.SetParam('north_start_val',39.0) & ok5=o.SetParam('north_end_val',37.0) & printf,u,'PARAMS-SET' & r=o.Execute() & printf,u,'EXECUTE:',byte(r) & free_lun,u & exit" > sarbatch_err17.txt 2>&1
echo EXIT=%ERRORLEVEL% >> sarbatch_err17.txt
