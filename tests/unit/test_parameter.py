"""Unit — Parameter (M3): tendency mask `base ± range` (D5, Truax).

base e range sono float o Envelope; l'estrazione è uniforme nella
banda, con RNG namespaced iniettato (D14); i bounds fanno da guardia.
"""

import numpy as np
import pytest

from src.parameters.parameter import Parameter
from src.parameters.parameter_definitions import ParameterBounds
from src.shared.seeding import rng_for
from src.envelopes.envelope import Envelope

VOLUME_BOUNDS = ParameterBounds(min_val=-120.0, max_val=12.0,
                                min_range=0.0, max_range=24.0)


class TestBaseDeterministica:
    def test_scalare_senza_range_e_costante(self):
        p = Parameter("volume", base=-6.0, bounds=VOLUME_BOUNDS)
        assert p.get_value(0.0) == -6.0
        assert p.get_value(99.0) == -6.0

    def test_base_envelope_evolve_nel_tempo(self):
        env = Envelope([[0.0, -24.0], [10.0, 0.0]])
        p = Parameter("volume", base=env, bounds=VOLUME_BOUNDS)
        assert p.get_value(0.0) == -24.0
        assert p.get_value(5.0) == pytest.approx(-12.0)
        assert p.get_value(10.0) == 0.0

    def test_clamp_di_sicurezza_sui_bounds(self):
        env = Envelope([[0.0, 0.0], [1.0, 50.0]])  # sfora max_val=12 a runtime
        p = Parameter("volume", base=env, bounds=VOLUME_BOUNDS)
        assert p.get_value(1.0) == 12.0


class TestTendencyMask:
    def test_valori_nella_banda_base_piu_meno_range(self):
        rng = rng_for(42, "l1", "volume")
        p = Parameter("volume", base=-6.0, bounds=VOLUME_BOUNDS,
                      mod_range=3.0, rng=rng)
        values = [p.get_value(0.0) for _ in range(200)]
        assert all(-9.0 <= v <= -3.0 for v in values)
        assert len(set(values)) > 1  # varia davvero

    def test_riproducibile_con_stesso_seed(self):
        p1 = Parameter("volume", base=-6.0, bounds=VOLUME_BOUNDS,
                       mod_range=3.0, rng=rng_for(42, "l1", "volume"))
        p2 = Parameter("volume", base=-6.0, bounds=VOLUME_BOUNDS,
                       mod_range=3.0, rng=rng_for(42, "l1", "volume"))
        assert [p1.get_value(0.0) for _ in range(10)] == \
               [p2.get_value(0.0) for _ in range(10)]

    def test_range_envelope_maschera_che_respira(self):
        """range 0→3 nel tempo: a t=0 deterministico, poi la banda si apre."""
        rng = rng_for(42, "l1", "volume")
        r_env = Envelope([[0.0, 0.0], [10.0, 3.0]])
        p = Parameter("volume", base=-6.0, bounds=VOLUME_BOUNDS,
                      mod_range=r_env, rng=rng)
        assert p.get_value(0.0) == -6.0  # banda chiusa
        vals = [p.get_value(10.0) for _ in range(100)]
        assert all(-9.0 <= v <= -3.0 for v in vals)
        assert max(vals) > -5.0  # la banda a t=10 è davvero aperta

    def test_range_senza_rng_e_un_errore_di_programmazione(self):
        with pytest.raises(ValueError, match="rng"):
            Parameter("volume", base=-6.0, bounds=VOLUME_BOUNDS,
                      mod_range=3.0)
