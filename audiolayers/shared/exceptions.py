"""Gerarchia degli errori di audiolayers.

Tutti gli errori rivolti al compositore derivano da ScoreError, così la
CLI può catturarli e stampare solo il messaggio (niente traceback).
"""


class ScoreError(Exception):
    """Errore nella partitura o nei dati che essa referenzia."""


class InvalidFieldValueError(ScoreError):
    """Valore di un campo YAML non valido (forma o contenuto)."""


class ParameterBoundError(ScoreError):
    """Valore di un parametro fuori dai bounds di sicurezza."""

    def __init__(self, param_name: str, value, min_bound, max_bound,
                 value_type: str = "value"):
        self.param_name = param_name
        # Solo ASCII nei messaggi d'errore: verranno stampati dalla CLI
        # anche su console Windows con codepage limitati.
        super().__init__(
            f"Parametro '{param_name}' fuori bounds: {value_type}={value} "
            f"non rientra in [{min_bound}, {max_bound}]"
        )
