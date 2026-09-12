# Failure-path tests for the real PixelQuay qualification orchestration.
# Copyright 2026 Trieflow LLC. MIT licensed.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'qualify-msix-install.ps1') -LibraryOnly

function Assert-True([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw "ASSERTION FAILED: $Message" }
}

function New-FakeOperations([string]$PrimaryFailure, [string[]]$CleanupFailures, [switch]$Noisy) {
    $global:PixelQuayQualificationTestCalls = [Collections.Generic.List[string]]::new()
    $operations = [ordered]@{}
    foreach ($name in @('Preflight','PrepareConsumerFixture','PrepareSignedCopy','Install','CaptureInstalledStderr','ActivateAndVerify','ConsumerWorkflow','CloseCleanly','UninstallAndVerify')) {
        $operationName = $name
        $operations[$name] = {
            $global:PixelQuayQualificationTestCalls.Add($operationName)
            if ($Noisy) { Write-Output "native stdout:$operationName"; Write-Output ([pscustomobject]@{ unrelated_native_output=$true }) }
            if ($PrimaryFailure -eq $operationName) { throw "primary:$operationName" }
        }.GetNewClosure()
    }
    foreach ($name in @('StopOwnedProcess','RestoreConsumerDisplay','RemoveConsumerFixture','RemoveOwnedPackage','RemoveTrustedCertificate','RemovePersonalCertificate','RemoveTemporaryFiles')) {
        $operationName = $name
        $operations[$name] = {
            $global:PixelQuayQualificationTestCalls.Add($operationName)
            if ($Noisy) { Write-Output "cleanup stdout:$operationName"; Write-Output 7 }
            if ($CleanupFailures -contains $operationName) { throw "cleanup:$operationName" }
        }.GetNewClosure()
    }
    return $operations
}

$result = Invoke-PixelQuayQualificationCore -Operations (New-FakeOperations '' @())
Assert-True $result.installation_qualification_passed 'success path must pass'
Assert-True (-not $result.primary_error) 'success path must have no primary error'
Assert-True ($result.cleanup_errors.Count -eq 0) 'success path must have no cleanup errors'
Assert-True (($global:PixelQuayQualificationTestCalls -join ',') -eq 'Preflight,PrepareConsumerFixture,PrepareSignedCopy,Install,CaptureInstalledStderr,ActivateAndVerify,ConsumerWorkflow,CloseCleanly,UninstallAndVerify,StopOwnedProcess,RestoreConsumerDisplay,RemoveConsumerFixture,RemoveOwnedPackage,RemoveTrustedCertificate,RemovePersonalCertificate,RemoveTemporaryFiles') 'all qualification and cleanup steps must run in order'

$result = Invoke-PixelQuayQualificationCore -Operations (New-FakeOperations 'ActivateAndVerify' @('RemoveOwnedPackage','RemovePersonalCertificate'))
Assert-True (-not $result.installation_qualification_passed) 'primary and cleanup failure must fail'
Assert-True ($result.primary_error -eq 'primary:ActivateAndVerify') 'primary failure must be retained exactly'
Assert-True ($result.cleanup_errors.Count -eq 2) 'all cleanup failures must be retained'
Assert-True (($result.cleanup_errors -join '|') -match 'RemoveOwnedPackage.*RemovePersonalCertificate') 'cleanup failures must identify their operations'
Assert-True (-not ($global:PixelQuayQualificationTestCalls -contains 'CloseCleanly')) 'later primary operations must not run after failure'
foreach ($cleanup in @('StopOwnedProcess','RestoreConsumerDisplay','RemoveConsumerFixture','RemoveOwnedPackage','RemoveTrustedCertificate','RemovePersonalCertificate','RemoveTemporaryFiles')) {
    Assert-True ($global:PixelQuayQualificationTestCalls -contains $cleanup) "cleanup operation $cleanup must still run"
}

$result = Invoke-PixelQuayQualificationCore -Operations (New-FakeOperations '' @('RemoveTrustedCertificate'))
Assert-True (-not $result.installation_qualification_passed) 'cleanup failure alone must fail qualification'
Assert-True (-not $result.primary_error) 'cleanup-only failure must not manufacture a primary failure'
Assert-True ($result.cleanup_errors.Count -eq 1) 'cleanup-only failure must be recorded'

$result = Invoke-PixelQuayQualificationCore -Operations (New-FakeOperations 'Preflight' @())
Assert-True (-not $result.installation_qualification_passed) 'preexisting-install/preflight failure must fail qualification'
Assert-True (($global:PixelQuayQualificationTestCalls -join ',') -eq 'Preflight,StopOwnedProcess,RestoreConsumerDisplay,RemoveConsumerFixture,RemoveOwnedPackage,RemoveTrustedCertificate,RemovePersonalCertificate,RemoveTemporaryFiles') 'preflight failure must skip mutation and still execute safe cleanup adapters'

