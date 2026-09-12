# Copyright 2026 Trieflow LLC. MIT. Actual capture operations, independently replayable.
function New-TintCaptureOperations($State,$Bound,[string]$InputRoot,[string]$Profile,[string]$Demo,[string]$Output,[string]$QualifiedSource) {
$record=$State.record;$fullName='1659hashfunction.PixelQuay_1.0.1.0_x64__r3hxytd7jt6c4'
$operations=[ordered]@{
 Preflight={
    foreach($path in @($profile,$demo)){if(Test-Path -LiteralPath $path){throw 'Existing demo or compatibility profile preserved'}}
    if(@(Get-AppxPackage -Name '1659hashfunction.PixelQuay' -ErrorAction Stop).Count){throw 'Existing assigned Store registration preserved'}
    New-Item -ItemType Directory -Path $state.output -ErrorAction Stop|Out-Null
    [IO.File]::Copy((Join-Path $inputRoot 'capture-inputs.json'),(Join-Path $output 'capture-inputs.json'),$false)
 }.GetNewClosure()
 Prepare={
    Add-Type -Path (Join-Path $QualifiedSource 'installer/windows/consumer_native.cs')
    Add-Type -AssemblyName UIAutomationClient,UIAutomationTypes,System.Drawing
    $state.fixture=Invoke-TintCaptureFiles create $state.statePath @('--root',$demo,'--profile',$profile)
    Start-PixelQuayConsumerDisplay $state
    $after=$state.displayEvidence.after
    if($after.width -lt 1920 -or $after.height -lt 1080){throw 'Actual capture display is below 1920 by 1080'}
    $candidate=Join-Path $env:RUNNER_TEMP ('.tintfable-capture-'+[guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $candidate -ErrorAction Stop|Out-Null;$state.temporary=$candidate
 }.GetNewClosure()
 Sign={
    $state.signed=Join-Path $state.temporary 'TintFable.capture.signed.msix';[IO.File]::Copy($state.package,$state.signed,$false)
    $state.certificate=New-SelfSignedCertificate -Type Custom -KeyUsage DigitalSignature -KeyExportPolicy NonExportable -KeySpec Signature -CertStoreLocation 'Cert:\CurrentUser\My' -TextExtension @('2.5.29.37={text}1.3.6.1.5.5.7.3.3','2.5.29.19={text}') -Subject 'CN=B6A2631A-FD32-45CC-AE12-82466975F528' -FriendlyName 'TintFable temporary marketing capture' -NotAfter (Get-Date).AddHours(2)
    $public=Join-Path $state.temporary 'capture-public.cer';Export-Certificate -Cert $state.certificate -FilePath $public|Out-Null
    $state.trustAttempted=$true;Import-Certificate -FilePath $public -CertStoreLocation 'Cert:\LocalMachine\TrustedPeople'|Out-Null
    $tool=Join-Path ${env:ProgramFiles(x86)} 'Windows Kits/10/bin/10.0.26100.0/x64/signtool.exe';$toolHash=(Get-FileHash $tool -Algorithm SHA256).Hash
    Invoke-CheckedNative $tool @('sign','/fd','SHA256','/sha1',$state.certificate.Thumbprint,'/s','My',$state.signed)
    Invoke-CheckedNative $tool @('verify','/pa','/all','/v',$state.signed)
    $signature=Get-AuthenticodeSignature -LiteralPath $state.signed
    if($signature.Status -ne [Management.Automation.SignatureStatus]::Valid -or $signature.SignerCertificate.Thumbprint -cne $state.certificate.Thumbprint -or
       (Get-FileHash $tool -Algorithm SHA256).Hash -cne $toolHash){throw 'Capture signed-copy certificate or signing tool changed'}
    $null=Assert-FileMatchesRecord $state.package $bound.package 'Unchanged original Store package'
 }.GetNewClosure()
 Install={
    $state.installAttempted=$true;Add-AppxPackage -Path $state.signed -ErrorAction Stop;$state.addCompleted=$true
    $matches=@(Get-AppxPackage -Name '1659hashfunction.PixelQuay' -ErrorAction Stop)
    if($matches.Count -ne 1 -or $matches[0].Name -cne '1659hashfunction.PixelQuay' -or $matches[0].Publisher -cne 'CN=B6A2631A-FD32-45CC-AE12-82466975F528' -or
       [string]$matches[0].Version -cne '1.0.1.0' -or [string]$matches[0].Architecture -cne 'X64' -or $matches[0].PackageFullName -cne $fullName -or
       $matches[0].PackageFamilyName -cne '1659hashfunction.PixelQuay_r3hxytd7jt6c4'){throw 'Installed capture identity differs; ownership not established'}
    $state.installed=$matches[0];$state.ownedPackageFullName=$fullName;$state.installedByUs=$true
    foreach($row in $record.payload.PSObject.Properties){$null=Assert-FileMatchesRecord (Join-Path $state.installed.InstallLocation $row.Name) $row.Value 'Installed unchanged payload'}
 }.GetNewClosure()
 Activate={
    Add-PixelQuayActivationTypes;$state.stopped=$false
    $state.brokerPid=[int][PixelQuayQualification.ActivationBroker]::Activate('1659hashfunction.PixelQuay_r3hxytd7jt6c4!PixelQuay')
    $state.process=[Diagnostics.Process]::GetProcessById($state.brokerPid);$null=$state.process.SafeHandle
    Assert-TintCaptureProcess $state;$state.processOwned=$true
    $deadline=[DateTime]::UtcNow.AddSeconds(30)
    do{$state.process.Refresh();if($state.process.HasExited){throw 'Capture process exited during startup'};Start-Sleep -Milliseconds 100}until($state.process.MainWindowHandle -ne 0 -or [DateTime]::UtcNow -ge $deadline)
    if($state.process.MainWindowHandle -eq 0){throw 'Actual editor main window unavailable'}
    Write-NewUtf8Json (Join-Path $output 'loaded-modules.json') (Get-TintCaptureModules $state)
    $state.ui=@{state=$state;process=$state.process;main=[long]$state.process.MainWindowHandle;brokers=@{};output=$output;
       record=@{purpose='marketing capture only';consumer_acceptance=$false;geometry=[Collections.Generic.List[object]]::new();picker_fields=[Collections.Generic.List[object]]::new();picker_trees=[Collections.Generic.List[object]]::new();observations=[Collections.Generic.List[object]]::new()}}
 }.GetNewClosure()
 Workflow={Invoke-TintCaptureUi $state.ui $state.statePath;Assert-TintCaptureFrames $state;Write-NewUtf8Json (Join-Path $output 'loaded-modules-after-capture.json') (Get-TintCaptureModules $state)}.GetNewClosure()
 ObserveFailure={Save-TintCaptureFailure $state}.GetNewClosure()
 Close={
    Assert-TintCaptureProcess $state
    if(-not $state.process.CloseMainWindow()){throw 'Capture editor refused normal close'}
    $state.processExit=[PixelQuayQualification.ConsumerNative]::ExitCode($state.process,15000)
    if($null -eq $state.processExit -or $state.processExit -ne 0){throw 'Capture editor did not close normally with zero'}
    $state.normalClose=$true;$state.stopped=$true
    $state.receipt=Invoke-TintCaptureFiles finish $state.statePath @('--stopped')
    Write-NewUtf8Json (Join-Path $output 'capture-verified-files.json') $state.receipt
 }.GetNewClosure()
 Uninstall={
    if(-not $state.installedByUs -or $state.ownedPackageFullName -cne $fullName){throw 'Capture package ownership unavailable'}
    Remove-AppxPackage -Package $state.ownedPackageFullName -ErrorAction Stop
    if(@(Get-AppxPackage -Name '1659hashfunction.PixelQuay' -ErrorAction Stop).Count){throw 'Capture registration remains after uninstall'}
    $state.uninstallVerified=$true
 }.GetNewClosure()
 Stop={
    if(-not $state.stopped){
        if(-not $state.processOwned){throw 'Unproven process retained; profile and demo preserved'}
        $exit=[PixelQuayQualification.ConsumerNative]::ExitCode($state.process,0)
        if($null -eq $exit){$state.process.Kill();$exit=[PixelQuayQualification.ConsumerNative]::ExitCode($state.process,10000)}
        if($null -eq $exit){throw 'Owned capture process shutdown unproven'}
        $state.cleanupExit=$exit;$state.stopped=$true
    }
 }.GetNewClosure()
 RestoreDisplay={Restore-PixelQuayConsumerDisplay $state}.GetNewClosure()
 RemovePackage={
    if($state.installAttempted){
        $remaining=@(Get-AppxPackage -Name '1659hashfunction.PixelQuay' -ErrorAction Stop)
        if($state.installedByUs){$owned=@($remaining|Where-Object PackageFullName -CEQ $state.ownedPackageFullName);if($owned.Count -gt 1){throw 'Ambiguous capture registration preserved'};if($owned.Count -eq 1){Remove-AppxPackage -Package $state.ownedPackageFullName -ErrorAction Stop}}
        $state.residual=@(Get-AppxPackage -Name '1659hashfunction.PixelQuay' -ErrorAction Stop|ForEach-Object PackageFullName)
        if($state.residual.Count -or ($state.addCompleted -and -not $state.installedByUs)){throw 'Unowned or unresolved registration preserved'}
    }
 }.GetNewClosure()
 RemoveProfileAndDemo={
    if($state.fixture){
        if(-not $state.stopped){throw 'Capture profile/demo preserved because process shutdown is unproven'}
        if(-not $state.receipt){Invoke-TintCaptureFiles seal-aborted-profile $state.statePath @('--stopped')|Out-Null}
        $removed=Invoke-TintCaptureFiles cleanup $state.statePath @('--stopped');$state.fixtureRemoved=$removed.removed -eq $true
    }
 }.GetNewClosure()
 RemoveTrust={if($state.trustAttempted -and $state.certificate){$path='Cert:\LocalMachine\TrustedPeople\'+$state.certificate.Thumbprint;if(Test-Path $path){Remove-Item $path -Force -ErrorAction Stop};if(Test-Path $path){throw 'Owned capture trust certificate remains'}}}.GetNewClosure()
 RemoveKey={if($state.certificate){$path='Cert:\CurrentUser\My\'+$state.certificate.Thumbprint;if(Test-Path $path){Remove-Item $path -DeleteKey -Force -ErrorAction Stop};if(Test-Path $path){throw 'Owned capture certificate/key remains'}}}.GetNewClosure()
 RemoveTemporary={if($state.temporary){Remove-Item -LiteralPath $state.temporary -Recurse -Force -ErrorAction Stop;if(Test-Path -LiteralPath $state.temporary){throw 'Owned capture signing directory remains'}}}.GetNewClosure()
}
return $operations
}
