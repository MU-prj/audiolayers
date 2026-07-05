"""Integration — stadio di output del motore (M9, D1, D16).

Chiude in-process (chiamando `render_score` diretto) i rami di `render.py`
che finora erano esercitati SOLO dagli e2e via subprocess, quindi invisibili
a coverage: report del picco/CLIPPING, `--normalize`, risoluzione del formato
(flag esplicito incluso l'alias `aif`), e bit depth / PCM_24.

Complementari agli e2e di `tests/e2e/test_cli_master.py`: là si verifica la
CLI vera end-to-end, qui il contratto del motore a livello di funzione.
"""

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from audiolayers.engine.render import render_score

SR = 48000


def _write_score(tmp_path: Path, pool: Path, *, master="0.0",
                 volume="0.0", envelope="raised_cosine", amp=0.5) -> Path:
    """Partitura a un layer, un frammento; parametri d'ampiezza pilotabili
    per portare (o no) il mix oltre 0 dBFS."""
    pool.mkdir(exist_ok=True)
    t = np.arange(SR) / SR
    sf.write(pool / "sine.wav",
             (amp * np.sin(2 * np.pi * 440 * t)).astype(np.float32), SR)
    score = tmp_path / "score.yaml"
    score.write_text(f"""\
seed: 1
master_volume: {master}
layers:
  - layer_id: "l"
    duration: 1.0
    pool: "{pool.as_posix()}"
    volume: {volume}
    fragment: {{duration: 0.5, envelope: {envelope}}}
""", encoding="utf-8")
    return score


class TestReportPicco:
    def test_picco_sotto_zero_dbfs_riportato(self, tmp_path, capsys):
        score = _write_score(tmp_path, tmp_path / "pool")
        render_score(score, tmp_path / "out.wav")
        out = capsys.readouterr().out
        assert "picco:" in out
        assert "CLIPPING" not in out

    def test_clipping_riportato_quando_supera_zero_dbfs(self, tmp_path, capsys):
        # sorgente quasi a fondo scala + boost master: il mix supera 1.0.
        score = _write_score(tmp_path, tmp_path / "pool",
                             amp=0.9, master="6.0", envelope="rectangle")
        render_score(score, tmp_path / "out.wav")
        out = capsys.readouterr().out
        assert "CLIPPING" in out
        assert "riduci master_volume" in out
        # senza --normalize il messaggio suggerisce la via alternativa
        assert "--normalize" in out

    def test_silenzio_assoluto_riportato(self, tmp_path, capsys):
        # sorgente muta (ampiezza 0): il mix è zero esatto, non solo basso.
        score = _write_score(tmp_path, tmp_path / "pool", amp=0.0)
        render_score(score, tmp_path / "out.wav")
        assert "silenzio assoluto" in capsys.readouterr().out


class TestNormalize:
    def test_normalize_porta_il_picco_a_meno_1_dbfs(self, tmp_path, capsys):
        score = _write_score(tmp_path, tmp_path / "pool", amp=0.2)
        out_path = tmp_path / "out.wav"
        render_score(score, out_path, normalize=True)
        assert "normalizzato a -1.00 dBFS" in capsys.readouterr().out
        audio, _ = sf.read(str(out_path), always_2d=True)
        peak_db = 20 * np.log10(np.abs(audio).max())
        assert peak_db == pytest.approx(-1.0, abs=0.05)

    def test_normalize_riscala_anche_un_mix_che_clippava(self, tmp_path, capsys):
        score = _write_score(tmp_path, tmp_path / "pool",
                             amp=0.9, master="6.0", envelope="rectangle")
        out_path = tmp_path / "out.wav"
        render_score(score, out_path, normalize=True)
        out = capsys.readouterr().out
        # riporta comunque il clipping originale, ma senza il suggerimento
        assert "CLIPPING" in out and "--normalize" not in out
        audio, _ = sf.read(str(out_path), always_2d=True)
        assert np.abs(audio).max() == pytest.approx(10 ** (-1 / 20), abs=1e-4)


class TestRisoluzioneFormato:
    def test_flag_esplicito_vince_sull_estensione(self, tmp_path):
        score = _write_score(tmp_path, tmp_path / "pool")
        out_path = tmp_path / "out.wav"          # estensione .wav...
        render_score(score, out_path, output_format="aiff")  # ...ma flag AIFF
        assert sf.info(str(out_path)).format == "AIFF"

    def test_alias_aif_diventa_aiff(self, tmp_path):
        score = _write_score(tmp_path, tmp_path / "pool")
        out_path = tmp_path / "out.aif"
        render_score(score, out_path, output_format="aif")
        assert sf.info(str(out_path)).format == "AIFF"

    def test_formato_inferito_dall_estensione(self, tmp_path):
        score = _write_score(tmp_path, tmp_path / "pool")
        out_path = tmp_path / "out.flac"
        render_score(score, out_path)            # nessun flag
        assert sf.info(str(out_path)).format == "FLAC"

    def test_estensione_sconosciuta_ripiega_su_wav(self, tmp_path):
        score = _write_score(tmp_path, tmp_path / "pool")
        out_path = tmp_path / "out.bin"
        render_score(score, out_path)
        assert sf.info(str(out_path)).format == "WAV"


class TestBitDepth:
    def test_default_float32(self, tmp_path):
        score = _write_score(tmp_path, tmp_path / "pool")
        out_path = tmp_path / "out.wav"
        render_score(score, out_path)
        assert sf.info(str(out_path)).subtype == "FLOAT"

    def test_bit_depth_24_da_pcm(self, tmp_path):
        score = _write_score(tmp_path, tmp_path / "pool")
        out_path = tmp_path / "out.wav"
        render_score(score, out_path, bit_depth="24")
        assert sf.info(str(out_path)).subtype == "PCM_24"

    def test_flac_e_sempre_pcm24_anche_con_32f(self, tmp_path):
        score = _write_score(tmp_path, tmp_path / "pool")
        out_path = tmp_path / "out.flac"
        render_score(score, out_path, output_format="flac", bit_depth="32f")
        info = sf.info(str(out_path))
        assert info.format == "FLAC" and info.subtype == "PCM_24"
