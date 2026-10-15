from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from src.client import gui
from src.config import config as config_module
from src.modules.local_speech import AudioSelection, AudioSource


def test_audio_mode_selects_playback_microphone_or_both(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module, "app_dir", lambda: tmp_path)
    speaker = AudioSource("loopback", 1, "扬声器", 48000, 2)
    microphone = AudioSource("microphone", 2, "麦克风", 44100, 1)
    monkeypatch.setattr(gui, "list_audio_sources", lambda: [speaker, microphone])
    app = QApplication.instance() or QApplication([])
    window = gui.MainWindow()

    assert window._selected_audio_source() == speaker
    window.source_mode.setCurrentIndex(1)
    assert window._selected_audio_source() == microphone
    window.source_mode.setCurrentIndex(2)
    assert window._selected_audio_source() == AudioSelection(speaker, microphone)
    assert window.speaker_combo.isEnabled() and window.microphone_combo.isEnabled()
    window._set_taskbar_hidden(True)
    assert window.windowFlags() & Qt.WindowType.WindowType_Mask == Qt.WindowType.Tool
    window._set_taskbar_hidden(False)
    assert window.windowFlags() & Qt.WindowType.WindowType_Mask == Qt.WindowType.Window
    window.close()
