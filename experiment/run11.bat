@echo off
setlocal
rem ==== path config (config.env) ====
for /f "usebackq tokens=1,* delims==" %%a in ("%~dp0config.env") do set %%a=%%b
cd /d %WORK_DIR%
"%ENVI_IDL%" -quiet -e "!PATH=!PATH+';'+'%SARSCAPE_LIB%\envi_extensions\idl\lib'+';'+'%SARSCAPE_LIB%\envi_extensions\idl\lib\hook'+';'+'%SARSCAPE_LIB%\envi_extensions\envi\sarscape_local_sav' & resolve_routine,'sarscape_batch_init',/COMPILE_FULL_FILE & SARscape_Batch_Init,Temp_Directory='%WORK_DIR%\sar_tmp' & openw,u,'%SAR_MODULES%',/get_lun & o1=obj_new('SARscapeBatch',Module='SARsFocusingSentinel1') & printf,u,'FocusingSentinel1 valid=',byte(OBJ_VALID(o1)) & o2=obj_new('SARscapeBatch',Module='SARsInSARInterferogramGeneration') & printf,u,'Interferogram valid=',byte(OBJ_VALID(o2)) & o3=obj_new('SARscapeBatch',Module='SARsInSARStackESBASInversion') & printf,u,'ESBASInversion valid=',byte(OBJ_VALID(o3)) & if OBJ_VALID(o2) then begin & lp=o2.ListParams() & printf,u,'PARAMS:',n_elements(lp) & if n_elements(lp) gt 0 then printf,u,strjoin(lp,'|') & endif & free_lun,u & exit" > sarbatch_err9.txt 2>&1
echo EXIT=%ERRORLEVEL% >> sarbatch_err9.txt
