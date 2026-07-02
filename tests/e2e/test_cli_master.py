"""E2E — CLI (M9): formati di output, bit depth, normalize, report picco."""

import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

SR = 48000


@pytest.fixture
def score(tmp_path: Path) -> Path:
    pool = tmp_path / "pool"
    pool.mkdir()
    t = np.arange(SR) / SR
    sf.write(pool / "sine.wav",
             (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32), SR)
    score = tmp_path / "score.yaml"
    score.write_text(f"""\
seed: 1
layers:
  - layer_id: "l"
    duration: 1.0
    pool: "{pool.as_posix()}"
    fragment: {{duration: 0.5}}
""", encoding="utf-8")
    return score


def run_cli(score, output, *flags):
    return subprocess.run(
        [sys.executable, "-m", "src.main", str(score), "-o", str(output),
         *flags],
        capture_output=True, text=True,
        cwd=Path(__file__).resolve().parents[2],
    )


@pytest.mark.e2e
def test_report_del_picco_sullo_stdout(score, tmp_path):
    result = run_cli(score, tmp_path / "out.wav")
    assert result.returncode == 0, result.stderr
    assert "picco:" in result.stdout      # D16: misura e riporta, sempre


@pytest.mark.e2e
def test_formato_flac_e_aiff(score, tmp_path):
    r = run_cli(score, tmp_path / "out.flac", "--format", "flac")
    assert r.returncode == 0, r.stderr
    info = sf.info(str(tmp_path / "out.flac"))
    assert info.format == "FLAC" and info.subtype == "PCM_24"

    r = run_cli(score, tmp_path / "out.aiff", "--format", "aiff")
    assert r.returncode == 0, r.stderr
    assert sf.info(str(tmp_path / "out.aiff")).format == "AIFF"


@pytest.mark.e2e
def test_formato_inferito_dall_estensione(score, tmp_path):
    r = run_cli(score, tmp_path / "out.flac")
    assert r.returncode == 0, r.stderr
    assert sf.info(str(tmp_path / "out.flac")).format == "FLAC"


@pytest.mark.e2e
def test_bit_depth_24(score, tmp_path):
    r = run_cli(score, tmp_path / "out.wav", "--bit-depth", "24")
    assert r.returncode == 0, r.stderr
    assert sf.info(str(tmp_path / "out.wav")).subtype == "PCM_24"


@pytest.mark.e2e
def test_normalize_porta_il_picco_a_meno_1_dbfs(score, tmp_path):
    r = run_cli(score, tmp_path / "out.wav", "--normalize")
    assert r.returncode == 0, r.stderr
    assert "normalizzato" in r.stdout
    audio, _ = sf.read(str(tmp_path / "out.wav"), always_2d=True)
    peak_db = 20 * np.log10(np.abs(audio).max())
    assert peak_db == pytest.approx(-1.0, abs=0.05)
