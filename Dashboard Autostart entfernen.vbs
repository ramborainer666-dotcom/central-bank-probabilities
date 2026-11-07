Option Explicit

Dim sh, fso, link
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
link = fso.BuildPath(sh.SpecialFolders("Startup"), "Central Bank Dashboard.lnk")
If fso.FileExists(link) Then
  fso.DeleteFile link, True
  MsgBox "Autostart entfernt. Ein aktuell laufender Dashboard-Server bleibt bis zum Windows-Neustart aktiv.", vbInformation, "Dashboard Autostart"
Else
  MsgBox "Es ist kein Dashboard-Autostart eingerichtet.", vbInformation, "Dashboard Autostart"
End If
