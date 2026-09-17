Set WshShell = CreateObject("WScript.Shell")
WshShell.Run """" & WshShell.CurrentDirectory & "\Start_Desktop_App.bat""", 0, False
