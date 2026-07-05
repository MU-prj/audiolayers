"""Strategie di selezione dal pool (M6, D6, D17).

Il pool è una lista ordinata di file; la strategia decide QUALE file
suona il frammento `index`. Tre implementazioni sotto un'interfaccia:

- sequential: in ordine, ciclando (deterministica)
- rotation: una permutazione casuale per ogni giro — ogni file una
  volta per giro, come uno shuffle-play (niente ripetizioni ravvicinate)
- random: estrazioni indipendenti uniformi

Le strategie stocastiche ricevono l'RNG namespaced del layer (D14).
"""

from abc import ABC, abstractmethod

from audiolayers.shared.exceptions import InvalidFieldValueError


class SelectionStrategy(ABC):
    """Interfaccia: indice del file del pool per il frammento `index`."""

    @abstractmethod
    def select(self, index: int) -> int:  # pragma: no cover
        ...


class SequentialSelection(SelectionStrategy):
    """I file in ordine alfabetico, ciclando."""

    def __init__(self, pool_size: int):
        self._pool_size = pool_size

    def select(self, index: int) -> int:
        return index % self._pool_size


class RandomSelection(SelectionStrategy):
    """Estrazione indipendente uniforme a ogni frammento."""

    def __init__(self, pool_size: int, rng):
        self._pool_size = pool_size
        self._rng = rng

    def select(self, index: int) -> int:
        return int(self._rng.integers(self._pool_size))


class RotationSelection(SelectionStrategy):
    """Permutazione casuale per giro: ogni file una volta per giro."""

    def __init__(self, pool_size: int, rng):
        self._pool_size = pool_size
        self._rng = rng
        self._round = -1
        self._permutation: list[int] = []

    def select(self, index: int) -> int:
        current_round = index // self._pool_size
        if current_round != self._round:
            self._round = current_round
            self._permutation = list(
                self._rng.permutation(self._pool_size)
            )
        return int(self._permutation[index % self._pool_size])


_STRATEGIES = {
    "sequential": SequentialSelection,
    "rotation": RotationSelection,
    "random": RandomSelection,
}


def available_selection_strategies() -> list[str]:
    """Nomi delle strategie di selezione (fonte per catalogo e GUI)."""
    return sorted(_STRATEGIES)


def build_selection_strategy(selection_block: dict, *, pool_size: int,
                             layer_id: str, seed) -> SelectionStrategy:
    """Factory dal blocco YAML `selection` (default: sequential)."""
    from audiolayers.shared.seeding import rng_for

    name = selection_block.get("strategy", "sequential")
    if name not in _STRATEGIES:
        raise InvalidFieldValueError(
            f"strategia di selezione '{name}' sconosciuta "
            f"(disponibili: {', '.join(sorted(_STRATEGIES))})"
        )
    if name == "sequential":
        return SequentialSelection(pool_size)
    return _STRATEGIES[name](pool_size, rng_for(seed, layer_id, "selection"))
