' Career OS - Start (hidden, no console window)
' Double-click this to launch Career OS with no visible window at all.
' Requires the one-time setup via start.bat to have run at least once
' (so Flask is installed).

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
strPath = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = strPath

pidFilePath = strPath & "\.careeros.pid"

' If a PID file already exists, check whether that process is actually
' still alive before starting a second copy.
alreadyRunning = False
If fso.FileExists(pidFilePath) Then
    Set pidFile = fso.OpenTextFile(pidFilePath, 1)
    existingPid = Trim(pidFile.ReadLine)
    pidFile.Close
    Set colProcesses = GetObject("winmgmts:").ExecQuery _
        ("Select * from Win32_Process Where ProcessId = " & existingPid)
    For Each objProcess In colProcesses
        alreadyRunning = True
    Next
End If

If alreadyRunning Then
    WshShell.Run "cmd /c start """" ""http://127.0.0.1:5000""", 0, False
    MsgBox "Career OS is already running. Opening it in your browser.", 64, "Career OS"
Else
    ' pythonw.exe has no console window of its own.
    Set objExec = WshShell.Exec("pythonw.exe app.py")
    Set outFile = fso.CreateTextFile(pidFilePath, True)
    outFile.WriteLine objExec.ProcessID
    outFile.Close

    WScript.Sleep 1500
    WshShell.Run "cmd /c start """" ""http://127.0.0.1:5000""", 0, False
End If
