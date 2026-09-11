# Private Windows qualification only. No Store identity, signing or release claim.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if (-not $IsWindows -or $env:CI -ne 'true') { throw 'Requires isolated Windows CI.' }
Set-Location (Resolve-Path (Join-Path $PSScriptRoot '../..'))
$env:Path = "$env:PIXELQUAY_MINGW\bin;$env:PIXELQUAY_MSYS\usr\bin;$env:Path"
function Invoke-Checked([string]$Program, [string[]]$Arguments) {
  & $Program @Arguments
  if ($LASTEXITCODE -ne 0) { throw "$Program failed with $LASTEXITCODE" }
}
$mingwArgument = '-p:MinGWFolder=' + $env:PIXELQUAY_MINGW
$pythonArgument = '-p:PythonExecutable=' + (Get-Command python).Source
Invoke-Checked dotnet @('--info')
Invoke-Checked dotnet @('restore','Pinta.sln','--use-lock-file',$mingwArgument)
Invoke-Checked dotnet @('build','Pinta.sln','-c','Release','--no-restore',$mingwArgument)
Invoke-Checked dotnet @('test','Pinta.sln','-c','Release','--no-build','--no-restore',$mingwArgument,'--logger','trx','--results-directory','build-evidence/tests')
Invoke-Checked python @('installer/windows/test_inventory_native.py')
Invoke-Checked dotnet @('publish','Pinta/Pinta.csproj','-p:BuildTranslations=true',$mingwArgument,$pythonArgument,'-c','Release','-r','win-x64','--self-contained','true','-p:PublishDir=../release/bin/')
Invoke-Checked python @('installer/windows/inventory_managed.py','--assets','Pinta/obj/project.assets.json','--output','release/bin/licenses/managed-packages.json')
New-Item -ItemType Directory -Force release/share/icons/hicolor | Out-Null
foreach ($item in @('icons','locale')) {
  $from = Join-Path 'release/bin' $item
  if (Test-Path $from) { Copy-Item -Recurse -Force "$from/*" "release/share/$item"; Remove-Item -Recurse $from }
}
Copy-Item installer/macos/hicolor.index.theme release/share/icons/hicolor/index.theme
$expected = 'release/bin/PixelQuay.exe'
if (-not (Test-Path $expected)) { throw 'PixelQuay executable missing.' }
Get-ChildItem -Recurse -Filter packages.lock.json | ForEach-Object {
  $relative = [IO.Path]::GetRelativePath((Get-Location).Path, $_.FullName)
  $target = Join-Path 'build-evidence/nuget-locks' $relative
  New-Item -ItemType Directory -Force (Split-Path $target -Parent) | Out-Null
  Copy-Item $_.FullName $target
}
$process = Start-Process (Resolve-Path $expected).Path -PassThru
try {
  $deadline = (Get-Date).AddSeconds(30)
  do {
    Start-Sleep -Milliseconds 500
    $process.Refresh()
    if ($process.HasExited) { throw "PixelQuay exited during startup: $($process.ExitCode)" }
  } until ($process.MainWindowHandle -ne 0 -or (Get-Date) -gt $deadline)
  if ($process.MainWindowHandle -eq 0) { throw 'No native main window appeared.' }
  $evidence = @{ generated_at_utc=[DateTime]::UtcNow.ToString('o'); source_commit=$env:GITHUB_SHA; windows_native_startup=$true; workflow_acceptance=$false; msix_built=$false; submitted=$false; executable_sha256=(Get-FileHash $expected -Algorithm SHA256).Hash; window_title=$process.MainWindowTitle; note='Native main window startup only. Interactive exports, DLL closure/source delivery, MSIX installation and Store gates remain pending.' }
  $evidence | ConvertTo-Json -Depth 4 | Set-Content build-evidence/windows-startup.json -Encoding utf8NoBOM
} finally {
  if (-not $process.HasExited) { $process.CloseMainWindow() | Out-Null; if (-not $process.WaitForExit(5000)) { $process.Kill() } }
}
