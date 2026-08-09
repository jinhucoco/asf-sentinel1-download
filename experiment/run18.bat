@echo off
setlocal
rem ==== path config (config.env) ====
for /f "usebackq tokens=1,* delims==" %%a in ("%~dp0config.env") do set %%a=%%b
cd /d %WORK_DIR%
"%ENVI_IDL%" -quiet -e "!PATH=!PATH+';'+'%SARSCAPE_LIB%\envi_extensions\idl\lib'+';'+'%SARSCAPE_LIB%\envi_extensions\idl\lib\hook'+';'+'%SARSCAPE_LIB%\envi_extensions\envi\sarscape_local_sav' & resolve_routine,'sarscape_batch_init',/COMPILE_FULL_FILE & SARscape_Batch_Init,Temp_Directory='%WORK_DIR%\sar_tmp' & openw,u,'%SAR_MODULES%',/get_lun & printf,u,'OPEN-OK' & o=obj_new('SARscapeBatch',Module='ToolsDemExtractionSrtm1') & printf,u,'OBJ:',byte(OBJ_VALID(o)) & lp=o.ListParams() & printf,u,'PARAMS-N:',n_elements(lp) & if n_elements(lp) gt 0 then printf,u,strjoin(lp,'|') & free_lun,u & exit" > sarbatch_err16.txt 2>&1
echo EXIT=%ERRORLEVEL% >> sarbatch_err16.txt
