# Copyright 2026 Trieflow LLC. MIT. Separate capture lifecycle; no new qualification claim.
param([Parameter(Mandatory)][string]$Inputs,[Parameter(Mandatory)][string]$QualifiedSource,[Parameter(Mandatory)][string]$CaptureOutput)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
if(-not $IsWindows -or $env:CI -cne 'true' -or $env:GITHUB_REPOSITORY -cne 'hashfunction/pixelquay'){throw 'Native TintFable capture requires isolated Windows CI'}
. (Join-Path $PSScriptRoot 'capture_library.ps1') -QualifiedSource $QualifiedSource
Import-Module Appx -UseWindowsPowerShell -ErrorAction Stop
$inputRoot=(Resolve-Path -LiteralPath $Inputs).Path
Invoke-CheckedNative python @((Join-Path $PSScriptRoot 'capture_checks.py'),'--inputs',$inputRoot,'--qualified-source',$script:TintQualifiedSource)
$bound=(Get-Content -LiteralPath (Join-Path $PSScriptRoot 'binding.json') -Raw|ConvertFrom-Json).qualified
$output=[IO.Path]::GetFullPath($CaptureOutput)
if(Test-Path -LiteralPath $output){throw 'Existing capture output preserved'}
$recordMatches=@(Get-ChildItem -LiteralPath (Join-Path $inputRoot 'metadata') -Recurse -File -Filter 'msix-store-package-record.json')
if($recordMatches.Count -ne 1){throw 'Original Store record missing/ambiguous'}
$record=Get-Content -LiteralPath $recordMatches[0].FullName -Raw|ConvertFrom-Json
Assert-PixelQuayRecordIdentity $record 'store';Assert-PixelQuayUnpackEvidence $record
$state=@{record=$record;package=(Join-Path $inputRoot 'store/TintFable_1.0.1.0_x64.msix');installed=$null;ownedPackageFullName=$null;installedByUs=$false;
    installAttempted=$false;addCompleted=$false;temporary=$null;certificate=$null;trustAttempted=$false;process=$null;processOwned=$false;brokerPid=0;stopped=$true;
    processExit=$null;cleanupExit=$null;normalClose=$false;uninstallVerified=$false;fixture=$null;fixtureRemoved=$false;receipt=$null;ui=$null;unsignedUnchanged=$false;framesVerified=$false;
    output=$output;statePath=(Join-Path $output 'capture-fixture-state.json');residual=@();displayOriginalMode=$null;displayDevice=$null;displayRestoreRequired=$false;displayEvidence=$null}
$fullName='1659hashfunction.PixelQuay_1.0.1.0_x64__r3hxytd7jt6c4'
$profile=Join-Path ([Environment]::GetFolderPath('ApplicationData')) 'PixelQuay';$demo='C:\TintFable Demo'
$operations=New-TintCaptureOperations $state $bound $inputRoot $profile $demo $output $script:TintQualifiedSource
$result=Invoke-TintCaptureLifecycle $operations
if($state.ui){
    if($result.primary_error){$state.ui.record.error=$result.primary_error}
    Write-NewUtf8Json (Join-Path $output 'capture-workflow.json') $state.ui.record
    foreach($broker in $state.ui.brokers.Values){$broker.Dispose()}
}
try{$null=Assert-FileMatchesRecord $state.package $bound.package 'Original unsigned after capture';$state.unsignedUnchanged=$true}catch{$result.cleanup_errors+=('Unsigned original: '+$_.Exception.Message)}
$captured=(-not $result.primary_error -and $result.cleanup_errors.Count -eq 0 -and $state.framesVerified -and $state.normalClose -and $state.uninstallVerified -and $state.fixtureRemoved -and $state.unsignedUnchanged -and $state.displayEvidence.restore_verified)
if(Test-Path -LiteralPath $output){Write-NewUtf8Json (Join-Path $output 'capture-result.json') @{schema_version=1;purpose='real marketing screenshots only';captured=$captured;consumer_acceptance=$false;installation_qualification_claimed=$false;product_binary_changed=$false;submission_changed=$false;
    capture_source_commit=$env:GITHUB_SHA;capture_run_id=$env:GITHUB_RUN_ID;capture_run_attempt=$env:GITHUB_RUN_ATTEMPT;qualified=$bound;
    package_full_name=$state.ownedPackageFullName;original_unsigned_unchanged=$state.unsignedUnchanged;certificate_private_key_exported=$false;
    screenshots_verified=$state.framesVerified;normal_close_verified=$state.normalClose;process_exit_code=$state.processExit;cleanup_exit_code=$state.cleanupExit;uninstall_verified=$state.uninstallVerified;
    owned_profile_and_demo_removed=$state.fixtureRemoved;display=$state.displayEvidence;residual_package_full_names=$state.residual;primary_error=$result.primary_error;cleanup_errors=$result.cleanup_errors}}
if($state.process){$state.process.Dispose()}
if(-not $captured){throw "TintFable native capture incomplete: $($result.primary_error); cleanup: $($result.cleanup_errors -join '; ')"}
Write-Output 'Captured three real TintFable screens; normal close, uninstall, profile/demo cleanup and original unsigned integrity verified.'
