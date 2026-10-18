from __future__ import annotations

import os
import queue
import threading
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from time import monotonic

import numpy as np
import pyaudiowpatch as pyaudio
import sherpa_onnx
from PyQt6.QtCore import QObject, pyqtSignal
from src.config.config import app_dir


MODEL_NAME = "sherpa-onnx-streaming-paraformer-bilingual-zh-en"
DEFAULT_MODEL_DIR = Path(r"D:\Codex\models\interview-asr") / MODEL_NAME


def model_dir() -> Path:
    configured = os.environ.get("INTERVIEW_ASR_MODEL_DIR")
    if configured:
        return Path(configured)
    bundled = app_dir() / "models" / MODEL_NAME
    return bundled if bundled.is_dir() else DEFAULT_MODEL_DIR


@dataclass(frozen=True)
class AudioSource:
    kind: str
    index: int
    name: str
    sample_rate: int
    channels: int
    is_default: bool = False

    @property
    def label(self) -> str:
        prefix = "会议声音" if self.kind == "loopback" else "麦克风"
        default = "（默认）" if self.is_default else ""
        name = self.name.replace("\ufffd", "").strip()
        return f"{prefix}{default} · {name or f'设备 {self.index}'}"


@dataclass(frozen=True)
class AudioSelection:
    loopback: AudioSource
    microphone: AudioSource

    @property
    def label(self) -> str:
        return f"会议声音 + 麦克风 · {self.loopback.name} / {self.microphone.name}"


def list_audio_sources() -> list[AudioSource]:
    """List WASAPI playback loopbacks and microphone inputs, default first."""
    with pyaudio.PyAudio() as audio:
        try:
            default_loopback = int(audio.get_default_wasapi_loopback()["index"])
        except (OSError, LookupError):
            default_loopback = -1
        try:
            default_mic = int(audio.get_default_wasapi_device(d_in=True)["index"])
        except (OSError, LookupError):
            default_mic = -1
        loopbacks = list(audio.get_loopback_device_info_generator())
        loopback_ids = {int(device["index"]) for device in loopbacks}
        inputs = [
            device
            for device in audio.get_device_info_generator_by_host_api(
                host_api_type=pyaudio.paWASAPI
            )
            if int(device["index"]) not in loopback_ids
            and int(device["maxInputChannels"]) > 0
        ]

    def convert(device: dict, kind: str, default_index: int) -> AudioSource:
        return AudioSource(
            kind=kind,
            index=int(device["index"]),
            name=str(device["name"]),
            sample_rate=int(device["defaultSampleRate"]),
            channels=min(2, int(device["maxInputChannels"])),
            is_default=int(device["index"]) == default_index,
        )

    sources = [convert(d, "loopback", default_loopback) for d in loopbacks]
    sources += [convert(d, "microphone", default_mic) for d in inputs]
    return sorted(sources, key=lambda s: (s.kind != "loopback", not s.is_default, s.index))


def pcm_to_mono(data: bytes, channels: int) -> np.ndarray:
    samples = np.frombuffer(data, dtype="<i2").astype(np.float32) / 32768.0
    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)
    return samples


def resample_chunk(samples: np.ndarray, rate: int, target_rate: int = 16000) -> np.ndarray:
    """Convert a 100 ms capture chunk to the recognizer sample rate."""
    target_length = max(1, round(len(samples) * target_rate / rate))
    return np.interp(
        np.linspace(0, len(samples), target_length, endpoint=False),
        np.arange(len(samples)),
        samples,
    ).astype(np.float32)