$result = @(Invoke-PixelQuayQualificationCore -Operations (New-FakeOperations '' @() -Noisy))
Assert-True ($result.Count -eq 1) 'native stdout must not contaminate the one structured result'
Assert-True $result[0].installation_qualification_passed 'noisy success must retain its success result'
$result = @(Invoke-PixelQuayQualificationCore -Operations (New-FakeOperations 'ActivateAndVerify' @('RemovePersonalCertificate') -Noisy))
Assert-True ($result.Count -eq 1) 'noisy failure must retain only one structured result'
Assert-True (-not $result[0].installation_qualification_passed) 'noisy failure cannot pass'
Assert-True ($result[0].primary_error -eq 'primary:ActivateAndVerify') 'native stdout must not erase primary failure'
Assert-True ($result[0].cleanup_errors.Count -eq 1) 'native stdout must not erase cleanup failure'

$packageRoot = Join-Path ([IO.Path]::GetTempPath()) 'package'
$insidePackage = Test-PathInside -Candidate (Join-Path $packageRoot 'bin/TintFable.exe') -Root $packageRoot
$siblingPackage = Test-PathInside -Candidate (Join-Path ([IO.Path]::GetTempPath()) 'package-other/foreign.dll') -Root $packageRoot
Assert-True $insidePackage 'exact package descendant must be accepted'
Assert-True (-not $siblingPackage) 'textual sibling prefix must not count as package path'
$recordFixture = [pscustomobject]@{ payload = [pscustomobject]@{ 'bin/TintFable.exe' = [pscustomobject]@{ bytes=1; sha256=('a' * 64) } } }
Assert-True ((Get-RecordPayloadEntry $recordFixture 'bin/TintFable.exe').bytes -eq 1) 'slash-qualified payload property must resolve exactly'
$exclusiveDirectory = Join-Path ([IO.Path]::GetTempPath()) ('pixelquay-ps-test-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $exclusiveDirectory | Out-Null
try {
    $exclusiveFile = Join-Path $exclusiveDirectory 'evidence.json'
    Write-NewUtf8Json $exclusiveFile ([ordered]@{ passed=$false })
    try { Write-NewUtf8Json $exclusiveFile ([ordered]@{ passed=$true }); throw 'expected exclusive write failure' }
    catch { Assert-True ($_.Exception.Message -notmatch 'expected exclusive') 'evidence writer must refuse replacement' }
    Assert-True ((Get-Content -LiteralPath $exclusiveFile -Raw | ConvertFrom-Json).passed -eq $false) 'failed replacement must preserve evidence bytes'
} finally {
    Remove-Item -LiteralPath $exclusiveDirectory -Recurse -Force
}
Add-PixelQuayActivationTypes
Assert-True ($null -ne ('PixelQuayQualification.NativePackageProbe' -as [type])) 'GetPackageFullName helper types must compile'

Remove-Variable PixelQuayQualificationTestCalls -Scope Global


$result=Invoke-PixelQuayQualificationCore -Operations (New-FakeOperations 'ConsumerWorkflow' @('RemoveConsumerFixture'))
Assert-True (-not $result.installation_qualification_passed) 'consumer and fixture-cleanup failures must fail qualification'
Assert-True ($result.primary_error -ceq 'primary:ConsumerWorkflow') 'consumer failure must remain primary'
Assert-True (-not ($global:PixelQuayQualificationTestCalls -contains 'CloseCleanly')) 'consumer failure cannot certify normal close'
Assert-True (($global:PixelQuayQualificationTestCalls.IndexOf('StopOwnedProcess')) -lt ($global:PixelQuayQualificationTestCalls.IndexOf('RemoveConsumerFixture'))) 'process stop must precede fixture cleanup'

$operations=New-FakeOperations 'ConsumerWorkflow' @()
$operations.RestoreConsumerDisplay={ $global:PixelQuayQualificationTestCalls.Add('RestoreConsumerDisplay');throw 'restore failed' }
$result=Invoke-PixelQuayQualificationCore -Operations $operations
Assert-True ($result.primary_error -ceq 'primary:ConsumerWorkflow') 'display restoration must retain the consumer failure'
Assert-True (($result.cleanup_errors -join ',') -match 'RestoreConsumerDisplay.*restore failed') 'display restoration failure must independently fail qualification'
Assert-True ($global:PixelQuayQualificationTestCalls.IndexOf('RestoreConsumerDisplay') -gt $global:PixelQuayQualificationTestCalls.IndexOf('StopOwnedProcess')) 'display restore must run after owned process cleanup'
Assert-True ($global:PixelQuayQualificationTestCalls -contains 'RemoveTemporaryFiles') 'restoration failure must not skip other cleanup'
$operations=New-FakeOperations '' @()
$operations.Remove('RestoreConsumerDisplay')
$failed=$false;try{Invoke-PixelQuayQualificationCore -Operations $operations}catch{$failed=$_.Exception.Message -match 'Missing qualification operation: RestoreConsumerDisplay'}
Assert-True ($failed -and $global:PixelQuayQualificationTestCalls.Count -eq 0) 'missing restoration adapter must refuse before any operation'
Write-Output 'PASS: 9 installation orchestration scenarios plus path/evidence/native-helper checks.'

# Execute the production UI-finally block: its real CreateNew writer freezes
# workflow-time evidence before the outer owner restores the original display.
$tokens=$null;$parseErrors=$null
$tree=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot 'consumer_ui.ps1'),[ref]$tokens,[ref]$parseErrors)
Assert-True ($parseErrors.Count -eq 0) 'consumer source must parse'
$consumer=$tree.Find({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -ceq 'Invoke-PixelQuayConsumerWorkflow'},$true)
$outerTry=@($consumer.Body.EndBlock.Statements | Where-Object {$_ -is [Management.Automation.Language.TryStatementAst]})
Assert-True ($outerTry.Count -eq 1) 'expected exact production consumer try/finally'
$text=$outerTry[0].Finally.Extent.Text
$finalizeConsumer=[scriptblock]::Create($text.Substring(1,$text.Length-2))
$actualDisplay=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'test-fixtures/store-export/34690127749-display-lifecycle.json') -Raw | ConvertFrom-Json -AsHashtable
$snapshotDirectory=Join-Path ([IO.Path]::GetTempPath()) ('pixelquay-evidence-test-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $snapshotDirectory | Out-Null
try {
    foreach($restoreFails in @($false,$true)) {
        $Output=Join-Path $snapshotDirectory ([string]$restoreFails)
        New-Item -ItemType Directory -Path $Output | Out-Null
        $DisplayState=@{displayEvidence=($actualDisplay.workflow_native_display | ConvertTo-Json -Depth 20 | ConvertFrom-Json -AsHashtable);
            displayDevice=$actualDisplay.workflow_native_display.device;displayOriginalMode=@{dmPelsWidth=1024;dmPelsHeight=768;dmBitsPerPel=32;dmDisplayFrequency=64;dmDisplayOrientation=0;dmDisplayFlags=0};displayRestoreRequired=$true}
        $broker=[IO.MemoryStream]::new()
        $ui=@{record=@{schema='pixelquay-consumer-workflow-v1';observations=@();ui_actions_completed=(-not $restoreFails)};brokers=@{owned=$broker}}
        if($restoreFails){$ui.record.error='original consumer failure'}
        & $finalizeConsumer
        Assert-True (-not $broker.CanRead) 'finalizer must still dispose retained broker adapters'
        $path=Join-Path $Output 'consumer-workflow.json'
        $originalBytes=[IO.File]::ReadAllBytes($path)
        $standalone=Get-Content -LiteralPath $path -Raw | ConvertFrom-Json -AsHashtable
        Assert-True (($standalone.native_display | ConvertTo-Json -Depth 20 -Compress) -ceq ($actualDisplay.workflow_native_display | ConvertTo-Json -Depth 20 -Compress)) 'workflow snapshot differs from actual observed pre-restore record'
        function Set-PixelQuayConsumerDisplayMode {param($Device,$Mode,$Flags);if($restoreFails){return -2};return 0}
        function Get-PixelQuayConsumerDisplayState {param($Device);return @{current=$DisplayState.displayOriginalMode}}
        $restoreError=$null
        try {Restore-PixelQuayConsumerDisplay $DisplayState}catch{$restoreError=$_.Exception.Message}
        Assert-True (($null -ne $restoreError) -eq $restoreFails) 'production restoration result differs'
        $embedded=@{consumer_workflow=$ui.record;consumer_native_display=$DisplayState.displayEvidence}
        Write-NewUtf8Json (Join-Path $Output 'installation.json') $embedded
        $serialized=Get-Content -LiteralPath (Join-Path $Output 'installation.json') -Raw | ConvertFrom-Json -AsHashtable
        Assert-True (($serialized.consumer_workflow | ConvertTo-Json -Depth 20 -Compress) -ceq ($standalone | ConvertTo-Json -Depth 20 -Compress)) 'Standalone and installed consumer evidence differ after actual restoration mutation'
        Assert-True ([Convert]::ToBase64String([IO.File]::ReadAllBytes($path)) -ceq [Convert]::ToBase64String($originalBytes)) 'workflow evidence bytes were replaced during restoration'
        if($restoreFails) {
            Assert-True ($serialized.consumer_workflow.error -ceq 'original consumer failure' -and -not $serialized.consumer_workflow.ui_actions_completed -and
                -not $serialized.consumer_native_display.restore_verified -and $serialized.consumer_native_display.restore_result -eq -2) 'snapshot changed primary failure or manufactured restoration success'
        } else {
            Assert-True (($serialized.consumer_native_display | ConvertTo-Json -Depth 20 -Compress) -ceq ($actualDisplay.installation_native_display | ConvertTo-Json -Depth 20 -Compress)) 'final independent display evidence differs from actual restored record'
        }
        # A nested mode list must also be independent, not just a shallow copy.
        $DisplayState.displayEvidence.supported_modes[0].width=999
        Assert-True ($ui.record.native_display.supported_modes[0].width -eq 640) 'workflow snapshot still aliases nested native display state'
    }
} finally {
    Remove-Item -LiteralPath $snapshotDirectory -Recurse -Force
}
Write-Output 'PASS: production finalizer preserves exact workflow snapshot through successful and failed display restoration; final restoration evidence and original failure remain independent.'
