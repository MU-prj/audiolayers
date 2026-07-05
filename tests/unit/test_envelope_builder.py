"""Unit — envelope builder (M2): dal valore YAML grezzo a float | Envelope.

Forme accettate (D5, convenzioni PGE):
- scalare                → float (costante, non è un envelope)
- [[t, v], …]            → Envelope, interpolazione lineare implicita
- {type, points, time_mode} → Envelope con opzioni esplicite
"""

import pytest

from audiolayers.envelopes.envelope import Envelope
from audiolayers.envelopes.envelope_builder import build_envelope, is_envelope_like
from audiolayers.shared.exceptions import InvalidFieldValueError


class TestFormeAccettate:
    def test_scalare_resta_float(self):
        assert build_envelope(3) == 3.0
        assert isinstance(build_envelope(3), float)
        assert build_envelope(-6.5) == -6.5

    def test_lista_breakpoint_diventa_envelope(self):
        env = build_envelope([[0.0, 5.0], [10.0, 40.0]])
        assert isinstance(env, Envelope)
        assert env.evaluate(5.0) == pytest.approx(22.5)

    def test_forma_dict_con_points(self):
        env = build_envelope({"points": [[0.0, 5.0], [10.0, 40.0]]})
        assert isinstance(env, Envelope)
        assert env.evaluate(10.0) == 40.0

    def test_dict_type_non_supportato_solleva_errore(self):
        with pytest.raises(InvalidFieldValueError, match="cubic"):
            build_envelope({"type": "cubic", "points": [[0, 0], [1, 1]]})


class TestTimeMode:
    def test_normalized_scala_i_tempi_sulla_duration(self):
        env = build_envelope(
            [[0.0, 5.0], [0.5, 40.0], [1.0, 5.0]],
            duration=30.0,
            time_mode="normalized",
        )
        assert env.evaluate(15.0) == 40.0  # 0.5 × 30 s
        assert env.evaluate(30.0) == 5.0

    def test_absolute_default_non_scala(self):
        env = build_envelope([[0.0, 5.0], [0.5, 40.0]], duration=30.0)
        assert env.evaluate(0.5) == 40.0

    def test_time_mode_locale_del_dict_sovrascrive_quello_ereditato(self):
        env = build_envelope(
            {"points": [[0.0, 0.0], [2.0, 10.0]], "time_mode": "absolute"},
            duration=30.0,
            time_mode="normalized",  # ereditato dal layer, ignorato
        )
        assert env.evaluate(2.0) == 10.0

    def test_time_mode_sconosciuto_solleva_errore(self):
        with pytest.raises(InvalidFieldValueError, match="time_mode"):
            build_envelope([[0, 0], [1, 1]], time_mode="percentuale")


class TestErroriDiValidazione:
    def test_bool_non_e_un_numero_valido(self):
        # bool è sottotipo di int in Python: va respinto PRIMA del ramo numerico.
        with pytest.raises(InvalidFieldValueError, match="boolean"):
            build_envelope(True)
        with pytest.raises(InvalidFieldValueError, match="boolean"):
            build_envelope(False)

    def test_dict_senza_points_solleva_errore(self):
        with pytest.raises(InvalidFieldValueError, match="points"):
            build_envelope({"type": "linear"})

    def test_tipo_grezzo_non_riconosciuto_solleva_errore(self):
        with pytest.raises(InvalidFieldValueError, match="atteso numero"):
            build_envelope("hanning")
        with pytest.raises(InvalidFieldValueError, match="atteso numero"):
            build_envelope(None)

    def test_normalized_senza_duration_e_un_errore(self):
        with pytest.raises(InvalidFieldValueError, match="duration"):
            build_envelope([[0.0, 0.0], [1.0, 1.0]], time_mode="normalized")


class TestClassificazione:
    def test_riconosce_le_forme_envelope(self):
        assert is_envelope_like([[0, 5], [1, 10]])
        assert is_envelope_like({"points": [[0, 5]]})

    def test_scarta_scalari_e_forme_estranee(self):
        assert not is_envelope_like(3.0)
        assert not is_envelope_like("hanning")
        assert not is_envelope_like([])
        assert not is_envelope_like({"bpm": 120})
