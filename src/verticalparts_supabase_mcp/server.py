from __future__ import annotations

import json
import re
from typing import Any

from mcp.server.fastmcp import FastMCP

from .audit import write_audit
from .config import settings
from .registry import load_projects, resolve_ref
from .safety import Risk, require_confirmation
from .sql_risk import classify as classify_sql
from .supabase_client import supabase

mcp = FastMCP("VerticalParts Supabase", host=settings.mcp_host, port=settings.mcp_port)


# --------------------------------------------------------------------------
# Validadores
# --------------------------------------------------------------------------

def _org_id(org_id: str | None) -> str:
    value = (org_id or settings.supabase_default_org_id).strip()
    if not re.fullmatch(r"[a-z0-9]{6,40}", value):
        raise ValueError("org_id inválido")
    return value


def _ref(ref: str) -> str:
    resolved = resolve_ref((ref or "").strip())
    if not re.fullmatch(r"[a-z0-9]{15,30}", resolved):
        raise ValueError("project_ref inválido (esperado ref real do Supabase ou nome registrado em config/projects.yaml)")
    return resolved


def _name(value: str, *, field: str = "name") -> str:
    v = (value or "").strip()
    if not v or len(v) > 100:
        raise ValueError(f"{field} inválido")
    return v


def _region(region: str) -> str:
    value = (region or "").strip()
    if not re.fullmatch(r"[a-z0-9-]{3,30}", value):
        raise ValueError("region inválida")
    return value


def _branch_id(branch_id: str) -> str:
    value = (branch_id or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9-]{8,64}", value):
        raise ValueError("branch_id inválido")
    return value


def _slug(slug: str, *, field: str = "slug") -> str:
    value = (slug or "").strip()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", value):
        raise ValueError(f"{field} inválido")
    return value


def _sql(query: str) -> str:
    value = (query or "").strip()
    if not value:
        raise ValueError("query SQL vazia")
    return value


# --------------------------------------------------------------------------
# Contexto
# --------------------------------------------------------------------------

@mcp.tool()
async def sb_whoami() -> Any:
    """Valida o Personal Access Token e retorna as organizações visíveis a ele."""
    orgs = await supabase.list_organizations()
    return {"organizations": orgs}


@mcp.tool()
async def sb_list_registered_projects() -> dict[str, Any]:
    """Lista os projetos registrados em config/projects.yaml do runtime, com criticidade/contexto."""
    return load_projects()


# --------------------------------------------------------------------------
# Organizações
# --------------------------------------------------------------------------

@mcp.tool()
async def sb_list_organizations() -> Any:
    """Lista as organizações Supabase visíveis ao Personal Access Token configurado."""
    return await supabase.list_organizations()


@mcp.tool()
async def sb_get_organization(org_id: str | None = None) -> Any:
    """Consulta detalhes de uma organização (padrão: SUPABASE_DEFAULT_ORG_ID)."""
    return await supabase.get_organization(_org_id(org_id))


# --------------------------------------------------------------------------
# Projetos
# --------------------------------------------------------------------------

@mcp.tool()
async def sb_list_projects() -> Any:
    """Lista todos os projetos visíveis ao Personal Access Token, em todas as organizações."""
    return await supabase.list_projects()


@mcp.tool()
async def sb_get_project(ref: str) -> Any:
    """Consulta detalhes de um projeto. `ref` pode ser o project_ref real ou um nome registrado em config/projects.yaml."""
    return await supabase.get_project(_ref(ref))


@mcp.tool()
async def sb_get_project_url(ref: str) -> Any:
    """Retorna a URL pública do projeto (https://<ref>.supabase.co)."""
    return await supabase.get_project_url(_ref(ref))


@mcp.tool()
async def sb_get_publishable_keys(ref: str) -> Any:
    """Retorna a(s) chave(s) anon/publishable do projeto — nunca a service_role key (nunca exposta por este MCP)."""
    return await supabase.get_publishable_keys(_ref(ref))


