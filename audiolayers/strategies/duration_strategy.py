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
from audiolayers.shared.seeding import rng_for

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
    """Durate da pattern ritmico ciclico riferito a un BPM (anche curva).

    Una voce del pattern può essere un dict {value, repeat} (issue #10):
    a ogni giro il valore si ripete un numero di volte estratto
    dall'RNG namespaced del layer (riproducibile col seed). `repeat`
    accetta un intero fisso, un range "lo-hi" o una lista di scelte.
    L'espansione è lazy: la sequenza cresce quanto serve.
    """

    def __init__(self, bpm, pattern: list, rng=None):
        self._bpm = build_envelope(bpm)
        self._entries = [self._parse_entry(v) for v in pattern]
        self._rng = rng
        self._expanded: list[float] = []

    @staticmethod
    def _parse_entry(voice) -> tuple[float, list[int]]:
        """(valore, scelte-di-ripetizione): scalare → [1]."""
        if isinstance(voice, dict):
            return float(voice["value"]), _repeat_choices(voice["repeat"])
        return float(voice), [1]

    def _extend(self) -> None:
        for value, choices in self._entries:
            n = choices[0] if len(choices) == 1 \
                else int(self._rng.choice(choices))
            self._expanded.extend([value] * n)

    def duration(self, index: int, time: float) -> float:
        while index >= len(self._expanded):
            self._extend()
        beat_seconds = 60.0 / resolve(self._bpm, time)
        return self._expanded[index] * WHOLE_NOTE_BEATS * beat_seconds


def _repeat_choices(spec) -> list[int]:
    """Normalizza `repeat` in una lista di scelte (issue #10).

    Tre forme: intero fisso (3), range "lo-hi" ("2-4" → [2, 3, 4]),
    lista esplicita ([2, 7] → solo 2 o 7). Tutte le scelte >= 1.
    """
    if isinstance(spec, int) and not isinstance(spec, bool):
        choices = [spec]
    elif isinstance(spec, str):
        lo, sep, hi = spec.partition("-")
        try:
            choices = (list(range(int(lo), int(hi) + 1)) if sep
                       else [int(lo)])
        except ValueError:
            choices = []
    elif isinstance(spec, (list, tuple)):
        try:
            choices = [int(x) for x in spec]
        except (TypeError, ValueError):
            choices = []
    else:
        choices = []
    if not choices or any(c < 1 for c in choices):
        raise InvalidFieldValueError(
            "voce di pattern dict: 'repeat' deve essere un intero >= 1, "
            "un range \"lo-hi\" o una lista di scelte, tutte >= 1")
    return choices


def _validate_pattern(pattern: list) -> None:
    """Le voci dict richiedono value > 0 e un `repeat` valido:
    intero, range "lo-hi" o lista di scelte, tutte >= 1 (issue #10)."""
    for voice in pattern:
        if not isinstance(voice, dict):
            continue
        if "value" not in voice or float(voice["value"]) <= 0:
            raise InvalidFieldValueError(
                "voce di pattern dict: serve 'value' positivo")
        _repeat_choices(voice.get("repeat"))


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
        _validate_pattern(rhythm["pattern"])
        rhythmic = RhythmicDurationStrategy(
            rhythm["bpm"], rhythm["pattern"],
            rng=rng_for(seed, layer_id, "rhythm"),
        )
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
