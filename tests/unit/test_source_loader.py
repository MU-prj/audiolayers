"""Unit — caricamento sorgenti (M7, D13): mono, SR di progetto.

- file al SR di progetto → passthrough
- SR diverso → resampling (soxr, fallback scipy) trasparente
- stereo → downmix a mono (D12)
"""

import numpy as np
import pytest
import soundfile as sf

from audiolayers.audio.source_loader import load_mono

SR = 48000


def write_sine(path, sr, freq=440.0, seconds=1.0, channels=1):
    t = np.arange(int(sr * seconds)) / sr
    sine = 0.5 * np.sin(2 * np.pi * freq * t)
    data = sine if channels == 1 else np.column_stack([sine, sine * 0.5])
    sf.write(str(path), data.astype(np.float32), sr)


def dominant_freq(signal, sr):
    spec = np.abs(np.fft.rfft(signal))
    return np.fft.rfftfreq(len(signal), 1 / sr)[spec.argmax()]


def test_sr_di_progetto_passthrough(tmp_path):
    write_sine(tmp_path / "a.wav", SR)
    data = load_mono(tmp_path / "a.wav", SR)
    assert data.ndim == 1
    assert len(data) == SR


def test_resampling_preserva_durata_e_frequenza(tmp_path):
    write_sine(tmp_path / "b.wav", 44100, freq=440.0)
    data = load_mono(tmp_path / "b.wav", SR)
    assert len(data) == pytest.approx(SR, abs=2)      # 1 s al nuovo SR
    assert dominant_freq(data, SR) == pytest.approx(440.0, abs=1.0)


def test_stereo_downmix_a_mono(tmp_path):
    write_sine(tmp_path / "c.wav", SR, channels=2)
    data = load_mono(tmp_path / "c.wav", SR)
    assert data.ndim == 1
    # media dei canali: (1.0 + 0.5) / 2 = 0.75 dell'ampiezza originale
    assert np.abs(data).max() == pytest.approx(0.5 * 0.75, rel=0.01)
