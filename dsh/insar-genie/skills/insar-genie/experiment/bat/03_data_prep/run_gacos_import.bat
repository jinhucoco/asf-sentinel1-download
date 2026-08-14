@echo off
setlocal
rem ==== path config (config.env) ====
for /f "usebackq tokens=1,* delims==" %%a in ("%~dp0..\..\config.env") do set %%a=%%b
cd /d %WORK_DIR%
"%ENVI_IDL%" -quiet -e "!PATH=!PATH+';'+'%SARSCAPE_LIB%\envi_extensions\idl\lib'+';'+'%SARSCAPE_LIB%\envi_extensions\idl\lib\hook'+';'+'%SARSCAPE_LIB%\envi_extensions\envi\sarscape_local_sav' & resolve_routine,'sarscape_batch_init',/COMPILE_FULL_FILE & SARscape_Batch_Init,Temp_Directory='%WORK_DIR%\sar\tmp' & openw,u,'%SAR_MODULES%',/get_lun & o=obj_new('SARscapeBatch',Module='ImportGacos') & a=o.SetParam('input_file_list','%WORK_DIR%\sar\gacos\20200104.ztd') & printf,u,'SETIN:',byte(a) & b=o.SetParam('output_file_list','%WORK_DIR%\sar\gacos_out\20200104') & printf,u,'SETOUT:',byte(b) & c=o.SetParam('generate_ql',0) & printf,u,'SETQL:',byte(c) & r=o.Execute() & printf,u,'EXECUTE:',byte(r) & free_lun,u & exit" > sarbatch_gacos_import.txt 2>&1
echo EXIT=%ERRORLEVEL% >> sarbatch_gacos_import.txt
