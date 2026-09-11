# Copyright 2026 Trieflow LLC. MIT. Real preflight with only platform/Appx adapter substituted.
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$source=Join-Path $PSScriptRoot 'qualify-msix-install.ps1'
$previousCi=$env:CI
$adapted=Join-Path ([IO.Path]::GetTempPath()) ('pixelquay-preflight-adapter-'+[guid]::NewGuid().ToString('N')+'.ps1')
$text=[IO.File]::ReadAllText($source).Replace('[Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT -or $env:CI -ne ''true''','$env:CI -ne ''true''')
[IO.File]::WriteAllText($adapted,$text)
try {
  . $adapted -LibraryOnly
  function global:Get-AppxPackage { [CmdletBinding()]param([string]$Name) return @() }
  function Invoke-PixelQuayQualificationCore([Collections.IDictionary]$Operations) {
    & $Operations.Preflight | Out-Null
    [pscustomobject]@{installation_qualification_passed=$true;primary_error=$null;cleanup_errors=@()}
  }
  $env:CI='true'
  foreach($variant in @('valid','zero','missing','empty','wrong-count','string','float','bool','extra','container-count')) {
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
        identity=[ordered]@{packageName='Trieflow.PixelQuay.Qualification';publisher='CN=PixelQuay-CI-Qualification';version='1.0.0.0';architecture='x64';applicationId='PixelQuay';executable='bin\PixelQuay.exe';deviceFamily='Windows.Desktop';minVersion='10.0.19041.0';maxVersionTested='10.0.26100.0';capability='runFullTrust'}
        makeAppx=[ordered]@{path=$make;sdkVersion='10.0.26100.0'}
        containerVerification=[ordered]@{verifiedPayloadFiles=1;package=[ordered]@{sha256=$sha}}
        payload=[ordered]@{'bin/PixelQuay.exe'=[ordered]@{bytes=1;sha256=('b'*64)}}
      }
      $record.unpackedVerification=[ordered]@{verifiedPayloadFiles=1}
      switch ($variant) {
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
      } elseif ($accepted -or $failure -notmatch 'unpack') { throw "Invalid $variant unpack evidence accepted or wrong failure: $failure" }
      Write-Output "PASS actual preflight unpack record: $variant"
    } finally { if(Test-Path $root){Remove-Item $root -Recurse -Force} }
  }
} finally {
  $env:CI=$previousCi
  Remove-Item $adapted -Force
  Remove-Item Function:\Get-AppxPackage -ErrorAction SilentlyContinue
}
