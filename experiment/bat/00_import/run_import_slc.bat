@echo off
setlocal
rem ==== path config (config.env) ====
for /f "usebackq tokens=1,* delims==" %%a in ("%~dp0..\..\config.env") do set %%a=%%b
cd /d %WORK_DIR%
rem ============================================================
rem  SLC 原始数据导入（SARscape ImportSLC / ImportEnviSarscapeOriginal）
rem  全链路第 0 步：把 ASF 下载的 SLC 原始数据导入为 SARscape 格式
rem  ⚠️ 状态：框架占位——本机当初用 SARscape GUI 手动导入（77 景），
rem     自动化参数未提取。执行前必须：
rem     1. 打开 SARscape 导入向导（Import → EnviSarscapeOriginal）
rem     2. 记录参数（输入目录 %SLC_DATA% / 输出格式 / 极化 / 命名规则）
rem     3. 用导入向导生成的参数替换下方 SetParam
rem  ⚠️ 未提取参数前请勿直接执行（EXECUTE 会失败）
rem ============================================================
"%ENVI_IDL%" -minimized -quiet -e "!PATH=!PATH+';'+'%SARSCAPE_LIB%\envi_extensions\idl\lib'+';'+'%SARSCAPE_LIB%\envi_extensions\idl\lib\hook'+';'+'%SARSCAPE_LIB%\envi_extensions\envi\sarscape_local_sav' & resolve_routine,'sarscape_batch_init',/COMPILE_FULL_FILE & SARscape_Batch_Init,Temp_Directory='%TMP_DIR%' & openw,u,'%SAR_MODULES%',/get_lun & ob=obj_new('SARscapeBatch',Module='ImportEnviSarscapeOriginal') & M='MAIN_IMPORT_ENVI_SARSCAPE_ORIG_CMD.' & p1=ob.SetParam(M+'INPUT_FILE_LIST','%SLC_DATA%') & p2=ob.SetParam(M+'OUTPUT_FORMAT','ENVI') & printf,u,'SETALL:',byte(p1),byte(p2) & pv=ob.VerifyParams() & printf,u,'VERIFY:',byte(pv) & pe=ob.Execute() & printf,u,'EXECUTE:',byte(pe) & free_lun,u & exit" > sarbatch_import_slc.txt 2>&1
echo EXIT=%ERRORLEVEL% >> sarbatch_import_slc.txt
