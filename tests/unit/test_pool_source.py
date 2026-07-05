"""Unit — strategy di provisioning del pool (plan 002, D-P4/D-P5/D-P7).

Il pool può essere una semplice cartella locale (default) o venire
popolato da Internet Archive via archivedigger. La strategy è idempotente:
conta i file già idonei e scarica solo la differenza.
"""

import numpy as np
import soundfile as sf
from archivedigger.models import IAFile, IAItem

from audiolayers.audio.pool import count_suitable_files
from audiolayers.provisioning.pool_source import ArchiveDiggerSource


def write_wav(path, seconds, sample_rate=48000):
    frames = round(seconds * sample_rate)
    sf.write(str(path), np.zeros(frames, dtype=np.float32), sample_rate)


class FakeArchiveClient:
    """Client Internet Archive finto: cataloghi in memoria, download che
    scrive wav reali. Registra query e max_items ricevuti."""

    def __init__(self, n_items=50, length=5.0):
        self._length = length
        self._ids = [f"item-{i:03d}" for i in range(n_items)]
        self.queries: list[str] = []
        self.max_items_seen: list[int] = []

    def search(self, query, sort="downloads desc", max_items=100):
        self.queries.append(query)
        self.max_items_seen.append(max_items)
        yield from self._ids[:max_items]

    def get_item(self, identifier):
        file = IAFile(name=f"{identifier}.wav", format="WAVE",
                      size=1000, length=self._length, source="original")
        return IAItem(identifier=identifier, metadata={}, files=[file])

    def download_file(self, item, file, local_path):
        local_path.parent.mkdir(parents=True, exist_ok=True)
        write_wav(local_path, self._length)


class GradualArchiveClient(FakeArchiveClient):
    """Rivela un item idoneo in più a ogni ricerca: il pool cresce di uno
    per giro, così c'è sempre progresso (mai lo stallo che fa `break`) ma il
    fabbisogno non viene mai coperto entro _MAX_ROUNDS."""

    def __init__(self):
        super().__init__(n_items=10, length=5.0)
        self._reveal = 0

    def search(self, query, sort="downloads desc", max_items=100):
        self._reveal += 1
        self.queries.append(query)
        self.max_items_seen.append(max_items)
        yield from self._ids[:min(self._reveal, max_items)]


DET_LAYER = {
    "layer_id": "det",
    "duration": 2.0,
    "fill_factor": 1.0,
    "fragment": {"duration": 0.5},
}


class TestPolicyProvision:
    def test_fixed_scarica_n_file_e_non_sporca_archivedigger(self, tmp_path):
        """Le chiavi di policy (mode/files/...) NON devono finire nella
        Config archivedigger (campi sconosciuti = errore)."""
        pool = tmp_path / "pool"
        layer = dict(DET_LAYER, pool=str(pool),
                     provision={"mode": "fixed", "count": 2,
                                "search": {"license": "cc"}})
        ArchiveDiggerSource(client=FakeArchiveClient()).ensure(layer, seed=1)
        assert count_suitable_files(pool, min_duration=0.5) == 2


class TestDiggerGlobale:
    def test_provision_top_level_aggrega_i_layer_sullo_stesso_pool(
            self, tmp_path):
        """Blocco provision a livello di partitura: un solo ragionamento
        per pool, fabbisogni sommati (2 layer x 4 frammenti = 8 file)."""
        import yaml as _yaml

        from audiolayers.provisioning.pool_source import provision_score
        pool = tmp_path / "pool"
        score = {
            "seed": 1,
            "provision": {"search": {"license": "cc"}},
            "layers": [dict(DET_LAYER, layer_id="a", pool=str(pool)),
                       dict(DET_LAYER, layer_id="b", pool=str(pool))],
        }
        path = tmp_path / "s.yaml"
        path.write_text(_yaml.safe_dump(score), encoding="utf-8")
        client = FakeArchiveClient()
        provision_score(path, client=client)
        assert count_suitable_files(pool, min_duration=0.5) == 8
        assert len(client.queries) == 1   # un solo giro per il pool

    def test_globale_ignora_i_provision_dei_layer(self, tmp_path):
        """Col digger globale i blocchi per-layer non contano: il fixed
        globale vince sul per-layer."""
        import yaml as _yaml

        from audiolayers.provisioning.pool_source import provision_score
        pool = tmp_path / "pool"
        score = {
            "seed": 1,
            "provision": {"mode": "fixed", "count": 3},
            "layers": [dict(DET_LAYER, pool=str(pool),
                            provision={"mode": "fixed", "count": 50})],
        }
        path = tmp_path / "s.yaml"
        path.write_text(_yaml.safe_dump(score), encoding="utf-8")
        provision_score(path, client=FakeArchiveClient())
        assert count_suitable_files(pool, min_duration=0.5) == 3


