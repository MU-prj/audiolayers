"""Integration — mix multi-layer e stadio master (M9, D15, D16).

- ogni layer ha un `onset` sulla timeline globale; i layer si sommano
- `solo`/`mute` per layer (convenzione PGE)
- `master_volume` in dB, envelope-abile
"""

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from src.engine.render import render_score

SR = 48000


@pytest.fixture
def pool(tmp_path: Path) -> Path:
    pool_dir = tmp_path / "pool"
    pool_dir.mkdir()
    t = np.arange(SR) / SR
    sf.write(pool_dir / "sine.wav",
             (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32), SR)
    return pool_dir


def render(tmp_path: Path, score_text: str) -> np.ndarray:
    score = tmp_path / "score.yaml"
    score.write_text(score_text, encoding="utf-8")
    out = tmp_path / "out.wav"
    render_score(score, out)
    audio, _ = sf.read(str(out), always_2d=True)
    return audio


def layer_block(layer_id, onset=0.0, extra=""):
    return f"""\
  - layer_id: "{layer_id}"
    onset: {onset}
    duration: 1.0
    fragment: {{duration: 0.5, envelope: rectangle}}
{extra}"""


def rms_window(audio, t_start, t_end):
    """RMS di una finestra: mai sondare un campione singolo (può essere
    uno zero-crossing esatto della sinusoide di test)."""
    seg = audio[round(t_start * SR):round(t_end * SR)]
    return float(np.sqrt((seg ** 2).mean()))


def test_onset_di_layer_posiziona_sulla_timeline_globale(tmp_path, pool):
    audio = render(tmp_path, f"""\
layers:
{layer_block("primo", 0.0, f'    pool: "{pool.as_posix()}"')}
{layer_block("secondo", 2.0, f'    pool: "{pool.as_posix()}"')}
""")
    assert len(audio) == 3 * SR                     # 2.0 + 1.0
    assert rms_window(audio, 1.4, 1.9) == 0.0       # buco tra i layer
    assert rms_window(audio, 2.1, 2.4) > 0.1        # il secondo suona


def test_i_layer_sovrapposti_si_sommano(tmp_path, pool):
    single = render(tmp_path, f"""\
layers:
{layer_block("a", 0.0, f'    pool: "{pool.as_posix()}"')}
""")
    double = render(tmp_path, f"""\
layers:
{layer_block("a", 0.0, f'    pool: "{pool.as_posix()}"')}
{layer_block("b", 0.0, f'    pool: "{pool.as_posix()}"')}
""")
    assert np.abs(double).max() == pytest.approx(2 * np.abs(single).max(),
                                                 rel=1e-6)


def test_mute_esclude_il_layer(tmp_path, pool):
    audio = render(tmp_path, f"""\
layers:
{layer_block("suona", 0.0, f'    pool: "{pool.as_posix()}"')}
{layer_block("zitto", 2.0, f'    pool: "{pool.as_posix()}"' + chr(10) + '    mute: true')}
""")
    assert len(audio) == 1 * SR   # il layer mutato non estende la timeline


def test_solo_esclude_tutti_gli_altri(tmp_path, pool):
    audio = render(tmp_path, f"""\
layers:
{layer_block("fuori", 0.0, f'    pool: "{pool.as_posix()}"')}
{layer_block("dentro", 2.0, f'    pool: "{pool.as_posix()}"' + chr(10) + '    solo: true')}
""")
    # solo il layer in solo: la timeline parte dal suo onset
    assert np.abs(audio[: SR]).max() == 0.0       # "fuori" non suona
    assert rms_window(audio, 2.1, 2.4) > 0.1


def test_master_volume_scala_il_mix(tmp_path, pool):
    full = render(tmp_path, f"""\
layers:
{layer_block("a", 0.0, f'    pool: "{pool.as_posix()}"')}
""")
    halved = render(tmp_path, f"""\
master_volume: -6.0
layers:
{layer_block("a", 0.0, f'    pool: "{pool.as_posix()}"')}
""")
    ratio = np.abs(halved).max() / np.abs(full).max()
    assert ratio == pytest.approx(10 ** (-6 / 20), rel=1e-4)


def test_master_volume_envelope_fade_out_globale(tmp_path, pool):
    audio = render(tmp_path, f"""\
master_volume: [[0.0, 0.0], [1.0, -120.0]]
layers:
{layer_block("a", 0.0, f'    pool: "{pool.as_posix()}"')}
""")
    first_rms = np.sqrt((audio[: SR // 4] ** 2).mean())
    last_rms = np.sqrt((audio[-SR // 4:] ** 2).mean())
    assert last_rms < first_rms * 0.01   # il fade out globale morde
