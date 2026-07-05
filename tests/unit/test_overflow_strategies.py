"""Unit — strategie di overflow in lettura (M7, D9, D17).

Quando `punto_di_lettura + durata` supera la fine del file:
- clamp_back (default): arretra lo start del minimo necessario
- loop: riparte dall'inizio (wrap modulare)
- zero_pad: legge il disponibile, poi silenzio
"""

import numpy as np
import pytest

from audiolayers.shared.exceptions import InvalidFieldValueError
from audiolayers.strategies.overflow_strategy import (ClampBackOverflow,
                                              LoopOverflow, ZeroPadOverflow,
                                              build_overflow_strategy)

SOURCE = np.arange(10, dtype=np.float64)  # campioni riconoscibili 0..9


class TestClampBack:
    def test_lettura_che_ci_sta_non_viene_toccata(self):
        seg = ClampBackOverflow().read(SOURCE, start=2, length=4)
        assert np.array_equal(seg, [2, 3, 4, 5])

    def test_sforo_arretra_al_minimo_necessario(self):
        seg = ClampBackOverflow().read(SOURCE, start=8, length=4)
        assert np.array_equal(seg, [6, 7, 8, 9])  # finisce a fine file

    def test_file_piu_corto_della_durata_da_tutto_il_file(self):
        seg = ClampBackOverflow().read(SOURCE, start=0, length=20)
        assert np.array_equal(seg, SOURCE)  # onesto: più corto


class TestLoop:
    def test_wrap_modulare_a_fine_file(self):
        seg = LoopOverflow().read(SOURCE, start=8, length=5)
        assert np.array_equal(seg, [8, 9, 0, 1, 2])

    def test_lunghezza_esatta_anche_su_piu_giri(self):
        seg = LoopOverflow().read(SOURCE, start=0, length=25)
        assert len(seg) == 25
        assert np.array_equal(seg[:10], SOURCE)
        assert np.array_equal(seg[10:20], SOURCE)


class TestZeroPad:
    def test_disponibile_poi_silenzio(self):
        seg = ZeroPadOverflow().read(SOURCE, start=7, length=6)
        assert np.array_equal(seg, [7, 8, 9, 0, 0, 0])
        assert len(seg) == 6

    def test_lettura_che_ci_sta_esatta_non_aggiunge_padding(self):
        # start+length == len(source): niente da imbottire, ramo senza concat.
        seg = ZeroPadOverflow().read(SOURCE, start=4, length=6)
        assert np.array_equal(seg, [4, 5, 6, 7, 8, 9])
        assert len(seg) == 6


class TestFactory:
    def test_default_clamp_back(self):
        assert isinstance(build_overflow_strategy({}), ClampBackOverflow)

    def test_dichiarata_nel_blocco_pointer(self):
        assert isinstance(build_overflow_strategy({"overflow": "loop"}),
                          LoopOverflow)
        assert isinstance(build_overflow_strategy({"overflow": "zero_pad"}),
                          ZeroPadOverflow)

    def test_sconosciuta_errore_con_le_disponibili(self):
        with pytest.raises(InvalidFieldValueError, match="clamp_back"):
            build_overflow_strategy({"overflow": "bounce"})
