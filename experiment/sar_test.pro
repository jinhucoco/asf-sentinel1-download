print, 'SARscape IDL test start'
!PATH = !PATH + ';' + 'C:\Program Files\SARMAP SA\SARscape\auxiliary\envi_extensions\idl\lib'
resolve_routine, 'sarmap_core', /COMPILE_FULL_FILE
print, 'sarmap_core loaded OK'
exit
