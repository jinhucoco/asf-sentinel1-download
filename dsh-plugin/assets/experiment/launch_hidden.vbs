' 隐藏窗口启动器: 用 VBS 以完全隐藏方式运行 bat
' 用法: wscript launch_hidden.vbs <bat路径> <日志路径>
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

batPath = WScript.Arguments(0)
logPath = WScript.Arguments(1)

' 0 = 隐藏窗口, 6 = 最小化, 1 = 正常
' 用 0 (SW_HIDE) 完全隐藏
shell.Run """" & batPath & """", 0, False
WScript.Sleep 1000
