# Copyright 2026 Trieflow LLC. MIT licensed.
# Exercise the real PixelQuay Install, UninstallAndVerify, and RemoveOwnedPackage
# closures. Only AppX cmdlets and unrelated Windows/UI operations are adapted.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'qualify-msix-install.ps1') -LibraryOnly
$script:ActualCore = ${function:Invoke-PixelQuayQualificationCore}
$global:PixelQuayRegistrationFixture = $null

function global:Get-AppxPackage {
    [CmdletBinding()] param([string]$Name)
    if ($Name -cne 'Trieflow.PixelQuay.Qualification') { throw 'Unscoped package query' }
    $fixture = $global:PixelQuayRegistrationFixture
    if ($fixture.observationFailure) {
        $fixture.observationFailure = $false
        throw 'registration observation failed'
    }
    return @($fixture.registrations)
}

function global:Add-AppxPackage {
    [CmdletBinding()] param([string]$Path)
    $fixture = $global:PixelQuayRegistrationFixture
    if ($Path -cne 'owned-pixelquay-test-copy.msix') { throw 'Wrong signed package path' }
    switch ($fixture.scenario) {
        'failed-add-race' { $fixture.registrations = @($fixture.raced); throw 'Add failed after another registration appeared' }
        'ambiguous-add' { $fixture.registrations = @($fixture.owned, $fixture.foreign) }
        'wrong-architecture' { $fixture.registrations = @($fixture.foreign) }
        'missing-add' { $fixture.registrations = @() }
        'observation-failed' { $fixture.registrations = @($fixture.owned); $fixture.observationFailure = $true }
        default { $fixture.registrations = @($fixture.owned) }
    }
    Write-Output 'native Add-AppxPackage output'
}

function global:Remove-AppxPackage {
    [CmdletBinding()] param([string]$Package)
    $fixture = $global:PixelQuayRegistrationFixture
    $fixture.removed.Add($Package)
    if ($fixture.scenario -eq 'remove-failed') { throw 'owned removal failed' }
    $fixture.registrations = @($fixture.registrations | Where-Object PackageFullName -CNE $Package)
    Write-Output 'native Remove-AppxPackage output'
}

function Invoke-PixelQuayQualificationCore([Collections.IDictionary]$Operations) {
    $fixture = $global:PixelQuayRegistrationFixture
    $state = $Operations.Preflight.Module.SessionState.PSVariable.GetValue('state')
    $state.output = $fixture.directory
    $state.package = Join-Path $fixture.directory 'source.msix'
    [IO.File]::WriteAllText($state.package, 'original unsigned bytes')
    $state.unsignedPackageSha256 = (Get-FileHash $state.package -Algorithm SHA256).Hash.ToLowerInvariant()
    $state.signedCopy = 'owned-pixelquay-test-copy.msix'
    $state.preflightPackageFullNames = @()
    $payload = [ordered]@{}
    foreach ($relative in @('bin/PixelQuay.exe','bin/coreclr.dll','bin/hostfxr.dll','bin/PixelQuay.runtimeconfig.json')) {
        $path = Join-Path $fixture.directory ($relative -replace '/', [IO.Path]::DirectorySeparatorChar)
        New-Item -ItemType Directory -Path (Split-Path $path -Parent) -Force | Out-Null
        [IO.File]::WriteAllText($path, "fixture:$relative")
        $payload[$relative] = [pscustomobject]@{
            bytes = (Get-Item -LiteralPath $path).Length
            sha256 = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
        }
    }
    $state.record = [pscustomobject]@{ sourceCommit = ('a' * 40); payload = [pscustomobject]$payload }
    $Operations.Preflight = { if (@(Get-AppxPackage -Name 'Trieflow.PixelQuay.Qualification').Count) { throw 'Fixture must start empty' } }
    foreach ($name in @('PrepareSignedCopy','CaptureInstalledStderr','ActivateAndVerify','CloseCleanly','StopOwnedProcess','RemoveTrustedCertificate','RemovePersonalCertificate','RemoveTemporaryFiles')) {
        $Operations[$name] = {}
    }
    if ($fixture.scenario -in @('normal-owned','normal-with-foreign')) {
        $Operations.CloseCleanly = {
            if ($global:PixelQuayRegistrationFixture.scenario -eq 'normal-with-foreign') {
                $global:PixelQuayRegistrationFixture.registrations += $global:PixelQuayRegistrationFixture.foreign
            }
        }
    } else {
        $Operations.UninstallAndVerify = {}
        $Operations.CloseCleanly = {
            if ($global:PixelQuayRegistrationFixture.scenario -eq 'owned-with-foreign') {
                $global:PixelQuayRegistrationFixture.registrations += $global:PixelQuayRegistrationFixture.foreign
            }
        }
    }
    return & $script:ActualCore $Operations
}

