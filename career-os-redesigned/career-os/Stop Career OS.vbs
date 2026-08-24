' Career OS - Stop
' Double-click this to stop the background Career OS process.

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
strPath = fso.GetParentFolderName(WScript.ScriptFullName)
pidFilePath = strPath & "\.careeros.pid"

If fso.FileExists(pidFilePath) Then
    Set pidFile = fso.OpenTextFile(pidFilePath, 1)
    strPID = Trim(pidFile.ReadLine)
    pidFile.Close
    WshShell.Run "taskkill /PID " & strPID & " /F", 0, True
    fso.DeleteFile pidFilePath
    MsgBox "Career OS stopped.", 64, "Career OS"
Else
    MsgBox "Career OS doesn't appear to be running (no record of it found).", 48, "Career OS"
End If
