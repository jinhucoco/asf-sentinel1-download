@echo off
cd /d D:\work\data
"C:\Program Files\Harris\ENVI56\IDL88\bin\bin.x86_64\envi_idl.exe" -quiet -e "openw,u,'D:\work\data\sar_modules.txt',/get_lun & d=file_lines('D:\work\data\sar\gacos_dates.txt') & printf,u,'TYPE:',size(d,/type),'N:',n_elements(d) & printf,u,'FIRST:',d[0] & printf,u,'LAST:',d[n_elements(d)-1] & free_lun,u & exit" > sarbatch_fl.txt 2>&1
echo EXIT=%ERRORLEVEL% >> sarbatch_fl.txt
