from __future__ import annotations

import ctypes
import sys

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSlider,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..config.config import Config
from ..modules.local_speech import AudioSelection, LocalSpeechRecognizer, SpeechSignals, list_audio_sources
from ..modules.questions import looks_like_question
from ..modules.resume import extract_resume_text
from ..modules.service import AnswerService, AnswerSignals


class MainWindow(QMainWindow):
    closed = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.config = Config()
        self.speech_signals = SpeechSignals()
        self.speech = LocalSpeechRecognizer(self.speech_signals)
        self.signals = AnswerSignals()
        self.service = AnswerService(self.signals)
        self.active = False
        self.answer_enabled = False
        self.last_question = ""
        self.answer_parts: list[str] = []
        self.capture_excluded = False
        self._taskbar_hidden = False

        self.setWindowTitle("语音面试助手 Voice Interview Assistant")
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.resize(850, 670)
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        self.stack.addWidget(self._build_setup())
        self.stack.addWidget(self._build_session())
        self.setWindowOpacity(self.config.profile.opacity / 100)

        self.speech_signals.ready.connect(self._speech_ready)
        self.speech_signals.partial.connect(self._speech_partial)
        self.speech_signals.final.connect(self._speech_final)
        self.speech_signals.level.connect(self._speech_level)
        self.speech_signals.error.connect(self._speech_error)
        self.signals.started.connect(self._answer_started)
        self.signals.delta.connect(self._answer_delta)
        self.signals.done.connect(self._answer_done)
        self.signals.error.connect(self._answer_error)

    def _build_setup(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.addWidget(QLabel("开始前准备"))
        form = QFormLayout()
        profile = self.config.profile

        self.job_title = QLineEdit(profile.job_title)
        self.company = QLineEdit(profile.company)
        self.job_description = QTextEdit(profile.job_description)
        self.job_description.setPlaceholderText("粘贴岗位职责和要求；只有相关问题才会引用。")
        self.job_description.setMaximumHeight(130)
        form.addRow("岗位名称", self.job_title)
        form.addRow("公司（可选）", self.company)
        form.addRow("岗位描述", self.job_description)

        resume_row = QHBoxLayout()
        self.resume_file = QLabel(profile.resume_file or "尚未导入 PDF")
        self.resume_file.setWordWrap(True)
        import_button = QPushButton("导入 PDF")
        import_button.clicked.connect(self._import_resume)
        resume_row.addWidget(self.resume_file, 1)
        resume_row.addWidget(import_button)
        form.addRow("简历文件", resume_row)

        self.resume_text = QTextEdit(profile.resume_text)
        self.resume_text.setPlaceholderText("PDF 提取的文字会显示在这里；请检查并修改错序或漏字。")
        form.addRow("简历文字", self.resume_text)

        self.opacity = QSlider(Qt.Orientation.Horizontal)
        self.opacity.setRange(35, 100)
        self.opacity.setValue(profile.opacity)
        self.opacity.valueChanged.connect(self._opacity_changed)
        self.opacity_label = QLabel(f"{profile.opacity}%")
        opacity_row = QHBoxLayout()
        opacity_row.addWidget(self.opacity, 1)
        opacity_row.addWidget(self.opacity_label)
        form.addRow("窗口透明度", opacity_row)

        self.hide_taskbar = QCheckBox("开始后隐藏任务栏图标；返回准备页时恢复")
        self.hide_taskbar.setChecked(profile.hide_taskbar)
        form.addRow("任务栏", self.hide_taskbar)

        self.source_mode = QComboBox()
        self.source_mode.addItem("会议声音（扬声器或耳机）", "loopback")
        self.source_mode.addItem("麦克风", "microphone")
        self.source_mode.addItem("会议声音 + 麦克风", "both")
        form.addRow("声音模式", self.source_mode)

        source_row = QHBoxLayout()
        self.speaker_combo = QComboBox()
        self.microphone_combo = QComboBox()
        self._refresh_audio_sources()
        refresh_button = QPushButton("刷新设备")
        refresh_button.clicked.connect(self._refresh_audio_sources)
        source_row.addWidget(self.speaker_combo, 1)
        source_row.addWidget(refresh_button)
        form.addRow("播放设备", source_row)
        form.addRow("麦克风设备", self.microphone_combo)
        self.source_mode.currentIndexChanged.connect(self._update_audio_controls)
        self._update_audio_controls()

        self.api_key = QLineEdit(self.config.api_key())
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key.setPlaceholderText("硅基流动 API Key；保存后下次自动读取")
        form.addRow("API Key", self.api_key)
        layout.addLayout(form, 1)

        note = QLabel(
            "会议声音采集所选播放设备；麦克风采集自己的声音；两者同时会合并转写。"
            "API Key 仅加密保存在本机当前 Windows 用户下；语音转写在本机完成。"
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        buttons = QHBoxLayout()
        clear_button = QPushButton("清除资料")
        clear_button.clicked.connect(self._clear_profile)
        start_button = QPushButton("开始面试")
        start_button.clicked.connect(self._start)
        buttons.addWidget(clear_button)
        buttons.addStretch()
        buttons.addWidget(start_button)
        layout.addLayout(buttons)
        return page

    def _build_session(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 14, 18, 14)
        self.status = QLabel("等待语音问题…")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.audio_level = QProgressBar()
        self.audio_level.setRange(0, 100)
        self.audio_level.setFormat("输入音量 %p%")
        layout.addWidget(self.audio_level)
        layout.addWidget(QLabel("识别到的语音"))
        self.question_text = QTextEdit()
        self.question_text.setReadOnly(True)
        self.question_text.setMaximumHeight(140)
        layout.addWidget(self.question_text)
        layout.addWidget(QLabel("回答建议"))
        self.answer_text = QTextEdit()
        self.answer_text.setReadOnly(True)
        layout.addWidget(self.answer_text, 1)
        buttons = QHBoxLayout()
        self.pause_button = QPushButton("暂停监听")
        self.pause_button.clicked.connect(self._toggle_pause)
        retry_button = QPushButton("重新回答")
        retry_button.clicked.connect(self._retry)
        current_button = QPushButton("回答当前识别文字")
        current_button.clicked.connect(self._answer_current)
        stop_button = QPushButton("结束并返回准备页")
        stop_button.clicked.connect(self._stop)
        buttons.addWidget(self.pause_button)
        buttons.addWidget(retry_button)
        buttons.addWidget(current_button)
        buttons.addStretch()
        buttons.addWidget(stop_button)
        layout.addLayout(buttons)
        return page

    def _save_profile(self) -> None:
        profile = self.config.profile
        profile.job_title = self.job_title.text().strip()
        profile.company = self.company.text().strip()
        profile.job_description = self.job_description.toPlainText().strip()
        profile.resume_text = self.resume_text.toPlainText().strip()
        profile.opacity = self.opacity.value()
        profile.hide_taskbar = self.hide_taskbar.isChecked()
        self.config.save()

    def _import_resume(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择 PDF 简历", "", "PDF (*.pdf)")
        if not path:
            return
        try:
            text = extract_resume_text(path)
        except Exception as exc:
            QMessageBox.warning(self, "简历导入失败", str(exc))
            return
        self.resume_text.setPlainText(text)
        self.resume_file.setText(path)
        self.config.profile.resume_file = path
        self._save_profile()

    def _clear_profile(self) -> None:
        answer = QMessageBox.question(self, "清除资料", "确定清除本机保存的岗位、简历和 API Key 吗？")
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.config.clear()
        self.job_title.clear()
        self.company.clear()
        self.job_description.clear()
        self.resume_text.clear()
        self.resume_file.setText("尚未导入 PDF")
        self.opacity.setValue(self.config.profile.opacity)
        self.hide_taskbar.setChecked(self.config.profile.hide_taskbar)
        self.api_key.clear()

    def _opacity_changed(self, value: int) -> None:
        self.opacity_label.setText(f"{value}%")
        self.setWindowOpacity(value / 100)
        QTimer.singleShot(0, self._exclude_from_capture)

    def _set_taskbar_hidden(self, hidden: bool) -> None:
        if self._taskbar_hidden == hidden:
            return
        self._taskbar_hidden = hidden
        window_type = Qt.WindowType.Tool if hidden else Qt.WindowType.Window
        self.setWindowFlags(window_type | Qt.WindowType.WindowStaysOnTopHint)
        self.show()
        QTimer.singleShot(0, self._exclude_from_capture)

    def _refresh_audio_sources(self) -> None:
        self.speaker_combo.clear()
        self.microphone_combo.clear()
        try:
            for source in list_audio_sources():
                combo = self.speaker_combo if source.kind == "loopback" else self.microphone_combo
                combo.addItem(source.label, source)
        except Exception as exc:
            self.speaker_combo.addItem(f"读取声音设备失败：{exc}")
        if self.speaker_combo.count() == 0:
            self.speaker_combo.addItem("没有可用的播放设备")
        if self.microphone_combo.count() == 0:
            self.microphone_combo.addItem("没有可用的麦克风")

    def _update_audio_controls(self) -> None:
        mode = self.source_mode.currentData()
        self.speaker_combo.setEnabled(mode in ("loopback", "both"))
        self.microphone_combo.setEnabled(mode in ("microphone", "both"))

    def _selected_audio_source(self):
        mode = self.source_mode.currentData()
        speaker = self.speaker_combo.currentData()
        microphone = self.microphone_combo.currentData()
        return AudioSelection(speaker, microphone) if mode == "both" and speaker and microphone else (
            speaker if mode == "loopback" else microphone if mode == "microphone" else None
        )

    def _start(self) -> None:
        source = self._selected_audio_source()
        if source is None:
            QMessageBox.warning(self, "没有声音来源", "请检查所选模式需要的设备，并点击“刷新设备”。")
            return
        key = self.api_key.text().strip()
        self._save_profile()
        try:
            self.config.save_api_key(key)
        except OSError as exc:
            QMessageBox.warning(self, "保存 API Key 失败", str(exc))
            return
        if key:
            self.service.set_api_key(key)
        try:
            self.speech.start(source)
        except Exception as exc:
            QMessageBox.warning(self, "无法启动本地语音识别", str(exc))
            return
        self.answer_enabled = bool(key)
        self.active = True
        self.pause_button.setEnabled(True)
        self.last_question = ""
        self.question_text.clear()
        self.answer_text.clear()
        self.audio_level.setValue(0)
        self.stack.setCurrentIndex(1)
        self.status.setText("正在加载本地语音模型…")
        self._set_taskbar_hidden(self.hide_taskbar.isChecked())
        QTimer.singleShot(0, self._exclude_from_capture)

    def _speech_ready(self, label: str) -> None:
        if self.active:
            self.status.setText(f"正在监听：{label}")

    def _speech_partial(self, text: str) -> None:
        if self.active:
            self.question_text.setPlainText(text)

    def _speech_final(self, text: str) -> None:
        if not self.active:
            return
        self.question_text.setPlainText(text)
        if looks_like_question(text) and text != self.last_question:
            self.last_question = text
            if self.answer_enabled:
                self.service.answer(text, self.config.profile)
            else:
                self.status.setText("问题已识别；填写 API Key 后才能生成回答。")
        else:
            self.status.setText("语音已转写；等待问题，或点击“回答当前识别文字”。")

    def _speech_level(self, level: int) -> None:
        if self.active:
            self.audio_level.setValue(level)

    def _speech_error(self, message: str) -> None:
        if self.stack.currentIndex() == 1:
            self.active = False
            self.speech.stop()
            self.pause_button.setEnabled(False)
            self.status.setText(message)

    def _toggle_pause(self) -> None:
        self.active = not self.active
        if self.active:
            self.speech.pause(False)
            self.pause_button.setText("暂停监听")
            self.status.setText("已恢复监听。")
        else:
            self.speech.pause(True)
            self.pause_button.setText("继续监听")
            self.status.setText("监听已暂停。")

    def _retry(self) -> None:
        if self.last_question and self.answer_enabled:
            self.service.answer(self.last_question, self.config.profile)

    def _answer_current(self) -> None:
        question = self.question_text.toPlainText().strip()
        if question:
            self.last_question = question
            if self.answer_enabled:
                self.service.answer(question, self.config.profile)
            else:
                self.status.setText("请先在准备页填写 API Key，才能生成回答。")

    def _stop(self) -> None:
        self.active = False
        self.speech.stop()
        self.service.cancel()
        self.pause_button.setText("暂停监听")
        self.pause_button.setEnabled(True)
        self.stack.setCurrentIndex(0)
        self._set_taskbar_hidden(False)

    def _answer_started(self) -> None:
        self.answer_parts = []
        self.answer_text.clear()
        self.status.setText("正在生成回答…")

    def _answer_delta(self, delta: str) -> None:
        self.answer_parts.append(delta)
        self.answer_text.setPlainText("".join(self.answer_parts))

    def _answer_done(self, answer: str) -> None:
        self.answer_text.setPlainText(answer)
        self.status.setText("等待下一个问题…")

    def _answer_error(self, message: str) -> None:
        self.status.setText(message)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        QTimer.singleShot(0, self._exclude_from_capture)

    def _exclude_from_capture(self) -> None:
        if sys.platform != "win32":
            return
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.SetWindowDisplayAffinity.argtypes = [ctypes.c_void_p, ctypes.c_uint]
        user32.SetWindowDisplayAffinity.restype = ctypes.c_int
        self.capture_excluded = bool(
            user32.SetWindowDisplayAffinity(int(self.winId()), 0x00000011)
        )
        if not self.capture_excluded and self.stack.currentIndex() == 1:
            self.status.setText("窗口捕获排除未生效；请勿假定屏幕共享中不可见。")

    def closeEvent(self, event) -> None:
        self.active = False
        self._save_profile()
        try:
            self.config.save_api_key(self.api_key.text())
        except OSError as exc:
            QMessageBox.warning(self, "保存 API Key 失败", str(exc))
            event.ignore()
            return
        self.speech.stop()
        super().closeEvent(event)
        if event.isAccepted():
            self.closed.emit()

    async def shutdown(self) -> None:
        await self.service.close()
