"""Pan mid/side a potenza costante (M8, D12).

mid  = s · cos(rad)          rad = gradi · π/180
side = s · sin(rad)
L = (mid + side) / √2
R = (mid − side) / √2

Proprietà: L² + R² = s² a qualunque angolo (potenza costante).
Convenzione: 0° = centro, +45° = tutto L, −45° = tutto R; lo spazio è
circolare (le trigonometriche assorbono il modulo 360): una ramp di pan
senza limiti fa RUOTARE il segnale con continuità.
"""

import numpy as np

_SQRT2 = np.sqrt(2.0)


def pan_stereo(signal: np.ndarray, degrees: float) -> np.ndarray:
    """Posiziona un segnale mono nel campo stereo: (N,) → (N, 2)."""
    rad = np.deg2rad(degrees)
    mid = signal * np.cos(rad)
    side = signal * np.sin(rad)
    return np.column_stack([(mid + side) / _SQRT2, (mid - side) / _SQRT2])
