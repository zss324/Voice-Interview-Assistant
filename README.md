# 语音面试助手 / Voice Interview Assistant

面向 Windows 11 的文字面试辅助工具：采集麦克风、会议播放声音，或同时采集两者；使用本机语音模型转写问题，再通过**硅基流动的 `deepseek-ai/DeepSeek-V4-Flash` API**生成文字回答。可预先填写岗位资料和导入简历，使涉及个人背景的问题得到有依据的回答。

本项目由 [Interview AI Windows11](https://github.com/Feng-s-Lab/interview_ai_win11) **简化并二次开发**而来。它聚焦桌面端语音问答，没有 Windows“实时字幕”依赖，也没有截图识题、网页端或多模型切换功能。

## 功能与运行条件

- 声音来源可选**会议声音**（所选扬声器或耳机的播放声音）、**麦克风**、**会议声音 + 麦克风**。
- 使用 sherpa-onnx 的中英双语流式模型在本机转写；文字问题显示在窗口中。识别到问题后自动生成回答，也可手动点击“回答当前识别文字”。如果模型没有给出句尾信号，程序会根据声音停顿或文字稳定情况结束当前问题；模型暂时返回空文字时会保留最后一次识别结果。手动回答后也会重置识别流，让下一个问题单独显示。
- 准备页可填写岗位名称、公司、岗位描述，导入带文字层的 PDF 简历并修改提取结果。与提问相关时才使用这些资料；普通知识题不主动带入个人背景。
- 岗位和简历文字保存在程序旁的 `profile.json`；API Key 通过 Windows 当前用户加密后保存在 `api_key.dat`，下次启动自动读取。“清除资料”会清除这两份本机数据，但不删除原 PDF。
- 准备页和面试页均可调整窗口透明度；面试页可临时隐藏窗口，通过 `Ctrl+Alt+H` 或系统托盘图标恢复。勾选“开始后隐藏任务栏图标”时，面试页不显示任务栏图标，返回准备页后恢复。在腾讯会议共享屏幕时，工具窗口不会显示在共享画面中；实体摄像头仍可能拍到显示器。
- 回答超过 15 秒没有首字、输出中断或总生成时间过长时，会停止等待并显示重试提示；可以随时点击“取消生成”。已经生成的部分文字会保留。

需要 Windows 11、可用的声音设备，以及用于生成回答的硅基流动 API Key。没有 Key 时可以测试转写，但不能生成回答。**普通用户直接安装发布页的安装包即可，语音模型已包含在内，无需安装 Python、部署模型或克隆源码。**

## 普通用户：下载安装包

1. 在本仓库的 **Releases（发行版）** 页面下载 `VoiceInterviewAssistant-Setup-1.2.3.exe`。请下载安装文件，而不是 GitHub 自动生成的 Source code ZIP；1.2.3 改进了部分声音设备上停顿后仍不自动结束问题的情况，并保留了面试页透明度、临时隐藏和回答超时功能。
2. 双击安装文件，按向导安装；安装后从桌面或开始菜单打开“语音面试助手”。安装程序将本机语音识别模型和程序一起放入安装目录。建议预留至少 700 MB 可用空间。
3. 按下一节注册硅基流动、获取 API Key。首次启动时把 Key 粘贴到准备页，此后程序会在当前 Windows 用户下加密保存。
4. 按“使用方法”配置麦克风和会议声音。语音转写在本机完成；生成回答仍需要网络连接。

安装包面向 64 位 Windows 11。它不包含你的简历、岗位资料或 API Key。卸载或更新前如需保留个人资料，请先备份安装目录里的 `profile.json` 和 `api_key.dat`；`api_key.dat` 通常只能由原 Windows 用户解密。安装包未经代码签名，Windows 可能显示发布者未知，请核对下载来源和发行版提供的 SHA-256 校验值。

## 注册硅基流动并获取 API Key

1. 打开[硅基流动注册邀请链接](https://cloud.siliconflow.cn/i/yTGHC9lP)注册账号。如页面要求手动填写邀请码，使用 `yTGHC9lP`。
2. 按平台提示完成实名认证。根据[硅基流动“推荐官”计划](https://www.siliconflow.cn/developer-talk/od7wj9rr23p95uhihmhrombp)，通过邀请注册且完成实名认证、符合活动条件的用户，可获得 **16 元通用代金券**；邀请人也可能获得奖励。领取方式、有效期和活动是否继续，以平台当时显示的规则为准。这是平台额度，不代表本工具或模型永久免费。
3. 登录硅基流动控制台，进入 **API 密钥** 页面，点击 **新建 API 密钥**，复制生成的 Key。可参考[硅基流动快速上手文档](https://docs.siliconflow.cn/docs/userguide/quickstart)。
4. 首次启动本工具时，将 Key 粘贴到准备页的“API Key”输入框，点击“开始面试”。程序会加密保存，下次自动填入。不要把 Key 写进 README、提交到 GitHub 或发送给其他人。

工具固定使用硅基流动接口 `https://api.siliconflow.cn/v1` 和模型 ID `deepseek-ai/DeepSeek-V4-Flash`；不需要另行购买 DeepSeek 官方 API Key。硅基流动的[模型页面](https://www.siliconflow.cn/models)可查询模型信息，费用与额度以平台账单为准。

## 高级用户：单独准备本地语音模型

仅当你运行单文件 EXE 或从源码启动时才需要本节。安装包已经包含模型。模型为 `sherpa-onnx-streaming-paraformer-bilingual-zh-en`。在 **PowerShell** 中执行以下命令；下载文件和解压目录都位于 `D:\Codex`，若已有完整模型则跳过下载。

```powershell
$modelRoot = 'D:\Codex\models\interview-asr'
$modelName = 'sherpa-onnx-streaming-paraformer-bilingual-zh-en'
$modelDir = Join-Path $modelRoot $modelName
$archive = Join-Path $modelRoot "$modelName.tar.bz2"
New-Item -ItemType Directory -Force -Path $modelRoot | Out-Null

$required = @('tokens.txt', 'encoder.int8.onnx', 'decoder.int8.onnx')
if (@($required | Where-Object { -not (Test-Path (Join-Path $modelDir $_)) }).Count -gt 0) {
    if (-not (Test-Path $archive)) {
        Invoke-WebRequest -Uri "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/$modelName.tar.bz2" -OutFile $archive
    }
    tar -xjf $archive -C $modelRoot
}

$required | ForEach-Object { Test-Path (Join-Path $modelDir $_) }
```

最后一段应输出三个 `True`。下载地址及文件名见 [sherpa-onnx Paraformer 模型说明](https://github.com/k2-fsa/sherpa/blob/master/docs/source/onnx/pretrained_models/online-paraformer/paraformer-models.rst)。若模型放在其他位置，启动程序前设置进程环境变量 `INTERVIEW_ASR_MODEL_DIR` 为**包含这三个文件的目录**：

```powershell
$env:INTERVIEW_ASR_MODEL_DIR = 'D:\Codex\models\interview-asr\sherpa-onnx-streaming-paraformer-bilingual-zh-en'
```

更新 EXE 不需要重新下载模型；单独移动 EXE 到另一台电脑时，仍需在那台电脑完成本节。

## 开发者：从源码运行或自行构建

### 单文件 EXE

如果仓库提供已打包的 `VoiceInterviewAssistant.exe`，将它保存到 `D:\Codex\Voice-Interview-Assistant\dist\`，完成模型准备后双击运行。EXE 不要求另装 Python；生成回答时仍需网络连接。

在 PowerShell 中可以做音频与模型自检：

```powershell
& 'D:\Codex\Voice-Interview-Assistant\dist\VoiceInterviewAssistant.exe' --check-audio
```

退出码 `0` 表示自检通过。自检只读取默认播放设备的短音频片段，不保存录音；它不能代替真实会议中的识别测试。

### 从 GitHub 源码运行

准备 **64 位 Python 3.12** 和 Git。在 GitHub 仓库页面点击 **Code → HTTPS** 复制仓库地址，然后在 PowerShell 中运行：

```powershell
$repoUrl = Read-Host '粘贴本仓库的 HTTPS 克隆地址'
git clone $repoUrl 'D:\Codex\Voice-Interview-Assistant'
Set-Location 'D:\Codex\Voice-Interview-Assistant'

$env:PIP_CACHE_DIR = 'D:\Codex\pip-cache'
$env:TEMP = 'D:\Codex\tmp'
$env:TMP = $env:TEMP
$env:PYINSTALLER_CONFIG_DIR = 'D:\Codex\pyinstaller-cache'
New-Item -ItemType Directory -Force -Path $env:PIP_CACHE_DIR, $env:TEMP, $env:PYINSTALLER_CONFIG_DIR | Out-Null

py -3.12 -m venv 'D:\Codex\Voice-Interview-Assistant\.venv'
& '.\.venv\Scripts\python.exe' -m pip install -e .
& '.\.venv\Scripts\python.exe' main.py
```

源码、虚拟环境和依赖下载缓存均位于 `D:\Codex`。模型仍需按第 2 节单独下载。若从 GitHub 下载 ZIP 并解压到该目录，可跳过 `git clone`，从 `Set-Location` 开始。

需要自行打包时，先在同一环境安装开发依赖，再运行 PyInstaller：

```powershell
& '.\.venv\Scripts\python.exe' -m pip install -e '.[dev]'
& '.\.venv\Scripts\python.exe' -m PyInstaller --noconfirm --clean main.spec
```

产物为 `dist\VoiceInterviewAssistant.exe`。打包前也应将 `PIP_CACHE_DIR`、`TEMP`、`TMP`、`PYINSTALLER_CONFIG_DIR` 指向 `D:\Codex`，避免工具把临时下载文件写到 C 盘。

### 构建包含模型的安装包

在完成上面的 EXE 构建并准备好模型后，安装 [Inno Setup](https://jrsoftware.org/isdl.php)，运行 `packaging\build-installer.ps1`。脚本默认使用 `D:\Codex\tools\InnoSetup7\ISCC.exe` 和 `D:\Codex\models\interview-asr\sherpa-onnx-streaming-paraformer-bilingual-zh-en`；位置不同可以用 `-CompilerPath`、`-ModelDir` 指定。当前源码构建产物位于 `dist-installer\VoiceInterviewAssistant-Setup-1.2.3.exe`。脚本只会打包这三个模型文件，不收录 `profile.json` 和 `api_key.dat`。

发布到 GitHub 时，请把安装包作为 Release asset 上传，并提供其 SHA-256 校验值。GitHub 自动生成的源码 ZIP 不含程序和模型。模型来源及许可信息见 [第三方组件说明](THIRD_PARTY_NOTICES.md)。

## 使用方法

1. 在**准备页**填写岗位名称、公司和岗位描述；点击“导入 PDF”选择带文字层的简历。检查“简历文字”中的顺序、错字和漏字。扫描版图片 PDF 暂不支持。
2. 选择声音模式：**会议声音**用于识别对方讲话，选择腾讯会议实际使用的扬声器或耳机；**麦克风**用于自测；**会议声音 + 麦克风**同时识别两边，需分别选择设备。建议使用耳机减少声音回传。
3. 按需调整透明度与“开始后隐藏任务栏图标”选项，确认 API Key 已填，点击“开始面试”。本地语音模型加载后，状态会显示监听设备；输入音量和识别文字随讲话更新。面试页仍可调透明度，也可点击“临时隐藏”；按 `Ctrl+Alt+H` 或点击系统托盘图标恢复。若全局快捷键和系统托盘都不可用，程序会拒绝隐藏，以免无法找回窗口。
4. 对方说完一个问题并停顿后，程序会尝试自动生成文字回答。若没有自动触发，点击“回答当前识别文字”；需要再次生成时点击“重新回答”。生成中可点击“取消生成”。若 15 秒没有首字、连续 10 秒没有新输出，或总时长超过 45 秒，程序会停止本次请求并提示重试；已显示的部分回答仍会保留。也可以暂停监听或返回准备页修改资料。
5. 想删除本机保存的岗位、简历和 Key，点击“清除资料”；原 PDF 文件不会被删除。

例如，“你的专业对这个岗位有什么用”会参考简历中的专业与岗位职责；“Java 的基础数据类型有哪些”按技术知识回答，不强行联系简历。回答是建议文本，仍需自行核对事实。

## 数据、费用与限制

- **语音识别在本机完成**；生成回答时，识别出的提问文字及与该问题相关的岗位描述、简历文字会发送到硅基流动 API。岗位和简历文字保存在程序目录的 `profile.json`。
- API Key 使用 Windows 当前用户的加密机制保存在同目录 `api_key.dat`；将此文件复制给其他 Windows 用户或电脑通常无法直接读取。不要把 `profile.json`、`api_key.dat` 或真实 `.env` 提交到公开仓库。
- 硅基流动的模型调用可能消耗赠送额度或产生费用；活动额度、价格和服务状态以平台页面为准。
- 麦克风、耳机和腾讯会议的设备设置必须匹配。若输入音量始终为零，检查 Windows 与腾讯会议的输入/输出设备，并点击“刷新设备”。
- 程序通过 Windows 窗口捕获排除接口，使工具窗口不出现在腾讯会议的屏幕共享画面中。
- 实体二机位摄像头拍摄的是显示器本身，不受窗口捕获排除接口影响。降低透明度可能影响自己阅读，临时隐藏时自己也看不到回答。
- 当前只解析带文字层的 PDF；提取结果需要人工校对。软件只提供文字建议，不会替你发声。

## 开发与测试

源码使用 Python 3.12、PyQt6、PyAudioWPatch、sherpa-onnx、PyMuPDF、OpenAI 兼容客户端和 pywin32。安装 `.[dev]` 后运行：

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
& '.\.venv\Scripts\python.exe' -m pytest -q
```

`QT_QPA_PLATFORM=offscreen` 仅用于自动化测试，正常启动程序时无需设置。

## 二次开发来源与参考

- [Feng-s-Lab / Interview AI Windows11](https://github.com/Feng-s-Lab/interview_ai_win11)：本项目的直接二次开发来源。保留原项目 MIT 许可证及版权声明；具体功能和部署以本 README 为准。
- [j4wg / interview-coder-withoupaywall-opensource](https://github.com/j4wg/interview-coder-withoupaywall-opensource)：早期界面与屏幕捕获排除需求的参考；本项目没有引入其截图答题功能。
- [k2-fsa / sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx)：本地流式语音识别库及模型来源。
- [s0d3s / PyAudioWPatch](https://github.com/s0d3s/PyAudioWPatch)：Windows WASAPI 播放设备回环采集。
- [PyMuPDF](https://github.com/pymupdf/PyMuPDF)：提取带文字层 PDF 中的简历文字。

许可证见 [LICENSE](LICENSE)。
