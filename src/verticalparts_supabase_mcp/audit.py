from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import settings

SENSITIVE_MARKERS = ("TOKEN", "SECRET", "PASSWORD", "DB_PASS", "API_KEY", "PRIVATE_KEY", "AUTHORIZATION")

# Literais dentro de texto livre (ex.: instrução SQL) que parecem senha/token
# atribuído por igualdade ou parâmetro nomeado, ex.: password='...' ou db_pass: "..."
_INLINE_SECRET_PATTERN = re.compile(
    r"(password|db_pass|secret|token)\s*[:=]\s*'[^']*'|(password|db_pass|secret|token)\s*[:=]\s*\"[^\"]*\"",
    re.IGNORECASE,
)


def _redact_inline_secrets(text: str) -> str:
    return _INLINE_SECRET_PATTERN.sub(lambda m: f"{m.group(1) or m.group(2)}=[REDACTED]", text)


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            upper = str(k).upper()
            if any(m in upper for m in SENSITIVE_MARKERS):
                out[k] = "[REDACTED]"
            elif isinstance(v, str):
                out[k] = _redact_inline_secrets(v)
            else:
                out[k] = _redact(v)
        return out
    if isinstance(value, list):
        return [_redact(v) for v in value]
    return value


def write_audit(action: str, payload: dict[str, Any]) -> None:
    path: Path = settings.audit_log
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "payload": _redact(payload),
    }
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
