"""Smart Parameter: la tendency mask fatta oggetto (D5, Truax).

`get_value(t)` = estrazione uniforme in `[base(t) − range(t), base(t) + range(t)]`
con RNG namespaced iniettato (D14), poi clamp di sicurezza sui bounds.
`range = 0` (o assente) → valore deterministico.
"""

from audiolayers.envelopes.envelope import Envelope
from audiolayers.parameters.parameter_definitions import ParameterBounds


def resolve(value, time: float) -> float:
    """Risolve float | Envelope | None a float al tempo dato."""
    if value is None:
        return 0.0
    if isinstance(value, Envelope):
        return value.evaluate(time)
    return float(value)


class Parameter:
    """Parametro con base ± range (entrambi float o Envelope) e bounds."""

    def __init__(self, name: str, base, bounds: ParameterBounds,
                 mod_range=None, rng=None):
        if mod_range is not None and rng is None:
            raise ValueError(
                f"il parametro '{name}' ha un range ma nessun rng iniettato: "
                "la casualità deve essere namespaced (D14)"
            )
        self.name = name
        self._base = base
        self._bounds = bounds
        self._mod_range = mod_range
        self._rng = rng

    def get_value(self, time: float) -> float:
        """Valore del parametro al tempo dato (unica API pubblica)."""
        base = resolve(self._base, time)
        band = self._band_width(time)
        if band > 0.0:
            value = self._rng.uniform(base - band, base + band)
        else:
            value = base
        return self._clamp(value)

    def _band_width(self, time: float) -> float:
        """Semiampiezza della maschera al tempo dato, nei limiti di range."""
        if self._mod_range is None:
            return 0.0
        band = resolve(self._mod_range, time)
        band = max(self._bounds.min_range, band)
        if self._bounds.max_range is not None:
            band = min(self._bounds.max_range, band)
        return band

    def _clamp(self, value: float) -> float:
        if self._bounds.min_val is not None:
            value = max(self._bounds.min_val, value)
        if self._bounds.max_val is not None:
            value = min(self._bounds.max_val, value)
        return value

    def __repr__(self) -> str:
        base = "Env" if isinstance(self._base, Envelope) else f"{self._base}"
        return f"<Parameter '{self.name}' base={base}>"
