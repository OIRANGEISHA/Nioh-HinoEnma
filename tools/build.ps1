param([ValidateSet('Debug','Release')][string]$Configuration = 'Release')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$version = Get-Content -LiteralPath (Join-Path $projectRoot 'version.json') -Raw | ConvertFrom-Json
$compiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
if (-not (Test-Path -LiteralPath $compiler)) { throw 'Windows x64 .NET Framework C# compiler not found.' }
$destination = Join-Path $projectRoot "artifacts\$Configuration"
New-Item -ItemType Directory -Path $destination -Force | Out-Null
$executable = Join-Path $destination "Nioh-HinoEnma-$($version.version)-windows-x64.exe"
$arguments = @('/nologo','/target:winexe','/platform:x64','/utf8output','/codepage:65001','/warnaserror+',
    '/reference:System.dll','/reference:System.Core.dll','/reference:System.Drawing.dll',
    '/reference:System.Windows.Forms.dll','/reference:System.Web.Extensions.dll',
    "/win32manifest:$projectRoot\launcher\app.manifest", "/out:$executable")
if ($Configuration -eq 'Release') { $arguments += '/optimize+' }
else { $arguments += @('/optimize-','/debug:full','/define:DEBUG;TRACE') }
$sources = 'Native.cs','Injector.cs','Program.cs','SelfTests.cs','Profile.generated.cs','AssemblyInfo.cs'
foreach ($source in $sources) { $arguments += (Join-Path $projectRoot "launcher\$source") }
& $compiler @arguments
if ($LASTEXITCODE -ne 0) { throw "C# $Configuration compilation failed." }
$selfTest = Join-Path $destination 'self-tests.json'
$process = Start-Process -FilePath $executable -ArgumentList '--self-test', ('"' + $selfTest + '"') -WindowStyle Hidden -Wait -PassThru
if ($process.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $selfTest)) { throw 'Offline self-tests failed.' }
$result = Get-Content -LiteralPath $selfTest -Raw | ConvertFrom-Json
if (-not $result.success -or $result.game_access -or $result.count -ne 28 -or @($result.checks).Count -ne 28) { throw 'Unexpected self-test result.' }
$details = @{
    configuration = $Configuration
    compiler = 'Windows .NET Framework C# compiler'
    compiler_file_version = (Get-Item -LiteralPath $compiler).VersionInfo.FileVersion
    windows_version = [Environment]::OSVersion.Version.ToString()
    powershell_version = $PSVersionTable.PSVersion.ToString()
    product_version = (Get-Item -LiteralPath $executable).VersionInfo.ProductVersion
    file_version = (Get-Item -LiteralPath $executable).VersionInfo.FileVersion
    pe_machine = 'x64'
    authenticode_status = (Get-AuthenticodeSignature -LiteralPath $executable).Status.ToString()
    offline_self_checks = $result.count
}
$json = $details | ConvertTo-Json
[IO.File]::WriteAllText((Join-Path $destination 'build.json'), $json + "`n", (New-Object Text.UTF8Encoding($false)))
Write-Output "$Configuration built; $($result.count) offline checks passed: $executable"
