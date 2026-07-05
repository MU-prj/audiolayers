"""Integration — pipeline completa `--dig`: analisi → download → render.

Il client Internet Archive è finto (scrive wav sintetici), tutto il resto
è codice reale: analyzer, archivedigger, render. Senza `--dig` il
comportamento resta quello di sempre (pool locale, nessuna rete).
"""

import textwrap

import pytest
import soundfile as sf

from audiolayers.main import main
from tests.unit.test_pool_source import FakeArchiveClient


def write_score(tmp_path, pool_dir):
    score = tmp_path / "score.yaml"
    score.write_text(textwrap.dedent(f"""\
        sample_rate: 48000
        seed: 7
        layers:
          - layer_id: "det"
            duration: 2.0
            pool: "{pool_dir.as_posix()}/"
            fill_factor: 1.0
            fragment:
              duration: 0.5
    """), encoding="utf-8")
    return score


class TestDigPipeline:
    def test_dig_scarica_il_pool_e_renderizza(self, tmp_path):
        """Pool inesistente + --dig → il wav esce e il pool è popolato."""
        pool = tmp_path / "pool"
        score = write_score(tmp_path, pool)
        out = tmp_path / "out.wav"

        exit_code = main([str(score), "-o", str(out), "--dig"],
                         client=FakeArchiveClient())

        assert exit_code == 0
        assert out.exists()
        info = sf.info(str(out))
        assert info.frames / info.samplerate == pytest.approx(2.0, abs=0.01)
        assert len(list(pool.glob("*.wav"))) == 4

    def test_senza_dig_pool_mancante_fallisce_come_prima(self, tmp_path):
        """Senza flag nessun download: pool assente → errore, zero rete."""
        pool = tmp_path / "pool"
        score = write_score(tmp_path, pool)
        with pytest.raises(FileNotFoundError):
            main([str(score), "-o", str(tmp_path / "out.wav")])
