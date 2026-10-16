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


def test_session_opacity_and_temporary_hide_restore(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module, "app_dir", lambda: tmp_path)
    monkeypatch.setattr(gui, "list_audio_sources", lambda: [])
    monkeypatch.setattr(gui.MainWindow, "_exclude_from_capture", lambda self: None)
    app = QApplication.instance() or QApplication([])
    window = gui.MainWindow()
    window.show()

    window.session_opacity.setValue(55)
    assert window.opacity.value() == 55
    assert window.session_opacity_label.text() == "55%"
    window.opacity.setValue(70)
    assert window.session_opacity.value() == 70

    window._hotkey_registered = True
    window._temporarily_hide()
    assert window.isHidden()
    window._restore_window()
    assert not window.isHidden()

    window._hotkey_registered = False
    window.close()
