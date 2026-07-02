"""Registry dei bounds di sicurezza per i parametri (D18, livello 1).

Risponde a: "quali sono i limiti di validità di ogni parametro?"
parameter_schema.py risponde a: "dove trovo i dati nel YAML?"
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ParameterBounds:
    """Limiti di un parametro e del suo range di variazione.

    max_val / max_range = None → nessun limite superiore
    (es. pan: spazio circolare infinito, D12).
    """

    min_val: float | None
    max_val: float | None
    min_range: float = 0.0
    max_range: float | None = None


PARAMETERS: dict[str, ParameterBounds] = {
    # spaziatura e tessuto (D2, D3)
    "fill_factor": ParameterBounds(min_val=0.001, max_val=50.0,
                                   max_range=25.0),
    "distribution": ParameterBounds(min_val=0.0, max_val=1.0,
                                    max_range=1.0),
    # frammento
    "fragment_duration": ParameterBounds(min_val=0.001, max_val=600.0,
                                         max_range=300.0),
    "pointer_start": ParameterBounds(min_val=0.0, max_val=1.0,
                                     max_range=1.0),
    # uscita (D10, D12)
    "volume": ParameterBounds(min_val=-120.0, max_val=12.0,
                              max_range=24.0),
    "pan": ParameterBounds(min_val=None, max_val=None,
                           max_range=None),  # gradi, mod 360 (D12)
    "master_volume": ParameterBounds(min_val=-120.0, max_val=12.0),
}


def get_parameter_definition(name: str) -> ParameterBounds:
    """Recupera i bounds dal registry; KeyError se il nome non esiste."""
    if name not in PARAMETERS:
        raise KeyError(
            f"Parametro '{name}' non definito in parameter_definitions.py"
        )
    return PARAMETERS[name]
