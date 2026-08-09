@echo off
cd /d D:\work\data
"C:\Program Files\Harris\ENVI56\IDL88\bin\bin.x86_64\envi_idl.exe" -quiet -e "openw,u,'D:\work\data\envi_idl_test.txt',/get_lun & printf,u,'ENVI-IDL-WRITE-OK' & free_lun,u & exit" 2>nul
