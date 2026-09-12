# Copyright 2026 Trieflow LLC. MIT. Real preflight with only platform/Appx adapter substituted.
param([ValidateSet('qualification','store')][string]$IdentityMode='qualification')
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$source=Join-Path $PSScriptRoot 'qualify-msix-install.ps1'
$previousCi=$env:CI
$adapted=Join-Path ([IO.Path]::GetTempPath()) ('pixelquay-preflight-adapter-'+[guid]::NewGuid().ToString('N')+'.ps1')
$text=[IO.File]::ReadAllText($source).Replace('[Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT -or $env:CI -ne ''true''','$env:CI -ne ''true''')
. (Join-Path $PSScriptRoot 'consumer_ui.ps1')
. (Join-Path $PSScriptRoot 'consumer_display.ps1')
$text=$text.Replace(". (Join-Path `$PSScriptRoot 'consumer_ui.ps1')",'')
$text=$text.Replace(". (Join-Path `$PSScriptRoot 'consumer_display.ps1')",'')
$text=$text.Replace('`$PSScriptRoot'.Replace('`',''), ("'"+$PSScriptRoot.Replace("'","''")+"'"))
[IO.File]::WriteAllText($adapted,$text)
try {
  $selectedFixtureMode=$IdentityMode
  . $adapted -LibraryOnly -IdentityMode $selectedFixtureMode
  if($IdentityMode -cne $selectedFixtureMode){throw 'Production loader changed the requested fixture identity mode'}
  $global:PixelQuayPreflightIdentity=Get-PixelQuayIdentity $IdentityMode
  function global:Get-AppxPackage { [CmdletBinding()]param([string]$Name) if($Name -cne $global:PixelQuayPreflightIdentity.packageName){throw 'Registration query changed compatibility identity'}; return @() }
  function Invoke-PixelQuayQualificationCore([Collections.IDictionary]$Operations) {
    & $Operations.Preflight | Out-Null
    $state=$Operations.Preflight.Module.SessionState.PSVariable.GetValue('state')
    $state.consumerDisplay.displayEvidence=@{restore_verified=$true}; $state.consumerReceipt=@{fixture=$true}; $state.consumerRemoved=$true; $state.cleanClose=$true
    [pscustomobject]@{installation_qualification_passed=$true;primary_error=$null;cleanup_errors=@()}
  }
  $env:CI='true'
  foreach($variant in @('valid','zero','missing','empty','wrong-count','string','float','bool','extra','container-count','old-executable','old-version','renamed-package','renamed-app-id','renamed-publisher','wrong-mode','wrong-mode-flag')) {
    $root=Join-Path ([IO.Path]::GetTempPath()) ('pixelquay-unpack-record-'+[guid]::NewGuid().ToString('N'))
    [IO.Directory]::CreateDirectory($root)|Out-Null
    try {
      $package=Join-Path $root 'input.msix'; [IO.File]::WriteAllBytes($package,[byte[]](1,2,3))
      $sdk=Join-Path $root 'Windows Kits/10/bin/10.0.26100.0/x64'; [IO.Directory]::CreateDirectory($sdk)|Out-Null
      $make=Join-Path $sdk 'makeappx.exe'; [IO.File]::WriteAllText($make,'make')
      $sign=Join-Path $sdk 'signtool.exe'; [IO.File]::WriteAllText($sign,'sign')
      $sha=(Get-FileHash $package -Algorithm SHA256).Hash.ToLowerInvariant()
      $record=[ordered]@{
        schemaVersion=1;identityMode=$IdentityMode;qualificationIdentityOnly=($IdentityMode -ceq 'qualification');signed=$false;publicRelease=$false;licenseClearanceClaimed=$false;installationQualificationPassed=$false
        sourceCommit=('a'*40)
        identity=Get-PixelQuayIdentity $IdentityMode
        makeAppx=[ordered]@{path=$make;sdkVersion='10.0.26100.0'}
        containerVerification=[ordered]@{verifiedPayloadFiles=1;package=[ordered]@{sha256=$sha}}
        payload=[ordered]@{'bin/TintFable.exe'=[ordered]@{bytes=1;sha256=('b'*64)}}
      }
      $record.unpackedVerification=[ordered]@{verifiedPayloadFiles=1}
      switch ($variant) {
        'wrong-mode' {$record.identityMode=if($IdentityMode -ceq 'store'){'qualification'}else{'store'}}
        'wrong-mode-flag' {$record.qualificationIdentityOnly=-not $record.qualificationIdentityOnly}
        'old-executable' { $record.identity.executable='bin\PixelQuay.exe' }
        'old-version' { $record.identity.version='1.0.0.0' }
        'renamed-package' { $record.identity.packageName='Trieflow.TintFable.Qualification' }
        'renamed-app-id' { $record.identity.applicationId='TintFable' }
        'renamed-publisher' { $record.identity.publisher='CN=TintFable-CI-Qualification' }
        'zero' { $record.unpackedVerification.verifiedPayloadFiles=0 }
        'missing' { $record.Remove('unpackedVerification') }
        'empty' { $record.unpackedVerification=[ordered]@{} }
        'wrong-count' { $record.unpackedVerification.verifiedPayloadFiles=2 }
        'string' { $record.unpackedVerification.verifiedPayloadFiles='1' }
        'float' { $record.unpackedVerification.verifiedPayloadFiles=[double]1.0 }
        'bool' { $record.unpackedVerification.verifiedPayloadFiles=$true }
        'extra' { $record.unpackedVerification.extra=$true }
        'container-count' { $record.containerVerification.verifiedPayloadFiles=0 }
      }
      $recordPath=Join-Path $root 'record.json'; $record|ConvertTo-Json -Depth 20|Set-Content -LiteralPath $recordPath
      $out=Join-Path $root 'out'
      $accepted=$false; $failure=$null
      try { Invoke-PixelQuayInstallQualification $package $recordPath $sign $out -IdentityMode $IdentityMode | Out-Null; $accepted=$true } catch { $failure=$_.Exception.Message }
      if ($variant -eq 'valid') {
        if (-not $accepted) { throw "Valid source payload/unpack count rejected: $failure" }
      } elseif ($variant -in @('wrong-mode','wrong-mode-flag')) {
        if ($accepted -or $failure -notmatch 'selected identity mode') {throw "Wrong identity mode accepted or wrong refusal: $failure"}
      } elseif ($variant -in @('old-executable','old-version','renamed-package','renamed-app-id','renamed-publisher','wrong-mode','wrong-mode-flag')) {
        if ($accepted -or $failure -notmatch 'Qualification identity mismatch') { throw "Rename identity mismatch accepted or wrong failure: $variant $failure" }
      } elseif ($accepted -or $failure -notmatch 'unpack') { throw "Invalid $variant unpack evidence accepted or wrong failure: $failure" }
      Write-Output "PASS actual preflight unpack record ($IdentityMode): $variant"
    } finally { if(Test-Path $root){Remove-Item $root -Recurse -Force} }
  }
} finally {
  $env:CI=$previousCi
  Remove-Item $adapted -Force
  Remove-Variable PixelQuayPreflightIdentity -Scope Global
  Remove-Item Function:\Get-AppxPackage -ErrorAction SilentlyContinue
}
