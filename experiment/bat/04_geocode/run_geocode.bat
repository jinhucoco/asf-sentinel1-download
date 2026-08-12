@echo off
cd /d D:\work\data
rem ============================================================
rem  SBAS 地理编码（InSARStackSBASGeocode）——第 5 步
rem  参数（2026-08-11 用户确认）：
rem    - 输出网格 30m（8:2 多视；参数名 geocode_rg/az_grid_size 待 VerifyParams 确认）
rem    - 产品相干阈值 0.2
rem    - 速度/高程精度阈值 30
rem    - 输出 LOS 向 + TIFF（不做垂直向）
rem  ⚠️ 参数名需 VerifyParams 输出校验，不对立即修正
rem ============================================================
"C:\Program Files\Harris\ENVI56\IDL88\bin\bin.x86_64\envi_idl.exe" -minimized -quiet -e "!PATH=!PATH+';'+'C:\Program Files\SARMAP SA\SARscape\auxiliary\envi_extensions\idl\lib'+';'+'C:\Program Files\SARMAP SA\SARscape\auxiliary\envi_extensions\idl\lib\hook'+';'+'C:\Program Files\SARMAP SA\SARscape\auxiliary\envi_extensions\envi\sarscape_local_sav' & resolve_routine,'sarscape_batch_init',/COMPILE_FULL_FILE & SARscape_Batch_Init,Temp_Directory='G:\gulang2_result_SBAS_processing\tmp' & openw,u,'D:\work\data\sar_modules.txt',/get_lun & ob=obj_new('SARscapeBatch',Module='InSARStackSBASGeocode') & M='MAIN_INSAR_STACK_SBAS_GEOCODE_CMD.' & p1=ob.SetParam(M+'AUXILIARY_FILE_NAME','G:\gulang2_result_SBAS_processing\CG_gulang2_SBAS_processing\auxiliary.sml') & p2=ob.SetParam(M+'geocode_rg_grid_size',30.0) & p3=ob.SetParam(M+'geocode_az_grid_size',30.0) & p4=ob.SetParam(M+'PRODUCT_COHERENCE_THRESHOLD',0.2) & p5=ob.SetParam(M+'VELOCITY_THRESHOLD',30.0) & p6=ob.SetParam(M+'HEIGHT_THRESHOLD',30.0) & printf,u,'SETALL:',byte(p1),byte(p2),byte(p3),byte(p4),byte(p5),byte(p6) & pv=ob.VerifyParams() & printf,u,'VERIFY:',byte(pv) & pe=ob.Execute() & printf,u,'EXECUTE:',byte(pe) & free_lun,u & exit" > sarbatch_geocode.txt 2>&1
echo EXIT=%ERRORLEVEL% >> sarbatch_geocode.txt
