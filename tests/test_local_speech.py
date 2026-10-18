import numpy as np

from src.modules import local_speech
from src.modules.local_speech import AudioSelection, AudioSource, pcm_to_mono, resample_chunk


def test_bundled_model_precedes_legacy_directory(tmp_path, monkeypatch):
    bundled = tmp_path / "models" / local_speech.MODEL_NAME
    bundled.mkdir(parents=True)
    monkeypatch.setattr(local_speech, "app_dir", lambda: tmp_path)
    monkeypatch.delenv("INTERVIEW_ASR_MODEL_DIR", raising=False)
    assert local_speech.model_dir() == bundled

    monkeypatch.setenv("INTERVIEW_ASR_MODEL_DIR", str(tmp_path / "custom"))
    assert local_speech.model_dir() == tmp_path / "custom"

    monkeypatch.delenv("INTERVIEW_ASR_MODEL_DIR")
    bundled.rmdir()
    assert local_speech.model_dir() == local_speech.DEFAULT_MODEL_DIR


def test_stereo_pcm_is_mixed_to_mono():
    stereo = np.array([32767, 0, 0, -32768], dtype="<i2")
    mono = pcm_to_mono(stereo.tobytes(), 2)
    assert mono.shape == (2,)
    assert np.isclose(mono[0], 0.5, atol=0.001)
    assert np.isclose(mono[1], -0.5, atol=0.001)


def test_combined_audio_uses_two_devices_and_common_sample_rate():
    speaker = AudioSource("loopback", 1, "扬声器", 48000, 2)
    microphone = AudioSource("microphone", 2, "麦克风", 44100, 1)
    selection = AudioSelection(speaker, microphone)
    assert "扬声器" in selection.label and "麦克风" in selection.label
    assert len(resample_chunk(np.ones(4800, dtype=np.float32), 48000)) == 1600
    assert len(resample_chunk(np.ones(4410, dtype=np.float32), 44100)) == 1600
