@echo off
setlocal
rem ==== path config (config.env) ====
for /f "usebackq tokens=1,* delims==" %%a in ("%~dp0..\..\config.env") do set %%a=%%b
cd /d %WORK_DIR%
rem ============================================================
rem ==== baseline config (from config.env, default fallback if missing) ====
if not defined MAX_PERC_BASELINE set MAX_PERC_BASELINE=2
if not defined MAX_TIME_BASELINE set MAX_TIME_BASELINE=180
rem ==== super reference (from config.env; empty falls back to bundled legacy list) ====
if not defined SUPER_REFERENCE set SUPER_REFERENCE=%SLC_DATA%/sentinel1_135_20230112_231116058_IW_D_VV_msc_slc_list
rem  SBAS Step 1: Connection Graph
rem  IRON RULE (2026-08-07 user methodology, verified 2026-08-21):
rem  Space baseline MUST be 2%-4%, NOT SARscape default 45%.
rem  45% -> long-baseline pairs -> poor coherence in low-coherence
rem  areas (desert) -> coregistration falls back to dense-DEM path
rem  (~380x slower, 21-24min/pair vs 6min/pair). 2% keeps short
rem  baselines -> sparse GCP coregistration -> fast + high quality.
rem  If connectivity <99% at 2%, raise to 4% (MAX_PERC_BASELINE=4).
rem ============================================================
rem ==== baseline config (from config.env, default fallback if missing) ====
if not defined MAX_PERC_BASELINE set MAX_PERC_BASELINE=2
if not defined MAX_TIME_BASELINE set MAX_TIME_BASELINE=180
"%ENVI_IDL%" -quiet -e "!PATH=!PATH+';'+'%SARSCAPE_LIB%\envi_extensions\idl\lib'+';'+'%SARSCAPE_LIB%\envi_extensions\idl\lib\hook'+';'+'%SARSCAPE_LIB%\envi_extensions\envi\sarscape_local_sav' & resolve_routine,'sarscape_batch_init',/COMPILE_FULL_FILE & SARscape_Batch_Init,Temp_Directory='%TMP_DIR%' & openr,fl,'%WORK_DIR%\sar\slc_list.txt',/get_lun & nd=file_lines('%WORK_DIR%\sar\slc_list.txt') & slc=strarr(nd) & readf,fl,slc & free_lun,fl & openw,u,'%SAR_MODULES%',/get_lun & o=obj_new('SARscapeBatch',Module='InSARStackSBASGenerateConnectionGraph') & P='MAIN_INSAR_STACK_SBAS_GENERATE_CONNECTION_GRAPH_CMD.' & printf,u,'OBJ:',byte(OBJ_VALID(o)) & a=o.SetParam(P+'INPUT_FILE_LIST',slc) & printf,u,'SETIN:',byte(a) & b=o.SetParam(P+'OUTPUT_DATA_FILE_NAME','%RESULT_ROOT%\CG_result') & printf,u,'SETOUT:',byte(b) & c=o.SetParam(P+'INPUT_SUPER_REFERENCE','%SUPER_REFERENCE%') & printf,u,'SETSR:',byte(c) & d1=o.SetParam(P+'MIN_PERC_BASELINE',0.0) & printf,u,'SETMINB:',byte(d1) & d2=o.SetParam(P+'MAX_PERC_BASELINE',%MAX_PERC_BASELINE%) & printf,u,'SETMAXB:',byte(d2) & d3=o.SetParam(P+'MIN_TIME_BASELINE',0) & printf,u,'SETMINT:',byte(d3) & d4=o.SetParam(P+'MAX_TIME_BASELINE',%MAX_TIME_BASELINE%) & printf,u,'SETMAXT:',byte(d4) & v=o.VerifyParams() & printf,u,'VERIFY:',byte(v) & r=o.Execute() & printf,u,'EXECUTE:',byte(r) & free_lun,u & exit" > sarbatch_cg_final.txt 2>&1
echo EXIT=%ERRORLEVEL% >> sarbatch_cg_final.txt
