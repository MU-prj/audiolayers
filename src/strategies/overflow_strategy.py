"""Strategie di overflow in lettura sorgente (M7, D9, D17).

Il punto di lettura normalizzato mappa su una posizione assoluta nel
file A PRESCINDERE dalla durata del frammento (0.5 = metà file, sempre).
Quando `start + length` supera la fine del file decide la Strategy:

- clamp_back (default): arretra lo start del minimo necessario perché
  la slice finisca a fine file — materiale reale contiguo, nessun click.
  Se il file è più corto della durata richiesta, restituisce tutto il
  file (segmento onestamente più corto).
- loop: prosegue ripartendo dall'inizio (wrap modulare), lunghezza esatta.
- zero_pad: legge il disponibile poi silenzio, lunghezza esatta.
"""

from abc import ABC, abstractmethod

import numpy as np

from src.shared.exceptions import InvalidFieldValueError


class OverflowStrategy(ABC):
    """Interfaccia: leggi `length` campioni da `source` a partire da `start`."""

    @abstractmethod
    def read(self, source: np.ndarray, start: int,
             length: int) -> np.ndarray:  # pragma: no cover
        ...


class ClampBackOverflow(OverflowStrategy):
    def read(self, source: np.ndarray, start: int, length: int) -> np.ndarray:
        if start + length > len(source):
            start = max(0, len(source) - length)
        return source[start:start + length]


class LoopOverflow(OverflowStrategy):
    def read(self, source: np.ndarray, start: int, length: int) -> np.ndarray:
        indices = (start + np.arange(length)) % len(source)
        return source[indices]


class ZeroPadOverflow(OverflowStrategy):
    def read(self, source: np.ndarray, start: int, length: int) -> np.ndarray:
        available = source[start:start + length]
        if len(available) == length:
            return available
        return np.concatenate(
            [available, np.zeros(length - len(available), dtype=source.dtype)]
        )


_STRATEGIES = {
    "clamp_back": ClampBackOverflow,
    "loop": LoopOverflow,
    "zero_pad": ZeroPadOverflow,
}


def available_overflow_strategies() -> list[str]:
    """Nomi delle strategie di overflow (fonte per catalogo e GUI)."""
    return sorted(_STRATEGIES)


def build_overflow_strategy(pointer_block: dict) -> OverflowStrategy:
    """Factory dal blocco YAML `pointer` (default: clamp_back)."""
    name = pointer_block.get("overflow", "clamp_back")
    if name not in _STRATEGIES:
        raise InvalidFieldValueError(
            f"strategia di overflow '{name}' sconosciuta "
            f"(disponibili: {', '.join(sorted(_STRATEGIES))})"
        )
    return _STRATEGIES[name]()
