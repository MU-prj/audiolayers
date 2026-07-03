"""Unit — schema + parser (M3): dal dict YAML del layer ai Parameter.

- chiavi assenti → default dallo schema (ParameterSpec)
- suffisso `_range` → tendency mask (D5)
- bounds violati → ParameterBoundError parlante (validazione al parse)
- ogni parametro riceve il suo RNG namespaced (D14)
"""

import pytest

from src.parameters.parser import create_layer_parameters
from src.shared.exceptions import ParameterBoundError


def make_params(layer_data: dict, seed=42, duration=30.0):
    return create_layer_parameters(
        layer_data, layer_id="l1", duration=duration, seed=seed
    )


class TestDefaultDalloSchema:
    def test_layer_vuoto_inizializza_tutti_i_default(self):
        params = make_params({})
        assert params["volume"].get_value(0.0) == 0.0
        assert params["pan"].get_value(0.0) == 0.0
        assert params["fill_factor"].get_value(0.0) == 1.0
        assert params["distribution"].get_value(0.0) == 0.0
        assert params["pointer_start"].get_value(0.0) == 0.0

    def test_fragment_duration_non_e_nello_schema(self):
        """La durata del grano è assemblata SOLO dalla DurationStrategy:
        una seconda copia nello schema sarebbe calcolata e mai letta
        (e correggerla a metà = bug invisibile)."""
        params = make_params({"fragment": {"duration": 1.25}})
        assert "fragment_duration" not in params

    def test_chiave_annidata_letta_con_dot_notation(self):
        params = make_params({"pointer": {"start": 0.75}})
        assert params["pointer_start"].get_value(0.0) == 0.75

    def test_valore_envelope_nel_yaml(self):
        params = make_params({"fill_factor": [[0.0, 0.5], [30.0, 2.0]]})
        assert params["fill_factor"].get_value(15.0) == pytest.approx(1.25)


class TestTendencyMaskDalYaml:
    def test_range_sorella_attiva_la_maschera(self):
        params = make_params({"volume": -6.0, "volume_range": 3.0})
        values = [params["volume"].get_value(0.0) for _ in range(100)]
        assert all(-9.0 <= v <= -3.0 for v in values)
        assert len(set(values)) > 1

    def test_riproducibile_a_parita_di_seed(self):
        p1 = make_params({"volume": -6.0, "volume_range": 3.0}, seed=7)
        p2 = make_params({"volume": -6.0, "volume_range": 3.0}, seed=7)
        assert [p1["volume"].get_value(0.0) for _ in range(10)] == \
               [p2["volume"].get_value(0.0) for _ in range(10)]


class TestValidazioneBounds:
    def test_scalare_fuori_bounds_solleva_errore_parlante(self):
        with pytest.raises(ParameterBoundError, match="volume"):
            make_params({"volume": 99.0})  # max 12 dB

    def test_breakpoint_envelope_fuori_bounds(self):
        with pytest.raises(ParameterBoundError, match="fill_factor"):
            make_params({"fill_factor": [[0.0, 1.0], [10.0, 500.0]]})

    def test_range_fuori_bounds(self):
        with pytest.raises(ParameterBoundError, match="volume"):
            make_params({"volume": 0.0, "volume_range": 90.0})  # max 24
