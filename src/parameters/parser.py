"""Parser dei parametri (D18, livello 3): dal dict YAML ai Parameter.

Combina schema (dove/default), definitions (bounds) ed envelope builder
(forme), inietta l'RNG namespaced (D14) e valida severamente al parse:
un valore fuori bounds ferma il render con un errore parlante, non
suona "quasi giusto" in silenzio.
"""

from src.envelopes.envelope import Envelope
from src.envelopes.envelope_builder import build_envelope
from src.parameters.parameter import Parameter
from src.parameters.parameter_definitions import (ParameterBounds,
                                                  get_parameter_definition)
from src.parameters.parameter_schema import (LAYER_PARAMETER_SCHEMA,
                                             ParameterSpec)
from src.shared.exceptions import ParameterBoundError
from src.shared.seeding import rng_for


def create_layer_parameters(layer_data: dict, *, layer_id: str,
                            duration: float, seed,
                            time_mode: str = "absolute",
                            schema: list[ParameterSpec] | None = None,
                            ) -> dict[str, Parameter]:
    """Crea tutti i Parameter di un layer dallo schema dichiarativo."""
    result: dict[str, Parameter] = {}
    for spec in schema or LAYER_PARAMETER_SCHEMA:
        bounds = get_parameter_definition(spec.name)

        raw_base = _get_nested(layer_data, spec.yaml_path, spec.default)
        base = build_envelope(raw_base, duration=duration, time_mode=time_mode)
        _validate(base, spec.name, bounds.min_val, bounds.max_val, "value")

        mod_range = None
        if spec.range_path is not None:
            raw_range = _get_nested(layer_data, spec.range_path, None)
            if raw_range is not None:
                mod_range = build_envelope(raw_range, duration=duration,
                                           time_mode=time_mode)
                _validate(mod_range, spec.name, bounds.min_range,
                          bounds.max_range, "range")

        result[spec.name] = Parameter(
            spec.name, base=base, bounds=bounds, mod_range=mod_range,
            rng=rng_for(seed, layer_id, spec.name) if mod_range is not None
            else None,
        )
    return result


def _get_nested(data: dict, path: str, default):
    """Naviga un dict con dot notation; default se il percorso manca."""
    current = data
    for key in path.split("."):
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current


def _validate(value, param_name: str, min_bound, max_bound,
              value_type: str) -> None:
    """Valida float o Envelope (ogni breakpoint) contro i bounds."""
    if isinstance(value, Envelope):
        candidates = value.values
    else:
        candidates = [value]
    for v in candidates:
        below = min_bound is not None and v < min_bound
        above = max_bound is not None and v > max_bound
        if below or above:
            raise ParameterBoundError(param_name, v, min_bound, max_bound,
                                      value_type)
