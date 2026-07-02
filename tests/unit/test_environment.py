"""Smoke test dell'ambiente: verifica che le dipendenze core siano
importabili e minimamente funzionanti. Nessuna logica di dominio."""

import numpy as np


def test_numpy_disponibile():
    assert np.zeros(4).shape == (4,)


def test_soundfile_disponibile():
    import soundfile as sf

    assert hasattr(sf, "write") and hasattr(sf, "read")


def test_yaml_disponibile():
    import yaml

    assert yaml.safe_load("a: 1") == {"a": 1}


def test_resampler_disponibile():
    """soxr preferito; scipy come fallback accettato (D13)."""
    try:
        import soxr  # noqa: F401
    except ImportError:
        from scipy.signal import resample_poly  # noqa: F401
