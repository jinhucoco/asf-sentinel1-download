pro test_sarbatch
logf = 'D:\work\data\sarbatch_log.txt'
openw,u,logf,/get_lun
printf,u,'STEP1: start'
!PATH = !PATH + ';' + 'C:\Program Files\SARMAP SA\SARscape\auxiliary\envi_extensions\idl\lib' + ';' + 'C:\Program Files\SARMAP SA\SARscape\auxiliary\envi_extensions\idl\lib\hook' + ';' + 'C:\Program Files\SARMAP SA\SARscape\auxiliary\envi_extensions\envi\sarscape_local_sav'
printf,u,'STEP2: path set'
resolve_routine, 'sarscape_batch_init', /COMPILE_FULL_FILE
printf,u,'STEP3: resolve done'
temp_dir = 'D:\work\data\sar_tmp'
SARscape_Batch_Init, Temp_Directory=temp_dir
printf,u,'STEP4: init done'
oSB = obj_new('SARscapeBatch')
printf,u,'STEP5: obj created valid=' + string(OBJ_VALID(oSB))
free_lun,u
SARscape_Batch_Exit
end
