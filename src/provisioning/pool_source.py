"""Strategy di provisioning del pool (plan 002, D-P4/D-P5/D-P7).

Due varianti sotto la stessa interfaccia:
- LocalPoolSource: il pool è una cartella locale già pronta (default);
- ArchiveDiggerSource: analizza il layer e scarica da Internet Archive
  i file mancanti via archivedigger (client iniettabile per i test).
"""

from pathlib import Path

import soundfile as sf

from src.engine.render import AUDIO_EXTENSIONS


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
