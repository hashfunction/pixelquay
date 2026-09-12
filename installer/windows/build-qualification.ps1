# Windows qualification only. No Store identity, signing or release claim.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if (-not $IsWindows -or $env:CI -ne 'true') { throw 'Requires isolated Windows CI.' }
Set-Location (Resolve-Path (Join-Path $PSScriptRoot '../..'))
$env:Path = "$env:PIXELQUAY_MINGW\bin;$env:PIXELQUAY_MSYS\usr\bin;$env:Path"
function Invoke-Checked([string]$Program, [string[]]$Arguments) {
  & $Program @Arguments
  if ($LASTEXITCODE -ne 0) { throw "$Program failed with $LASTEXITCODE" }
}
. (Join-Path $PSScriptRoot 'consumer_ui.ps1')
Add-Type -Path (Join-Path $PSScriptRoot 'consumer_native.cs')
$pixelPython=(Get-Command python).Source
$pixelStartupState=Join-Path (Get-Location) 'build-evidence/unpackaged-consumer-owner.json'
[IO.Directory]::CreateDirectory((Split-Path $pixelStartupState -Parent)) | Out-Null
$pixelStartupRoot=Join-Path $env:RUNNER_TEMP ('pixelquay-startup-'+[guid]::NewGuid().ToString('N'))
$pixelStartupProfile=Join-Path ([Environment]::GetFolderPath('ApplicationData')) 'PixelQuay'
$pixelStartupOwnership=Invoke-PixelQuayFiles create $pixelStartupState @('--root',$pixelStartupRoot,'--profile',$pixelStartupProfile) -Python $pixelPython
$process=$null; $pixelProcessHandle=$null; $pixelProcessOwned=$false; $pixelStartupStopped=$true; $pixelNormalClose=$false; $pixelProfileRemoved=$false; $pixelBuildError=$null
try {
$mingwArgument = '-p:MinGWFolder=' + $env:PIXELQUAY_MINGW
$pythonArgument = '-p:PythonExecutable=' + (Get-Command python).Source
Invoke-Checked dotnet @('--info')
Invoke-Checked dotnet @('restore','Pinta.sln','--use-lock-file',$mingwArgument)
Invoke-Checked dotnet @('build','Pinta.sln','-c','Release','--no-restore',$mingwArgument)
Invoke-Checked dotnet @('test','Pinta.sln','-c','Release','--no-build','--no-restore',$mingwArgument,'--logger','trx','--results-directory','build-evidence/tests')
Invoke-Checked python @('installer/windows/test_inventory_native.py')
Invoke-Checked python @('installer/windows/test_managed_notices.py')
Invoke-Checked dotnet @('publish','Pinta/Pinta.csproj','-p:BuildTranslations=true',$mingwArgument,$pythonArgument,'-c','Release','-r','win-x64','--self-contained','true','-p:PublishDir=../release/bin/')
Invoke-Checked python @('installer/windows/inventory_managed.py','--assets','Pinta/obj/project.assets.json','--output','release/bin/licenses/managed-packages.json')
New-Item -ItemType Directory -Force release/share/icons/hicolor | Out-Null
foreach ($item in @('icons','locale')) {
  $from = Join-Path 'release/bin' $item
  if (Test-Path $from) { Copy-Item -Recurse -Force "$from/*" "release/share/$item"; Remove-Item -Recurse $from }
}
Copy-Item installer/macos/hicolor.index.theme release/share/icons/hicolor/index.theme
$expected = 'release/bin/TintFable.exe'
if (-not (Test-Path $expected)) { throw 'TintFable executable missing.' }
Get-ChildItem -Recurse -Filter packages.lock.json | ForEach-Object {
  $relative = [IO.Path]::GetRelativePath((Get-Location).Path, $_.FullName)
  $target = Join-Path 'build-evidence/nuget-locks' $relative
  New-Item -ItemType Directory -Force (Split-Path $target -Parent) | Out-Null
  Copy-Item $_.FullName $target
}
# The installed MSYS2 development tree must not satisfy missing package DLLs.
$env:Path = "$env:SystemRoot\System32;$env:SystemRoot"
$pixelStartupStopped=$false
$process = Start-Process (Resolve-Path $expected).Path -PassThru
$pixelProcessHandle=$process.SafeHandle
if ($pixelProcessHandle.IsInvalid -or $pixelProcessHandle.IsClosed -or
    [IO.Path]::GetFullPath($process.Path) -ine (Resolve-Path $expected).Path) { throw 'Unpackaged startup process ownership was not established' }
$pixelProcessOwned=$true
  $deadline = (Get-Date).AddSeconds(30)
  do {
    Start-Sleep -Milliseconds 500
    $process.Refresh()
    if ($process.HasExited) { throw "TintFable exited during startup: $($process.ExitCode)" }
  } until ($process.MainWindowHandle -ne 0 -or (Get-Date) -gt $deadline)
  if ($process.MainWindowHandle -eq 0) { throw 'No native main window appeared.' }
  $packageRoot = (Resolve-Path 'release').Path + [IO.Path]::DirectorySeparatorChar
  $windowsRoot = $env:SystemRoot + [IO.Path]::DirectorySeparatorChar
  $modules = @($process.Modules | ForEach-Object { @{ name=$_.ModuleName; path=$_.FileName } })
  $outside = @($modules | Where-Object { -not $_.path.StartsWith($packageRoot, [StringComparison]::OrdinalIgnoreCase) -and -not $_.path.StartsWith($windowsRoot, [StringComparison]::OrdinalIgnoreCase) })
  $modules | ConvertTo-Json -Depth 3 | Set-Content build-evidence/loaded-modules.json -Encoding utf8NoBOM
  if ($outside.Count -gt 0) { throw "Package loaded modules outside its own directory or Windows: $($outside.path -join ', ')" }
  $evidence = @{ generated_at_utc=[DateTime]::UtcNow.ToString('o'); source_commit=$env:GITHUB_SHA; windows_native_startup=$true; workflow_acceptance=$false; msix_built=$false; submitted=$false; executable_sha256=(Get-FileHash $expected -Algorithm SHA256).Hash; window_title=$process.MainWindowTitle; note='Native main window startup only. Interactive exports, DLL closure/source delivery, MSIX installation and Store gates remain pending.' }
  $evidence | ConvertTo-Json -Depth 4 | Set-Content build-evidence/windows-startup.json -Encoding utf8NoBOM
} catch {
  $pixelBuildError=$_.Exception.Message
  throw
} finally {
  $pixelCleanupErrors=[Collections.Generic.List[string]]::new()
  try {
    if ($process) {
      if (-not $pixelProcessOwned) { throw 'Unproved unpackaged process/profile preserved' }
      $exit=[PixelQuayQualification.ConsumerNative]::ExitCode($process,0)
      if ($null -eq $exit) {
        $closeAccepted=$process.CloseMainWindow()
        $exit=[PixelQuayQualification.ConsumerNative]::ExitCode($process,5000)
        $pixelNormalClose=$closeAccepted -and $null -ne $exit -and $exit -eq 0
        if (-not $pixelNormalClose) { $pixelCleanupErrors.Add('Unpackaged startup did not close normally with zero') }
      } else { $pixelCleanupErrors.Add('Unpackaged startup exited before normal close') }
      if ($null -eq $exit) {
        $process.Kill()
        $exit=[PixelQuayQualification.ConsumerNative]::ExitCode($process,10000)
      }
      if ($null -eq $exit) { throw 'Unpackaged process shutdown is unproven' }
      $pixelStartupStopped=$true
    }
  } catch { $pixelCleanupErrors.Add($_.Exception.Message) }
  if ($pixelStartupStopped) {
    try {
      Invoke-PixelQuayFiles baseline $pixelStartupState @('--stopped') -Python $pixelPython | Out-Null
      $cleanup=Invoke-PixelQuayFiles cleanup $pixelStartupState @('--stopped') -Python $pixelPython
      $pixelProfileRemoved=$cleanup.removed -eq $true
    } catch { $pixelCleanupErrors.Add($_.Exception.Message) }
    finally { if ($process) { $process.Dispose() } }
  }
  $pixelLifecycle=@{schema='pixelquay-unpackaged-profile-v1';retained_process_owned=$pixelProcessOwned;process_stopped=$pixelStartupStopped;normal_close_verified=$pixelNormalClose;owned_profile_and_fixture_removed=$pixelProfileRemoved;primary_error=$pixelBuildError;cleanup_errors=@($pixelCleanupErrors)}
  try {
    $metadata=[Text.Encoding]::UTF8.GetBytes(($pixelLifecycle | ConvertTo-Json -Depth 6))
    $file=[IO.File]::Open((Join-Path (Get-Location) 'build-evidence/unpackaged-profile-cleanup.json'),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try {$file.Write($metadata,0,$metadata.Length)}finally{$file.Dispose()}
  } catch {$pixelCleanupErrors.Add('Cleanup evidence: '+$_.Exception.Message)}
  if ($pixelCleanupErrors.Count) { throw "Unpackaged startup cleanup failed: $($pixelCleanupErrors -join '; '). Primary: $pixelBuildError" }
}
