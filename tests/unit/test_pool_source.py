"""Unit — strategy di provisioning del pool (plan 002, D-P4/D-P5/D-P7).

Il pool può essere una semplice cartella locale (default) o venire
popolato da Internet Archive via archivedigger. La strategy è idempotente:
conta i file già idonei e scarica solo la differenza.
"""

import numpy as np
import soundfile as sf

from src.provisioning.pool_source import count_suitable_files


def write_wav(path, seconds, sample_rate=48000):
    frames = round(seconds * sample_rate)
    sf.write(str(path), np.zeros(frames, dtype=np.float32), sample_rate)


class TestCountSuitableFiles:
    def test_conta_solo_i_file_abbastanza_lunghi(self, tmp_path):
        write_wav(tmp_path / "corto.wav", 0.2)
        write_wav(tmp_path / "lungo.wav", 2.0)
        write_wav(tmp_path / "esatto.wav", 1.0)
        (tmp_path / "non_audio.txt").write_text("x")
        assert count_suitable_files(tmp_path, min_duration=1.0) == 2

    def test_cartella_mancante_conta_zero(self, tmp_path):
        assert count_suitable_files(tmp_path / "inesistente",
                                    min_duration=1.0) == 0
