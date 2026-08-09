@echo off
cd /d D:\work\data
"C:\Program Files\Harris\ENVI56\IDL88\bin\bin.x86_64\idl.exe" -quiet -e "print,'IDL-FROM-BAT' & exit" > idl_bat_out.txt 2>&1
echo EXITCODE=%ERRORLEVEL% >> idl_bat_out.txt