@mcp.tool()
async def sb_create_project(
    name: str, region: str, db_pass: str, org_id: str | None = None, plan: str = "free", confirmation: str | None = None
) -> Any:
    """Cria um projeto novo. Tem custo financeiro real em plano pago — verifique sb_get_cost antes. Exige confirmation='CONFIRMO'."""
    require_confirmation(Risk.CRITICAL, confirmation)
    o, n, r = _org_id(org_id), _name(name), _region(region)
    if not db_pass or len(db_pass) < 8:
        raise ValueError("db_pass deve ter pelo menos 8 caracteres")
    result = await supabase.create_project(o, n, r, db_pass, plan)
    write_audit("sb_create_project", {"org_id": o, "name": n, "region": r, "plan": plan, "db_pass": "[REDACTED]", "ok": True})
    return result


@mcp.tool()
async def sb_pause_project(ref: str, confirmation: str | None = None) -> Any:
    """Pausa um projeto (reversível via sb_restore_project). Exige confirmation='CONFIRMO'."""
    require_confirmation(Risk.CRITICAL, confirmation)
    r = _ref(ref)
    result = await supabase.pause_project(r)
    write_audit("sb_pause_project", {"ref": r, "ok": True})
    return result


@mcp.tool()
async def sb_restore_project(ref: str, confirmation: str | None = None) -> Any:
    """Restaura um projeto pausado. Exige confirmation='CONFIRMO'."""
    require_confirmation(Risk.CRITICAL, confirmation)
    r = _ref(ref)
    result = await supabase.restore_project(r)
    write_audit("sb_restore_project", {"ref": r, "ok": True})
    return result


@mcp.tool()
async def sb_delete_project(ref: str, confirmation: str | None = None) -> Any:
    """Apaga um projeto PERMANENTEMENTE — banco, Auth, Storage e Edge Functions juntos, sem lixeira. A operação mais destrutiva do catálogo. Exige confirmation='CONFIRMO_DESTRUTIVO'."""
    require_confirmation(Risk.DESTRUCTIVE, confirmation)
    r = _ref(ref)
    result = await supabase.delete_project(r)
    write_audit("sb_delete_project", {"ref": r, "ok": True})
    return result


@mcp.tool()
async def sb_get_cost(org_id: str | None = None, resource_type: str = "project") -> Any:
    """Consulta o custo estimado de um novo recurso (ex.: um novo projeto) antes de criá-lo."""
    return await supabase.get_cost(_org_id(org_id), resource_type)


@mcp.tool()
async def sb_confirm_cost(resource_type: str = "project", recurrence: str = "monthly", org_id: str | None = None, confirmation: str | None = None) -> Any:
    """Confirma explicitamente um custo apresentado por sb_get_cost, gerando o comprovante que algumas operações de criação exigem. Exige confirmation='CONFIRMO'."""
    require_confirmation(Risk.CRITICAL, confirmation)
    o = _org_id(org_id)
    result = await supabase.confirm_cost(o, resource_type, recurrence)
    write_audit("sb_confirm_cost", {"org_id": o, "resource_type": resource_type, "recurrence": recurrence, "ok": True})
    return result


# --------------------------------------------------------------------------
# Banco de dados
# --------------------------------------------------------------------------

@mcp.tool()
async def sb_list_tables(ref: str, schemas: list[str] | None = None) -> Any:
    """Lista tabelas do projeto (padrão: schema public)."""
    return await supabase.list_tables(_ref(ref), schemas)


@mcp.tool()
async def sb_list_extensions(ref: str) -> Any:
    """Lista extensões Postgres disponíveis/instaladas no projeto."""
    return await supabase.list_extensions(_ref(ref))


@mcp.tool()
async def sb_list_migrations(ref: str) -> Any:
    """Lista o histórico de migrações aplicadas via sb_apply_migration."""
    return await supabase.list_migrations(_ref(ref))


@mcp.tool()
async def sb_apply_migration(ref: str, name: str, query: str, confirmation: str | None = None) -> Any:
    """Aplica uma migração de schema (DDL), rastreada no histórico do Supabase. Prefira esta tool a sb_execute_sql para mudanças de schema duradouras. Exige confirmation='CONFIRMO'."""
    require_confirmation(Risk.CRITICAL, confirmation)
    r, n, q = _ref(ref), _name(name, field="name"), _sql(query)
    result = await supabase.apply_migration(r, n, q)
    write_audit("sb_apply_migration", {"ref": r, "name": n, "query": q, "ok": True})
    return result


