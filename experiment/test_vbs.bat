@echo off
cd /d D:\work\data
"C:\Program Files\Harris\ENVI56\IDL88\bin\bin.x86_64\envi_idl.exe" -minimized -quiet -e "print,'VBS_TEST_OK' & exit" > sarbatch_vbs_test.txt 2>&1
