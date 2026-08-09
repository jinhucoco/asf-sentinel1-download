@echo off
cd /d D:\work\data
"C:\Program Files\Harris\ENVI56\IDL88\bin\bin.x86_64\envi_idl.exe" -quiet -e "print,'ENVI-IDL-WORKS' & exit" > envi_idl_out.txt 2>&1
echo EXITCODE=%ERRORLEVEL% >> envi_idl_out.txt
