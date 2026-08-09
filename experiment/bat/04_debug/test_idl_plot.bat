@echo off
setlocal
rem ==== path config (config.env) ====
for /f "usebackq tokens=1,* delims==" %%a in ("%~dp0..\..\config.env") do set %%a=%%b
cd /d %WORK_DIR%
"%ENVI_IDL%" -quiet -e "!PATH=!PATH+';'+'%SARSCAPE_LIB%\envi_extensions\idl\lib'+';'+'%SARSCAPE_LIB%\envi_extensions\idl\lib\hook'+';'+'%SARSCAPE_LIB%\envi_extensions\envi\sarscape_local_sav' & resolve_routine,'sarscape_batch_init',/COMPILE_FULL_FILE & SARscape_Batch_Init,Temp_Directory='%TMP_DIR%' & set_plot,'win' & x=findgen(10) & y=x^2 & window,0,xsize=400,ysize=300 & plot,x,y,title='IDL Plot Test',xtitle='X',ytitle='Y' & f='%RESULT_ROOT%\CG_gulang2_SBAS_processing\connection_graph\plot\idl_test.png' & tvscl,rdbuf(/true) & write_png,f,tvrd(true=1) & print,'PLOT_OK' & exit" > sarbatch_plot_test.txt 2>&1
echo EXIT=%ERRORLEVEL% >> sarbatch_plot_test.txt
