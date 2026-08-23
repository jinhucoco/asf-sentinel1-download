@echo off
setlocal
rem ==== path config (config.env) ====
for /f "usebackq tokens=1,* delims==" %%a in ("%~dp0..\..\config.env") do set %%a=%%b
cd /d %WORK_DIR%
"%ENVI_IDL%" -quiet -e "!PATH=!PATH+';'+'%SARSCAPE_LIB%\envi_extensions\idl\lib'+';'+'%SARSCAPE_LIB%\envi_extensions\idl\lib\hook'+';'+'%SARSCAPE_LIB%\envi_extensions\envi\sarscape_local_sav' & resolve_routine,'sarscape_batch_init',/COMPILE_FULL_FILE & SARscape_Batch_Init,Temp_Directory='%WORK_DIR%\sar\tmp' & openw,u,'%SAR_MODULES%',/get_lun & o=obj_new('SARscapeBatch',Module='ImportGacos') & printf,u,'input_file_name:',byte(o.SetParam('input_file_name','%WORK_DIR%\sar\gacos\20200104.ztd')) & printf,u,'input_file_list:',byte(o.SetParam('input_file_list','%WORK_DIR%\sar\gacos\20200104.ztd')) & printf,u,'output_file_name:',byte(o.SetParam('output_file_name','%WORK_DIR%\sar\gacos_out\20200104')) & printf,u,'output_file_list:',byte(o.SetParam('output_file_list','%WORK_DIR%\sar\gacos_out\20200104')) & printf,u,'make_tiff:',byte(o.SetParam('make_tiff',0)) & free_lun,u & exit" > sarbatch_gacos_params.txt 2>&1
echo EXIT=%ERRORLEVEL% >> sarbatch_gacos_params.txt
