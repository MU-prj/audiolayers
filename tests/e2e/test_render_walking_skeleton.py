"""E2E — walking skeleton (M1): la CLI renderizza una partitura minima.

Caso minimo assoluto: 1 layer, 1 file sorgente, selezione sequenziale,
durata frammento fissa, fill_factor=1, distribution=0, nessuna componente
stocastica. Con F=1 e durate fisse i frammenti tassellano esattamente la
durata-obiettivo (D7), quindi la lunghezza dell'output è deterministica.
"""

import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

PROJECT_SR = 48000


@pytest.fixture
def score_and_pool(tmp_path: Path) -> dict:
    """Crea un pool con una sinusoide di 1 s e una partitura minima."""
    pool_dir = tmp_path / "pool"
    pool_dir.mkdir()
    t = np.arange(PROJECT_SR) / PROJECT_SR
    sine = 0.5 * np.sin(2 * np.pi * 440.0 * t)
    sf.write(pool_dir / "sine.wav", sine.astype(np.float32), PROJECT_SR)

    score = tmp_path / "score.yaml"
    score.write_text(
        f"""\
sample_rate: {PROJECT_SR}
layers:
  - layer_id: "solo_layer"
    duration: 2.0
    pool: "{pool_dir.as_posix()}"
    fill_factor: 1.0
    fragment:
      duration: 0.5
""",
        encoding="utf-8",
    )
    return {"score": score, "output": tmp_path / "out.wav"}


def _run_cli(score: Path, output: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "src.main", str(score), "-o", str(output)],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[2],
    )


@pytest.mark.e2e
def test_render_produce_wav_stereo_48k_durata_esatta(score_and_pool):
    result = _run_cli(score_and_pool["score"], score_and_pool["output"])

    assert result.returncode == 0, f"CLI fallita:\n{result.stderr}"
    out = score_and_pool["output"]
    assert out.exists(), "il file di output non è stato creato"

    info = sf.info(str(out))
    assert info.samplerate == PROJECT_SR
    assert info.channels == 2
    assert info.subtype == "FLOAT"  # float32 di default (D1/D16)
    # 4 frammenti da 0.5 s back-to-back → 2.0 s esatti (D2, D7)
    assert info.frames == 2 * PROJECT_SR


@pytest.mark.e2e
def test_output_contiene_audio_non_silenzio(score_and_pool):
    """La sinusoide del pool deve arrivare nell'output: RMS coerente.

    Sorgente: sinusoide ampiezza 0.5 → RMS 0.5/√2 ≈ 0.354.
    Pan a 0° (D12): ogni canale = segnale/√2 → RMS atteso ≈ 0.25,
    meno l'energia dei fade dell'inviluppo anti-click di default
    (raised cosine 8+10 ms su frammenti da 0.5 s, D11) → tolleranza 2%.
    """
    result = _run_cli(score_and_pool["score"], score_and_pool["output"])
    assert result.returncode == 0, f"CLI fallita:\n{result.stderr}"

    audio, _ = sf.read(str(score_and_pool["output"]), always_2d=True)
    rms = np.sqrt(np.mean(audio**2, axis=0))
    assert rms[0] == pytest.approx(0.25, rel=0.02)
    assert rms[1] == pytest.approx(0.25, rel=0.02)


@pytest.mark.e2e
def test_pan_al_centro_produce_canali_identici(score_and_pool):
    """Pan default 0° = centro (D12): L e R identici campione per campione."""
    result = _run_cli(score_and_pool["score"], score_and_pool["output"])
    assert result.returncode == 0, f"CLI fallita:\n{result.stderr}"

    audio, _ = sf.read(str(score_and_pool["output"]), always_2d=True)
    assert np.array_equal(audio[:, 0], audio[:, 1])
