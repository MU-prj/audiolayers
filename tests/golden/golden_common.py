"""Infrastruttura condivisa dei golden test (M10, D19).

Il pool audio è generato deterministicamente (sinusoidi fisse, float32):
identico su ogni macchina, niente file audio sorgente versionati.
I RIFERIMENTI renderizzati invece sono versionati in references/.

Per rigenerarli dopo un cambiamento intenzionale del motore:
    python tests/golden/regenerate_references.py
"""

from pathlib import Path

import numpy as np
import soundfile as sf

GOLDEN_DIR = Path(__file__).parent
SCORES_DIR = GOLDEN_DIR / "scores"
REFERENCES_DIR = GOLDEN_DIR / "references"

SR = 48000


def build_pool(target_dir: Path) -> Path:
    """Pool deterministico: due sinusoidi e un accordo, sempre identici."""
    pool = target_dir / "pool"
    pool.mkdir(parents=True, exist_ok=True)
    t = np.arange(SR) / SR
    sf.write(pool / "a_440.wav",
             (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32), SR)
    sf.write(pool / "b_880.wav",
             (0.4 * np.sin(2 * np.pi * 880 * t)).astype(np.float32), SR)
    chord = 0.3 * (np.sin(2 * np.pi * 330 * t) + np.sin(2 * np.pi * 550 * t))
    sf.write(pool / "c_chord.wav", chord.astype(np.float32), SR)
    return pool


def materialize_score(name: str, pool: Path, target_dir: Path) -> Path:
    """Sostituisce {POOL} nel template e scrive la partitura concreta."""
    template = (SCORES_DIR / name).read_text(encoding="utf-8")
    score = target_dir / name
    score.write_text(template.replace("{POOL}", pool.as_posix()),
                     encoding="utf-8")
    return score


def score_names() -> list[str]:
    return sorted(p.name for p in SCORES_DIR.glob("*.yaml"))
