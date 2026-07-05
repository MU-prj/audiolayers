"""Unit — inviluppo per-frammento (M8, D11, D17).

Anti-click: ogni frammento apre e chiude morbidamente (raised cosine
di default); con overlap (F>1) gli inviluppi producono crossfade
emergenti. `rectangle` = nessun inviluppo (Strategy esplicita).
"""

import numpy as np
import pytest

from audiolayers.shared.exceptions import InvalidFieldValueError
from audiolayers.strategies.fragment_envelope import (RaisedCosineEnvelope,
                                              RectangleEnvelope,
                                              build_fragment_envelope)

SR = 48000


class TestRaisedCosine:
    def test_apre_da_zero_e_chiude_a_zero(self):
        seg = np.ones(SR // 2)  # 0.5 s di DC a 1.0
        out = RaisedCosineEnvelope(attack=0.008, release=0.010).apply(seg, SR)
        assert out[0] == pytest.approx(0.0, abs=1e-6)
        assert out[-1] == pytest.approx(0.0, abs=1e-3)
        assert len(out) == len(seg)

    def test_plateau_a_uno_nel_mezzo(self):
        seg = np.ones(SR // 2)
        out = RaisedCosineEnvelope(attack=0.008, release=0.010).apply(seg, SR)
        middle = out[SR // 4]
        assert middle == pytest.approx(1.0)

    def test_attack_e_release_rispettano_le_durate(self):
        seg = np.ones(SR)
        out = RaisedCosineEnvelope(attack=0.1, release=0.2).apply(seg, SR)
        n_attack, n_release = round(0.1 * SR), round(0.2 * SR)
        assert out[n_attack - 1] == pytest.approx(1.0, abs=1e-3)
        assert np.all(out[n_attack: SR - n_release] == 1.0)

    def test_frammento_piu_corto_dei_fade_usa_finestra_intera(self):
        """Niente plateau: una campana raised-cosine su tutto il segmento."""
        seg = np.ones(100)  # ~2 ms, meno di attack+release
        out = RaisedCosineEnvelope(attack=0.008, release=0.010).apply(seg, SR)
        assert len(out) == 100
        assert out[0] == pytest.approx(0.0, abs=1e-6)
        assert out.max() <= 1.0


class TestRectangle:
    def test_lascia_il_segnale_intatto(self):
        seg = np.linspace(-1, 1, 100)
        out = RectangleEnvelope().apply(seg, SR)
        assert np.array_equal(out, seg)


class TestFactory:
    def test_default_raised_cosine_con_fade_di_default(self):
        strat = build_fragment_envelope({})
        assert isinstance(strat, RaisedCosineEnvelope)

    def test_dichiarato_nel_blocco_fragment(self):
        strat = build_fragment_envelope({"envelope": "rectangle"})
        assert isinstance(strat, RectangleEnvelope)

    def test_sconosciuto_errore_con_i_disponibili(self):
        with pytest.raises(InvalidFieldValueError, match="raised_cosine"):
            build_fragment_envelope({"envelope": "hanning_super"})
