#Requires -Version 5.1
<#
.SYNOPSIS
    Установщик tg-chat-monitor для Windows.
    Скачивает Python (если нет), создаёт venv, ставит зависимости, запускает мастер настройки.
#>

$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$PythonVersion = "3.12.10"
$MinPython = [version]"3.10.0"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$VenvPath = Join-Path $ProjectRoot "venv"
$VenvPython = Join-Path $VenvPath "Scripts\python.exe"
$VenvPip = Join-Path $VenvPath "Scripts\pip.exe"
$Requirements = Join-Path $ProjectRoot "requirements.txt"
$SetupScript = Join-Path $ProjectRoot "setup.py"
$TempDir = Join-Path $ProjectRoot "installer\windows\.cache"

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host "  >> $Message" -ForegroundColor Cyan
}

function Write-Ok([string]$Message) {
    Write-Host "  [OK] $Message" -ForegroundColor Green
}

function Write-Warn([string]$Message) {
    Write-Host "  [!] $Message" -ForegroundColor Yellow
}

function Write-Err([string]$Message) {
    Write-Host "  [ОШИБКА] $Message" -ForegroundColor Red
}

function Get-ArchSuffix {
    if ($env:PROCESSOR_ARCHITECTURE -eq "ARM64") {
        return "arm64"
    }
    return "amd64"
}

function Test-PythonVersion([string]$PythonExe) {
    if (-not (Test-Path $PythonExe)) {
        return $null
    }
    try {
        $versionText = & $PythonExe -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')" 2>$null
        $version = [version]$versionText.Trim()
        if ($version -ge $MinPython) {
            return $version
        }
    } catch {}
    return $null
}

function Find-SystemPython {
    $candidates = @(
        "python",
        "python3",
        "py -3.12",
        "py -3"
    )

    foreach ($cmd in $candidates) {
        try {
            if ($cmd -like "py *") {
                $parts = $cmd -split " "
                $versionText = & $parts[0] $parts[1] -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')" 2>$null
            } else {
                $versionText = & $cmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')" 2>$null
            }
            if ($LASTEXITCODE -eq 0 -and $versionText) {
                $version = [version]$versionText.Trim()
                if ($version -ge $MinPython) {
                    if ($cmd -like "py *") {
                        return @{ Exe = "$($parts[0]) $($parts[1])"; Version = $version; IsPyLauncher = $true }
                    }
                    $resolved = (Get-Command $cmd -ErrorAction SilentlyContinue).Source
                    return @{ Exe = $resolved; Version = $version; IsPyLauncher = $false }
                }
            }
        } catch {}
    }

    $localPython = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"
    $version = Test-PythonVersion $localPython
    if ($version) {
        return @{ Exe = $localPython; Version = $version; IsPyLauncher = $false }
    }

    return $null
}

function Invoke-PythonCommand([hashtable]$PythonInfo, [string[]]$CommandArgs) {
    if ($PythonInfo.IsPyLauncher) {
        $parts = $PythonInfo.Exe -split " "
        & $parts[0] $parts[1] @CommandArgs
    } else {
        & $PythonInfo.Exe @CommandArgs
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Команда Python завершилась с ошибкой (код $LASTEXITCODE): $($CommandArgs -join ' ')"
    }
}

function Install-PortablePython {
    $arch = Get-ArchSuffix
    $installerName = "python-$PythonVersion-$arch.exe"
    $installerUrl = "https://www.python.org/ftp/python/$PythonVersion/$installerName"
    $installerPath = Join-Path $TempDir $installerName
    $targetDir = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312"

    if (-not (Test-Path $TempDir)) {
        New-Item -ItemType Directory -Path $TempDir -Force | Out-Null
    }

    Write-Step "Скачивание Python $PythonVersion ($arch)..."
    Write-Host "      $installerUrl" -ForegroundColor DarkGray

    try {
        Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath -UseBasicParsing
    } catch {
        throw "Не удалось скачать Python. Проверьте подключение к интернету.`n$($_.Exception.Message)"
    }

    Write-Step "Установка Python (без прав администратора, в профиль пользователя)..."
    Write-Host "      Подождите 1-2 минуты..." -ForegroundColor DarkGray

    $installArgs = @(
        "/quiet",
        "InstallAllUsers=0",
        "PrependPath=1",
        "Include_pip=1",
        "Include_launcher=1",
        "Include_test=0",
        "TargetDir=$targetDir"
    )

    $process = Start-Process -FilePath $installerPath -ArgumentList $installArgs -Wait -PassThru
    if ($process.ExitCode -ne 0) {
        throw "Установщик Python завершился с кодом $($process.ExitCode)"
    }

    $pythonExe = Join-Path $targetDir "python.exe"
    $version = Test-PythonVersion $pythonExe
    if (-not $version) {
        throw "Python установлен, но не найден по пути: $pythonExe"
    }

    Write-Ok "Python $version установлен: $pythonExe"
    return @{ Exe = $pythonExe; Version = $version; IsPyLauncher = $false }
}

