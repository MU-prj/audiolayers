"""Piano di un layer: parametri + sequenza di frammenti, prima dell'audio.

È il punto condiviso tra render e analyzer di provisioning (plan 002):
entrambi devono costruire ESATTAMENTE la stessa sequenza (stesse Strategy,
stesso seed namespaced), il render per suonarla, l'analyzer per ricavarne
i requisiti di pool. Un solo assemblaggio = niente divergenze silenziose.
"""

from dataclasses import dataclass

from audiolayers.core.fragment_sequence import FragmentSpec, build_fragment_sequence
from audiolayers.parameters.parameter import Parameter
from audiolayers.parameters.parser import create_layer_parameters
from audiolayers.shared.seeding import rng_for
from audiolayers.strategies.duration_strategy import build_duration_strategies


def active_layers(layers: list) -> list:
    """Convenzione solo/mute (PGE): se esistono layer in solo suonano
    solo quelli, altrimenti tutti tranne i mutati. Vale per il render e
    per chiunque debba sapere quali layer contano (es. provisioning)."""
    def flag(layer, name):
        return name in layer and layer[name] is not False

    soloed = [l for l in layers if flag(l, "solo")]
    if soloed:
        return soloed
    return [l for l in layers if not flag(l, "mute")]


@dataclass(frozen=True)
class LayerPlan:
    """Parametri risolti e frammenti posati di un layer."""

    params: dict[str, Parameter]
    fragments: list[FragmentSpec]


def build_layer_plan(layer: dict, seed) -> LayerPlan:
    """Assembla parametri e sequenza di frammenti dal dict YAML del layer."""
    layer_id = layer.get("layer_id", "layer")
    target_duration = float(layer["duration"])
    time_mode = layer.get("time_mode", "absolute")

    params = create_layer_parameters(
        layer, layer_id=layer_id, duration=target_duration, seed=seed,
        time_mode=time_mode,
    )
    grain_strategy, ioi_strategy = build_duration_strategies(
        layer.get("fragment", {}), layer_id=layer_id,
        duration=target_duration, seed=seed, time_mode=time_mode,
    )
    fragments = build_fragment_sequence(
        duration_strategy=grain_strategy,
        ioi_strategy=ioi_strategy,
        fill_factor=params["fill_factor"],
        distribution=params["distribution"],
        target_duration=target_duration,
        rng=rng_for(seed, layer_id, "onset"),
    )
    return LayerPlan(params=params, fragments=fragments)
