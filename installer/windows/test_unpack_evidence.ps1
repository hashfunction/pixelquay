# Copyright 2026 Trieflow LLC. MIT. Real preflight with only platform/Appx adapter substituted.
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
[IO.File]::WriteAllText($adapted,$text)
try {
  . $adapted -LibraryOnly
  function global:Get-AppxPackage { [CmdletBinding()]param([string]$Name) if($Name -cne 'Trieflow.PixelQuay.Qualification'){throw 'Registration query changed compatibility identity'}; return @() }
  function Invoke-PixelQuayQualificationCore([Collections.IDictionary]$Operations) {
    & $Operations.Preflight | Out-Null
    $state=$Operations.Preflight.Module.SessionState.PSVariable.GetValue('state')
    $state.consumerDisplay.displayEvidence=@{restore_verified=$true}; $state.consumerReceipt=@{fixture=$true}; $state.consumerRemoved=$true; $state.cleanClose=$true
    [pscustomobject]@{installation_qualification_passed=$true;primary_error=$null;cleanup_errors=@()}
  }
  $env:CI='true'
  foreach($variant in @('valid','zero','missing','empty','wrong-count','string','float','bool','extra','container-count','old-executable','old-version','renamed-package','renamed-app-id','renamed-publisher')) {
    $root=Join-Path ([IO.Path]::GetTempPath()) ('pixelquay-unpack-record-'+[guid]::NewGuid().ToString('N'))
    [IO.Directory]::CreateDirectory($root)|Out-Null
    try {
      $package=Join-Path $root 'input.msix'; [IO.File]::WriteAllBytes($package,[byte[]](1,2,3))
      $sdk=Join-Path $root 'Windows Kits/10/bin/10.0.26100.0/x64'; [IO.Directory]::CreateDirectory($sdk)|Out-Null
      $make=Join-Path $sdk 'makeappx.exe'; [IO.File]::WriteAllText($make,'make')
      $sign=Join-Path $sdk 'signtool.exe'; [IO.File]::WriteAllText($sign,'sign')
      $sha=(Get-FileHash $package -Algorithm SHA256).Hash.ToLowerInvariant()
      $record=[ordered]@{
        schemaVersion=1;qualificationIdentityOnly=$true;signed=$false;publicRelease=$false;licenseClearanceClaimed=$false;installationQualificationPassed=$false
        sourceCommit=('a'*40)
        identity=[ordered]@{packageName='Trieflow.PixelQuay.Qualification';publisher='CN=PixelQuay-CI-Qualification';version='1.0.1.0';architecture='x64';applicationId='PixelQuay';executable='bin\TintFable.exe';deviceFamily='Windows.Desktop';minVersion='10.0.19041.0';maxVersionTested='10.0.26100.0';capability='runFullTrust'}
        makeAppx=[ordered]@{path=$make;sdkVersion='10.0.26100.0'}
        containerVerification=[ordered]@{verifiedPayloadFiles=1;package=[ordered]@{sha256=$sha}}
        payload=[ordered]@{'bin/TintFable.exe'=[ordered]@{bytes=1;sha256=('b'*64)}}
      }
      $record.unpackedVerification=[ordered]@{verifiedPayloadFiles=1}
      switch ($variant) {
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
      try { Invoke-PixelQuayInstallQualification $package $recordPath $sign $out | Out-Null; $accepted=$true } catch { $failure=$_.Exception.Message }
      if ($variant -eq 'valid') {
        if (-not $accepted) { throw "Valid source payload/unpack count rejected: $failure" }
      } elseif ($variant -in @('old-executable','old-version','renamed-package','renamed-app-id','renamed-publisher')) {
        if ($accepted -or $failure -notmatch 'Qualification identity mismatch') { throw "Rename identity mismatch accepted or wrong failure: $variant $failure" }
      } elseif ($accepted -or $failure -notmatch 'unpack') { throw "Invalid $variant unpack evidence accepted or wrong failure: $failure" }
      Write-Output "PASS actual preflight unpack record: $variant"
    } finally { if(Test-Path $root){Remove-Item $root -Recurse -Force} }
  }
} finally {
  $env:CI=$previousCi
  Remove-Item $adapted -Force
  Remove-Item Function:\Get-AppxPackage -ErrorAction SilentlyContinue
}
