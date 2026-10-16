#ifndef ModelDir
  #error ModelDir must be supplied by build-installer.ps1
#endif

#define AppVersion "1.2.0"
#define ModelName "sherpa-onnx-streaming-paraformer-bilingual-zh-en"

[Setup]
AppId={{2B650B3F-1DD5-4E0A-A5CC-7A203173F1BD}
AppName=语音面试助手
AppVersion={#AppVersion}
AppPublisher=Voice Interview Assistant contributors
DefaultDirName={localappdata}\Programs\VoiceInterviewAssistant
DefaultGroupName=语音面试助手
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
WizardStyle=modern
Compression=lzma2
SolidCompression=yes
OutputDir=..\dist-installer
OutputBaseFilename=VoiceInterviewAssistant-Setup-{#AppVersion}
UninstallDisplayIcon={app}\VoiceInterviewAssistant.exe
LicenseFile=..\LICENSE

[Languages]
Name: "chinesesimp"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Files]
Source: "..\dist\VoiceInterviewAssistant.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\THIRD_PARTY_NOTICES.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\packaging\LICENSE-APACHE-2.0.txt"; DestDir: "{app}\licenses"; Flags: ignoreversion
Source: "{#ModelDir}\tokens.txt"; DestDir: "{app}\models\{#ModelName}"; Flags: ignoreversion
Source: "{#ModelDir}\encoder.int8.onnx"; DestDir: "{app}\models\{#ModelName}"; Flags: ignoreversion
Source: "{#ModelDir}\decoder.int8.onnx"; DestDir: "{app}\models\{#ModelName}"; Flags: ignoreversion

[Icons]
Name: "{group}\语音面试助手"; Filename: "{app}\VoiceInterviewAssistant.exe"
Name: "{autodesktop}\语音面试助手"; Filename: "{app}\VoiceInterviewAssistant.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "其他选项："

[Run]
Filename: "{app}\VoiceInterviewAssistant.exe"; Description: "启动语音面试助手"; Flags: nowait postinstall skipifsilent
