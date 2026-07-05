"""Generatori di durata dei frammenti — Strategy pattern (M4, D8, D17).

Due strategie sotto la stessa interfaccia:
- TendencyDurationStrategy: durata da tendency mask (Parameter, D5)
- RhythmicDurationStrategy: pattern ciclico di valori ritmici su BPM

Convenzione ritmica: i valori del pattern sono frazioni di semibreve
(1/4 = un movimento). A un dato BPM: secondi = valore × 240 / bpm.
"""

from abc import ABC, abstractmethod

from audiolayers.envelopes.envelope_builder import build_envelope
from audiolayers.parameters.parameter import Parameter, resolve
from audiolayers.parameters.parser import create_parameter
from audiolayers.shared.exceptions import InvalidFieldValueError

WHOLE_NOTE_BEATS = 4.0  # semibreve = 4 movimenti


class DurationStrategy(ABC):
    """Interfaccia: durata del frammento `index` al tempo musicale `time`."""

    @abstractmethod
    def duration(self, index: int, time: float) -> float:  # pragma: no cover
        ...


class TendencyDurationStrategy(DurationStrategy):
    """Durata da tendency mask: regolare (range 0) o casuale, modulabile."""

    def __init__(self, parameter: Parameter):
        self._parameter = parameter

    def duration(self, index: int, time: float) -> float:
        return self._parameter.get_value(time)


class RhythmicDurationStrategy(DurationStrategy):
    """Durate da pattern ritmico ciclico riferito a un BPM (anche curva)."""

    def __init__(self, bpm, pattern: list):
        self._bpm = build_envelope(bpm)
        self._pattern = [float(v) for v in pattern]

    def duration(self, index: int, time: float) -> float:
        bpm_now = resolve(self._bpm, time)
        beat_seconds = 60.0 / bpm_now
        value = self._pattern[index % len(self._pattern)]
        return value * WHOLE_NOTE_BEATS * beat_seconds


def build_duration_strategies(fragment_block: dict, *, layer_id: str,
                              duration: float, seed,
                              time_mode: str = "absolute",
                              ) -> tuple[DurationStrategy, DurationStrategy]:
    """Factory dal blocco YAML `fragment` (D17): coppia (grano, ioi).

    - `grano` decide quanto DURA ogni frammento;
    - `ioi` decide OGNI QUANTO ne nasce uno (prima di fill_factor).

    Senza `rhythm` coincidono (il flusso classico). Con `rhythm` la
    griglia degli onset è ritmica; se `duration`/`duration_range` sono
    dichiarati, la lunghezza del grano resta controllabile a parte
    (staccato granulare), altrimenti il grano riempie lo slot.
    """
    has_rhythm = "rhythm" in fragment_block
    has_tendency = ("duration" in fragment_block
                    or "duration_range" in fragment_block)

    rhythmic = None
    if has_rhythm:
        rhythm = fragment_block["rhythm"]
        if "bpm" not in rhythm:
            raise InvalidFieldValueError("'fragment.rhythm' richiede 'bpm'")
        if "pattern" not in rhythm or not rhythm["pattern"]:
            raise InvalidFieldValueError(
                "'fragment.rhythm' richiede un 'pattern' non vuoto"
            )
        rhythmic = RhythmicDurationStrategy(rhythm["bpm"], rhythm["pattern"])
        if not has_tendency:
            return rhythmic, rhythmic

    parameter = create_parameter(
        "fragment_duration",
        fragment_block.get("duration", 0.5),
        fragment_block.get("duration_range"),
        layer_id=layer_id, duration=duration, seed=seed,
        time_mode=time_mode,
    )
    grain = TendencyDurationStrategy(parameter)
    return grain, (rhythmic if rhythmic is not None else grain)
