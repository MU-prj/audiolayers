"""Builder: dal valore YAML grezzo a float | Envelope (D5).

Un parametro numerico può essere scritto come scalare (costante),
lista di breakpoint `[[t, v], …]`, o dict `{type, points, time_mode}`.
Il resto del sistema vede solo float o Envelope.
"""

from audiolayers.envelopes.envelope import Envelope
from audiolayers.shared.exceptions import InvalidFieldValueError

SUPPORTED_INTERPOLATIONS = ("linear",)
TIME_MODES = ("absolute", "normalized")


def build_envelope(raw, duration: float | None = None,
                   time_mode: str = "absolute"):
    """Converte il valore YAML grezzo in float (scalare) o Envelope.

    Args:
        raw: valore come appare nel YAML.
        duration: durata del layer, usata per scalare i tempi quando
            time_mode è "normalized".
        time_mode: "absolute" (secondi) o "normalized" ([0,1] × duration).
            La forma dict può sovrascriverlo localmente.
    """
    _validate_time_mode(time_mode)

    if isinstance(raw, bool):
        raise InvalidFieldValueError(
            f"valore booleano non valido per un parametro numerico: {raw!r}"
        )
    if isinstance(raw, (int, float)):
        return float(raw)

    if isinstance(raw, list):
        return Envelope(_scale_times(raw, duration, time_mode))

    if isinstance(raw, dict):
        interp = raw.get("type", "linear")
        if interp not in SUPPORTED_INTERPOLATIONS:
            raise InvalidFieldValueError(
                f"interpolazione '{interp}' non supportata "
                f"(disponibili: {', '.join(SUPPORTED_INTERPOLATIONS)})"
            )
        if "points" not in raw:
            raise InvalidFieldValueError(
                "la forma dict di un envelope richiede la chiave 'points'"
            )
        local_mode = raw.get("time_mode", time_mode)
        _validate_time_mode(local_mode)
        return Envelope(_scale_times(raw["points"], duration, local_mode))

    raise InvalidFieldValueError(
        f"valore non valido per un parametro: {raw!r} "
        "(atteso numero, lista di breakpoint, o dict envelope)"
    )


def _validate_time_mode(time_mode: str) -> None:
    if time_mode not in TIME_MODES:
        raise InvalidFieldValueError(
            f"time_mode '{time_mode}' non valido "
            f"(disponibili: {', '.join(TIME_MODES)})"
        )


def _scale_times(breakpoints: list, duration: float | None,
                 time_mode: str) -> list:
    """Con time_mode normalized, mappa i tempi [0,1] su [0, duration]."""
    if time_mode != "normalized":
        return breakpoints
    if duration is None:
        raise InvalidFieldValueError(
            "time_mode 'normalized' richiede una duration su cui scalare"
        )
    return [[bp[0] * duration, bp[1]] for bp in breakpoints]


def is_envelope_like(value) -> bool:
    """True se il valore YAML rappresenta un envelope (non uno scalare)."""
    if isinstance(value, dict):
        return "points" in value
    return isinstance(value, list) and len(value) > 0
