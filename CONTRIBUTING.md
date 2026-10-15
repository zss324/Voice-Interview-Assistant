# 开发说明

本项目面向 Windows 11，使用 Python 3.12。部署、模型下载和运行步骤见 [README.md](README.md)。

修改后可在 PowerShell 中运行：

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
& '.\.venv\Scripts\python.exe' -m pytest -q
& '.\.venv\Scripts\python.exe' -m PyInstaller --noconfirm --clean main.spec
```

打包前将 `PIP_CACHE_DIR`、`TEMP`、`TMP`、`PYINSTALLER_CONFIG_DIR` 设置到 `D:\Codex` 下。修改音频、Qt 或本机加密依赖后，还需在 Windows 上实际启动打包的 EXE，并检查语音设备与正常退出。不要提交 `profile.json`、`api_key.dat`、`.env`、简历或模型权重。保留原项目 MIT 许可证与版权声明。
