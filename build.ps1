$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
New-Item -ItemType Directory -Force out, dist | Out-Null
javac --release 17 -encoding UTF-8 -d out src/Main.java
if ($LASTEXITCODE -ne 0) { throw "Falha na compilacao Java" }
jar --create --file dist/p2p.jar --main-class Main -C out .
if ($LASTEXITCODE -ne 0) { throw "Falha na criacao do JAR" }
Write-Host "Compilado: dist/p2p.jar"
