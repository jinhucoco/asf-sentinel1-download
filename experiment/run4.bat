@echo off
cd /d D:\work\data
"C:\Program Files\Harris\ENVI56\IDL88\bin\bin.x86_64\envi_idl.exe" -quiet -e ".compile D:\work\data\test_sarbatch & test_sarbatch & exit" > sarbatch_err2.txt 2>&1
echo EXIT=%ERRORLEVEL% >> sarbatch_err2.txt
