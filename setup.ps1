# setup.ps1 - Cloudflare IP 优选工具一键部署脚本（防闪退版）
# 
# 用法：直接双击运行，或右键“使用 PowerShell 运行”即可，脚本会自动请求管理员权限。

$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "Cloudflare IP 优选部署"

# ==================== 管理员权限检查与自动提权 ====================
function Test-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal $identity
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-Administrator)) {
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host " Cloudflare IP 优选工具 - 智能部署" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "❌ 当前未以管理员身份运行。" -ForegroundColor Red
    Write-Host ""
    Write-Host "本脚本需要管理员权限才能创建计划任务。" -ForegroundColor Yellow
    Write-Host ""
    $choice = Read-Host "是否尝试以管理员身份重新启动脚本？(Y/N)"
    if ($choice -eq 'Y' -or $choice -eq 'y') {
        Write-Host "正在请求管理员权限..." -ForegroundColor Green
        try {
            $arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
            Start-Process PowerShell -Verb RunAs -ArgumentList $arguments
            exit 0
        } catch {
            Write-Host "❌ 无法自动提权: $_" -ForegroundColor Red
            Write-Host ""
            Write-Host "请手动操作：" -ForegroundColor Yellow
            Write-Host "  1. 关闭此窗口。" -ForegroundColor White
            Write-Host "  2. 按 Win + X，选择 'Windows PowerShell (管理员)'。" -ForegroundColor White
            Write-Host "  3. 使用 cd 命令进入脚本所在目录：" -ForegroundColor White
            Write-Host "     cd '$PSScriptRoot'" -ForegroundColor Cyan
            Write-Host "  4. 执行 .\setup.ps1" -ForegroundColor White
            Write-Host ""
            Read-Host "按 Enter 键退出"
            exit 1
        }
    } else {
        Write-Host ""
        Write-Host "请手动以管理员身份运行此脚本：" -ForegroundColor Yellow
        Write-Host "  1. 关闭此窗口。" -ForegroundColor White
        Write-Host "  2. 按 Win + X，选择 'Windows PowerShell (管理员)'。" -ForegroundColor White
        Write-Host "  3. 使用 cd 命令进入脚本所在目录：" -ForegroundColor White
        Write-Host "     cd '$PSScriptRoot'" -ForegroundColor Cyan
        Write-Host "  4. 执行 .\setup.ps1" -ForegroundColor White
        Write-Host ""
        Read-Host "按 Enter 键退出"
        exit 1
    }
}

# 此时一定是以管理员身份运行了
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Cloudflare IP 优选工具 - 智能部署" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ---------- 切换至脚本所在目录 ----------
Set-Location $PSScriptRoot
$ScriptDir = $PSScriptRoot
Write-Host "工作目录: $ScriptDir`n" -ForegroundColor Gray

# ==================== 计划任务配置 ====================
$TaskName = "Cloudflare IP 优选"
$TaskIntervalMinutes = 5
$PythonExePath = $null
$PythonScriptPath = Join-Path $ScriptDir "main.py"
$WorkingDirectory = $ScriptDir
# ====================================================

# ---------- 辅助函数：刷新环境变量 PATH ----------
function Refresh-EnvPath {
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
}

# ---------- 计算下一个整点5分钟时间（用于首次触发）----------
function Get-NextAlignedTime {
    param([int]$IntervalMinutes = 5)
    $now = Get-Date
    $currentTotalMinutes = $now.Hour * 60 + $now.Minute
    $nextTotalMinutes = [math]::Ceiling($currentTotalMinutes / $IntervalMinutes) * $IntervalMinutes
    $nextTime = $now.Date.AddMinutes($nextTotalMinutes)
    return $nextTime
}

$firstRunTime = Get-NextAlignedTime -IntervalMinutes $TaskIntervalMinutes
$startBoundaryStr = $firstRunTime.ToString("yyyy-MM-ddTHH:mm:ss")
$startTimeDisplay = $firstRunTime.ToString("HH:mm")

# ---------- 1. 检测/安装 Python ----------
Write-Host "[1/4] 检查 Python..." -ForegroundColor Green
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) { $pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue }
if ($pythonCmd) {
    $PythonExePath = $pythonCmd.Source
    Write-Host "✅ Python 已安装: $PythonExePath" -ForegroundColor Gray
} else {
    Write-Host "未检测到 Python，正在尝试通过 winget 安装 Python 3..." -ForegroundColor Yellow
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Write-Host "❌ 未找到 winget，请手动安装 Python 3 并确保已添加到 PATH。" -ForegroundColor Red
        Write-Host "下载地址: https://www.python.org/downloads/" -ForegroundColor White
        Read-Host "按 Enter 键退出"
        exit 1
    }
    winget install Python.Python.3 --accept-package-agreements --accept-source-agreements
    Refresh-EnvPath
    Start-Sleep -Seconds 5
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCmd) { $pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue }
    if (-not $pythonCmd) {
        Write-Host "❌ 未能自动检测到 Python，请手动安装后重新运行本脚本。" -ForegroundColor Red
        Read-Host "按 Enter 键退出"
        exit 1
    }
    $PythonExePath = $pythonCmd.Source
    Write-Host "✅ Python 安装完成: $PythonExePath" -ForegroundColor Green
}

