from __future__ import annotations

from .config import settings


class SupabaseAuth:
    """Autenticação por Personal Access Token: diferente do github-mcp (GitHub
    App, JWT trocado por installation token com cache/expiração), a Management
    API do Supabase usa o PAT diretamente como Bearer, sem troca nem expiração
    gerenciada por este MCP. Módulo mantido separado por simetria estrutural
    com os MCPs irmãos e como ponto único de evolução futura (ver 04_SDD
    seção 9) caso o Supabase venha a suportar OAuth App / tokens escopados."""

    def headers(self) -> dict[str, str]:
        token = settings.resolve_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }


supabase_auth = SupabaseAuth()
