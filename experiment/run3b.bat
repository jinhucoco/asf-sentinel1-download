@echo off
cd /d D:\work\data
"C:\Program Files\Harris\ENVI56\IDL88\bin\bin.x86_64\envi_idl.exe" -quiet -e ".run D:\work\data\test_sarbatch" > sarbatch_err.txt 2>&1
echo EXIT=%ERRORLEVEL% >> sarbatch_err.txt