function Ensure-VirtualEnv([hashtable]$PythonInfo) {
    if (Test-Path $VenvPython) {
        $version = Test-PythonVersion $VenvPython
        if ($version) {
            Write-Ok "Виртуальное окружение уже есть (Python $version)"
            return
        }
        Write-Warn "Повреждённое venv - пересоздаём..."
        Remove-Item -Recurse -Force $VenvPath
    }

    Write-Step "Создание виртуального окружения..."
    Invoke-PythonCommand $PythonInfo @("-m", "venv", $VenvPath)
    Write-Ok "Окружение создано: $VenvPath"
}

function Install-Dependencies {
    Write-Step "Установка зависимостей из requirements.txt..."
    & $VenvPython -m pip install --upgrade pip --quiet
    & $VenvPip install -r $Requirements
    if ($LASTEXITCODE -ne 0) {
        throw "Не удалось установить зависимости"
    }
    Write-Ok "Зависимости установлены"
}

function Start-SetupWizard {
    $envPath = Join-Path $ProjectRoot ".env"
    if (Test-Path $envPath) {
        Write-Ok "Файл .env уже существует - пропускаем мастер настройки"
        return
    }

    Write-Step "Запуск мастера настройки в браузере..."
    Write-Host "      Заполните настройки, сохраните .env и нажмите 'Запустить бота'" -ForegroundColor DarkGray
    Write-Host "      Для остановки мастера нажмите Ctrl+C в этом окне" -ForegroundColor DarkGray
    & $VenvPython $SetupScript
}

function New-ProjectShortcut {
    param(
        [string]$ShortcutName,
        [string]$BatFileName,
        [string]$Description
    )

    $target = Join-Path $ProjectRoot $BatFileName
    if (-not (Test-Path $target)) {
        return $null
    }

    $desktop = [Environment]::GetFolderPath("Desktop")
    $shortcutPath = Join-Path $desktop "$ShortcutName.lnk"

    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $target
    $shortcut.WorkingDirectory = $ProjectRoot
    $shortcut.Description = $Description
    $shortcut.Save()

    Write-Ok "Ярлык на рабочем столе: $ShortcutName"
    return $shortcutPath
}

function Install-DesktopShortcuts {
    Write-Step "Создание ярлыков на рабочем столе..."
    New-ProjectShortcut "tg-chat-monitor" "start.bat" "Запуск бота tg-chat-monitor" | Out-Null
    New-ProjectShortcut "tg-chat-monitor (установка)" "install.bat" "Установка tg-chat-monitor" | Out-Null
}

function Invoke-LaunchPrompt {
    $envPath = Join-Path $ProjectRoot ".env"
    if (-not (Test-Path $envPath)) {
        Write-Warn "Файл .env не найден - сначала завершите настройку в браузере"
        return
    }

    Write-Host ""
    Write-Host "  Запустить бота сейчас? (Y/n): " -ForegroundColor White -NoNewline
    $answer = Read-Host
    if ($answer -eq "" -or $answer -match "^[yY]|^[дД]") {
        Write-Step "Запуск tg-chat-monitor..."
        $startBat = Join-Path $ProjectRoot "start.bat"
        Start-Process -FilePath $startBat -WorkingDirectory $ProjectRoot
        Write-Ok "Бот запущен в новом окне"
    }
}

# --- main ---

Clear-Host
Write-Host ""
Write-Host "  ============================================================" -ForegroundColor White
Write-Host "    tg-chat-monitor - установка для Windows" -ForegroundColor White
Write-Host "  ============================================================" -ForegroundColor White
Write-Host ""
Write-Host "  Папка проекта: $ProjectRoot" -ForegroundColor DarkGray

Set-Location $ProjectRoot

try {
    Write-Step "Проверка Python..."
    $pythonInfo = Find-SystemPython

    if ($pythonInfo) {
        Write-Ok "Найден Python $($pythonInfo.Version): $($pythonInfo.Exe)"
    } else {
        Write-Warn "Python 3.10+ не найден - будет скачан и установлен автоматически"
        $pythonInfo = Install-PortablePython
    }

    Ensure-VirtualEnv $pythonInfo
    Install-Dependencies
    Start-SetupWizard
    Install-DesktopShortcuts

    Write-Host ""
    Write-Host "  ============================================================" -ForegroundColor Green
    Write-Host "    Установка завершена!" -ForegroundColor Green
    Write-Host "  ============================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Запуск бота (любой способ):" -ForegroundColor White
    Write-Host "    - ярлык 'tg-chat-monitor' на рабочем столе" -ForegroundColor Yellow
    Write-Host "    - файл start.bat в папке проекта" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Не нужно вводить python main.py вручную!" -ForegroundColor DarkGray
    Write-Host "  Папка проекта: $ProjectRoot" -ForegroundColor DarkGray
    Write-Host ""

    Invoke-LaunchPrompt

} catch {
    Write-Host ""
    Write-Err $_.Exception.Message
    Write-Host ""
    Write-Host "  Если проблема повторяется:" -ForegroundColor DarkGray
    Write-Host "  1. Проверьте интернет-соединение" -ForegroundColor DarkGray
    Write-Host "  2. Установите Python 3.10+ вручную с https://www.python.org/downloads/" -ForegroundColor DarkGray
    Write-Host "  3. Запустите install.bat снова" -ForegroundColor DarkGray
    Write-Host ""
    exit 1
}