@mcp.tool()
async def sb_execute_sql(ref: str, query: str, confirmation: str | None = None) -> Any:
    """Executa SQL livre contra o Postgres do projeto. Risco DINÂMICO conforme o conteúdo da instrução (ver 01_RAG RAG-006A): SELECT/EXPLAIN/SHOW/WITH sem termo de escrita = leitura, sem confirmação; INSERT/UPDATE/CREATE/ALTER/GRANT = CRITICAL, exige confirmation='CONFIRMO'; DROP/DELETE/TRUNCATE/REVOKE = DESTRUCTIVE, exige confirmation='CONFIRMO_DESTRUTIVO'."""
    r, q = _ref(ref), _sql(query)
    risk = classify_sql(q)
    require_confirmation(risk, confirmation)
    result = await supabase.execute_sql(r, q)
    if risk != Risk.READ:
        write_audit("sb_execute_sql", {"ref": r, "query": q, "risk": str(risk), "ok": True})
    return result


@mcp.tool()
async def sb_get_advisors(ref: str, advisor_type: str = "security") -> Any:
    """Consulta os advisors do projeto. advisor_type: security|performance."""
    if advisor_type not in {"security", "performance"}:
        raise ValueError("advisor_type deve ser security ou performance")
    return await supabase.get_advisors(_ref(ref), advisor_type)


@mcp.tool()
async def sb_query_logs(ref: str, service: str = "api", sql: str | None = None) -> Any:
    """Consulta logs recentes do projeto. service: api|postgres|auth|storage|edge-function. `sql` opcional para uma consulta customizada contra os logs (Logflare SQL)."""
    if service not in {"api", "postgres", "auth", "storage", "edge-function"}:
        raise ValueError("service inválido")
    return await supabase.query_logs(_ref(ref), service, sql)


@mcp.tool()
async def sb_generate_typescript_types(ref: str) -> Any:
    """Gera os tipos TypeScript do schema do banco, para uso em integração de frontend."""
    return await supabase.generate_typescript_types(_ref(ref))


# --------------------------------------------------------------------------
# Branches de desenvolvimento (experimental — ver 04_SDD seção 9)
# --------------------------------------------------------------------------

@mcp.tool()
async def sb_list_branches(ref: str) -> Any:
    """Lista branches de desenvolvimento do projeto. Feature experimental/paga da própria Supabase — ver 04_SDD seção 9."""
    return await supabase.list_branches(_ref(ref))


@mcp.tool()
async def sb_create_branch(ref: str, name: str, confirmation: str | None = None) -> Any:
    """Cria uma branch de desenvolvimento. Experimental (ver 04_SDD seção 9). Exige confirmation='CONFIRMO'."""
    require_confirmation(Risk.CRITICAL, confirmation)
    r, n = _ref(ref), _name(name, field="name")
    result = await supabase.create_branch(r, n)
    write_audit("sb_create_branch", {"ref": r, "name": n, "ok": True})
    return result


@mcp.tool()
async def sb_delete_branch(branch_id: str, confirmation: str | None = None) -> Any:
    """Apaga uma branch de desenvolvimento. Experimental (ver 04_SDD seção 9). Exige confirmation='CONFIRMO_DESTRUTIVO'."""
    require_confirmation(Risk.DESTRUCTIVE, confirmation)
    b = _branch_id(branch_id)
    result = await supabase.delete_branch(b)
    write_audit("sb_delete_branch", {"branch_id": b, "ok": True})
    return result


@mcp.tool()
async def sb_merge_branch(branch_id: str, confirmation: str | None = None) -> Any:
    """Aplica (merge) as mudanças da branch de desenvolvimento no projeto de produção associado. Experimental (ver 04_SDD seção 9). Exige confirmation='CONFIRMO'."""
    require_confirmation(Risk.CRITICAL, confirmation)
    b = _branch_id(branch_id)
    result = await supabase.merge_branch(b)
    write_audit("sb_merge_branch", {"branch_id": b, "ok": True})
    return result


