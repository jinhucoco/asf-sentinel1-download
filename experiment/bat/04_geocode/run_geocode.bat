@echo off
setlocal
rem ==== path config (config.env) ====
for /f "usebackq tokens=1,* delims==" %%a in ("%~dp0..\..\config.env") do set %%a=%%b
cd /d %WORK_DIR%
rem ============================================================
rem  SBAS 地理编码（InSARStackSBASGeocode）——第 5 步
rem  参数（官方大写全名，2026-08-12 实测验证）：
rem    - 输出网格 30m（GEOCODE_CMD.GEOCODE_RG/AZ_GRID_SIZE）
rem    - 精度阈值 30m/30m（PRECISION_HEIGHT/VELOCITY_THR）
rem    - 产品相干阈值 0.2（COHERENCE_THR）
rem    - LOS 投影 + TIFF + 速率分级矢量（GENERATE_SHAPE_FLAG）
rem    - REBUILD_ALL=OK 全量重建（覆盖旧网格产物）
rem  ⚠️ 参数名必须用官方大写全名（GUI 名/小写名会静默失效，用默认 14m 网格）
rem ============================================================
"%ENVI_IDL%" -minimized -quiet -e "!PATH=!PATH+';'+'%SARSCAPE_LIB%\envi_extensions\idl\lib'+';'+'%SARSCAPE_LIB%\envi_extensions\idl\lib\hook'+';'+'%SARSCAPE_LIB%\envi_extensions\envi\sarscape_local_sav' & resolve_routine,'sarscape_batch_init',/COMPILE_FULL_FILE & SARscape_Batch_Init,Temp_Directory='%TMP_DIR%' & openw,u,'%SAR_MODULES%',/get_lun & ob=obj_new('SARscapeBatch',Module='InSARStackSBASGeocode') & p1=ob.SetParam('MAIN_INSAR_STACK_SBAS_GEOCODE_CMD.AUXILIARY_FILE_NAME','%RESULT_ROOT%\CG_gulang2_SBAS_processing\auxiliary.sml') & p2=ob.SetParam('MAIN_INSAR_STACK_SBAS_GEOCODE_CMD.REBUILD_ALL_FLAG','OK') & p3=ob.SetParam('GEOCODE_CMD.GEOCODE_RG_GRID_SIZE','30.0') & p4=ob.SetParam('GEOCODE_CMD.GEOCODE_AZ_GRID_SIZE','30.0') & p5=ob.SetParam('GEOCODE_CMD.GEOCODE_ORBIT_INTERPOL','10.0') & p6=ob.SetParam('DISPLACEMENT_PROJECTION_CMD.GENERATE_LOS_FLAG','OK') & p7=ob.SetParam('DISPLACEMENT_PROJECTION_CMD.GENERATE_VERTICAL_FLAG','NotOK') & p8=ob.SetParam('DISPLACEMENT_PROJECTION_CMD.GENERATE_MAX_SLOPE_FLAG','NotOK') & p9=ob.SetParam('DISPLACEMENT_PROJECTION_CMD.GENERATE_USER_CUSTOM_FLAG','NotOK') & p10=ob.SetParam('MAIN_INSAR_STACK_SBAS_GEOCODE_CMD.PRECISION_HEIGHT_THR','30.0') & p11=ob.SetParam('MAIN_INSAR_STACK_SBAS_GEOCODE_CMD.PRECISION_VELOCITY_THR','30.0') & p12=ob.SetParam('MAIN_INSAR_STACK_SBAS_GEOCODE_CMD.COHERENCE_THR','0.2') & p13=ob.SetParam('MAIN_INSAR_STACK_SBAS_GEOCODE_CMD.GENERATE_RASTER_FLAG','OK') & p14=ob.SetParam('MAIN_INSAR_STACK_SBAS_GEOCODE_CMD.GENERATE_SHAPE_FLAG','OK') & p15=ob.SetParam('MAIN_INSAR_STACK_SBAS_GEOCODE_CMD.SHAPE_TIME_SERIES_FLAG','OK') & p16=ob.SetParam('MAIN_INSAR_STACK_SBAS_GEOCODE_CMD.SET_CODE_FOR_TEMPORAL_INTERPOL_VALUES_FLAG','OK') & p17=ob.SetParam('MAIN_INSAR_STACK_SBAS_GEOCODE_CMD.SET_CODE_FOR_SPATIAL_INTERPOL_VALUES_FLAG','OK') & p18=ob.SetParam('MAIN_INSAR_STACK_SBAS_GEOCODE_CMD.SERIES_DBF_STRING','D_') & p19=ob.SetParam('GENERAL_PARAMETERS_CMD.MAKE_TIFF','OK') & p20=ob.SetParam('GENERAL_PARAMETERS_CMD.QUICK_LOOK_FORMAT','ql_tiff') & p21=ob.SetParam('OUT_CARTOGRAPHIC_SYSTEM.OCS_STATE','GEO-GLOBAL') & p22=ob.SetParam('OUT_CARTOGRAPHIC_SYSTEM.OCS_PROJECTION','GEO') & p23=ob.SetParam('OUT_CARTOGRAPHIC_SYSTEM.OCS_ELLIPSOID','WGS84') & printf,u,'SETALL:',byte(p1),byte(p2),byte(p3),byte(p4),byte(p5),byte(p6),byte(p7),byte(p8),byte(p9),byte(p10),byte(p11),byte(p12),byte(p13),byte(p14),byte(p15),byte(p16),byte(p17),byte(p18),byte(p19),byte(p20),byte(p21),byte(p22),byte(p23) & pv=ob.VerifyParams() & printf,u,'VERIFY:',byte(pv) & pe=ob.Execute() & printf,u,'EXECUTE:',byte(pe) & free_lun,u & exit" > sarbatch_geocode.txt 2>&1
echo EXIT=%ERRORLEVEL% >> sarbatch_geocode.txt
