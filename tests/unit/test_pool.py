"""Unit — il seam `pool`: cos'è un pool valido lo sa UN modulo solo.

Render e provisioning importano da qui: niente più import di privati
del renderer attraverso i confini dei sottosistemi.
"""

import numpy as np
import pytest
import soundfile as sf

from audiolayers.audio.pool import AUDIO_EXTENSIONS, count_suitable_files, scan_pool


def write_wav(path, seconds, sample_rate=48000):
    frames = round(seconds * sample_rate)
    sf.write(str(path), np.zeros(frames, dtype=np.float32), sample_rate)


class TestScanPool:
    def test_solo_estensioni_audio_in_ordine_stabile(self, tmp_path):
        write_wav(tmp_path / "b.wav", 0.1)
        write_wav(tmp_path / "a.flac", 0.1)
        (tmp_path / "note.txt").write_text("x")
        files = scan_pool(tmp_path)
        assert [f.name for f in files] == ["a.flac", "b.wav"]

    def test_pool_vuoto_errore_esplicito(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            scan_pool(tmp_path)

    def test_estensioni_note(self):
        assert ".wav" in AUDIO_EXTENSIONS and ".flac" in AUDIO_EXTENSIONS


class TestCountSuitable:
    def test_conta_per_durata_reale(self, tmp_path):
        write_wav(tmp_path / "corto.wav", 0.2)
        write_wav(tmp_path / "lungo.wav", 2.0)
        assert count_suitable_files(tmp_path, min_duration=1.0) == 1

    def test_cartella_mancante_zero(self, tmp_path):
        assert count_suitable_files(tmp_path / "no", min_duration=1.0) == 0