def check_audio_pipeline() -> str:
    """Load the model and read one playback chunk for packaged diagnostics."""
    sources = list_audio_sources()
    source = next((item for item in sources if item.kind == "loopback"), None)
    if source is None:
        raise RuntimeError("没有找到可用的播放设备回环输入。")
    directory = model_dir()
    recognizer = sherpa_onnx.OnlineRecognizer.from_paraformer(
        tokens=str(directory / "tokens.txt"),
        encoder=str(directory / "encoder.int8.onnx"),
        decoder=str(directory / "decoder.int8.onnx"),
        num_threads=2,
        sample_rate=16000,
        feature_dim=80,
    )
    stream = recognizer.create_stream()
    frames = max(1, source.sample_rate // 10)
    with pyaudio.PyAudio() as audio:
        with audio.open(
            format=pyaudio.paInt16,
            channels=source.channels,
            rate=source.sample_rate,
            input=True,
            input_device_index=source.index,
            frames_per_buffer=frames,
        ) as capture:
            raw = capture.read(frames, exception_on_overflow=False)
    stream.accept_waveform(source.sample_rate, pcm_to_mono(raw, source.channels))
    while recognizer.is_ready(stream):
        recognizer.decode_stream(stream)
    return source.label


class SpeechSignals(QObject):
    ready = pyqtSignal(str)
    partial = pyqtSignal(str)
    final = pyqtSignal(str)
    level = pyqtSignal(int)
    error = pyqtSignal(str)


class UtteranceBoundary:
    """Detect a completed utterance when the model does not report an endpoint."""

    QUIET_LEVEL = 18
    QUIET_SECONDS = 0.9
    STABLE_SECONDS = 1.4
    NOISY_STABLE_SECONDS = 3.0

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.last_text = ""
        self.last_change_at: float | None = None
        self.last_loud_at: float | None = None

    def observe(self, text: str, level: int, now: float, endpoint: bool) -> bool:
        if text != self.last_text:
            self.last_text = text
            self.last_change_at = now
        if level >= self.QUIET_LEVEL:
            self.last_loud_at = now
        if not text:
            return False
        if endpoint:
            return True
        if self.last_change_at is None:
            return False
        stable_for = now - self.last_change_at
        quiet_for = float("inf") if self.last_loud_at is None else now - self.last_loud_at
        return (stable_for >= self.STABLE_SECONDS and quiet_for >= self.QUIET_SECONDS) or (
            stable_for >= self.NOISY_STABLE_SECONDS
        )


class LocalSpeechRecognizer:
    def __init__(self, signals: SpeechSignals) -> None:
        self.signals = signals
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._paused = threading.Event()
        self._discard_current = threading.Event()

    def start(self, source: AudioSource | AudioSelection) -> None:
        if self._thread is not None and self._thread.is_alive():
            raise RuntimeError("语音识别仍在运行，请先停止。")
        directory = model_dir()
        required = ("tokens.txt", "encoder.int8.onnx", "decoder.int8.onnx")
        missing = [name for name in required if not (directory / name).is_file()]
        if missing:
            raise FileNotFoundError(f"本地语音模型不完整：{directory}；缺少 {', '.join(missing)}")
        self._stop.clear()
        self._paused.clear()
        self._discard_current.clear()
        self._thread = threading.Thread(target=self._run, args=(source, directory), daemon=True)
        self._thread.start()

    def pause(self, paused: bool) -> None:
        if paused:
            self._paused.set()
        else:
            self._paused.clear()

    def discard_current_utterance(self) -> None:
        """Start a fresh recognition stream after a manually submitted question."""
        self._discard_current.set()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=5)
        if self._thread is not None and not self._thread.is_alive():
            self._thread = None

    def _mixed_chunks(self, source: AudioSelection):
        queues: list[queue.Queue[np.ndarray]] = [queue.Queue(maxsize=10), queue.Queue(maxsize=10)]
        failures: queue.Queue[Exception] = queue.Queue()

        def capture(device: AudioSource, stream, chunks: queue.Queue[np.ndarray]) -> None:
            try:
                frames = max(1, device.sample_rate // 10)
                while not self._stop.is_set():
                    raw = stream.read(frames, exception_on_overflow=False)
                    samples = resample_chunk(pcm_to_mono(raw, device.channels), device.sample_rate)
                    try:
                        chunks.put_nowait(samples)
                    except queue.Full:
                        chunks.get_nowait()
                        chunks.put_nowait(samples)
            except Exception as exc:
                failures.put(exc)

        with ExitStack() as stack:
            audio = stack.enter_context(pyaudio.PyAudio())
            devices = (source.loopback, source.microphone)
            streams = [
                stack.enter_context(audio.open(
                    format=pyaudio.paInt16,
                    channels=device.channels,
                    rate=device.sample_rate,
                    input=True,
                    input_device_index=device.index,
                    frames_per_buffer=max(1, device.sample_rate // 10),
                ))
                for device in devices
            ]
            threads = [
                threading.Thread(target=capture, args=(device, stream, chunks), daemon=True)
                for device, stream, chunks in zip(devices, streams, queues)
            ]
            for thread in threads:
                thread.start()
            try:
                while not self._stop.is_set():
                    if not failures.empty():
                        raise failures.get_nowait()
                    try:
                        playback = queues[0].get(timeout=0.2)
                    except queue.Empty:
                        continue
                    try:
                        microphone = queues[1].get_nowait()
                    except queue.Empty:
                        microphone = np.zeros_like(playback)
                    yield 16000, np.clip((playback + microphone) * 0.7, -1.0, 1.0)
            finally:
                self._stop.set()
                for thread in threads:
                    thread.join(timeout=2)

    def _single_chunks(self, source: AudioSource):
        frames = max(1, source.sample_rate // 10)
        with pyaudio.PyAudio() as audio:
            with audio.open(
                format=pyaudio.paInt16,
                channels=source.channels,
                rate=source.sample_rate,
                input=True,
                input_device_index=source.index,
                frames_per_buffer=frames,
            ) as capture:
                while not self._stop.is_set():
                    raw = capture.read(frames, exception_on_overflow=False)
                    yield source.sample_rate, pcm_to_mono(raw, source.channels)

    def _run(self, source: AudioSource | AudioSelection, directory: Path) -> None:
        try:
            recognizer = sherpa_onnx.OnlineRecognizer.from_paraformer(
                tokens=str(directory / "tokens.txt"),
                encoder=str(directory / "encoder.int8.onnx"),
                decoder=str(directory / "decoder.int8.onnx"),
                num_threads=2,
                sample_rate=16000,
                feature_dim=80,
                enable_endpoint_detection=True,
                rule1_min_trailing_silence=2.4,
                rule2_min_trailing_silence=1.2,
                rule3_min_utterance_length=300,
            )
            stream = recognizer.create_stream()
            last_partial = ""
            boundary = UtteranceBoundary()
            was_paused = False
            chunks = self._mixed_chunks(source) if isinstance(source, AudioSelection) else self._single_chunks(source)
            self.signals.ready.emit(source.label)
            for sample_rate, samples in chunks:
                if self._paused.is_set():
                    if not was_paused:
                        recognizer.reset(stream)
                        last_partial = ""
                        boundary.reset()
                        was_paused = True
                    self.signals.level.emit(0)
                    continue
                was_paused = False
                if self._discard_current.is_set():
                    recognizer.reset(stream)
                    last_partial = ""
                    boundary.reset()
                    self._discard_current.clear()
                level = min(100, int(np.sqrt(np.mean(samples * samples)) * 1000))
                self.signals.level.emit(level)
                stream.accept_waveform(sample_rate, samples)
                while recognizer.is_ready(stream):
                    recognizer.decode_stream(stream)
                result = recognizer.get_result(stream).strip()
                if result and result != last_partial:
                    last_partial = result
                    self.signals.partial.emit(result)
                if boundary.observe(result, level, monotonic(), recognizer.is_endpoint(stream)):
                    if result:
                        self.signals.final.emit(result)
                    recognizer.reset(stream)
                    last_partial = ""
                    boundary.reset()
        except Exception as exc:
            if not self._stop.is_set():
                self.signals.error.emit(f"本地语音识别失败：{exc}")
