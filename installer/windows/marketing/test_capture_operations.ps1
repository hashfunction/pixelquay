# Copyright 2026 Trieflow LLC. MIT. Actual qualified loader plus production registration closures.
param([string]$QualifiedSource=(Join-Path $PSScriptRoot '../../..'))
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'capture_library.ps1') -QualifiedSource $QualifiedSource
foreach($name in @('Get-PixelQuayIdentity','Assert-PixelQuayRecordIdentity','Set-PixelQuayPickerPath','Set-PixelQuayRecipeField','Save-PixelQuayObservation','Get-PixelQuayScopes','Start-PixelQuayConsumerDisplay','Restore-PixelQuayConsumerDisplay','Add-PixelQuayActivationTypes','New-TintCaptureOperations','Invoke-TintCaptureUi','Assert-TintCaptureFrames')){if(-not (Get-Command $name -CommandType Function)){throw "Original helper missing: $name"}}
Add-Type -Path (Join-Path $script:TintQualifiedSource 'installer/windows/consumer_native.cs')
Add-TintCaptureTypes
$global:TintFixture=$null
function global:Get-AppxPackage {param($Name,$ErrorAction)if($Name -cne '1659hashfunction.PixelQuay'){throw 'Unscoped capture query'};return @($global:TintFixture.registrations)}
function global:Add-AppxPackage {param($Path,$ErrorAction)
    $f=$global:TintFixture
    if($f.scenario -ceq 'add-race'){$f.registrations=@($f.owned);throw 'Add failed'}
    if($f.scenario -ceq 'wrong-family'){$f.registrations=@($f.foreign)}else{$f.registrations=@($f.owned)}
}
function global:Remove-AppxPackage {param($Package,$ErrorAction)$global:TintFixture.removed.Add($Package);$global:TintFixture.registrations=@($global:TintFixture.registrations|Where-Object PackageFullName -CNE $Package)}
foreach($scenario in @('normal','add-race','wrong-family','foreign-after-owned')){
    $temp=Join-Path ([IO.Path]::GetTempPath()) ('tint-capture-owned-'+[guid]::NewGuid().ToString('N'));[IO.Directory]::CreateDirectory($temp)|Out-Null
    try{
        $owned=[pscustomobject]@{Name='1659hashfunction.PixelQuay';Publisher='CN=B6A2631A-FD32-45CC-AE12-82466975F528';Version='1.0.1.0';Architecture='X64';PackageFullName='1659hashfunction.PixelQuay_1.0.1.0_x64__r3hxytd7jt6c4';PackageFamilyName='1659hashfunction.PixelQuay_r3hxytd7jt6c4';InstallLocation=$temp}
        $foreign=$owned.PSObject.Copy();$foreign.PackageFullName='1659hashfunction.PixelQuay_1.0.1.0_x64__foreign';$foreign.PackageFamilyName='1659hashfunction.PixelQuay_foreign'
        $global:TintFixture=@{scenario=$scenario;owned=$owned;foreign=$foreign;registrations=@();removed=[Collections.Generic.List[string]]::new()}
        $file=Join-Path $temp 'TintFable.exe';[IO.File]::WriteAllText($file,'actual fixture bytes')
        $record=[pscustomobject]@{payload=[pscustomobject]@{'TintFable.exe'=[pscustomobject]@{bytes=(Get-Item $file).Length;sha256=(Get-FileHash $file -Algorithm SHA256).Hash.ToLowerInvariant()}}}
        $state=@{record=$record;signed='signed-fixture.msix';installAttempted=$false;addCompleted=$false;installedByUs=$false;installed=$null;ownedPackageFullName=$null;residual=@();stopped=$false;processOwned=$false;fixture=$true;receipt=$null}
        $ops=New-TintCaptureOperations $state @{} $temp $temp $temp $temp $script:TintQualifiedSource
        $failed=$false;try{& $ops.Install}catch{$failed=$true}
        if($scenario -cin @('normal','foreign-after-owned')){if($failed -or -not $state.installedByUs){throw 'Exact normal capture registration failed'}}else{if(-not $failed -or $state.installedByUs){throw 'Unowned registration accepted'}}
        if($scenario -ceq 'foreign-after-owned'){$global:TintFixture.registrations+=@($foreign)}
        $cleanupFailed=$false;try{& $ops.RemovePackage}catch{$cleanupFailed=$true}
        if(($scenario -ceq 'normal') -eq $cleanupFailed){throw 'Wrong registration cleanup outcome'}
        if($scenario -cin @('add-race','wrong-family') -and $global:TintFixture.removed.Count){throw 'Unowned registration removed'}
        if($scenario -cin @('normal','foreign-after-owned') -and ($global:TintFixture.removed.Count -ne 1 -or $global:TintFixture.removed[0] -cne $owned.PackageFullName)){throw 'Removal scope changed'}
        foreach($name in @('Stop','RemoveProfileAndDemo')){$failed=$false;try{& $ops[$name]}catch{$failed=$true};if(-not $failed){throw 'Unowned live process allowed cleanup'}}
    }finally{Remove-Item $temp -Recurse -Force}
}
Remove-Item Function:\Get-AppxPackage,Function:\Add-AppxPackage,Function:\Remove-AppxPackage
Remove-Variable TintFixture -Scope Global
Write-Output 'PASS actual qualified loader/native compilation, four capture registration ownership scenarios and unproved-process cleanup refusals.'
