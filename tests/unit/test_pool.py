"""Unit — il seam `pool`: cos'è un pool valido lo sa UN modulo solo.

Render e provisioning importano da qui: niente più import di privati
del renderer attraverso i confini dei sottosistemi.
"""

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from audiolayers.audio.pool import (AUDIO_EXTENSIONS, count_suitable_files,
                             resolve_pool, scan_pool)


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


class TestResolvePool:
    """Issue #13: la cartella pool del layer è derivabile. La tabella
    completa dei casi sta in docs/plans/2026-07-06-004-pool-dinamico.md."""

    def test_pool_esplicito_senza_globale_resta_quello(self):
        layer = {"layer_id": "a", "pool": "campioni/mare/"}
        assert resolve_pool(layer) == Path("campioni/mare")

    def test_pool_assente_senza_globale_deriva_dal_layer_id(self):
        assert resolve_pool({"layer_id": "strato07"}) == \
            Path("audio/pool/strato07")

    def test_pool_assente_con_globale_condivide_la_base(self):
        score = {"provision": {"pool": "downloads/"}}
        assert resolve_pool({"layer_id": "a"}, score) == Path("downloads")
        assert resolve_pool({"layer_id": "b"}, score) == Path("downloads")

    def test_auto_con_globale_apre_la_sottocartella_del_layer(self):
        score = {"provision": {"pool": "downloads/"}}
        layer = {"layer_id": "strato00", "pool": "auto"}
        assert resolve_pool(layer, score) == Path("downloads/strato00")

    def test_pool_esplicito_vince_sulla_base_globale(self):
        score = {"provision": {"pool": "downloads/"}}
        layer = {"layer_id": "a", "pool": "campioni/mare/"}
        assert resolve_pool(layer, score) == Path("campioni/mare")

    def test_auto_senza_globale_equivale_ad_assente(self):
        assert resolve_pool({"layer_id": "a", "pool": "auto"}) == \
            Path("audio/pool/a")

    def test_provision_globale_senza_pool_non_attiva_la_condivisione(self):
        """Blocco provision di radice senza `pool` (issue #8 puro): i
        layer senza override restano sul default derivato."""
        score = {"provision": {"mode": "fixed", "count": 3}}
        assert resolve_pool({"layer_id": "a"}, score) == Path("audio/pool/a")


class TestCountSuitable:
    def test_conta_per_durata_reale(self, tmp_path):
        write_wav(tmp_path / "corto.wav", 0.2)
        write_wav(tmp_path / "lungo.wav", 2.0)
        assert count_suitable_files(tmp_path, min_duration=1.0) == 1

    def test_cartella_mancante_zero(self, tmp_path):
        assert count_suitable_files(tmp_path / "no", min_duration=1.0) == 0