# ---------- 2. 检测/安装 Git ----------
Write-Host "[2/4] 检查 Git..." -ForegroundColor Green
$gitCmd = Get-Command git -ErrorAction SilentlyContinue
if ($gitCmd) {
    Write-Host "✅ Git 已安装: $($gitCmd.Source)" -ForegroundColor Gray
} else {
    Write-Host "未检测到 Git，正在通过 winget 安装 Git..." -ForegroundColor Yellow
    winget install Git.Git --accept-package-agreements --accept-source-agreements
    Write-Host "✅ Git 安装完成。" -ForegroundColor Green
}

# ---------- 3. 检测/安装 curl ----------
Write-Host "[3/4] 检查 curl..." -ForegroundColor Green
$curlCmd = Get-Command curl -ErrorAction SilentlyContinue
if ($curlCmd) {
    $curlPath = $curlCmd.Source
    if (-not $curlPath) {
        $curlPath = (Get-Command curl -CommandType Application -ErrorAction SilentlyContinue).Source
    }
    Write-Host "✅ curl 已安装: $curlPath" -ForegroundColor Gray
} else {
    Write-Host "未检测到 curl，正在通过 winget 安装 curl..." -ForegroundColor Yellow
    winget install cURL.cURL --accept-package-agreements --accept-source-agreements
    Write-Host "✅ curl 安装完成。" -ForegroundColor Green
}

# ---------- 4. 安装所有 Python 依赖（requests, aiohttp, brotlicffi）----------
Write-Host "[4/4] 检查并安装 Python 依赖..." -ForegroundColor Green

# 先升级 pip，确保安装过程顺畅
Write-Host "  升级 pip..." -ForegroundColor Gray
& $PythonExePath -m pip install --upgrade pip --quiet

# 检查并安装 requests
$reqInstalled = & $PythonExePath -m pip show requests 2>$null
if (-not $reqInstalled) {
    Write-Host "  安装 requests..." -ForegroundColor Yellow
    & $PythonExePath -m pip install requests --quiet
    Write-Host "  ✅ requests 安装完成" -ForegroundColor Green
} else {
    Write-Host "  ✅ requests 已安装" -ForegroundColor Gray
}

# 检查并安装 aiohttp
$aioInstalled = & $PythonExePath -m pip show aiohttp 2>$null
if (-not $aioInstalled) {
    Write-Host "  安装 aiohttp..." -ForegroundColor Yellow
    & $PythonExePath -m pip install aiohttp --quiet
    Write-Host "  ✅ aiohttp 安装完成" -ForegroundColor Green
} else {
    Write-Host "  ✅ aiohttp 已安装" -ForegroundColor Gray
}

# 检查并安装 brotli 解压支持（优先 brotlicffi，纯 Python 实现，兼容性更好）
$brotliInstalled = & $PythonExePath -m pip show brotlicffi 2>$null
if (-not $brotliInstalled) {
    $brotliInstalled = & $PythonExePath -m pip show brotli 2>$null
}
if (-not $brotliInstalled) {
    Write-Host "  安装 brotlicffi（解压支持）..." -ForegroundColor Yellow
    try {
        & $PythonExePath -m pip install brotlicffi --quiet
        Write-Host "  ✅ brotlicffi 安装完成" -ForegroundColor Green
    } catch {
        Write-Host "  ⚠️ brotlicffi 安装失败，尝试安装 brotli..." -ForegroundColor Yellow
        & $PythonExePath -m pip install brotli --quiet
        Write-Host "  ✅ brotli 安装完成" -ForegroundColor Green
    }
} else {
    Write-Host "  ✅ brotli 解压库已安装" -ForegroundColor Gray
}
Write-Host ""

# ---------- 创建 .gitignore 保护隐私 ----------
Write-Host "正在创建 .gitignore..." -ForegroundColor Green
$GitignorePath = Join-Path $ScriptDir ".gitignore"
@"
config.json
git_sync.ps1
git_sync.sh
__pycache__/
"@ | Out-File -FilePath $GitignorePath -Encoding utf8 -Force
Write-Host "✅ .gitignore 已创建`n" -ForegroundColor Gray

# ---------- 验证 main.py 是否存在 ----------
if (-not (Test-Path $PythonScriptPath)) {
    Write-Host "❌ 错误：未找到 main.py 文件，请确保脚本位于正确目录。" -ForegroundColor Red
    Write-Host "   预期位置: $PythonScriptPath" -ForegroundColor Yellow
    Read-Host "按 Enter 键退出"
    exit 1
}

