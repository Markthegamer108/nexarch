param(
  [string]$Arch = 'AVX2',
  [string]$Out = 'nexarch.exe'
)
$ErrorActionPreference = 'Stop'

$vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
$vs = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $vs) { throw 'Visual Studio C++ build tools were not found.' }

$objDir = Join-Path $PSScriptRoot 'build'
New-Item -ItemType Directory -Force $objDir | Out-Null
$sources = (Get-ChildItem (Join-Path $PSScriptRoot 'src\*.cpp') | ForEach-Object { '"' + $_.FullName + '"' }) -join ' '
$exe = Join-Path $PSScriptRoot $Out

$bat = Join-Path $objDir 'build.bat'
@"
@echo off
set "PATH=%SystemRoot%\System32;%ProgramFiles(x86)%\Microsoft Visual Studio\Installer;%PATH%"
call "$vs\VC\Auxiliary\Build\vcvars64.bat" >nul || exit /b 1
cl /nologo /std:c++20 /O2 /Oi /GL /EHsc /MP /DNDEBUG /D_CRT_SECURE_NO_WARNINGS /W3 /arch:$Arch /Fo"$objDir\\" $sources /Fe:"$exe" /link /LTCG
"@ | Set-Content -Encoding ASCII $bat

& $env:ComSpec /c "`"$bat`""
if ($LASTEXITCODE -ne 0) { throw "Build failed (exit code $LASTEXITCODE)." }
Write-Host "Built $exe"
