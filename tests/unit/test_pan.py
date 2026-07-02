"""Unit — pan mid/side a potenza costante (M8, D12).

mid = s·cos(rad), side = s·sin(rad), L = (mid+side)/√2, R = (mid−side)/√2
0° = centro, +45° = tutto L, −45° = tutto R, spazio circolare (mod 360).
"""

import numpy as np
import pytest

from src.audio.pan import pan_stereo

SIGNAL = np.array([1.0, -0.5, 0.25])


def test_zero_gradi_centro():
    out = pan_stereo(SIGNAL, degrees=0.0)
    assert out.shape == (3, 2)
    np.testing.assert_allclose(out[:, 0], SIGNAL / np.sqrt(2))
    np.testing.assert_allclose(out[:, 1], SIGNAL / np.sqrt(2))


def test_piu_45_tutto_a_sinistra():
    out = pan_stereo(SIGNAL, degrees=45.0)
    np.testing.assert_allclose(out[:, 0], SIGNAL, atol=1e-12)
    np.testing.assert_allclose(out[:, 1], 0.0, atol=1e-12)


def test_meno_45_tutto_a_destra():
    out = pan_stereo(SIGNAL, degrees=-45.0)
    np.testing.assert_allclose(out[:, 0], 0.0, atol=1e-12)
    np.testing.assert_allclose(out[:, 1], SIGNAL, atol=1e-12)


def test_potenza_costante_a_ogni_angolo():
    for deg in (0, 17, 45, 90, 133, 180, 270, 315):
        out = pan_stereo(SIGNAL, degrees=float(deg))
        power = out[:, 0] ** 2 + out[:, 1] ** 2
        np.testing.assert_allclose(power, SIGNAL ** 2, atol=1e-12)


def test_spazio_circolare_mod_360():
    np.testing.assert_allclose(pan_stereo(SIGNAL, 30.0),
                               pan_stereo(SIGNAL, 390.0), atol=1e-12)
    np.testing.assert_allclose(pan_stereo(SIGNAL, -45.0),
                               pan_stereo(SIGNAL, 315.0), atol=1e-12)
