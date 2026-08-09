@echo off
setlocal
rem ==== path config (config.env) ====
for /f "usebackq tokens=1,* delims==" %%a in ("%~dp0config.env") do set %%a=%%b
cd /d %WORK_DIR%
"%ENVI_IDL%" -quiet -e "!PATH=!PATH+';'+'%SARSCAPE_LIB%\envi_extensions\idl\lib'+';'+'%SARSCAPE_LIB%\envi_extensions\idl\lib\hook'+';'+'%SARSCAPE_LIB%\envi_extensions\envi\sarscape_local_sav' & resolve_routine,'sarscape_batch_init',/COMPILE_FULL_FILE & SARscape_Batch_Init,Temp_Directory='%WORK_DIR%\sar_tmp' & oSB=obj_new('SARscapeBatch') & openw,u,'%SAR_MODULES%',/get_lun & printf,u,'FILE-OK' & CATCH,err & if err ne 0 then begin & printf,u,'CATCH-ERR:',!ERROR_STATE.MSG & CATCH,/CANCEL & endif & m=oSB.Manifest() & printf,u,'MANIFEST-OK N=',n_elements(m) & if n_elements(m) gt 0 then printf,u,strjoin(m,'|') & free_lun,u & exit" > sarbatch_err7.txt 2>&1
echo EXIT=%ERRORLEVEL% >> sarbatch_err7.txt
