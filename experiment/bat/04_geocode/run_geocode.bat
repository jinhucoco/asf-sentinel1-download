@echo off
setlocal
rem ==== path config (config.env) ====
for /f "usebackq tokens=1,* delims==" %%a in ("%~dp0..\..\config.env") do set %%a=%%b
cd /d %WORK_DIR%
rem ============================================================
rem  SBAS 地理编码（InSARStackSBASGeocode）——第 5 步
rem  参数（交接文档三十章）：
rem    - 输出网格 30m（与 8:2 多视匹配；4:1 → 15m）
rem    - 精度阈值 30+30m（速度/高程）
rem  ⚠️ 参数名按 run_interf 风格推断，执行前用 VERIFY 输出校验
rem ============================================================
"%ENVI_IDL%" -minimized -quiet -e "!PATH=!PATH+';'+'%SARSCAPE_LIB%\envi_extensions\idl\lib'+';'+'%SARSCAPE_LIB%\envi_extensions\idl\lib\hook'+';'+'%SARSCAPE_LIB%\envi_extensions\envi\sarscape_local_sav' & resolve_routine,'sarscape_batch_init',/COMPILE_FULL_FILE & SARscape_Batch_Init,Temp_Directory='%TMP_DIR%' & openw,u,'%SAR_MODULES%',/get_lun & ob=obj_new('SARscapeBatch',Module='InSARStackSBASGeocode') & M='MAIN_INSAR_STACK_SBAS_GEOCODE_CMD.' & p1=ob.SetParam(M+'AUXILIARY_FILE_NAME','%RESULT_ROOT%\CG_gulang2_SBAS_processing\auxiliary.sml') & p2=ob.SetParam(M+'GRID_SIZE',30.0) & p3=ob.SetParam(M+'VELOCITY_THRESHOLD',30.0) & p4=ob.SetParam(M+'HEIGHT_THRESHOLD',30.0) & printf,u,'SETALL:',byte(p1),byte(p2),byte(p3),byte(p4) & pv=ob.VerifyParams() & printf,u,'VERIFY:',byte(pv) & pe=ob.Execute() & printf,u,'EXECUTE:',byte(pe) & free_lun,u & exit" > sarbatch_geocode.txt 2>&1
echo EXIT=%ERRORLEVEL% >> sarbatch_geocode.txt
