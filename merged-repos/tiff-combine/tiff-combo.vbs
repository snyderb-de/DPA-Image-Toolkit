command = "powershell.exe -nologo -command ""\\DOSFS01\DPA\Records Services\Temporary\bryan\scripts\tif-combo-user.ps1"""
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run command, 0