class TestArchiveDiggerSource:
    def test_pool_vuoto_scarica_un_file_per_frammento(self, tmp_path):
        """Layer da 4 frammenti, pool vuoto → 4 file idonei scaricati."""
        pool = tmp_path / "pool"
        layer = dict(DET_LAYER, pool=str(pool))
        client = FakeArchiveClient()
        ArchiveDiggerSource(client=client).ensure(layer, seed=1)
        assert count_suitable_files(pool, min_duration=0.5) == 4

    def test_pool_gia_pieno_non_tocca_internet_archive(self, tmp_path):
        """Idempotenza (D-P5): file idonei già sufficienti → zero ricerche."""
        pool = tmp_path / "pool"
        pool.mkdir()
        for i in range(4):
            write_wav(pool / f"gia_{i}.wav", 2.0)
        layer = dict(DET_LAYER, pool=str(pool))
        client = FakeArchiveClient()
        ArchiveDiggerSource(client=client).ensure(layer, seed=1)
        assert client.queries == []

    def test_pool_parziale_chiede_solo_la_differenza(self, tmp_path):
        """3 file idonei su 4 → alla ricerca si chiede 1 solo item."""
        pool = tmp_path / "pool"
        pool.mkdir()
        for i in range(3):
            write_wav(pool / f"gia_{i}.wav", 2.0)
        layer = dict(DET_LAYER, pool=str(pool))
        client = FakeArchiveClient()
        ArchiveDiggerSource(client=client).ensure(layer, seed=1)
        assert client.max_items_seen[0] == 1
        assert count_suitable_files(pool, min_duration=0.5) == 4

    def test_blocco_provision_finisce_nella_query(self, tmp_path):
        """La partitura orienta la ricerca; senza blocco valgono i default
        (license cc). La collection dichiarata deve comparire nella query."""
        layer = dict(DET_LAYER, pool=str(tmp_path / "pool"),
                     provision={"search": {"collection": ["field-recordings"]}})
        client = FakeArchiveClient()
        ArchiveDiggerSource(client=client).ensure(layer, seed=1)
        assert "field-recordings" in client.queries[0]
        assert "license" in client.queries[0].lower()

    def test_archivio_insufficiente_avvisa_e_non_cicla_per_sempre(
            self, tmp_path, capsys):
        """Solo 2 item disponibili per 4 frammenti → warning esplicito,
        il metodo termina e il pool tiene quello che c'è."""
        pool = tmp_path / "pool"
        layer = dict(DET_LAYER, pool=str(pool))
        client = FakeArchiveClient(n_items=2)
        ArchiveDiggerSource(client=client).ensure(layer, seed=1)
        assert count_suitable_files(pool, min_duration=0.5) == 2
        assert "ATTENZIONE" in capsys.readouterr().out

    def test_progresso_lento_esaurisce_i_giri_e_avvisa(
            self, tmp_path, capsys):
        """Archivio che stilla un file nuovo per giro: c'è progresso (mai
        break per stallo) ma non basta entro _MAX_ROUNDS → il loop esaurisce
        i giri, avvisa, e lascia proseguire il render col poco raccolto."""
        pool = tmp_path / "pool"
        layer = dict(DET_LAYER, pool=str(pool))       # servono 4 file
        client = GradualArchiveClient()
        ArchiveDiggerSource(client=client).ensure(layer, seed=1)
        # 3 giri × +1 file = 3 idonei su 4: sotto il fabbisogno ma non zero
        assert count_suitable_files(pool, min_duration=0.5) == 3
        assert len(client.queries) == 3               # ha usato tutti i giri
        assert "ATTENZIONE" in capsys.readouterr().out


