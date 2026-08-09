@echo off
setlocal
rem ==== path config (config.env) ====
for /f "usebackq tokens=1,* delims==" %%a in ("%~dp0..\..\config.env") do set %%a=%%b
cd /d %WORK_DIR%
"%ENVI_IDL%" -quiet -e "!PATH=!PATH+';'+'%SARSCAPE_LIB%\envi_extensions\idl\lib'+';'+'%SARSCAPE_LIB%\envi_extensions\idl\lib\hook'+';'+'%SARSCAPE_LIB%\envi_extensions\envi\sarscape_local_sav' & resolve_routine,'sarscape_batch_init',/COMPILE_FULL_FILE & SARscape_Batch_Init,Temp_Directory='%WORK_DIR%\sar\tmp' & openw,u,'%SAR_MODULES%',/get_lun & o=obj_new('SARscapeBatch',Module='ImportEnviOriginal') & printf,u,'OBJ:',byte(OBJ_VALID(o)) & a=o.SetParam('input_file_list',['%WORK_DIR%\sar\dem\yanjiuqu.dat']) & printf,u,'IN:',byte(a) & b=o.SetParam('output_file_list',['%WORK_DIR%\sar\dem\yanjiuqu.dat_envi']) & printf,u,'OUT:',byte(b) & c=o.SetParam('data_units','Geoidal DEM') & printf,u,'UNITS:',byte(c) & r=o.Execute() & printf,u,'EXECUTE:',byte(r) & free_lun,u & exit" > sarbatch_err22.txt 2>&1
echo EXIT=%ERRORLEVEL% >> sarbatch_err22.txt
