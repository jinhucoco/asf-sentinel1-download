@echo off
setlocal
rem ==== path config (config.env) ====
for /f "usebackq tokens=1,* delims==" %%a in ("%~dp0..\..\config.env") do set %%a=%%b
cd /d %WORK_DIR%
rem ============================================================
rem  SBAS Step 2: Interferogram generation
rem  SPEED IRON RULES (measured 2026-08-21, minqin vs gulang2):
rem  1. OpenCL comes from SARscape Preferences ONLY (default "NO PLATFORMS" =
rem     no GPU). MUST enable it first: ENVI -> SARscape -> Preferences ->
rem     OpenCL platform/device (GUI). ~4x faster with GPU for heavy steps.
rem  2. Speed is decided by the COREGISTRATION PATH: sparse-GCP (fast) vs
rem     dense-DEM (slow ~380x) - driven by baseline length & coherence.
rem     A 2-4% connection graph (run_cg_final.bat) keeps short baselines
rem     so coregistration stays on the fast path even in desert/low-coh areas.
rem  3. GUI adds spectral whitening before coregistration (~35min/scene,
rem     improves accuracy in low-coherence zones); batch default has none.
rem ============================================================
"%ENVI_IDL%" -minimized -quiet -e "!PATH=!PATH+';'+'%SARSCAPE_LIB%\envi_extensions\idl\lib'+';'+'%SARSCAPE_LIB%\envi_extensions\idl\lib\hook'+';'+'%SARSCAPE_LIB%\envi_extensions\envi\sarscape_local_sav' & resolve_routine,'sarscape_batch_init',/COMPILE_FULL_FILE & SARscape_Batch_Init,Temp_Directory='%TMP_DIR%' & openr,fl,'%GACOS_LIST%',/get_lun & nd=file_lines('%GACOS_LIST%') & gacos=strarr(nd) & readf,fl,gacos & free_lun,fl & openw,u,'%SAR_MODULES%',/get_lun & ob=obj_new('SARscapeBatch',Module='InSARStackSBASInterferogramGeneration') & M='MAIN_INSAR_STACK_SBAS_INTERFEROGRAM_GENERATION_CMD.' & p1=ob.SetParam(M+'AUXILIARY_FILE_NAME','%RESULT_ROOT%\CG_result_SBAS_processing\auxiliary.sml') & p2=ob.SetParam(M+'DEM_FILE_NAME','%DEM_FILE%') & p3=ob.SetParam(M+'RG_LOOKS_NBR',8.0) & p4=ob.SetParam(M+'AZ_LOOKS_NBR',2.0) & p5=ob.SetParam('ATMOSPHERE_PD_CMD.EXTERNAL_SENSOR','GACOS') & p6=ob.SetParam('ATMOSPHERE_PD_CMD.WATER_VAPOUR_FILE_LIST',gacos) & p7=ob.SetParam(M+'UPHA_CMD.UPHA_METHOD_TYPE','MCF') & p8=ob.SetParam(M+'UPHA_CMD.UPHA_COH_THRESHOLD',0.2) & p9=ob.SetParam(M+'UPHA_CMD.UPHA_LEVELS_NBR',1.0) & p10=ob.SetParam('FILTERING_CMD.FILTERING_METHOD','GOLDSTEIN') & p11=ob.SetParam('FILTERING_CMD.GOLDSTEIN_WINSIZE',64.0) & p12=ob.SetParam('FILTERING_CMD.COH_AZ_BOXSIZE',5.0) & p13=ob.SetParam('FILTERING_CMD.COH_RG_BOXSIZE',5.0) & p14=ob.SetParam('COREGISTRATION_CMD.COREGISTRATION_WITH_DEM_FLAG','OK') & p15=ob.SetParam('INTERF_CMD.INT_SPECTRAL_SHIFT_FILTER_FLAG','OK') & p16=ob.SetParam(M+'LAYOVER_SHADOW_MASK_FLAG','OK') & printf,u,'SETALL:',byte(p1),byte(p2),byte(p3),byte(p4),byte(p5),byte(p6),byte(p7),byte(p8) & printf,u,'SETALL2:',byte(p9),byte(p10),byte(p11),byte(p12),byte(p13),byte(p14),byte(p15),byte(p16) & pv=ob.VerifyParams() & printf,u,'VERIFY:',byte(pv) & pe=ob.Execute() & printf,u,'EXECUTE:',byte(pe) & free_lun,u & exit" > sarbatch_interf.txt 2>&1
echo EXIT=%ERRORLEVEL% >> sarbatch_interf.txt
