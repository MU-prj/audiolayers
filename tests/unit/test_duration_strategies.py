"""Unit — generatori di durata (M4, D8): Strategy intercambiabili (D17).

- tendency: durata da tendency mask (base ± range, via Parameter)
- rhythmic: pattern ciclico di valori ritmici riferiti a un BPM
  (convenzione: 1/4 = un movimento = 60/bpm secondi; 1 = semibreve)
"""

import pytest

from src.strategies.duration_strategy import (RhythmicDurationStrategy,
                                              TendencyDurationStrategy,
                                              build_duration_strategy)
from src.parameters.parameter import Parameter
from src.parameters.parameter_definitions import get_parameter_definition
from src.shared.exceptions import InvalidFieldValueError
from src.shared.seeding import rng_for


class TestRhythmic:
    def test_pattern_convertito_in_secondi_dal_bpm(self):
        """A 120 BPM: 1/4 = 0.5 s, 1/8 = 0.25 s, 1/2 = 1.0 s."""
        strat = RhythmicDurationStrategy(bpm=120.0,
                                         pattern=[0.25, 0.125, 0.125, 0.5])
        durs = [strat.duration(i, time=0.0) for i in range(4)]
        assert durs == pytest.approx([0.5, 0.25, 0.25, 1.0])

    def test_il_pattern_cicla_oltre_la_sua_lunghezza(self):
        strat = RhythmicDurationStrategy(bpm=120.0, pattern=[0.25, 0.125])
        assert strat.duration(0, 0.0) == strat.duration(2, 0.0)
        assert strat.duration(1, 0.0) == strat.duration(5, 0.0)

    def test_bpm_envelope_accelerando(self):
        """Il BPM può essere una curva: il brano accelera (D8 modulabile)."""
        strat = RhythmicDurationStrategy(bpm=[[0.0, 60.0], [10.0, 120.0]],
                                         pattern=[0.25])
        assert strat.duration(0, time=0.0) == pytest.approx(1.0)
        assert strat.duration(0, time=10.0) == pytest.approx(0.5)


class TestTendency:
    def test_delega_al_parameter(self):
        bounds = get_parameter_definition("fragment_duration")
        param = Parameter("fragment_duration", base=0.5, bounds=bounds,
                          mod_range=0.2, rng=rng_for(42, "l1", "fragment_duration"))
        strat = TendencyDurationStrategy(param)
        durs = [strat.duration(i, 0.0) for i in range(100)]
        assert all(0.3 <= d <= 0.7 for d in durs)
        assert len(set(durs)) > 1


class TestFactory:
    def test_blocco_rhythm_crea_la_strategia_ritmica(self):
        strat = build_duration_strategy(
            {"rhythm": {"bpm": 120, "pattern": [0.25]}},
            layer_id="l1", duration=30.0, seed=42,
        )
        assert isinstance(strat, RhythmicDurationStrategy)

    def test_default_e_tendency(self):
        strat = build_duration_strategy({}, layer_id="l1", duration=30.0,
                                        seed=42)
        assert isinstance(strat, TendencyDurationStrategy)
        assert strat.duration(0, 0.0) == 0.5  # default dallo schema

    def test_duration_e_rhythm_insieme_sono_un_errore(self):
        """Convenzione PGE recente: niente priorità implicite, errore."""
        with pytest.raises(InvalidFieldValueError, match="rhythm"):
            build_duration_strategy(
                {"duration": 0.5, "rhythm": {"bpm": 120, "pattern": [0.25]}},
                layer_id="l1", duration=30.0, seed=42,
            )

    def test_rhythm_senza_bpm_o_pattern_e_un_errore(self):
        with pytest.raises(InvalidFieldValueError, match="bpm"):
            build_duration_strategy({"rhythm": {"pattern": [0.25]}},
                                    layer_id="l1", duration=30.0, seed=42)
        with pytest.raises(InvalidFieldValueError, match="pattern"):
            build_duration_strategy({"rhythm": {"bpm": 120}},
                                    layer_id="l1", duration=30.0, seed=42)
