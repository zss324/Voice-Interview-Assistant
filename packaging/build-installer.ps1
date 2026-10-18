param(
    [string] $ModelDir = 'D:\Codex\models\interview-asr\sherpa-onnx-streaming-paraformer-bilingual-zh-en',
    [string] $CompilerPath = 'D:\Codex\tools\InnoSetup7\ISCC.exe',
    [string] $ExePath = '',
    [string] $ExpectedExeSha256 = ''
)

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$modelPath = (Resolve-Path $ModelDir).Path
foreach ($file in @('tokens.txt', 'encoder.int8.onnx', 'decoder.int8.onnx')) {
    if (-not (Test-Path -LiteralPath (Join-Path $modelPath $file))) {
        throw "模型缺少文件：$file"
    }
}
$resolvedExePath = if ($ExePath) { $ExePath } else { Join-Path $projectRoot 'dist\VoiceInterviewAssistant.exe' }
if (-not (Test-Path -LiteralPath $resolvedExePath)) {
    throw "找不到已构建的 EXE：$resolvedExePath"
}
$resolvedExePath = (Resolve-Path -LiteralPath $resolvedExePath).Path
if ($ExpectedExeSha256) {
    $actualExeSha256 = (Get-FileHash -LiteralPath $resolvedExePath -Algorithm SHA256).Hash
    if ($actualExeSha256 -ne $ExpectedExeSha256) {
        throw "EXE SHA-256 不匹配：$actualExeSha256"
    }
}
if (-not (Test-Path -LiteralPath $CompilerPath)) {
    throw "找不到 Inno Setup 编译器：$CompilerPath"
}

$env:TEMP = 'D:\Codex\tmp'
$env:TMP = $env:TEMP
New-Item -ItemType Directory -Force -Path $env:TEMP, (Join-Path $projectRoot 'dist-installer') | Out-Null
Push-Location $PSScriptRoot
try {
    & $CompilerPath "/DModelDir=$modelPath" "/DExePath=$resolvedExePath" 'VoiceInterviewAssistant.iss'
    if ($LASTEXITCODE -ne 0) { throw "安装包编译失败，退出码 $LASTEXITCODE" }
}
finally {
    Pop-Location
}
