"""Strategy di provisioning del pool (plan 002, D-P4/D-P5/D-P7).

ArchiveDiggerSource analizza il layer e scarica da Internet Archive i
file mancanti via archivedigger (client iniettabile per i test). Senza
--dig il provisioning semplicemente non viene invocato: il pool è una
normale cartella locale, non serve una strategy no-op per dirlo.
"""

from pathlib import Path

from archivedigger.api import dig
from archivedigger.config import Config

from audiolayers.audio.pool import count_suitable_files
from audiolayers.provisioning.analyzer import (PoolRequirements,
                                       analyze_layer, apply_policy)

#: Default di ricerca quando la partitura non dice nulla (D-P4).
#: Solo formati che il loader sa leggere: niente mp3.
_DEFAULT_PROVISION = {
    "search": {"license": "cc"},
    "files": {"prefer": [["Flac", "WAVE", "AIFF"]]},
}

#: Giri di ricerca al massimo: a ogni giro max_items raddoppia (D-P5).
_MAX_ROUNDS = 3

#: Chiavi di POLITICA del blocco provision (issue #8): le consuma
#: apply_policy, non devono arrivare alla Config archivedigger.
_POLICY_KEYS = ("mode", "count", "variety", "min_margin", "max_factor")


def _split_policy(provision: dict | None) -> tuple[dict, dict]:
    """Separa (policy, config-di-ricerca) dal blocco provision."""
    rest = dict(provision or {})
    policy = {k: rest.pop(k) for k in list(rest) if k in _POLICY_KEYS}
    return policy, rest


class ArchiveDiggerSource:
    """Popola il pool da Internet Archive via archivedigger (D-P7).

    Idempotente: conta i file già idonei e scarica solo la differenza.
    Se Internet Archive non copre il fabbisogno, avvisa e lascia
    proseguire il render (la selezione sequential cicla).
    """

    def __init__(self, client=None):
        self._client = client

    def ensure(self, layer: dict, seed) -> None:
        policy, search_cfg = _split_policy(layer.get("provision"))
        requirements = apply_policy(analyze_layer(layer, seed), policy)
        self.ensure_pool(Path(layer["pool"]), requirements, search_cfg)

    def ensure_pool(self, pool: Path, requirements: PoolRequirements,
                    search_cfg: dict) -> None:
        pool.mkdir(parents=True, exist_ok=True)

        shortfall = self._shortfall(pool, requirements)
        if shortfall <= 0:
            return

        for round_index in range(_MAX_ROUNDS):
            before = shortfall
            config = self._build_config(search_cfg, requirements, pool,
                                        max_items=shortfall * (2 ** round_index))
            dig(config, client=self._client)
            shortfall = self._shortfall(pool, requirements)
            if shortfall <= 0:
                return
            if shortfall == before:
                break  # nessun progresso: inutile allargare ancora

        print(f"ATTENZIONE: pool '{pool}' ha "
              f"{requirements.files_needed - shortfall} file idonei su "
              f"{requirements.files_needed} richiesti -- il render procede, "
              f"la selezione ciclera' sui file disponibili")

    def _shortfall(self, pool: Path, requirements) -> int:
        suitable = count_suitable_files(
            pool, min_duration=requirements.min_file_duration)
        return requirements.files_needed - suitable

    def _build_config(self, search_cfg: dict, requirements, pool: Path,
                      *, max_items: int) -> Config:
        """Config archivedigger: default ← blocco `provision`, con filtri
        e conteggi calcolati da analyzer+policy (non dichiarabili)."""
        computed = {
            "search": {"max_items": max_items},
            "filters": {
                "min_duration": requirements.min_file_duration,
                "max_duration": requirements.max_file_duration,
                "max_files_per_item": 1,
            },
            "download": {"destdir": str(pool)},
        }
        job: dict = {}
        _merge(job, _DEFAULT_PROVISION)
        _merge(job, search_cfg)
        _merge(job, computed)
        return Config.build(job=job)


def provision_score(score_path, client=None) -> None:
    """Assicura il pool di ogni layer attivo della partitura (flag --dig).

    Il seed dell'analisi è quello della partitura; se assente si usa 0:
    per i layer deterministici non cambia nulla, per quelli casuali il
    conteggio è comunque una fotografia valida quanto un'altra.
    """
    import yaml

    from audiolayers.core.layer_plan import active_layers

    data = yaml.safe_load(Path(score_path).read_text(encoding="utf-8"))
    seed = data.get("seed") if data.get("seed") is not None else 0
    source = ArchiveDiggerSource(client=client)
    layers = active_layers(data["layers"])

    global_provision = data.get("provision")
    if not global_provision:
        for layer in layers:
            source.ensure(layer, seed)
        return

    # Digger GLOBALE (issue #8): un solo blocco provision a livello di
    # partitura, i blocchi per-layer vengono ignorati. I fabbisogni dei
    # layer che condividono lo stesso pool si sommano, le durate minime
    # si allineano al piu' esigente; la policy si applica all'aggregato.
    policy, search_cfg = _split_policy(global_provision)
    groups: dict[str, PoolRequirements] = {}
    for layer in layers:
        req = analyze_layer(layer, seed)
        key = str(Path(layer["pool"]))
        if key in groups:
            g = groups[key]
            groups[key] = PoolRequirements(
                files_needed=g.files_needed + req.files_needed,
                min_file_duration=max(g.min_file_duration,
                                      req.min_file_duration),
                max_file_duration=max(g.max_file_duration,
                                      req.max_file_duration))
        else:
            groups[key] = req
    for pool, req in groups.items():
        source.ensure_pool(Path(pool), apply_policy(req, policy), search_cfg)


def _merge(base: dict, overlay: dict) -> None:
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _merge(base[key], value)
        else:
            base[key] = value
