param(
    [string] $ModelDir = 'D:\Codex\models\interview-asr\sherpa-onnx-streaming-paraformer-bilingual-zh-en',
    [string] $CompilerPath = 'D:\Codex\tools\InnoSetup7\ISCC.exe'
)

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$modelPath = (Resolve-Path $ModelDir).Path
foreach ($file in @('tokens.txt', 'encoder.int8.onnx', 'decoder.int8.onnx')) {
    if (-not (Test-Path -LiteralPath (Join-Path $modelPath $file))) {
        throw "模型缺少文件：$file"
    }
}
if (-not (Test-Path -LiteralPath (Join-Path $projectRoot 'dist\VoiceInterviewAssistant.exe'))) {
    throw '请先用 PyInstaller 构建 dist\VoiceInterviewAssistant.exe'
}
if (-not (Test-Path -LiteralPath $CompilerPath)) {
    throw "找不到 Inno Setup 编译器：$CompilerPath"
}

$env:TEMP = 'D:\Codex\tmp'
$env:TMP = $env:TEMP
New-Item -ItemType Directory -Force -Path $env:TEMP, (Join-Path $projectRoot 'dist-installer') | Out-Null
Push-Location $PSScriptRoot
try {
    & $CompilerPath "/DModelDir=$modelPath" 'VoiceInterviewAssistant.iss'
    if ($LASTEXITCODE -ne 0) { throw "安装包编译失败，退出码 $LASTEXITCODE" }
}
finally {
    Pop-Location
}
