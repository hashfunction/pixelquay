# Package and qualify both identities before retaining an unsigned Store package. Copyright 2026 Trieflow LLC, MIT.
param([switch]$LibraryOnly)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
function Invoke-Checked([string]$Program, [string[]]$Arguments) {
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Program failed with $LASTEXITCODE" }
}
function Invoke-TintFablePackageRelease([string]$PowerShell,[string]$SourceCommit,[string]$SdkDirectory,[string]$TemporaryRoot,[string]$Evidence='build-evidence') {
    $packages=@{}
    foreach($mode in @('qualification','store')) {
        $directory=Join-Path $TemporaryRoot $(if($mode -ceq 'store'){'tintfable-msix-store-package'}else{'tintfable-msix-package'})
        $filename=if($mode -ceq 'store'){'TintFable_1.0.1.0_x64.msix'}else{'TintFable.Qualification_1.0.1.0_x64.msix'}
        $recordName=if($mode -ceq 'store'){'msix-store-package-record.json'}else{'msix-package-record.json'}
        $installName=if($mode -ceq 'store'){'msix-store-install'}else{'msix-install'}
        Invoke-Checked python @('installer/windows/msix_qualification.py','--release','release','--artwork','branding/tintfable.png','--source-root','.','--source-commit',$SourceCommit,'--makeappx',(Join-Path $SdkDirectory 'makeappx.exe'),'--sdk-version','10.0.26100.0','--output',$directory,'--identity-mode',$mode)
        $record=Join-Path $directory 'package-record.json'
        $recordDestination=Join-Path $Evidence $recordName
        if(Test-Path -LiteralPath $recordDestination){throw 'Existing package evidence must not be replaced'}
        Copy-Item -LiteralPath $record -Destination $recordDestination -ErrorAction Stop
        $packages[$mode]=Join-Path $directory $filename
        Invoke-Checked $PowerShell @('-NoLogo','-NoProfile','-File','installer/windows/qualify-msix-install.ps1','-Package',$packages[$mode],'-PackageRecord',$record,'-SignTool',(Join-Path $SdkDirectory 'signtool.exe'),'-Output',(Join-Path $Evidence $installName),'-IdentityMode',$mode)
    }
    Invoke-Checked python @('installer/windows/store_export.py','--source-root','.','--evidence',$Evidence,'--qualification-package',$packages.qualification,'--store-package',$packages.store,'--output',(Join-Path $Evidence 'store-upload'))
}
if ($LibraryOnly) {return}
if (-not $IsWindows -or $env:CI -ne 'true' -or $PSVersionTable.PSVersion.Major -lt 7) { throw 'Requires Windows CI and PowerShell 7.' }
Set-Location (Resolve-Path (Join-Path $PSScriptRoot '../..'))
$powerShell = (Get-Process -Id $PID).Path
Invoke-Checked python @('installer/windows/test_msix_qualification.py')
Invoke-Checked python @('installer/windows/test_store_identity.py')
Invoke-Checked python @('installer/windows/test_store_export.py')
Invoke-Checked $powerShell @('-NoLogo','-NoProfile','-File','installer/windows/test_store_orchestration.ps1')
Invoke-Checked python @('installer/windows/test_consumer_workflow.py')
Invoke-Checked $powerShell @('-NoLogo','-NoProfile','-File','installer/windows/test_consumer_input.ps1')
Invoke-Checked $powerShell @('-NoLogo','-NoProfile','-File','installer/windows/test_consumer_geometry.ps1')
Invoke-Checked $powerShell @('-NoLogo','-NoProfile','-File','installer/windows/test_consumer_geometry_record.ps1')
Invoke-Checked $powerShell @('-NoLogo','-NoProfile','-File','installer/windows/test_consumer_display.ps1')
Invoke-Checked $powerShell @('-NoLogo','-NoProfile','-File','installer/windows/test_consumer_picker.ps1')
Invoke-Checked $powerShell @('-NoLogo','-NoProfile','-File','installer/windows/test_consumer_native_picker.ps1')
Invoke-Checked $powerShell @('-NoLogo','-NoProfile','-File','installer/windows/test_unpacked_profile_lifecycle.ps1')
Invoke-Checked $powerShell @('-NoLogo','-NoProfile','-File','installer/windows/test_qualify_msix_install.ps1')
Invoke-Checked $powerShell @('-NoLogo','-NoProfile','-File','installer/windows/test_registration_ownership.ps1')
Invoke-Checked $powerShell @('-NoLogo','-NoProfile','-File','installer/windows/test_registration_ownership.ps1','-IdentityMode','store')
Invoke-Checked $powerShell @('-NoLogo','-NoProfile','-File','installer/windows/test_msix_evidence.ps1')
Invoke-Checked $powerShell @('-NoLogo','-NoProfile','-File','installer/windows/test_unpack_evidence.ps1')
Invoke-Checked $powerShell @('-NoLogo','-NoProfile','-File','installer/windows/test_unpack_evidence.ps1','-IdentityMode','store')
Invoke-Checked $powerShell @('-NoLogo','-NoProfile','-File','installer/windows/test_temporary_ownership.ps1')
$sourceCommit = (git rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $sourceCommit -cne $env:GITHUB_SHA) { throw 'Source commit differs from this qualification run.' }
$sdkVersion = '10.0.26100.0'
$sdkDirectory = Join-Path ${env:ProgramFiles(x86)} "Windows Kits\10\bin\$sdkVersion\x64"
Invoke-TintFablePackageRelease $powerShell $sourceCommit $sdkDirectory $env:RUNNER_TEMP
