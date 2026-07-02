"""Inviluppo d'ampiezza per-frammento (M8, D11, D17).

Tagliare una slice dentro un file produce quasi sempre un click ai
bordi: l'inviluppo apre e chiude morbidamente il frammento. Con
overlap (F>1) gli inviluppi generano crossfade emergenti — il
crossfade non ha codice dedicato, emerge dal design (D11).
"""

from abc import ABC, abstractmethod

import numpy as np

from src.shared.exceptions import InvalidFieldValueError

DEFAULT_ATTACK = 0.008   # s
DEFAULT_RELEASE = 0.010  # s


class FragmentEnvelopeStrategy(ABC):
    """Interfaccia: applica l'inviluppo a un segmento mono."""

    @abstractmethod
    def apply(self, segment: np.ndarray,
              sample_rate: int) -> np.ndarray:  # pragma: no cover
        ...


class RectangleEnvelope(FragmentEnvelopeStrategy):
    """Nessun inviluppo: il segmento passa intatto."""

    def apply(self, segment: np.ndarray, sample_rate: int) -> np.ndarray:
        return segment


class RaisedCosineEnvelope(FragmentEnvelopeStrategy):
    """Fade-in/out raised-cosine (mezzo Hann) con plateau a 1."""

    def __init__(self, attack: float = DEFAULT_ATTACK,
                 release: float = DEFAULT_RELEASE):
        self._attack = attack
        self._release = release

    def apply(self, segment: np.ndarray, sample_rate: int) -> np.ndarray:
        n = len(segment)
        n_attack = round(self._attack * sample_rate)
        n_release = round(self._release * sample_rate)

        if n_attack + n_release >= n:
            # Frammento più corto dei fade: campana intera, niente plateau.
            window = 0.5 * (1.0 - np.cos(2.0 * np.pi * np.arange(n) / n))
            return segment * window

        window = np.ones(n)
        ramp_in = np.arange(n_attack) / n_attack
        window[:n_attack] = 0.5 * (1.0 - np.cos(np.pi * ramp_in))
        ramp_out = np.arange(n_release) / n_release
        window[n - n_release:] = 0.5 * (1.0 + np.cos(np.pi * ramp_out))
        return segment * window


_STRATEGIES = {
    "raised_cosine": RaisedCosineEnvelope,
    "rectangle": RectangleEnvelope,
}


def build_fragment_envelope(fragment_block: dict) -> FragmentEnvelopeStrategy:
    """Factory dal blocco YAML `fragment` (default: raised_cosine)."""
    name = fragment_block.get("envelope", "raised_cosine")
    if name not in _STRATEGIES:
        raise InvalidFieldValueError(
            f"inviluppo '{name}' sconosciuto "
            f"(disponibili: {', '.join(sorted(_STRATEGIES))})"
        )
    if name == "raised_cosine":
        return RaisedCosineEnvelope(
            attack=float(fragment_block.get("attack", DEFAULT_ATTACK)),
            release=float(fragment_block.get("release", DEFAULT_RELEASE)),
        )
    return RectangleEnvelope()
