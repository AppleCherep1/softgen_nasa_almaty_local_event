$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
New-Item -ItemType Directory -Force -Path 'models' | Out-Null
$ruZip = Join-Path $PSScriptRoot 'models\ru-download.zip'
$enZip = Join-Path $PSScriptRoot 'models\en-download.zip'
if (!(Test-Path 'models\vosk-model-small-ru') -and !(Test-Path 'models\vosk-model-small-ru-0.22')) {
    Invoke-WebRequest 'https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip' -OutFile $ruZip
    Expand-Archive $ruZip -DestinationPath 'models'
    Rename-Item 'models\vosk-model-small-ru-0.22' 'vosk-model-small-ru'
    Remove-Item $ruZip
}
if (!(Test-Path 'models\vosk-model-small-en-us-0.15')) {
    Invoke-WebRequest 'https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip' -OutFile $enZip
    Expand-Archive $enZip -DestinationPath 'models'
    Remove-Item $enZip
}
Write-Output 'Models extracted. Restart server and check /health. Existing model folders were left untouched.'
