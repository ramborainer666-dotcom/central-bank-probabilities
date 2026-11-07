Option Explicit

' Central Bank Probability Monitor: start local server invisibly.
' Double-click this file. No permanent PowerShell window is needed.
' The server only listens on 127.0.0.1 (not exposed to the network).

Dim sh, fso, root, url, check, attempt, command, quiet
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(WScript.ScriptFullName)
url = "http://127.0.0.1:8766/dashboard/index.html"
quiet = (WScript.Arguments.Count > 0)
If quiet Then quiet = (LCase(WScript.Arguments(0)) = "--quiet")

If Not fso.FileExists(fso.BuildPath(root, "dashboard\index.html")) Or Not fso.FileExists(fso.BuildPath(root, "local_server.py")) Then
  If Not quiet Then MsgBox "dashboard\index.html fehlt. Bitte das komplette GitHub-Projekt verwenden.", vbExclamation, "Central Bank Dashboard"
  WScript.Quit 1
End If

check = CheckDashboard(url)
If check = 2 Then
  If Not quiet Then MsgBox "Port 8766 ist bereits von einem anderen Webserver belegt." & vbCrLf & "Beende diesen Server und versuche es erneut.", vbExclamation, "Central Bank Dashboard"
  WScript.Quit 2
End If

If check <> 1 Then
  ' Run without a visible console. Use the installed Windows Python launcher.
  command = "cmd.exe /d /c py " & Quote(fso.BuildPath(root, "local_server.py"))
  On Error Resume Next
  sh.Run command, 0, False
  If Err.Number <> 0 Then
    If Not quiet Then MsgBox "Python konnte nicht gestartet werden: " & Err.Description, vbCritical, "Central Bank Dashboard"
    WScript.Quit 3
  End If
  On Error GoTo 0

  check = 0
  For attempt = 1 To 20
    WScript.Sleep 400
    check = CheckDashboard(url)
    If check <> 0 Then Exit For
  Next
End If

Select Case check
  Case 1
    If Not quiet Then sh.Run "explorer.exe " & Quote(url), 1, False
  Case 2
    If Not quiet Then MsgBox "Port 8766 liefert eine andere Webseite. Bitte den anderen Server beenden.", vbExclamation, "Central Bank Dashboard"
  Case Else
    If Not quiet Then MsgBox "Lokaler Server wurde nicht erreichbar. Pruefe, ob Python (py) installiert ist." & vbCrLf & "Test in PowerShell: py --version", vbCritical, "Central Bank Dashboard"
End Select

Function Quote(value)
  Quote = Chr(34) & value & Chr(34)
End Function

Function CheckDashboard(target)
  Dim req, body, status
  CheckDashboard = 0
  On Error Resume Next
  Set req = CreateObject("WinHttp.WinHttpRequest.5.1")
  req.SetTimeouts 600, 600, 1000, 1000
  req.Open "GET", target, False
  req.Send
  If Err.Number <> 0 Then
    Err.Clear
    Exit Function
  End If
  status = req.Status
  body = req.ResponseText
  If Err.Number <> 0 Then
    Err.Clear
    Exit Function
  End If
  On Error GoTo 0
  If status = 200 Then
    If InStr(1, body, "Central Bank Probability Monitor", vbTextCompare) > 0 Then
      CheckDashboard = 1
    Else
      CheckDashboard = 2
    End If
  Else
    CheckDashboard = 2
  End If
End Function
