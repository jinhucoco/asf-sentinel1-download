@echo off
setlocal
rem ==== path config (config.env) ====
for /f "usebackq tokens=1,* delims==" %%a in ("%~dp0..\..\config.env") do set %%a=%%b
cd /d %WORK_DIR%
"%ENVI_IDL%" -quiet -e "!PATH=!PATH+';'+'%SARSCAPE_LIB%\envi_extensions\idl\lib'+';'+'%SARSCAPE_LIB%\envi_extensions\idl\lib\hook'+';'+'%SARSCAPE_LIB%\envi_extensions\envi\sarscape_local_sav' & resolve_routine,'sarscape_batch_init',/COMPILE_FULL_FILE & SARscape_Batch_Init,Temp_Directory='%WORK_DIR%\sar_tmp' & openw,u,'%SAR_MODULES%',/get_lun & oSB=obj_new('SARscapeBatch') & CATCH,err & if err ne 0 then begin & printf,u,'ERR:',!ERROR_STATE.MSG & CATCH,/CANCEL & endif & r=oSB.SearchModule('SENTINEL') & printf,u,'SEARCH-SENTINEL N=',n_elements(r) & if n_elements(r) gt 0 then printf,u,strjoin(r,'|') & r2=oSB.SearchModule('SBAS') & printf,u,'SEARCH-SBAS N=',n_elements(r2) & if n_elements(r2) gt 0 then printf,u,strjoin(r2,'|') & r3=oSB.SearchModule('') & printf,u,'SEARCH-ALL N=',n_elements(r3) & free_lun,u & exit" > sarbatch_err10.txt 2>&1
echo EXIT=%ERRORLEVEL% >> sarbatch_err10.txt
