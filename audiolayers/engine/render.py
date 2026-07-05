"""Pipeline di rendering: partitura YAML → buffer stereo → file audio.

Dal M5 il layer è cablato sul sistema dichiarativo: parametri con
tendency mask (D5), durate da Strategy (D8), onset da fill_factor +
distribution con stop senza mozzatura (D2, D3, D7), seeding namespaced
con seed di sessione da timestamp sempre loggato (D14).
"""

import time as _time
from pathlib import Path

import numpy as np
import soundfile as sf
import yaml

from audiolayers.audio.pan import pan_stereo
from audiolayers.audio.pool import scan_pool
from audiolayers.audio.source_loader import load_mono
from audiolayers.core.layer_plan import active_layers, build_layer_plan
from audiolayers.strategies.fragment_envelope import build_fragment_envelope
from audiolayers.strategies.overflow_strategy import build_overflow_strategy
from audiolayers.strategies.selection_strategy import build_selection_strategy

DEFAULT_SAMPLE_RATE = 48000


def render_score(score_path: Path, output_path: Path, *,
                 output_format: str | None = None,
                 bit_depth: str = "32f",
                 normalize: bool = False) -> None:
    """Renderizza la partitura e scrive il file di output.

    Default: WAV float32 (D1). `output_format` (wav/aiff/flac) e
    `bit_depth` (32f/24) arrivano dalla CLI; `normalize` porta il picco
    a -1 dBFS (mai di default, D16).
    """
    data = yaml.safe_load(Path(score_path).read_text(encoding="utf-8"))
    sample_rate = int(data.get("sample_rate", DEFAULT_SAMPLE_RATE))
    master = _build_master(data.get("master_volume", 0.0))  # valida SUBITO
    seed = _resolve_seed(data)

    layers = active_layers(data["layers"])

    # Ogni layer ha un onset sulla timeline globale (D15).
    placed = []
    for layer in layers:
        onset_frames = round(float(layer.get("onset", 0.0)) * sample_rate)
        placed.append((onset_frames, _render_layer(layer, sample_rate, seed)))

    total_frames = max(offset + len(buf) for offset, buf in placed)
    mix = np.zeros((total_frames, 2), dtype=np.float64)
    for offset, buf in placed:
        mix[offset:offset + len(buf)] += buf

    mix = _apply_master(mix, master, sample_rate)
    mix = _report_peak_and_normalize(mix, normalize)

    fmt, subtype = _resolve_format(output_path, output_format, bit_depth)
    sf.write(str(output_path), mix.astype(np.float32), sample_rate,
             format=fmt, subtype=subtype)


def _build_master(master_volume):
    """Costruisce e VALIDA il master contro i bounds del registry:
    la partitura fuori range non parte proprio (niente sorprese a fine
    render)."""
    from audiolayers.envelopes.envelope_builder import build_envelope
    from audiolayers.parameters.parser import validate_parameter

    master = build_envelope(master_volume)
    validate_parameter(master, "master_volume")
    return master


def _apply_master(mix: np.ndarray, master,
                  sample_rate: int) -> np.ndarray:
    """master in dB (float o Envelope), curva per-campione."""
    from audiolayers.envelopes.envelope import Envelope

    if isinstance(master, Envelope):
        times = np.arange(len(mix)) / sample_rate
        gain = 10.0 ** (master.evaluate_array(times) / 20.0)
        return mix * gain[:, None]
    return mix * (10.0 ** (master / 20.0))


def _report_peak_and_normalize(mix: np.ndarray,
                               normalize: bool) -> np.ndarray:
    """Misura il picco e lo RIPORTA (D16); --normalize opzionale."""
    peak = float(np.abs(mix).max())
    if peak == 0.0:
        print("picco: silenzio assoluto")
        return mix
    peak_db = 20.0 * np.log10(peak)
    if peak > 1.0:
        print(f"CLIPPING: picco {peak_db:+.2f} dBFS "
              f"-- riduci master_volume di almeno {peak_db:.2f} dB"
              + (" (o usa --normalize)" if not normalize else ""))
    else:
        print(f"picco: {peak_db:+.2f} dBFS")
    if normalize:
        target = 10.0 ** (-1.0 / 20.0)  # -1 dBFS
        mix = mix * (target / peak)
        print("normalizzato a -1.00 dBFS")
    return mix


_FORMATS = {
    ".wav": "WAV", ".aiff": "AIFF", ".aif": "AIFF", ".flac": "FLAC",
}


def _resolve_format(output_path: Path, output_format: str | None,
                    bit_depth: str) -> tuple[str, str]:
    """Formato dal flag CLI, o dall'estensione, o WAV (D1)."""
    if output_format is not None:
        fmt = output_format.upper()
        if fmt == "AIF":
            fmt = "AIFF"
    else:
        fmt = _FORMATS.get(Path(output_path).suffix.lower(), "WAV")
    # FLAC non supporta il float: sempre PCM 24 bit.
    if fmt == "FLAC" or bit_depth == "24":
        return fmt, "PCM_24"
    return fmt, "FLOAT"


def _resolve_seed(data: dict):
    """Seed dalla partitura; assente → da timestamp, SEMPRE loggato (D14)."""
    if "seed" in data and data["seed"] is not None:
        return data["seed"]
    seed = _time.time_ns()
    # Solo ASCII nell'output CLI: le console Windows in pipe si strozzano
    # su caratteri non-ASCII (stessa lezione dei messaggi d'errore).
    print(f"seed di sessione (generato): {seed} "
          f"-- aggiungi 'seed: {seed}' alla partitura per riprodurre")
    return seed


def _render_layer(layer: dict, sample_rate: int, seed) -> np.ndarray:
    """Renderizza un layer: sequenza di frammenti → timeline stereo."""
    layer_id = layer.get("layer_id", "layer")

    plan = build_layer_plan(layer, seed)
    params, fragments = plan.params, plan.fragments

    pool_files = scan_pool(Path(layer["pool"]))
    # Precarica il pool una volta sola (mono, al SR di progetto, D13).
    sources = [load_mono(p, sample_rate) for p in pool_files]
    selection = build_selection_strategy(
        layer.get("selection", {}), pool_size=len(sources),
        layer_id=layer_id, seed=seed,
    )
    overflow = build_overflow_strategy(layer.get("pointer", {}))
    envelope = build_fragment_envelope(layer.get("fragment", {}))

    extent = max(f.onset + f.duration for f in fragments)
    buffer = np.zeros((round(extent * sample_rate), 2), dtype=np.float64)

    for index, frag in enumerate(fragments):
        # Quale file suona questo frammento lo decide la Strategy (D6).
        source = sources[selection.select(index)]
        # Punto di lettura [0,1] → posizione assoluta nel file (D9),
        # indipendente dalla durata; l'overflow decide la Strategy.
        start_norm = params["pointer_start"].get_value(frag.onset)
        start_frame = round(start_norm * len(source))
        segment = overflow.read(source, start_frame,
                                round(frag.duration * sample_rate))

        # La voce del frammento (M8): gain dB (D10) → inviluppo
        # anti-click (D11) → pan mid/side (D12). I parametri sono
        # campionati al tempo di posa, con le loro tendency mask.
        gain = 10.0 ** (params["volume"].get_value(frag.onset) / 20.0)
        shaped = envelope.apply(segment, sample_rate) * gain
        stereo = pan_stereo(shaped, params["pan"].get_value(frag.onset))

        start = round(frag.onset * sample_rate)
        end = min(start + len(stereo), len(buffer))
        buffer[start:end] += stereo[: end - start]

    return buffer
