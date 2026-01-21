$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\OneDrive\Desktop\Portfolio Dashboard.lnk")
$Shortcut.TargetPath = "$PSScriptRoot\Dashboard.vbs"
$Shortcut.WorkingDirectory = $PSScriptRoot
$Shortcut.Save()
Write-Host "Acceso directo creado en el Escritorio"
