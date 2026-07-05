"""Unit — Envelope (M2): funzione f(t) → v a tratti su breakpoint.

Il mattone di D5: ogni parametro (base e range delle tendency mask)
può essere una curva nel tempo. Interpolazione lineare (v1).
"""

import pytest

from audiolayers.envelopes.envelope import Envelope


class TestInterpolazioneLineare:
    def test_valore_esatto_sui_breakpoint(self):
        env = Envelope([[0.0, 5.0], [10.0, 40.0], [30.0, 5.0]])
        assert env.evaluate(0.0) == 5.0
        assert env.evaluate(10.0) == 40.0
        assert env.evaluate(30.0) == 5.0

    def test_interpolazione_tra_breakpoint(self):
        env = Envelope([[0.0, 5.0], [10.0, 40.0], [30.0, 5.0]])
        assert env.evaluate(5.0) == pytest.approx(22.5)   # metà del 1° segmento
        assert env.evaluate(20.0) == pytest.approx(22.5)  # metà del 2° segmento


class TestComportamentoAiBordi:
    def test_hold_prima_del_primo_breakpoint(self):
        env = Envelope([[2.0, 10.0], [5.0, 20.0]])
        assert env.evaluate(0.0) == 10.0
        assert env.evaluate(-100.0) == 10.0

    def test_hold_dopo_ultimo_breakpoint(self):
        env = Envelope([[2.0, 10.0], [5.0, 20.0]])
        assert env.evaluate(5.1) == 20.0
        assert env.evaluate(1e9) == 20.0


class TestNormalizzazioneInput:
    def test_breakpoint_non_ordinati_vengono_ordinati(self):
        """L'utente non deve garantire l'ordine (convenzione PGE)."""
        env = Envelope([[10.0, 40.0], [0.0, 5.0], [30.0, 5.0]])
        assert env.evaluate(0.0) == 5.0
        assert env.evaluate(5.0) == pytest.approx(22.5)
        assert env.evaluate(10.0) == 40.0

    def test_singolo_breakpoint_e_una_costante(self):
        env = Envelope([[3.0, 7.5]])
        assert env.evaluate(0.0) == 7.5
        assert env.evaluate(100.0) == 7.5

    def test_zero_breakpoint_solleva_errore_chiaro(self):
        from audiolayers.shared.exceptions import InvalidFieldValueError

        with pytest.raises(InvalidFieldValueError, match="breakpoint"):
            Envelope([])


class TestValutazioneVettoriale:
    def test_evaluate_array_coincide_con_evaluate(self):
        import numpy as np

        env = Envelope([[0.0, 5.0], [10.0, 40.0], [30.0, 5.0]])
        times = np.array([0.0, 5.0, 10.0, 20.0, 30.0, 99.0])
        out = env.evaluate_array(times)
        assert out.shape == times.shape
        assert list(out) == [env.evaluate(t) for t in times]
