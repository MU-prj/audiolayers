"""Parser dei parametri (D18, livello 3): dal dict YAML ai Parameter.

Combina schema (dove/default), definitions (bounds) ed envelope builder
(forme), inietta l'RNG namespaced (D14) e valida severamente al parse:
un valore fuori bounds ferma il render con un errore parlante, non
suona "quasi giusto" in silenzio.
"""

from audiolayers.envelopes.envelope import Envelope
from audiolayers.envelopes.envelope_builder import build_envelope
from audiolayers.parameters.parameter import Parameter
from audiolayers.parameters.parameter_definitions import (ParameterBounds,
                                                  get_parameter_definition)
from audiolayers.parameters.parameter_schema import (LAYER_PARAMETER_SCHEMA,
                                             ParameterSpec)
from audiolayers.shared.exceptions import ParameterBoundError
from audiolayers.shared.seeding import rng_for


def create_parameter(name: str, raw_base, raw_range=None, *, layer_id: str,
                     duration: float, seed,
                     time_mode: str = "absolute") -> Parameter:
    """Crea un singolo Parameter validato, con RNG namespaced (D14)."""
    bounds = get_parameter_definition(name)

    base = build_envelope(raw_base, duration=duration, time_mode=time_mode)
    _validate(base, name, bounds.min_val, bounds.max_val, "value")

    mod_range = None
    if raw_range is not None:
        mod_range = build_envelope(raw_range, duration=duration,
                                   time_mode=time_mode)
        _validate(mod_range, name, bounds.min_range, bounds.max_range,
                  "range")

    return Parameter(
        name, base=base, bounds=bounds, mod_range=mod_range,
        rng=rng_for(seed, layer_id, name) if mod_range is not None else None,
    )


def create_layer_parameters(layer_data: dict, *, layer_id: str,
                            duration: float, seed,
                            time_mode: str = "absolute",
                            schema: list[ParameterSpec] | None = None,
                            ) -> dict[str, Parameter]:
    """Crea tutti i Parameter di un layer dallo schema dichiarativo."""
    result: dict[str, Parameter] = {}
    for spec in schema or LAYER_PARAMETER_SCHEMA:
        raw_base = _get_nested(layer_data, spec.yaml_path, spec.default)
        raw_range = (_get_nested(layer_data, spec.range_path, None)
                     if spec.range_path is not None else None)
        result[spec.name] = create_parameter(
            spec.name, raw_base, raw_range, layer_id=layer_id,
            duration=duration, seed=seed, time_mode=time_mode,
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


def validate_parameter(value, param_name: str) -> None:
    """Valida un valore (float o Envelope) contro i bounds del registry.

    Punto pubblico per i consumatori fuori dallo schema dichiarativo
    (master_volume, attack/release): stessi bounds, stesso errore.
    """
    bounds = get_parameter_definition(param_name)
    _validate(value, param_name, bounds.min_val, bounds.max_val, "base")


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
