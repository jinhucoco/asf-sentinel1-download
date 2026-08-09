@echo off
setlocal
rem ==== path config (config.env) ====
for /f "usebackq tokens=1,* delims==" %%a in ("%~dp0config.env") do set %%a=%%b
cd /d %WORK_DIR%
"%ENVI_IDL%" -quiet -e "!PATH=!PATH+';'+'%SARSCAPE_LIB%\envi_extensions\idl\lib'+';'+'%SARSCAPE_LIB%\envi_extensions\idl\lib\hook'+';'+'%SARSCAPE_LIB%\envi_extensions\envi\sarscape_local_sav' & resolve_routine,'sarscape_batch_init',/COMPILE_FULL_FILE & SARscape_Batch_Init,Temp_Directory='%WORK_DIR%\sar_tmp' & openw,u,'%SAR_MODULES%',/get_lun & oSB=obj_new('SARscapeBatch',Module='BaseMultilooking') & printf,u,'BaseMultilooking valid=',string(OBJ_VALID(oSB)) & oSB2=obj_new('SARscapeBatch',Module='ImportSLC') & printf,u,'ImportSLC valid=',string(OBJ_VALID(oSB2)) & oSB3=obj_new('SARscapeBatch',Module='SBASProcessing') & printf,u,'SBASProcessing valid=',string(OBJ_VALID(oSB3)) & free_lun,u & exit" > sarbatch_err8.txt 2>&1
echo EXIT=%ERRORLEVEL% >> sarbatch_err8.txt
