"""Costruzione della sequenza di frammenti (M5): onset + durata.

Il modello (D2, D3, D7):
- durata del frammento i → DurationStrategy (tendency o rhythmic)
- IOI sincrono = durata / fill_factor(t)
- `distribution` (Truax): 0 = metronomo, 1 = async uniforme 0..2×IOI,
  valori intermedi = miscela lineare
- stop: quando il prossimo onset supererebbe la durata-obiettivo;
  l'ultimo frammento suona per intero (mai mozzato)

La costruzione è sinistra→destra: gli envelope dei parametri sono
campionati al tempo di posa di ciascun frammento.
"""

from dataclasses import dataclass

from audiolayers.parameters.parameter import Parameter
from audiolayers.strategies.duration_strategy import DurationStrategy


@dataclass(frozen=True)
class FragmentSpec:
    """Un frammento posato sulla timeline: quando e per quanto."""

    onset: float
    duration: float


def build_fragment_sequence(*, duration_strategy: DurationStrategy,
                            fill_factor: Parameter,
                            distribution: Parameter,
                            target_duration: float,
                            rng,
                            ioi_strategy: DurationStrategy | None = None,
                            ) -> list[FragmentSpec]:
    """Genera la sequenza di FragmentSpec per un layer.

    `ioi_strategy` (default: la stessa del grano) decide la base
    dell'intervallo tra onset: con la griglia ritmica gli onset seguono
    il pattern mentre la durata del grano resta indipendente.
    """
    fragments: list[FragmentSpec] = []
    t = 0.0
    index = 0
    while t < target_duration:
        dur = duration_strategy.duration(index, t)
        fragments.append(FragmentSpec(onset=t, duration=dur))

        # Mai richiamare la stessa strategy due volte: una tendency mask
        # estrarrebbe un secondo valore (draw in piu' = golden rotti).
        if ioi_strategy is None or ioi_strategy is duration_strategy:
            base = dur
        else:
            base = ioi_strategy.duration(index, t)
        ioi_sync = base / fill_factor.get_value(t)
        d = distribution.get_value(t)
        if d > 0.0:
            # Truax fino a 1 (uniforme 0..2x); oltre 1 lo spread si
            # amplifica (0..2x*d): nuvole con buchi e grappoli marcati.
            ioi_async = rng.uniform(0.0, 2.0 * ioi_sync * max(1.0, d))
            blend = min(d, 1.0)
            ioi = (1.0 - blend) * ioi_sync + blend * ioi_async
        else:
            ioi = ioi_sync

        t += ioi
        index += 1
    return fragments