foreach ($scenario in @('failed-add-race','ambiguous-add','wrong-architecture','missing-add','observation-failed','owned','owned-with-foreign','remove-failed','normal-owned','normal-with-foreign')) {
    $temporary = Join-Path ([IO.Path]::GetTempPath()) ('pixelquay-registration-test-' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $temporary | Out-Null
    try {
        $owned = [pscustomobject]@{
            Name='Trieflow.PixelQuay.Qualification'; Publisher='CN=PixelQuay-CI-Qualification'; Version='1.0.0.0'; Architecture='X64'
            PackageFullName='Trieflow.PixelQuay.Qualification_1.0.0.0_x64__fixture'; PackageFamilyName='Trieflow.PixelQuay.Qualification_fixture'; InstallLocation=$temporary
        }
        $foreign = [pscustomobject]@{
            Name=$owned.Name; Publisher=$owned.Publisher; Version=$owned.Version; Architecture='Arm64'
            PackageFullName='Trieflow.PixelQuay.Qualification_1.0.0.0_arm64__fixture'; PackageFamilyName=$owned.PackageFamilyName; InstallLocation=$temporary
        }
        # The racing registration has the exact qualification tuple and full name.
        # A tuple match cannot establish ownership after our Add failed.
        $raced = $owned.PSObject.Copy()
        $global:PixelQuayRegistrationFixture = [ordered]@{
            scenario=$scenario; directory=$temporary; owned=$owned; foreign=$foreign; raced=$raced
            registrations=@(); removed=[Collections.Generic.List[string]]::new(); observationFailure=$false
        }
        $failure = $null
        try { Invoke-PixelQuayInstallQualification unused unused unused $temporary | Out-Null } catch { $failure = $_.Exception.Message }
        $fixture = $global:PixelQuayRegistrationFixture
        $evidence = Get-Content (Join-Path $temporary 'installation-qualification.json') -Raw | ConvertFrom-Json
        if ($scenario -in @('failed-add-race','ambiguous-add','wrong-architecture','missing-add','observation-failed')) {
            if ($fixture.removed.Count) { throw "${scenario}: unowned or ambiguous registration was removed" }
            if ($scenario -ne 'missing-add' -and -not $fixture.registrations.Count) { throw "${scenario}: preserved registration disappeared" }
            if (-not $failure -or $evidence.installation_qualification_passed -or -not $evidence.primary_error) { throw "${scenario}: original failure was lost" }
            if ($evidence.cleanup_errors.Count -ne 1 -or $evidence.cleanup_errors[0] -notmatch 'preserved|cannot be ruled out') { throw "${scenario}: unresolved registration was not reported" }
            if ($evidence.registration_ownership_established -or $evidence.owned_package_full_name) { throw "${scenario}: registration ownership was falsely claimed" }
        } else {
            if ($fixture.removed.Count -ne 1 -or $fixture.removed[0] -cne $owned.PackageFullName) { throw "${scenario}: removal was not limited to exact owned PackageFullName" }
            if (-not $evidence.registration_ownership_established -or $evidence.owned_package_full_name -cne $owned.PackageFullName) { throw "${scenario}: exact established ownership is missing" }
            if ($scenario -in @('owned','normal-owned')) {
                if ($failure -or -not $evidence.installation_qualification_passed -or $fixture.registrations.Count) { throw "${scenario}: owned registration success control failed" }
                if ($scenario -eq 'normal-owned' -and -not $evidence.uninstall_verified) { throw 'Normal uninstall did not execute' }
            } else {
                if (-not $failure -or $evidence.installation_qualification_passed -or -not $fixture.registrations.Count -or $evidence.cleanup_errors.Count -ne 1) { throw "${scenario}: residue/removal failure must fail and retain evidence" }
            }
        }
        Write-Output "PASS actual PixelQuay registration ownership flow: $scenario"
    } finally {
        Remove-Item -LiteralPath $temporary -Recurse -Force
    }
}

Remove-Item Function:\Get-AppxPackage,Function:\Add-AppxPackage,Function:\Remove-AppxPackage
Remove-Variable PixelQuayRegistrationFixture -Scope Global
