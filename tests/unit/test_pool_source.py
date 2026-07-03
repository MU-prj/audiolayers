"""Unit — strategy di provisioning del pool (plan 002, D-P4/D-P5/D-P7).

Il pool può essere una semplice cartella locale (default) o venire
popolato da Internet Archive via archivedigger. La strategy è idempotente:
conta i file già idonei e scarica solo la differenza.
"""

import numpy as np
import soundfile as sf
from archivedigger.models import IAFile, IAItem

from src.provisioning.pool_source import (ArchiveDiggerSource,
                                          count_suitable_files)


def write_wav(path, seconds, sample_rate=48000):
    frames = round(seconds * sample_rate)
    sf.write(str(path), np.zeros(frames, dtype=np.float32), sample_rate)


class FakeArchiveClient:
    """Client Internet Archive finto: cataloghi in memoria, download che
    scrive wav reali. Registra query e max_items ricevuti."""

    def __init__(self, n_items=50, length=5.0):
        self._length = length
        self._ids = [f"item-{i:03d}" for i in range(n_items)]
        self.queries: list[str] = []
        self.max_items_seen: list[int] = []

    def search(self, query, sort="downloads desc", max_items=100):
        self.queries.append(query)
        self.max_items_seen.append(max_items)
        yield from self._ids[:max_items]

    def get_item(self, identifier):
        file = IAFile(name=f"{identifier}.wav", format="WAVE",
                      size=1000, length=self._length, source="original")
        return IAItem(identifier=identifier, metadata={}, files=[file])

    def download_file(self, item, file, local_path):
        local_path.parent.mkdir(parents=True, exist_ok=True)
        write_wav(local_path, self._length)


DET_LAYER = {
    "layer_id": "det",
    "duration": 2.0,
    "fill_factor": 1.0,
    "fragment": {"duration": 0.5},
}


class TestArchiveDiggerSource:
    def test_pool_vuoto_scarica_un_file_per_frammento(self, tmp_path):
        """Layer da 4 frammenti, pool vuoto → 4 file idonei scaricati."""
        pool = tmp_path / "pool"
        layer = dict(DET_LAYER, pool=str(pool))
        client = FakeArchiveClient()
        ArchiveDiggerSource(client=client).ensure(layer, seed=1)
        assert count_suitable_files(pool, min_duration=0.5) == 4


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
