@echo off
setlocal
rem ==== path config (config.env) ====
for /f "usebackq tokens=1,* delims==" %%a in ("%~dp0..\..\config.env") do set %%a=%%b
cd /d %WORK_DIR%
"%ENVI_IDL%" -quiet -e "!PATH=!PATH+';'+'%SARSCAPE_LIB%\envi_extensions\idl\lib'+';'+'%SARSCAPE_LIB%\envi_extensions\idl\lib\hook'+';'+'%SARSCAPE_LIB%\envi_extensions\envi\sarscape_local_sav' & resolve_routine,'sarscape_batch_init',/COMPILE_FULL_FILE & SARscape_Batch_Init,Temp_Directory='%WORK_DIR%\sar\tmp' & openw,u,'%SAR_MODULES%',/get_lun & mlist=['ImportGacos','SARsImportGacos','Import','InSARAtmosphericCorrection'] & for i=0,n_elements(mlist)-1 do begin & o=obj_new('SARscapeBatch',Module=mlist[i]) & printf,u,mlist[i],':',byte(OBJ_VALID(o)) & obj_destroy,o & endfor & free_lun,u & exit" > sarbatch_gacos_test.txt 2>&1
echo EXIT=%ERRORLEVEL% >> sarbatch_gacos_test.txt
