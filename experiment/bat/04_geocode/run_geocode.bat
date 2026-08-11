@echo off
cd /d D:\work\data
rem ============================================================
rem  SBAS 地理编码（InSARStackSBASGeocode）——第 5 步
rem  参数（交接文档三十章）：
rem    - 输出网格 30m（与 8:2 多视匹配）
rem    - 精度阈值 30+30m（速度/高程）
rem  ⚠️ 参数名需 VerifyParams 输出校验
rem ============================================================
"C:\Program Files\Harris\ENVI56\IDL88inin.x86_64\envi_idl.exe" -minimized -quiet -e "!PATH=!PATH+';'+'C:\Program Files\SARMAP SA\SARscapeuxiliary\envi_extensions\idl\lib'+';'+'C:\Program Files\SARMAP SA\SARscapeuxiliary\envi_extensions\idl\lib\hook'+';'+'C:\Program Files\SARMAP SA\SARscapeuxiliary\envi_extensions\envi\sarscape_local_sav' & resolve_routine,'sarscape_batch_init',/COMPILE_FULL_FILE & SARscape_Batch_Init,Temp_Directory='G:\gulang2_result_SBAS_processing	mp' & openw,u,'D:\work\data\sar_modules.txt',/get_lun & ob=obj_new('SARscapeBatch',Module='InSARStackSBASGeocode') & M='MAIN_INSAR_STACK_SBAS_GEOCODE_CMD.' & p1=ob.SetParam(M+'AUXILIARY_FILE_NAME','G:\gulang2_result_SBAS_processing\CG_gulang2_SBAS_processinguxiliary.sml') & p2=ob.SetParam(M+'GRID_SIZE',30.0) & p3=ob.SetParam(M+'VELOCITY_THRESHOLD',30.0) & p4=ob.SetParam(M+'HEIGHT_THRESHOLD',30.0) & printf,u,'SETALL:',byte(p1),byte(p2),byte(p3),byte(p4) & pv=ob.VerifyParams() & printf,u,'VERIFY:',byte(pv) & pe=ob.Execute() & printf,u,'EXECUTE:',byte(pe) & free_lun,u & exit" > sarbatch_geocode.txt 2>&1
echo EXIT=%ERRORLEVEL% >> sarbatch_geocode.txt
