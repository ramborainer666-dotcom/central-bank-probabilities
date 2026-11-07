Option Explicit

' Create a user-only Startup shortcut that runs the dashboard server
' hidden after Windows logon. It does not open the browser automatically.
Dim sh, fso, root, launch, folder, link, shortcut, answer
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(WScript.ScriptFullName)
launch = fso.BuildPath(root, "Dashboard starten.vbs")
If Not fso.FileExists(launch) Then
  MsgBox "Dashboard starten.vbs fehlt im Projektordner.", vbCritical, "Dashboard Autostart"
  WScript.Quit 1
End If

folder = sh.SpecialFolders("Startup")
link = fso.BuildPath(folder, "Central Bank Dashboard.lnk")
Set shortcut = sh.CreateShortcut(link)
shortcut.TargetPath = sh.ExpandEnvironmentStrings("%SystemRoot%") & "\System32\wscript.exe"
shortcut.Arguments = Chr(34) & launch & Chr(34) & " --quiet"
shortcut.WorkingDirectory = root
shortcut.Description = "Startet Central Bank Dashboard unsichtbar beim Windows-Login"
shortcut.Save
MsgBox "Autostart eingerichtet. Der lokale Dashboard-Server startet nach jeder Windows-Anmeldung unsichtbar." & vbCrLf & "Zum Oeffnen: Dashboard starten.vbs doppelklicken oder die Browser-Adresse aufrufen.", vbInformation, "Dashboard Autostart"
