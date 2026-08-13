@echo off
setlocal
rem ==== path config (config.env) ====
for /f "usebackq tokens=1,* delims==" %%a in ("%~dp0..\..\config.env") do set %%a=%%b
cd /d %WORK_DIR%
rem ============================================================
rem  SBAS 反演第 2 步（InSARStackSBASInversionStep2）
rem  参数：
rem    - 形变模型 same_as_first（与第 1 步一致）
rem    - 产品相干阈值 0.2 / 解缠 MCF 0.2 / 等级 2
rem    - 大气低通 1200m / 大气高通 365 天
rem  ⚠️ 参数名需 VerifyParams 输出校验
rem ============================================================
"%ENVI_IDL%" -minimized -quiet -e "!PATH=!PATH+';'+'%SARSCAPE_LIB%\envi_extensions\idl\lib'+';'+'%SARSCAPE_LIB%\envi_extensions\idl\lib\hook'+';'+'%SARSCAPE_LIB%\envi_extensions\envi\sarscape_local_sav' & resolve_routine,'sarscape_batch_init',/COMPILE_FULL_FILE & SARscape_Batch_Init,Temp_Directory='%TMP_DIR%' & openw,u,'%SAR_MODULES%',/get_lun & ob=obj_new('SARscapeBatch',Module='InSARStackSBASInversionStep2') & M='MAIN_INSAR_STACK_SBAS_INVERSION_STEP2_CMD.' & p1=ob.SetParam(M+'AUXILIARY_FILE_NAME','%RESULT_ROOT%\CG_gulang2_SBAS_processing\auxiliary.sml') & p2=ob.SetParam(M+'DISPLACEMENT_MODEL_TYPE','same_as_first') & p3=ob.SetParam(M+'PRODUCT_COHERENCE_THRESHOLD',0.2) & p4=ob.SetParam(M+'UPHA_CMD.UPHA_METHOD_TYPE','MCF') & p5=ob.SetParam(M+'UPHA_CMD.UPHA_COH_THRESHOLD',0.2) & p6=ob.SetParam(M+'UPHA_CMD.UPHA_LEVELS_NBR',2.0) & p7=ob.SetParam(M+'ATMOSPHERE_PD_CMD.LOW_PASS_FILTER',1200.0) & p8=ob.SetParam(M+'ATMOSPHERE_PD_CMD.HIGH_PASS_FILTER',365.0) & printf,u,'SETALL:',byte(p1),byte(p2),byte(p3),byte(p4),byte(p5),byte(p6),byte(p7),byte(p8) & pv=ob.VerifyParams() & printf,u,'VERIFY:',byte(pv) & pe=ob.Execute() & printf,u,'EXECUTE:',byte(pe) & free_lun,u & exit" > sarbatch_inv2.txt 2>&1
echo EXIT=%ERRORLEVEL% >> sarbatch_inv2.txt
