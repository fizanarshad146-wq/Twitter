Set WshShell = CreateObject("WScript.Shell")
strDesktop = WshShell.SpecialFolders("Desktop")
strCurrentDir = WshShell.CurrentDirectory

Set oLink = WshShell.CreateShortcut(strDesktop & "\X Auto Poster Desktop.lnk")
oLink.TargetPath = strCurrentDir & "\Start_App_Silent.vbs"
oLink.WorkingDirectory = strCurrentDir
oLink.Description = "X / Twitter Auto Posting Multi-Account Desktop App"
oLink.Save

WScript.Echo "✅ Desktop Shortcut Created Successfully!"
