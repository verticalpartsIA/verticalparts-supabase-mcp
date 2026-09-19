from __future__ import annotations

from enum import StrEnum


class Risk(StrEnum):
    READ = "read"
    OPERATIONAL = "operational"
    CRITICAL = "critical"
    DESTRUCTIVE = "destructive"
    BREAK_GLASS = "break_glass"


def require_confirmation(risk: Risk, confirmation: str | None) -> None:
    if risk in {Risk.READ, Risk.OPERATIONAL}:
        return
    expected = {
        Risk.CRITICAL: "CONFIRMO",
        Risk.DESTRUCTIVE: "CONFIRMO_DESTRUTIVO",
        Risk.BREAK_GLASS: "BREAK_GLASS",
    }[risk]
    if confirmation != expected:
        raise PermissionError(
            f"Operação {risk} exige confirmação explícita: {expected}. "
            "A LLM deve explicar alvo, efeito e possibilidade de rollback antes de pedir a confirmação."
        )
