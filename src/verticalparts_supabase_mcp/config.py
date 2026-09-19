from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def _bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    mcp_transport: str = os.getenv("MCP_TRANSPORT", "stdio")
    mcp_host: str = os.getenv("MCP_HOST", "127.0.0.1")
    mcp_port: int = int(os.getenv("MCP_PORT", "8022"))

    supabase_access_token_path: Path | None = (
        Path(os.getenv("SUPABASE_ACCESS_TOKEN_PATH")).expanduser()
        if os.getenv("SUPABASE_ACCESS_TOKEN_PATH")
        else None
    )
    supabase_access_token_inline: str = os.getenv("SUPABASE_ACCESS_TOKEN", "")
    supabase_api_base: str = os.getenv("SUPABASE_API_BASE", "https://api.supabase.com/v1").rstrip("/")
    supabase_default_org_id: str = os.getenv("SUPABASE_DEFAULT_ORG_ID", "")

    projects_file: Path = Path(os.getenv("SUPABASE_PROJECTS_FILE", "./config/projects.yaml"))
    policies_file: Path = Path(os.getenv("SUPABASE_POLICIES_FILE", "./config/policies.yaml"))
    audit_log: Path = Path(os.getenv("SUPABASE_AUDIT_LOG", "./data/audit.jsonl"))

    allow_break_glass: bool = _bool("SUPABASE_ALLOW_BREAK_GLASS", False)

    def resolve_access_token(self) -> str:
        if self.supabase_access_token_path:
            if not self.supabase_access_token_path.exists():
                raise RuntimeError(
                    f"Personal Access Token do Supabase não encontrado: {self.supabase_access_token_path}"
                )
            token = self.supabase_access_token_path.read_text(encoding="utf-8").strip()
            if token:
                return token
        if self.supabase_access_token_inline.strip():
            return self.supabase_access_token_inline.strip()
        raise RuntimeError(
            "Nenhum Personal Access Token configurado (SUPABASE_ACCESS_TOKEN_PATH ou SUPABASE_ACCESS_TOKEN)"
        )

    def validate_runtime(self) -> None:
        self.resolve_access_token()


settings = Settings()
