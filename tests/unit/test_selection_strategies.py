"""Unit — strategie di selezione dal pool (M6, D6, D17).

- sequential: i file in ordine, ciclando
- rotation: una permutazione casuale per ogni giro (ogni file una
  volta per giro, come uno shuffle-play)
- random: estrazioni indipendenti uniformi
Tutte con RNG namespaced (D14) dove serve.
"""

import pytest

from audiolayers.shared.exceptions import InvalidFieldValueError
from audiolayers.shared.seeding import rng_for
from audiolayers.strategies.selection_strategy import (RandomSelection,
                                               RotationSelection,
                                               SequentialSelection,
                                               build_selection_strategy)


class TestSequential:
    def test_in_ordine_ciclando(self):
        strat = SequentialSelection(pool_size=3)
        assert [strat.select(i) for i in range(7)] == [0, 1, 2, 0, 1, 2, 0]


class TestRandom:
    def test_riproducibile_e_copre_il_pool(self):
        s1 = RandomSelection(pool_size=4, rng=rng_for(42, "l1", "selection"))
        s2 = RandomSelection(pool_size=4, rng=rng_for(42, "l1", "selection"))
        picks1 = [s1.select(i) for i in range(50)]
        picks2 = [s2.select(i) for i in range(50)]
        assert picks1 == picks2                      # stesso seed
        assert set(picks1) == {0, 1, 2, 3}           # copre tutto il pool
        assert all(0 <= p < 4 for p in picks1)


class TestRotation:
    def test_ogni_giro_e_una_permutazione_completa(self):
        strat = RotationSelection(pool_size=4,
                                  rng=rng_for(42, "l1", "selection"))
        picks = [strat.select(i) for i in range(12)]
        for round_start in (0, 4, 8):
            round_picks = picks[round_start:round_start + 4]
            assert sorted(round_picks) == [0, 1, 2, 3]  # tutti, una volta

    def test_i_giri_differiscono_tra_loro(self):
        strat = RotationSelection(pool_size=6,
                                  rng=rng_for(42, "l1", "selection"))
        rounds = [[strat.select(i) for i in range(r * 6, (r + 1) * 6)]
                  for r in range(4)]
        assert len({tuple(r) for r in rounds}) > 1   # non sempre lo stesso

    def test_riproducibile_a_parita_di_seed(self):
        s1 = RotationSelection(pool_size=5, rng=rng_for(7, "l", "selection"))
        s2 = RotationSelection(pool_size=5, rng=rng_for(7, "l", "selection"))
        assert [s1.select(i) for i in range(15)] == \
               [s2.select(i) for i in range(15)]


class TestFactory:
    def test_default_sequential(self):
        strat = build_selection_strategy({}, pool_size=3,
                                         layer_id="l1", seed=42)
        assert isinstance(strat, SequentialSelection)

    def test_strategia_dichiarata_nel_yaml(self):
        strat = build_selection_strategy({"strategy": "random"},
                                         pool_size=3, layer_id="l1", seed=42)
        assert isinstance(strat, RandomSelection)
        strat = build_selection_strategy({"strategy": "rotation"},
                                         pool_size=3, layer_id="l1", seed=42)
        assert isinstance(strat, RotationSelection)

    def test_strategia_sconosciuta_errore_con_le_disponibili(self):
        with pytest.raises(InvalidFieldValueError, match="sequential"):
            build_selection_strategy({"strategy": "shuffle"},
                                     pool_size=3, layer_id="l1", seed=42)
