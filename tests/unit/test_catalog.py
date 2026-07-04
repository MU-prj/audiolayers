"""Unit — catalogo dei parametri: LA fonte unica (plan deepening D1).

Bounds, default, enum, env-abilità e spiegazioni di ogni parametro
vivono qui e vengono DERIVATI dal motore (registry bounds, registri
delle Strategy, default degli inviluppi): la GUI si genera da /api/params
e non può più divergere.
"""

from src.parameters.catalog import catalog, catalog_entry
from src.parameters.parameter_definitions import get_parameter_definition
from src.strategies.fragment_envelope import (DEFAULT_ATTACK,
                                              available_envelopes)
from src.strategies.overflow_strategy import available_overflow_strategies
from src.strategies.selection_strategy import available_selection_strategies


class TestCatalogo:
    def test_ha_le_tre_sezioni(self):
        cat = catalog()
        assert set(cat) == {"global", "layer", "provision"}
        assert cat["layer"], "sezione layer vuota"

    def test_bounds_derivati_dal_registry_del_motore(self):
        """fill_factor nel catalogo = bounds veri del motore, non copie."""
        entry = catalog_entry("layer", "fill_factor")
        bounds = get_parameter_definition("fill_factor")
        assert entry["min"] == bounds.min_val
        assert entry["max"] == bounds.max_val

    def test_enum_derivati_dai_registri_delle_strategy(self):
        assert (catalog_entry("layer", "selection.strategy")["options"]
                == available_selection_strategies())
        assert (catalog_entry("layer", "pointer.overflow")["options"]
                == available_overflow_strategies())
        assert (catalog_entry("layer", "fragment.envelope")["options"]
                == available_envelopes())

    def test_default_attack_dal_motore(self):
        assert catalog_entry("layer", "fragment.attack")["default"] == DEFAULT_ATTACK

    def test_ogni_voce_ha_etichetta_e_spiegazione(self):
        for section in catalog().values():
            for entry in section:
                assert entry["label"], entry["path"]
                assert entry["info"], entry["path"]

    def test_env_solo_dove_il_motore_modula(self):
        """duration/onset/attack/release sono scalari per il motore:
        niente flag env nel catalogo."""
        for path in ("duration", "onset", "fragment.attack",
                     "fragment.release"):
            assert not catalog_entry("layer", path).get("env"), path
        for path in ("fill_factor", "fragment.duration", "volume", "pan"):
            assert catalog_entry("layer", path)["env"], path

    def test_serializzabile_json(self):
        import json
        json.dumps(catalog())
