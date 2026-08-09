@echo off
setlocal
rem ==== path config (config.env) ====
for /f "usebackq tokens=1,* delims==" %%a in ("%~dp0config.env") do set %%a=%%b
cd /d %WORK_DIR%
"%ENVI_IDL%" -quiet -e "!PATH=!PATH+';'+'%SARSCAPE_LIB%\envi_extensions\idl\lib'+';'+'%SARSCAPE_LIB%\envi_extensions\idl\lib\hook'+';'+'%SARSCAPE_LIB%\envi_extensions\envi\sarscape_local_sav' & resolve_routine,'sarscape_batch_init',/COMPILE_FULL_FILE & SARscape_Batch_Init,Temp_Directory='%TMP_DIR%' & openw,u,'%SAR_MODULES%',/get_lun & o=obj_new('SARscapeBatch',Module='InSARStackSBASGenerateConnectionGraph') & h=help,/structure,o & printf,u,o & methods=obj_class(o) & printf,u,'CLASS:',methods & free_lun,u & exit" > sarbatch_methods.txt 2>&1
echo EXIT=%ERRORLEVEL% >> sarbatch_methods.txt
