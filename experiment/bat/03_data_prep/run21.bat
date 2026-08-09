@echo off
setlocal
rem ==== path config (config.env) ====
for /f "usebackq tokens=1,* delims==" %%a in ("%~dp0..\..\config.env") do set %%a=%%b
cd /d %WORK_DIR%
"%ENVI_IDL%" -quiet -e "!PATH=!PATH+';'+'%SARSCAPE_LIB%\envi_extensions\idl\lib'+';'+'%SARSCAPE_LIB%\envi_extensions\idl\lib\hook'+';'+'%SARSCAPE_LIB%\envi_extensions\envi\sarscape_local_sav' & resolve_routine,'sarscape_batch_init',/COMPILE_FULL_FILE & SARscape_Batch_Init,Temp_Directory='%WORK_DIR%\sar\tmp' & openw,u,'%SAR_MODULES%',/get_lun & printf,u,'NEW-RUN' & o=obj_new('SARscapeBatch',Module='ToolsDemExtractionSrtm1') & a=o.SetParam('input_file_list',['%WORK_DIR%\sar\dem\n37e102.hgt']) & printf,u,'input_file_list:',byte(a) & b=o.SetParam('dem_file_list',['%WORK_DIR%\sar\dem\n37e102.hgt']) & printf,u,'dem_file_list:',byte(b) & c=o.SetParam('input_dem',['%WORK_DIR%\sar\dem\n37e102.hgt']) & printf,u,'input_dem:',byte(c) & d=o.SetParam('input_srtm_files',['%WORK_DIR%\sar\dem\n37e102.hgt']) & printf,u,'input_srtm_files:',byte(d) & free_lun,u & exit" > sarbatch_err19.txt 2>&1
echo EXIT=%ERRORLEVEL% >> sarbatch_err19.txt