# ========== 创建计划任务（优先 COM 对象，失败后回退 schtasks） ==========
Write-Host "正在配置 Windows 计划任务 '$TaskName' ..." -ForegroundColor Yellow
Write-Host "   首次运行时间: $startBoundaryStr (之后每 $TaskIntervalMinutes 分钟永久重复，无限期)" -ForegroundColor Gray

try {
    $taskService = New-Object -ComObject Schedule.Service
    $taskService.Connect()
    $rootFolder = $taskService.GetFolder("\")

    try { $rootFolder.DeleteTask($TaskName, 0) } catch { }

    $taskDefinition = $taskService.NewTask(0)
    $taskDefinition.RegistrationInfo.Description = "每$TaskIntervalMinutes分钟运行一次 Cloudflare IP 优选工具（永久重复）"

    $taskDefinition.Principal.LogonType = 5
    $taskDefinition.Principal.RunLevel = 1

    $taskDefinition.Settings.Enabled = $true
    $taskDefinition.Settings.StartWhenAvailable = $false
    $taskDefinition.Settings.AllowHardTerminate = $true
    $taskDefinition.Settings.ExecutionTimeLimit = "PT72H"
    $taskDefinition.Settings.MultipleInstances = 3
    $taskDefinition.Settings.Priority = 0
    $taskDefinition.Settings.DisallowStartIfOnBatteries = $true
    $taskDefinition.Settings.StopIfGoingOnBatteries = $true

    $trigger = $taskDefinition.Triggers.Create(1)
    $trigger.StartBoundary = $startBoundaryStr
    $trigger.Repetition.Interval = "PT${TaskIntervalMinutes}M"
    $trigger.Repetition.StopAtDurationEnd = $false
    $trigger.Enabled = $true

    $action = $taskDefinition.Actions.Create(0)
    $action.Path = $PythonExePath
    $action.Arguments = "`"$PythonScriptPath`""
    $action.WorkingDirectory = $WorkingDirectory

    $rootFolder.RegisterTaskDefinition(
        $TaskName,
        $taskDefinition,
        6,
        "SYSTEM",
        $null,
        5
    ) | Out-Null

    Write-Host "✅ 计划任务 '$TaskName' 创建成功！" -ForegroundColor Green
    Write-Host "   创建方式: COM 对象" -ForegroundColor Gray
    Write-Host "   触发器: $startBoundaryStr 首次运行，之后每 $TaskIntervalMinutes 分钟永久重复（无限期）" -ForegroundColor Gray
    Write-Host "   执行命令: `"$PythonExePath`" `"$PythonScriptPath`"" -ForegroundColor Gray
    Write-Host "   运行账户: SYSTEM" -ForegroundColor Gray
    Write-Host "   电池设置: 仅交流电源时运行" -ForegroundColor Gray

} catch {
    Write-Host "⚠️ COM 对象创建失败: $_" -ForegroundColor Yellow
    Write-Host "   尝试使用 schtasks 命令作为备选方案..." -ForegroundColor Yellow

    $schtasksArgs = @(
        "/Create",
        "/TN", $TaskName,
        "/TR", "`"$PythonExePath`" `"$PythonScriptPath`"",
        "/SC", "ONCE",
        "/ST", $startTimeDisplay,
        "/SD", $firstRunTime.ToString("yyyy/MM/dd"),
        "/RI", $TaskIntervalMinutes,
        "/DU", "9999/12/31",
        "/RU", "SYSTEM",
        "/F",
        "/RL", "HIGHEST"
    )

    $result = & schtasks @schtasksArgs 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ 计划任务 '$TaskName' 创建成功！" -ForegroundColor Green
        Write-Host "   创建方式: schtasks" -ForegroundColor Gray
    } else {
        Write-Host "❌ 自动创建计划任务失败。" -ForegroundColor Red
        Write-Host ""
        Write-Host "请手动创建（详见控制台输出的指引）" -ForegroundColor Yellow
    }
}

# ---------- 后续指引 ----------
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " 🎉 部署完成！" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "👉 接下来请完成以下手动配置步骤：" -ForegroundColor White
Write-Host "1. 编辑 config.json，填写 WxPusher 的 APP_TOKEN 和 UID（如需通知）" -ForegroundColor White
Write-Host "2. 编辑 git_sync.ps1，填写你的 GitHub Token、用户名及仓库名" -ForegroundColor White
Write-Host "3. 可选：在'任务计划程序' (taskschd.msc) 中查看或调整任务" -ForegroundColor Gray
Write-Host "4. 手动运行一次测试：python main.py（或等待计划任务自动执行）" -ForegroundColor Green
Write-Host ""

$response = Read-Host "是否立即运行一次 main.py 进行测试？(Y/N)"
if ($response -eq 'Y' -or $response -eq 'y') {
    Write-Host "正在运行 main.py ..." -ForegroundColor Cyan
    & $PythonExePath $PythonScriptPath
}

Read-Host "`n部署完成，按 Enter 键退出"