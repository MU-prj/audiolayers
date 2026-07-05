"""Unit — generatori di durata (M4, D8): Strategy intercambiabili (D17).

- tendency: durata da tendency mask (base ± range, via Parameter)
- rhythmic: pattern ciclico di valori ritmici riferiti a un BPM
  (convenzione: 1/4 = un movimento = 60/bpm secondi; 1 = semibreve)
"""

import pytest

from audiolayers.strategies.duration_strategy import (RhythmicDurationStrategy,
                                              TendencyDurationStrategy,
                                              build_duration_strategies)
from audiolayers.parameters.parameter import Parameter
from audiolayers.parameters.parameter_definitions import get_parameter_definition
from audiolayers.shared.exceptions import InvalidFieldValueError
from audiolayers.shared.seeding import rng_for


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
    """La factory ritorna la coppia (grano, ioi): quanto DURA il grano e
    OGNI QUANTO ne nasce uno. Senza rhythm coincidono; con rhythm la
    griglia è ritmica e la durata resta controllabile a parte."""

    def test_blocco_rhythm_guida_la_griglia_e_riempie_lo_slot(self):
        grain, ioi = build_duration_strategies(
            {"rhythm": {"bpm": 120, "pattern": [0.25]}},
            layer_id="l1", duration=30.0, seed=42,
        )
        assert isinstance(ioi, RhythmicDurationStrategy)
        assert grain is ioi   # senza duration dichiarata, grano = slot

    def test_default_e_tendency(self):
        grain, ioi = build_duration_strategies({}, layer_id="l1",
                                               duration=30.0, seed=42)
        assert isinstance(grain, TendencyDurationStrategy)
        assert grain is ioi
        assert grain.duration(0, 0.0) == 0.5  # default dallo schema

    def test_duration_e_rhythm_insieme_compongono(self):
        """Rhythm decide quando, duration quanto: grani corti su griglia
        ritmica (staccato granulare) senza dover scegliere tra i due."""
        grain, ioi = build_duration_strategies(
            {"duration": 0.05, "rhythm": {"bpm": 120, "pattern": [0.25]}},
            layer_id="l1", duration=30.0, seed=42,
        )
        assert isinstance(ioi, RhythmicDurationStrategy)
        assert isinstance(grain, TendencyDurationStrategy)
        assert grain.duration(0, 0.0) == pytest.approx(0.05)
        assert ioi.duration(0, 0.0) == pytest.approx(0.5)  # 1/4 a 120

    def test_rhythm_senza_bpm_o_pattern_e_un_errore(self):
        with pytest.raises(InvalidFieldValueError, match="bpm"):
            build_duration_strategies({"rhythm": {"pattern": [0.25]}},
                                      layer_id="l1", duration=30.0, seed=42)
        with pytest.raises(InvalidFieldValueError, match="pattern"):
            build_duration_strategies({"rhythm": {"bpm": 120}},
                                      layer_id="l1", duration=30.0, seed=42)