@mcp.tool()
async def sb_reset_branch(branch_id: str, confirmation: str | None = None) -> Any:
    """Reseta os dados da branch de desenvolvimento para o estado do projeto de produção. Descarta mudanças da branch. Experimental (ver 04_SDD seção 9). Exige confirmation='CONFIRMO_DESTRUTIVO'."""
    require_confirmation(Risk.DESTRUCTIVE, confirmation)
    b = _branch_id(branch_id)
    result = await supabase.reset_branch(b)
    write_audit("sb_reset_branch", {"branch_id": b, "ok": True})
    return result


@mcp.tool()
async def sb_rebase_branch(branch_id: str, confirmation: str | None = None) -> Any:
    """Rebasa a branch de desenvolvimento sobre o estado atual da produção. Experimental (ver 04_SDD seção 9). Exige confirmation='CONFIRMO'."""
    require_confirmation(Risk.CRITICAL, confirmation)
    b = _branch_id(branch_id)
    result = await supabase.rebase_branch(b)
    write_audit("sb_rebase_branch", {"branch_id": b, "ok": True})
    return result


# --------------------------------------------------------------------------
# Edge Functions
# --------------------------------------------------------------------------

@mcp.tool()
async def sb_list_edge_functions(ref: str) -> Any:
    """Lista as Edge Functions do projeto."""
    return await supabase.list_edge_functions(_ref(ref))


@mcp.tool()
async def sb_get_edge_function(ref: str, slug: str) -> Any:
    """Consulta detalhes de uma Edge Function."""
    return await supabase.get_edge_function(_ref(ref), _slug(slug))


@mcp.tool()
async def sb_deploy_edge_function(ref: str, slug: str, body_json: str, confirmation: str | None = None) -> Any:
    """Publica (cria ou atualiza) uma Edge Function. `body_json` no formato esperado pela Management API (entrypoint, arquivos, import_map). Frequentemente tem efeito em produção imediatamente após o deploy. Exige confirmation='CONFIRMO'."""
    require_confirmation(Risk.CRITICAL, confirmation)
    r, s = _ref(ref), _slug(slug, field="slug")
    body = json.loads(body_json)
    result = await supabase.deploy_edge_function(r, s, body)
    write_audit("sb_deploy_edge_function", {"ref": r, "slug": s, "ok": True})
    return result


@mcp.tool()
async def sb_delete_edge_function(ref: str, slug: str, confirmation: str | None = None) -> Any:
    """Apaga uma Edge Function. Exige confirmation='CONFIRMO_DESTRUTIVO'."""
    require_confirmation(Risk.DESTRUCTIVE, confirmation)
    r, s = _ref(ref), _slug(slug, field="slug")
    result = await supabase.delete_edge_function(r, s)
    write_audit("sb_delete_edge_function", {"ref": r, "slug": s, "ok": True})
    return result


# --------------------------------------------------------------------------
# Break-glass
# --------------------------------------------------------------------------

@mcp.tool()
async def sb_api_call(method: str, path: str, body_json: str | None = None, confirmation: str | None = None) -> Any:
    """BREAK-GLASS: chamada direta à Management API do Supabase (api.supabase.com/v1) para endpoint ainda sem tool semântica. GET é leitura; qualquer outro método exige confirmation='BREAK_GLASS'. Exige SUPABASE_ALLOW_BREAK_GLASS=true. NUNCA use para tentar obter service_role key — isso é bloqueado por política, não por limitação técnica desta tool."""
    method_u = method.upper().strip()
    if "api-keys" in path and "reveal=true" in (path or ""):
        raise PermissionError("Recuperação de chave secreta (service_role) via break-glass é bloqueada por política deste MCP")
    if method_u != "GET":
        if not settings.allow_break_glass:
            raise PermissionError("Break-glass está desabilitado por SUPABASE_ALLOW_BREAK_GLASS=false")
        require_confirmation(Risk.BREAK_GLASS, confirmation)
    body = json.loads(body_json) if body_json else None
    result = await supabase.api_call(method_u, path, body)
    write_audit("sb_api_call", {"method": method_u, "path": path, "ok": True})
    return result


def main() -> None:
    transport = settings.mcp_transport.strip().lower()
    if transport not in {"stdio", "sse", "streamable-http"}:
        raise RuntimeError(f"MCP_TRANSPORT inválido: {transport}")
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
