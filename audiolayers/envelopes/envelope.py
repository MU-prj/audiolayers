"""Envelope: funzione f(t) → v definita a tratti su breakpoint (D5).

Sostituisce qualunque valore scalare ovunque il parser lo accetti:
è il mattone di base delle tendency masks (base ± range, entrambi
curve nel tempo). Interpolazione lineare (v1).
"""

import numpy as np

from audiolayers.shared.exceptions import InvalidFieldValueError


class Envelope:
    """Curva a breakpoint `[[t, v], …]` con interpolazione lineare."""

    def __init__(self, breakpoints: list):
        if not breakpoints:
            raise InvalidFieldValueError(
                "un envelope richiede almeno un breakpoint [tempo, valore]"
            )
        # L'utente non deve garantire l'ordine: ordina per tempo crescente.
        ordered = sorted(breakpoints, key=lambda bp: bp[0])
        self._times = np.array([bp[0] for bp in ordered], dtype=np.float64)
        self._values = np.array([bp[1] for bp in ordered], dtype=np.float64)

    def evaluate(self, time: float) -> float:
        """Valore dell'envelope al tempo dato."""
        return float(np.interp(time, self._times, self._values))

    def evaluate_array(self, times: np.ndarray) -> np.ndarray:
        """Valutazione vettoriale (per curve per-campione, es. master)."""
        return np.interp(times, self._times, self._values)

    @property
    def values(self) -> list[float]:
        """I valori dei breakpoint (per validazione bounds al parse)."""
        return self._values.tolist()
