from __future__ import annotations

import re

from .safety import Risk

# Heurístico de segurança, não um parser SQL completo — ver 01_RAG RAG-006A.
# Busca por palavra-chave em qualquer posição da string normalizada (não só no
# início), para reduzir o risco de uma instrução destrutiva "escondida" atrás
# de uma cláusula inicial inofensiva (ex.: um CTE seguido de DELETE).

_DESTRUCTIVE_KEYWORDS = ("DROP", "DELETE", "TRUNCATE", "REVOKE")
_CRITICAL_KEYWORDS = ("INSERT", "UPDATE", "CREATE", "ALTER", "GRANT", "MERGE", "UPSERT", "REPLACE")
_READ_STARTERS = ("SELECT", "EXPLAIN", "SHOW", "WITH")

_COMMENT_PATTERN = re.compile(r"--[^\n]*|/\*.*?\*/", re.DOTALL)
_WORD_PATTERN_CACHE: dict[str, re.Pattern[str]] = {}


def _word_pattern(keyword: str) -> re.Pattern[str]:
    if keyword not in _WORD_PATTERN_CACHE:
        _WORD_PATTERN_CACHE[keyword] = re.compile(rf"\b{keyword}\b", re.IGNORECASE)
    return _WORD_PATTERN_CACHE[keyword]


def _normalize(query: str) -> str:
    without_comments = _COMMENT_PATTERN.sub(" ", query or "")
    return without_comments.strip()


def classify(query: str) -> Risk:
    normalized = _normalize(query)
    if not normalized:
        raise ValueError("Instrução SQL vazia")

    for keyword in _DESTRUCTIVE_KEYWORDS:
        if _word_pattern(keyword).search(normalized):
            return Risk.DESTRUCTIVE

    for keyword in _CRITICAL_KEYWORDS:
        if _word_pattern(keyword).search(normalized):
            return Risk.CRITICAL

    first_word = re.split(r"\s+", normalized, maxsplit=1)[0].upper()
    if first_word in _READ_STARTERS:
        return Risk.READ

    # Formato não reconhecido: nunca assumir leitura por engano.
    return Risk.CRITICAL
