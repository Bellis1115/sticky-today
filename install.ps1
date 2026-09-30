$ErrorActionPreference = "Stop"

$project = Split-Path -Parent $MyInvocation.MyCommand.Path
$script = Join-Path $project "sticky_today.py"
if (-not (Test-Path $script)) {
    throw "找不到程序文件：$script"
}

$pythonw = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
if (-not $pythonw) {
    $python = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
    if ($python) {
        $pythonw = $python -replace "python\.exe$", "pythonw.exe"
    }
}
if (-not $pythonw -or -not (Test-Path $pythonw)) {
    throw "找不到 Python。请先安装 Python 3，并勾选 Add Python to PATH。"
}

$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "今日便利贴.lnk"
$icon = Join-Path $project "sticky_today.ico"
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $pythonw
$shortcut.Arguments = '"' + $script + '"'
$shortcut.WorkingDirectory = $project
$shortcut.IconLocation = if (Test-Path $icon) { "$icon,0" } else { "$pythonw,0" }
$shortcut.Description = "今日便利贴"
$shortcut.Save()

Write-Host "安装完成：$shortcutPath"
Write-Host "以后直接双击桌面上的‘今日便利贴’即可启动。"
Read-Host "按 Enter 退出"
