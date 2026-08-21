@echo off
setlocal
rem ==== path config (config.env) ====
for /f "usebackq tokens=1,* delims==" %%a in ("%~dp0..\..\config.env") do set %%a=%%b
cd /d %WORK_DIR%
rem ============================================================
rem  DEM preprocessing - SARscape standard flow (user-taught, 2026-08-04)
rem  Step1: merge hgt tiles -> <name>.dat (ENVI format, float32 WGS84)
rem  Step2: ImportEnviOriginal -> <name>.dat_envi  (GEOIDAL DEM / EGM96)
rem  Step3: ToolsGeoid -> final DEM                (SUBTRACT / EGM96)
rem
rem  IRON RULES (measured):
rem   - DATA_UNITS must be 'GEOIDAL DEM' (NOT 'DEM' - SetParam returns 0)
rem   - GEOID_OPERATION must be 'SUBTRACT' (no spaces - 'SUBTRACT GEOID' rejected)
rem   - NASADEM is orthometric height; InSAR needs ellipsoidal height,
rem     so the EGM96 geoid subtraction is REQUIRED (error ~ -30..-40m otherwise)
rem   - config.env: DEM_RAW (hgt files), DEM_DAT / DEM_ENVI / DEM_FINAL
rem ============================================================
python "%WORK_DIR%\experiment\tools\merge_hgt_dem.py" --input %DEM_RAW% --output "%DEM_DAT%" || exit /b 1

"%ENVI_IDL%" -quiet -e "!PATH=!PATH+';'+'%SARSCAPE_LIB%\envi_extensions\idl\lib'+';'+'%SARSCAPE_LIB%\envi_extensions\idl\lib\hook'+';'+'%SARSCAPE_LIB%\envi_extensions\envi\sarscape_local_sav' & resolve_routine,'sarscape_batch_init',/COMPILE_FULL_FILE & SARscape_Batch_Init,Temp_Directory='%TMP_DIR%' & openw,u,'%SAR_MODULES%',/get_lun & o1=obj_new('SARscapeBatch',Module='ImportEnviOriginal') & P1='MAIN_BASIC_IMPORT_FILE_ENVI_ORIGINAL_CMD.' & printf,u,'OBJ1:',byte(OBJ_VALID(o1)) & a=o1.SetParam(P1+'INPUT_FILE_LIST','%DEM_DAT%') & printf,u,'SETIN1:',byte(a) & b=o1.SetParam(P1+'OUTPUT_FILE_LIST','%DEM_ENVI%') & printf,u,'SETOUT1:',byte(b) & c=o1.SetParam(P1+'DATA_UNITS','GEOIDAL DEM') & printf,u,'SETUNITS:',byte(c) & d=o1.SetParam(P1+'GEOID_TYPE','EGM96') & printf,u,'SETGEOID:',byte(d) & v1=o1.VerifyParams() & printf,u,'VERIFY1:',byte(v1) & r1=o1.Execute() & printf,u,'EXECUTE1:',byte(r1) & o2=obj_new('SARscapeBatch',Module='ToolsGeoid') & P2='MAIN_TOOLS_GEOID_CMD.' & printf,u,'OBJ2:',byte(OBJ_VALID(o2)) & e=o2.SetParam(P2+'INPUT_FILE_NAME','%DEM_ENVI%') & printf,u,'SETIN2:',byte(e) & f=o2.SetParam(P2+'OUTPUT_FILE_NAME','%DEM_FINAL%') & printf,u,'SETOUT2:',byte(f) & g=o2.SetParam(P2+'GEOID_OPERATION','SUBTRACT') & printf,u,'SETOP:',byte(g) & h=o2.SetParam(P2+'GEOID_TYPE','EGM96') & printf,u,'SETGEOID2:',byte(h) & v2=o2.VerifyParams() & printf,u,'VERIFY2:',byte(v2) & r2=o2.Execute() & printf,u,'EXECUTE2:',byte(r2) & free_lun,u & exit" > sarbatch_dem.txt 2>&1
echo EXIT=%ERRORLEVEL% >> sarbatch_dem.txt
