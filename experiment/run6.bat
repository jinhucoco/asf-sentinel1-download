@echo off
cd /d D:\work\data
"C:\Program Files\Harris\ENVI56\IDL88\bin\bin.x86_64\envi_idl.exe" -quiet -e "!PATH=!PATH+';'+'C:\Program Files\SARMAP SA\SARscape\auxiliary\envi_extensions\idl\lib'+';'+'C:\Program Files\SARMAP SA\SARscape\auxiliary\envi_extensions\idl\lib\hook'+';'+'C:\Program Files\SARMAP SA\SARscape\auxiliary\envi_extensions\envi\sarscape_local_sav' & resolve_routine,'sarscape_batch_init',/COMPILE_FULL_FILE & SARscape_Batch_Init,Temp_Directory='D:\work\data\sar_tmp' & oSB=obj_new('SARscapeBatch') & openw,u,'D:\work\data\sb.txt',/get_lun & printf,u,string(OBJ_VALID(oSB)) & free_lun,u & exit" > sarbatch_err4.txt 2>&1
echo EXIT=%ERRORLEVEL% >> sarbatch_err4.txt
