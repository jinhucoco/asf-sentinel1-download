@echo off
setlocal
rem ==== path config (config.env) ====
for /f "usebackq tokens=1,* delims==" %%a in ("%~dp0..\..\config.env") do set %%a=%%b
cd /d %WORK_DIR%
"%ENVI_IDL%" -quiet -e "!PATH=!PATH+';'+'%SARSCAPE_LIB%\envi_extensions\idl\lib'+';'+'%SARSCAPE_LIB%\envi_extensions\idl\lib\hook'+';'+'%SARSCAPE_LIB%\envi_extensions\envi\sarscape_local_sav' & resolve_routine,'sarscape_batch_init',/COMPILE_FULL_FILE & SARscape_Batch_Init,Temp_Directory='%WORK_DIR%\sar\tmp' & openr,fl,'%WORK_DIR%\sar\gacos_dates.txt',/get_lun & nd=file_lines('%WORK_DIR%\sar\gacos_dates.txt') & dates=strarr(nd) & readf,fl,dates & free_lun,fl & openw,u,'%SAR_MODULES%',/get_lun & printf,u,'NDATES:',nd & for i=0,nd-1 do begin & o=obj_new('SARscapeBatch',Module='ImportGacos') & a=o.SetParam('input_file_list','%WORK_DIR%\sar\gacos\'+dates[i]+'.ztd') & b=o.SetParam('output_file_list','%WORK_DIR%\sar\gacos_out\'+dates[i]) & r=o.Execute() & printf,u,dates[i],':',byte(a),byte(b),byte(r) & obj_destroy,o & endfor & free_lun,u & exit" > sarbatch_gacos_bulk.txt 2>&1
echo EXIT=%ERRORLEVEL% >> sarbatch_gacos_bulk.txt
