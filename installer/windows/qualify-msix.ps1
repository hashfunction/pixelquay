# CI-only packaging and installed startup. Copyright 2026 Trieflow LLC, MIT.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if (-not $IsWindows -or $env:CI -ne 'true' -or $PSVersionTable.PSVersion.Major -lt 7) { throw 'Requires Windows CI and PowerShell 7.' }
Set-Location (Resolve-Path (Join-Path $PSScriptRoot '../..'))
function Invoke-Checked([string]$Program, [string[]]$Arguments) {
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Program failed with $LASTEXITCODE" }
}
$powerShell = (Get-Process -Id $PID).Path
Invoke-Checked python @('installer/windows/test_msix_qualification.py')
Invoke-Checked python @('installer/windows/test_consumer_workflow.py')
Invoke-Checked $powerShell @('-NoLogo','-NoProfile','-File','installer/windows/test_consumer_input.ps1')
Invoke-Checked $powerShell @('-NoLogo','-NoProfile','-File','installer/windows/test_consumer_picker.ps1')
Invoke-Checked $powerShell @('-NoLogo','-NoProfile','-File','installer/windows/test_unpacked_profile_lifecycle.ps1')
Invoke-Checked $powerShell @('-NoLogo','-NoProfile','-File','installer/windows/test_qualify_msix_install.ps1')
Invoke-Checked $powerShell @('-NoLogo','-NoProfile','-File','installer/windows/test_registration_ownership.ps1')
Invoke-Checked $powerShell @('-NoLogo','-NoProfile','-File','installer/windows/test_msix_evidence.ps1')
Invoke-Checked $powerShell @('-NoLogo','-NoProfile','-File','installer/windows/test_unpack_evidence.ps1')
Invoke-Checked $powerShell @('-NoLogo','-NoProfile','-File','installer/windows/test_temporary_ownership.ps1')
$sourceCommit = (git rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $sourceCommit -cne $env:GITHUB_SHA) { throw 'Source commit differs from this qualification run.' }
$sdkVersion = '10.0.26100.0'
$sdkDirectory = Join-Path ${env:ProgramFiles(x86)} "Windows Kits\10\bin\$sdkVersion\x64"
$packageOutput = Join-Path $env:RUNNER_TEMP 'pixelquay-msix-package'
Invoke-Checked python @('installer/windows/msix_qualification.py','--release','release','--artwork','branding/pixelquay.png','--source-root','.','--source-commit',$sourceCommit,'--makeappx',(Join-Path $sdkDirectory 'makeappx.exe'),'--sdk-version',$sdkVersion,'--output',$packageOutput)
Invoke-Checked $powerShell @('-NoLogo','-NoProfile','-File','installer/windows/qualify-msix-install.ps1','-Package',(Join-Path $packageOutput 'PixelQuay.Qualification_1.0.0.0_x64.msix'),'-PackageRecord',(Join-Path $packageOutput 'package-record.json'),'-SignTool',(Join-Path $sdkDirectory 'signtool.exe'),'-Output','build-evidence/msix-install')
