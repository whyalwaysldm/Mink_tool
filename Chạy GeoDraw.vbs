' Chay GeoDraw khong hien cua so cmd (double-click file nay).
' Lan dau chua co PyQt6 -> mo file .bat de cai dat (co cua so de xem tien trinh).
Option Explicit
Dim sh, fso, root, mainPy, logPath, cands, c, found, f
Set sh  = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
root    = fso.GetParentFolderName(WScript.ScriptFullName)
mainPy  = root & "\geodraw\main.py"
logPath = root & "\error_log.txt"

cands = Array("""" & root & "\python\pythonw.exe""", "pyw -3", "pythonw")
found = ""
For Each c In cands
    If c <> cands(0) Or fso.FileExists(root & "\python\pythonw.exe") Then
        On Error Resume Next
        If sh.Run(c & " -c ""import PyQt6.QtWidgets""", 0, True) = 0 Then
            If Err.Number = 0 Then found = c
        End If
        Err.Clear
        On Error GoTo 0
        If found <> "" Then Exit For
    End If
Next

If found = "" Then
    sh.Run """" & root & "\Ch" & ChrW(7841) & "y GeoDraw.bat""", 1, False
    WScript.Quit
End If

If fso.FileExists(logPath) Then fso.DeleteFile logPath
sh.CurrentDirectory = root & "\geodraw"
sh.Run found & " """ & mainPy & """", 0, True

If fso.FileExists(logPath) Then
    Set f = fso.OpenTextFile(logPath, 1, False, -2)
    MsgBox f.ReadAll, vbExclamation, "GeoDraw - loi"
    f.Close
End If
