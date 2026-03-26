"""
Speech-to-text: record one utterance from the microphone, transcribe with faster-whisper, return plain text.
"""

from __future__ import annotations

import tempfile
import wave
from pathlib import Path

RECORD_SECONDS = 3
SAMPLE_RATE = 16000
INPUT_DEVICE = None  # None = default input device


WHISPER_MODEL_SIZE = "base"
WHISPER_DEVICE = "cpu"
WHISPER_COMPUTE_TYPE = "int8"  # int8 for CPU, "float16" for GPU


_whisper_model = None


def _get_model():
    global _whisper_model
    if _whisper_model is None:
        try:
            from faster_whisper import WhisperModel
        except ImportError as e:
            raise ImportError(
                "faster-whisper is not installed. Install with: pip install faster-whisper"
            ) from e
        _whisper_model = WhisperModel(
            WHISPER_MODEL_SIZE,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE_TYPE,
        )
    return _whisper_model


def _record_audio() -> Path:
    """Record from microphone to a temporary WAV file. Returns path to the file."""
    try:
        import sounddevice as sd
        import numpy as np
    except ImportError as e:
        raise ImportError(
            "sounddevice and numpy are required. Install with: pip install sounddevice numpy"
        ) from e

    try:
        devices = sd.query_devices()
    except Exception as e:
        raise RuntimeError(
            "Could not query audio devices. Is a microphone connected and drivers installed?"
        ) from e

    default_input = sd.default.device[0]
    if default_input is None or default_input < 0:
        raise RuntimeError(
            "No default input device found. Check microphone permissions and system settings."
        )

    device = INPUT_DEVICE if INPUT_DEVICE is not None else default_input
    channels = 1
    dtype = np.int16

    try:
        recording = sd.rec(
            frames=int(RECORD_SECONDS * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=channels,
            dtype=dtype,
            device=device,
        )
        sd.wait()
    except Exception as e:
        raise RuntimeError(
            f"Failed to record from microphone (device={device}). "
            "Check permissions and that the device is not in use."
        ) from e

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp_path = Path(tmp.name)
    tmp.close()

    try:
        with wave.open(str(tmp_path), "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(2)  # 16-bit = 2 bytes
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(recording.tobytes())
    except Exception as e:
        tmp_path.unlink(missing_ok=True)
        raise RuntimeError(f"Failed to write temporary WAV file: {e}") from e

    return tmp_path


def transcribe_once() -> str:

    wav_path = None
    try:
        wav_path = _record_audio()
        model = _get_model()
        segments, _ = model.transcribe(
            str(wav_path),
            beam_size=1,
            language=None,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500, speech_pad_ms=200),
        )
        parts = [s.text.strip() for s in segments if s.text]
        text = " ".join(parts).strip()
    finally:
        if wav_path is not None and wav_path.exists():
            wav_path.unlink(missing_ok=True)

    if not text:
        raise ValueError("Empty transcript: no speech detected or model produced no text.")

    return text
