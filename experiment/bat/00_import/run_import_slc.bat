@echo off
setlocal
rem ==== path config (config.env) ====
for /f "usebackq tokens=1,* delims==" %%a in ("%~dp0..\..\config.env") do set %%a=%%b
cd /d %WORK_DIR%
rem ============================================================
rem  SLC raw data import (SARscape ImportSentinel1Format)
rem  Step 0 of full chain: import ASF-downloaded SLC zips
rem  ENVI path: /SARscape/Import Data/SAR Spaceborne/Single Sensor/Sentinel-1
rem
rem  Params from config.env:
rem    SLC_DATA       input dir containing *.zip (S1A/S1B/S1C IW SLC)
rem    SLC_ROI        optional AOI shapefile (WGS84) - bursts clipped
rem    SLC_OUTPUT     output dir (auto-named, RENAME flag=OK)
rem    SLC_POLARIZATION  ALL_POL / ONLY_VV_POL(default) / ONLY_HH_POL
rem                   / ONLY_VV_HH_POL / ONLY_VH_HV_POL / ONLY_VV_VH_POL
rem                   / ONLY_HH_HV_POL / ONLY_VH_POL / ONLY_HV_POL
rem
rem  Usage:
rem    run_import_slc.bat          real run (one scene ~10-15 min)
rem    run_import_slc.bat verify   verify params only (VerifyParams=1)
rem
rem  NOTE: keep comments ASCII - UTF-8 Chinese breaks cmd/GBK parsing
rem ============================================================

rem ---- defaults if not set in config.env ----
if "%SLC_DATA%"=="" set SLC_DATA=UNSET
if "%SLC_OUTPUT%"=="" set SLC_OUTPUT=%SLC_DATA%
if "%SLC_POLARIZATION%"=="" set SLC_POLARIZATION=ONLY_VV_POL

set "COMMON=!PATH=!PATH+';'+'%SARSCAPE_LIB%\envi_extensions\idl\lib'+';'+'%SARSCAPE_LIB%\envi_extensions\idl\lib\hook'+';'+'%SARSCAPE_LIB%\envi_extensions\envi\sarscape_local_sav' & resolve_routine,'sarscape_batch_init',/COMPILE_FULL_FILE & SARscape_Batch_Init,Temp_Directory='%TMP_DIR%' & openw,u,'%SAR_MODULES%',/get_lun & inp=file_search('%SLC_DATA%','*.zip') & nf=n_elements(inp) & printf,u,'NFILES:',nf & outdir='%SLC_OUTPUT%' & outs=outdir+'/'+file_basename(inp,'.zip') & o=obj_new('SARscapeBatch',Module='ImportSentinel1Format') & P='MAIN_IMPORT_SENTINEL1_CMD.' & printf,u,'OBJ:',byte(OBJ_VALID(o)) & r0=o.SetParam('GENERAL_PARAMETERS_CMD.RENAME_THE_FILE_USING_PARAMETERS_FLAG','OK') & printf,u,'SETRENAME:',byte(r0) & a=o.SetParam(P+'SARSCAPEENVIRONMENT','IDL_ENVI_ENV') & printf,u,'SETENV:',byte(a) & b=o.SetParam(P+'INPUT_FILE_LIST',inp) & printf,u,'SETIN:',byte(b) & if strlen('%SLC_ROI%') gt 0 then c=o.SetParam(P+'INPUT_ROI_FILE','%SLC_ROI%') else c=1 & printf,u,'SETROI:',byte(c) & d=o.SetParam(P+'OUTPUT_FILE_LIST',outs) & printf,u,'SETOUT:',byte(d) & e=o.SetParam(P+'GENERATE_IW_EW_POWER_FLAG','OK') & printf,u,'SETPWR:',byte(e) & f=o.SetParam(P+'CROSS_COPOLARIZATION_FLAG','%SLC_POLARIZATION%') & printf,u,'SETPOL:',byte(f) & g=o.SetParam(P+'MAKE_SLC_LIST_MOSAIC_FLAG','OK') & printf,u,'SETMOS:',byte(g) & h=o.SetParam(P+'REBUILD_ALL_FLAG','NotOK') & printf,u,'SETRBL:',byte(h) & i=o.SetParam(P+'REMOVE_NOISE_FROM_LUT_FLAG','OK') & printf,u,'SETNOISE:',byte(i) & j=o.SetParam(P+'SKIP_SAMPLE_FLAG','NotOK') & printf,u,'SETSMP:',byte(j) & k=o.SetParam(P+'CONTINUE_WHEN_FAIL_FLAG','OK') & printf,u,'SETCF:',byte(k) & l=o.SetParam(P+'ONLY_REPORTS_FLAG','NotOK') & printf,u,'SETREP:',byte(l) & m=o.SetParam(P+'SKIP_ORBIT_WARNING_FLAG','NotOK') & printf,u,'SETORB:',byte(m) & n=o.SetParam(P+'EXIT_INSTEAD_WARNING_FLAG','NotOK') & printf,u,'SETEXIT:',byte(n) & v=o.VerifyParams() & printf,u,'VERIFY:',byte(v)"

if /i "%~1"=="verify" (
  "%ENVI_IDL%" -quiet -e "%COMMON% & free_lun,u & exit" > sarbatch_import_slc_verify.txt 2>&1
  echo EXIT=%ERRORLEVEL% >> sarbatch_import_slc_verify.txt
) else (
  "%ENVI_IDL%" -quiet -e "%COMMON% & r=o.Execute() & printf,u,'EXECUTE:',byte(r) & free_lun,u & exit" > sarbatch_import_slc.txt 2>&1
  echo EXIT=%ERRORLEVEL% >> sarbatch_import_slc.txt
)
