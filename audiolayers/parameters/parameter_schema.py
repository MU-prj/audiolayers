"""Schema dichiarativo dei parametri di layer (D18, livello 2).

Risponde a: "dove trovo i dati nel YAML, e con quali default?"
Un parametro assente nella partitura nasce col default dichiarato qui.

Per aggiungere un parametro: una riga di bounds in
parameter_definitions.py + una ParameterSpec qui. Fine.
"""

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class ParameterSpec:
    """Specifica dichiarativa di un parametro di layer.

    Attributes:
        name: chiave nel registry bounds E nome del Parameter risultante.
        yaml_path: percorso nel YAML (dot notation: 'fragment.duration').
        default: valore usato se la chiave è assente nella partitura.
        range_path: percorso YAML del `_range` associato (tendency mask).
    """

    name: str
    yaml_path: str
    default: Any
    range_path: Optional[str] = None


LAYER_PARAMETER_SCHEMA: list[ParameterSpec] = [
    ParameterSpec("volume", "volume", 0.0, "volume_range"),
    ParameterSpec("pan", "pan", 0.0, "pan_range"),
    ParameterSpec("fill_factor", "fill_factor", 1.0, "fill_factor_range"),
    ParameterSpec("distribution", "distribution", 0.0),
    # NB: fragment.duration NON è qui: la assembla la DurationStrategy
    # (unico punto), perché è mutuamente esclusiva con fragment.rhythm.
    ParameterSpec("pointer_start", "pointer.start", 0.0,
                  "pointer.start_range"),
]
