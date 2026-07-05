"""Caricamento delle sorgenti audio (M7, D13).

Ogni file entra nel motore come mono float64 al sample rate di
progetto: stereo → downmix (media dei canali, D12), SR diverso →
resampling con soxr (qualità Very High); fallback scipy se soxr
non è disponibile sulla macchina.
"""

from pathlib import Path

import numpy as np
import soundfile as sf

try:
    import soxr

    def _resample(data: np.ndarray, sr_in: int, sr_out: int) -> np.ndarray:
        return soxr.resample(data, sr_in, sr_out, quality="VHQ")

except ImportError:  # pragma: no cover - dipende dalla macchina
    from math import gcd

    from scipy.signal import resample_poly

    def _resample(data: np.ndarray, sr_in: int, sr_out: int) -> np.ndarray:
        divisor = gcd(sr_in, sr_out)
        return resample_poly(data, sr_out // divisor, sr_in // divisor)


def load_mono(path: Path, sample_rate: int) -> np.ndarray:
    """Carica un file audio come mono float64 al SR di progetto."""
    data, file_sr = sf.read(str(path), dtype="float64", always_2d=True)
    mono = data.mean(axis=1)  # downmix (D12)
    if file_sr != sample_rate:
        mono = np.asarray(_resample(mono, file_sr, sample_rate),
                          dtype=np.float64)
    return mono
