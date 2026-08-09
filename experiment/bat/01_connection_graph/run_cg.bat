@echo off
setlocal
rem ==== path config (config.env) ====
for /f "usebackq tokens=1,* delims==" %%a in ("%~dp0..\..\config.env") do set %%a=%%b
cd /d %WORK_DIR%
"%ENVI_IDL%" -quiet -e "!PATH=!PATH+';'+'%SARSCAPE_LIB%\envi_extensions\idl\lib'+';'+'%SARSCAPE_LIB%\envi_extensions\idl\lib\hook'+';'+'%SARSCAPE_LIB%\envi_extensions\envi\sarscape_local_sav' & resolve_routine,'sarscape_batch_init',/COMPILE_FULL_FILE & SARscape_Batch_Init,Temp_Directory='%WORK_DIR%\sar\tmp' & openr,fl,'%WORK_DIR%\sar\slc_list.txt',/get_lun & nd=file_lines('%WORK_DIR%\sar\slc_list.txt') & slc=strarr(nd) & readf,fl,slc & free_lun,fl & openw,u,'%SAR_MODULES%',/get_lun & o=obj_new('SARscapeBatch',Module='InSARStackSBASGenerateConnectionGraph') & a=o.SetParam('input_file_list',slc) & printf,u,'SETIN:',byte(a) & sr=o.SetParam('input_super_reference','%SLC_DATA%/sentinel1_135_20230112_231116058_IW_D_VV_msc_slc_list') & printf,u,'SETSR:',byte(sr) & mb=o.SetParam('max_time_baseline',180.0) & printf,u,'SETMAXT:',byte(mb) & r=o.Execute() & printf,u,'EXECUTE:',byte(r) & free_lun,u & exit" > sarbatch_cg.txt 2>&1
echo EXIT=%ERRORLEVEL% >> sarbatch_cg.txt
