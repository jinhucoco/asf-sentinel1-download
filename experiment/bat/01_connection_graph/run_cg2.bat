@echo off
setlocal
rem ==== path config (config.env) ====
for /f "usebackq tokens=1,* delims==" %%a in ("%~dp0..\..\config.env") do set %%a=%%b
cd /d %WORK_DIR%
"%ENVI_IDL%" -quiet -e "!PATH=!PATH+';'+'%SARSCAPE_LIB%\envi_extensions\idl\lib'+';'+'%SARSCAPE_LIB%\envi_extensions\idl\lib\hook'+';'+'%SARSCAPE_LIB%\envi_extensions\envi\sarscape_local_sav' & resolve_routine,'sarscape_batch_init',/COMPILE_FULL_FILE & SARscape_Batch_Init,Temp_Directory='%WORK_DIR%\sar\tmp' & openr,fl,'%WORK_DIR%\sar\slc_list.txt',/get_lun & nd=file_lines('%WORK_DIR%\sar\slc_list.txt') & slc=strarr(nd) & readf,fl,slc & free_lun,fl & openw,u,'%SAR_MODULES%',/get_lun & o=obj_new('SARscapeBatch',Module='InSARStackSBASGenerateConnectionGraph') & P='MAIN_INSAR_STACK_SBAS_GENERATE_CONNECTION_GRAPH_CMD.' & printf,u,'OBJ:',byte(OBJ_VALID(o)) & a=o.SetParam(P+'INPUT_FILE_LIST',slc) & printf,u,'SETIN:',byte(a) & b=o.SetParam(P+'OUTPUT_DATA_FILE_NAME','%WORK_DIR%\sar\out\CG_gulang2') & printf,u,'SETOUT:',byte(b) & c=o.SetParam(P+'INPUT_SUPER_REFERENCE','%SLC_DATA%/sentinel1_135_20230112_231116058_IW_D_VV_msc_slc_list') & printf,u,'SETSR:',byte(c) & v=o.VerifyParams() & printf,u,'VERIFY:',byte(v) & r=o.Execute() & printf,u,'EXECUTE:',byte(r) & free_lun,u & exit" > sarbatch_cg2.txt 2>&1
echo EXIT=%ERRORLEVEL% >> sarbatch_cg2.txt
