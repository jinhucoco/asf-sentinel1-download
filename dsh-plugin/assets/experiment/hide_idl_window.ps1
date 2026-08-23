# 单次执行: 隐藏所有 IDL Workbench 窗口（由守护每轮调用, 无循环）
$src = @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public class HideOnce {
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint p);
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc cb, IntPtr l);
    public delegate bool EnumWindowsProc(IntPtr h, IntPtr l);
}
'@
Add-Type -TypeDefinition $src
$cb = [HideOnce+EnumWindowsProc]{ param($h, $l)
    $sb = New-Object System.Text.StringBuilder 256
    [HideOnce]::GetWindowText($h, $sb, 256) | Out-Null
    $t = $sb.ToString()
    if ($t -match 'IDLWorkspace|IDL Workbench' -and [HideOnce]::IsWindowVisible($h)) {
        [HideOnce]::ShowWindow($h, 6) | Out-Null
        [HideOnce]::ShowWindow($h, 0) | Out-Null
    }
    return $true
}
[HideOnce]::EnumWindows($cb, [IntPtr]::Zero) | Out-Null
