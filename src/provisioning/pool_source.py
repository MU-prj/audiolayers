"""Strategy di provisioning del pool (plan 002, D-P4/D-P5/D-P7).

Due varianti sotto la stessa interfaccia:
- LocalPoolSource: il pool è una cartella locale già pronta (default);
- ArchiveDiggerSource: analizza il layer e scarica da Internet Archive
  i file mancanti via archivedigger (client iniettabile per i test).
"""

from pathlib import Path

import soundfile as sf
from archivedigger.api import dig
from archivedigger.config import Config

from src.engine.render import AUDIO_EXTENSIONS
from src.provisioning.analyzer import analyze_layer

#: Default di ricerca quando la partitura non dice nulla (D-P4).
#: Solo formati che il loader sa leggere: niente mp3.
_DEFAULT_PROVISION = {
    "search": {"license": "cc"},
    "files": {"prefer": [["Flac", "WAVE", "AIFF"]]},
}

#: Giri di ricerca al massimo: a ogni giro max_items raddoppia (D-P5).
_MAX_ROUNDS = 3


class LocalPoolSource:
    """Il pool è una cartella locale già pronta: nessuna azione."""

    def ensure(self, layer: dict, seed) -> None:
        return None


class ArchiveDiggerSource:
    """Popola il pool da Internet Archive via archivedigger (D-P7).

    Idempotente: conta i file già idonei e scarica solo la differenza.
    Se Internet Archive non copre il fabbisogno, avvisa e lascia
    proseguire il render (la selezione sequential cicla).
    """

    def __init__(self, client=None):
        self._client = client

    def ensure(self, layer: dict, seed) -> None:
        requirements = analyze_layer(layer, seed)
        pool = Path(layer["pool"])
        pool.mkdir(parents=True, exist_ok=True)

        shortfall = self._shortfall(pool, requirements)
        if shortfall <= 0:
            return

        for round_index in range(_MAX_ROUNDS):
            before = shortfall
            config = self._build_config(layer, requirements, pool,
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

    def _build_config(self, layer: dict, requirements, pool: Path,
                      *, max_items: int) -> Config:
        """Config archivedigger: default ← blocco `provision` del layer,
        con filtri e conteggi calcolati dall'analyzer (non dichiarabili)."""
        provision = layer.get("provision") or {}
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
        _merge(job, provision)
        _merge(job, computed)
        return Config.build(job=job)


def _merge(base: dict, overlay: dict) -> None:
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _merge(base[key], value)
        else:
            base[key] = value


def count_suitable_files(pool_dir: Path, *, min_duration: float) -> int:
    """Quanti file del pool durano almeno `min_duration` secondi.

    La durata è quella reale letta dall'header (non metadati esterni).
    Cartella assente o vuota → 0: il chiamante deciderà di scaricare.
    """
    pool_dir = Path(pool_dir)
    if not pool_dir.is_dir():
        return 0
    count = 0
    for path in pool_dir.iterdir():
        if path.suffix.lower() not in AUDIO_EXTENSIONS:
            continue
        info = sf.info(str(path))
        if info.frames / info.samplerate >= min_duration:
            count += 1
    return count
