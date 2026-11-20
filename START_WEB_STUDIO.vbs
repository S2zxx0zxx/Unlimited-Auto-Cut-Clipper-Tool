' LiveClip Zero Studio — first-party, console-free Windows launcher.
' Works with the Python virtual environment from START_WINDOWS.bat.
' Changes PATH only for this launched process, never Windows system settings.
Option Explicit
Dim shell, fs, home, exe, env, current, root, ffmpegDir, command
Set shell = CreateObject("WScript.Shell")
Set fs = CreateObject("Scripting.FileSystemObject")
home = fs.GetParentFolderName(WScript.ScriptFullName)
exe = fs.BuildPath(home, ".venv\Scripts\pythonw.exe")
If Not fs.FileExists(exe) Then
  MsgBox "LiveClip Studio is not installed yet." & vbCrLf & _
         "First run START_WINDOWS.bat once to install the local dependencies.", _
         vbInformation, "LiveClip Zero Studio"
  WScript.Quit 1
End If
root = shell.ExpandEnvironmentStrings("%SystemRoot%")
Set env = shell.Environment("PROCESS")
current = env("PATH")
ffmpegDir = "C:\ffmpeg-9.1-essentials_build\bin"
If Not fs.FileExists(fs.BuildPath(ffmpegDir,"ffmpeg.exe")) Then
  ffmpegDir = "C:\ffmpeg\bin"
End If
If Not fs.FileExists(fs.BuildPath(ffmpegDir,"ffmpeg.exe")) Then
  ffmpegDir = "C:\Program Files\ffmpeg\bin"
End If
env("PATH") = root & "\System32;" & root & ";" & ffmpegDir & ";" & current
If shell.Run("cmd.exe /c ffmpeg -version >nul 2>nul", 0, True) <> 0 Then
  MsgBox "FFmpeg not found." & vbCrLf & _
         "Install FFmpeg and ffprobe, then retry. Your current PATH was not modified.", _
         vbExclamation, "LiveClip Zero Studio"
  WScript.Quit 1
End If
shell.CurrentDirectory = home
command = """" & exe & """ -m liveclip.web_studio"
shell.Run command, 0, False
