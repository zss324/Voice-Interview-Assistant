import numpy as np
from types import SimpleNamespace

from src.modules import local_speech
from src.modules.local_speech import AudioSelection, AudioSource, UtteranceBoundary, pcm_to_mono, resample_chunk


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


def test_utterance_finishes_after_quiet_stable_text_and_resets():
    boundary = UtteranceBoundary()
    assert not boundary.observe("请介绍一下自己", 50, 0.0, False)
    assert not boundary.observe("请介绍一下自己", 0, 0.8, False)
    assert boundary.observe("请介绍一下自己", 0, 1.5, False)
    boundary.reset()
    assert not boundary.observe("你的项目是什么", 45, 2.0, False)


def test_utterance_finishes_after_silence_even_if_partial_text_keeps_changing():
    boundary = UtteranceBoundary()
    assert not boundary.observe("请介绍", 70, 0.0, False)
    assert not boundary.observe("请介绍一下", 0, 0.8, False)
    assert boundary.observe("请介绍一下自己", 0, 1.5, False)


def test_utterance_finishes_when_model_endpoint_or_noisy_text_stabilizes():
    boundary = UtteranceBoundary()
    assert boundary.observe("Java 基础数据类型有哪些", 40, 0.0, True)
    boundary.reset()
    assert not boundary.observe("为什么这样设计", 50, 1.0, False)
    assert not boundary.observe("为什么这样设计", 50, 3.9, False)
    assert boundary.observe("为什么这样设计", 50, 4.1, False)


def test_small_recognition_corrections_do_not_extend_noisy_wait_forever():
    boundary = UtteranceBoundary()
    assert not boundary.observe("你的项目是什么", 50, 0.0, False)
    assert not boundary.observe("你的项目是什么?", 50, 1.0, False)
    assert not boundary.observe("你的项目是什么？", 50, 2.0, False)
    assert boundary.observe("你的项目是什么？", 50, 3.1, False)


def test_continuously_changing_recognition_has_a_maximum_segment_length():
    boundary = UtteranceBoundary()
    assert not boundary.observe("请介绍", 50, 0.0, False)
    assert not boundary.observe("请介绍你的经历", 50, 4.0, False)
    assert not boundary.observe("请介绍你的经历和项目", 50, 8.0, False)
    assert boundary.observe("请介绍你的经历和项目经验", 50, 12.1, False)


def test_recognizer_emits_separate_questions_without_model_endpoints(tmp_path, monkeypatch):
    class FakeRecognizer:
        resets = 0

        def create_stream(self):
            return SimpleNamespace(accept_waveform=lambda *args: None)

        def is_ready(self, stream):
            return False

        def get_result(self, stream):
            return ("请介绍一下自己", "你的项目是什么")[min(self.resets, 1)]

        def is_endpoint(self, stream):
            return False

        def reset(self, stream):
            self.resets += 1

    fake = FakeRecognizer()
    monkeypatch.setattr(
        local_speech.sherpa_onnx,
        "OnlineRecognizer",
        SimpleNamespace(from_paraformer=lambda **kwargs: fake),
    )
    moments = iter((0.0, 0.8, 1.5, 2.0, 2.8, 3.6))
    monkeypatch.setattr(local_speech, "monotonic", lambda: next(moments))
    loud = np.full(1600, 0.05, dtype=np.float32)
    quiet = np.zeros(1600, dtype=np.float32)
    recognizer = local_speech.LocalSpeechRecognizer(local_speech.SpeechSignals())
    recognizer._single_chunks = lambda source: (
        (16000, samples) for samples in (loud, quiet, quiet, loud, quiet, quiet)
    )
    finals = []
    errors = []
    recognizer.signals.final.connect(finals.append)
    recognizer.signals.error.connect(errors.append)

    recognizer._run(AudioSource("loopback", 1, "扬声器", 16000, 1), tmp_path)

    assert not errors, errors
    assert finals == ["请介绍一下自己", "你的项目是什么"]
    assert fake.resets == 2


def test_recognizer_keeps_last_nonempty_text_when_model_temporarily_returns_blank(tmp_path, monkeypatch):
    class FakeRecognizer:
        def create_stream(self):
            return SimpleNamespace(accept_waveform=lambda *args: None)

        def is_ready(self, stream):
            return False

        def get_result(self, stream):
            return ("请介绍一下自己", "", "")[calls.pop(0)]

        def is_endpoint(self, stream):
            return False

        def reset(self, stream):
            pass

    calls = [0, 1, 2]
    fake = FakeRecognizer()
    monkeypatch.setattr(local_speech.sherpa_onnx, "OnlineRecognizer", SimpleNamespace(from_paraformer=lambda **kwargs: fake))
    moments = iter((0.0, 0.8, 1.5))
    monkeypatch.setattr(local_speech, "monotonic", lambda: next(moments))
    recognizer = local_speech.LocalSpeechRecognizer(local_speech.SpeechSignals())
    recognizer._single_chunks = lambda source: (
        (16000, samples) for samples in (np.full(1600, 0.05, dtype=np.float32), np.zeros(1600, dtype=np.float32), np.zeros(1600, dtype=np.float32))
    )
    finals = []
    recognizer.signals.final.connect(finals.append)
    recognizer._run(AudioSource("loopback", 1, "扬声器", 16000, 1), tmp_path)
    assert finals == ["请介绍一下自己"]
