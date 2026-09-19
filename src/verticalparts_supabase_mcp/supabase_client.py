from __future__ import annotations

from typing import Any

import httpx

from .config import settings
from .supabase_auth import supabase_auth


class SupabaseClient:
    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> httpx.Response:
        url = path if path.startswith("http") else f"{settings.supabase_api_base}{path}"
        headers = supabase_auth.headers()
        async with httpx.AsyncClient(timeout=60) as client:
            return await client.request(method, url, headers=headers, params=params, json=json)

    async def request_ok(self, method: str, path: str, **kwargs: Any) -> Any:
        resp = await self.request(method, path, **kwargs)
        if resp.status_code == 401:
            raise RuntimeError(
                "Supabase Management API retornou 401 — o Personal Access Token está "
                "ausente, inválido ou foi revogado (não há token de troca para renovar "
                "automaticamente, ver 04_SDD seção 2.3)."
            )
        if resp.status_code >= 400:
            raise RuntimeError(f"Supabase Management API {method} {path} -> {resp.status_code}: {resp.text[:1000]}")
        if resp.status_code == 204 or not resp.content:
            return {"ok": True, "status": resp.status_code}
        return resp.json()

    # --- whoami / organizações ---

    async def list_organizations(self) -> Any:
        return await self.request_ok("GET", "/organizations")

    async def get_organization(self, org_id: str) -> Any:
        return await self.request_ok("GET", f"/organizations/{org_id}")

    # --- projetos ---

    async def list_projects(self) -> Any:
        return await self.request_ok("GET", "/projects")

    async def get_project(self, ref: str) -> Any:
        return await self.request_ok("GET", f"/projects/{ref}")

    async def create_project(
        self, org_id: str, name: str, region: str, db_pass: str, plan: str = "free"
    ) -> Any:
        return await self.request_ok(
            "POST",
            "/projects",
            json={
                "organization_id": org_id,
                "name": name,
                "region": region,
                "db_pass": db_pass,
                "plan": plan,
            },
        )

    async def pause_project(self, ref: str) -> Any:
        return await self.request_ok("POST", f"/projects/{ref}/pause")

    async def restore_project(self, ref: str) -> Any:
        return await self.request_ok("POST", f"/projects/{ref}/restore")

    async def delete_project(self, ref: str) -> Any:
        return await self.request_ok("DELETE", f"/projects/{ref}")

    async def get_project_url(self, ref: str) -> Any:
        return {"project_url": f"https://{ref}.supabase.co"}

    async def get_publishable_keys(self, ref: str) -> Any:
        keys = await self.request_ok("GET", f"/projects/{ref}/api-keys", params={"reveal": "false"})
        # Defesa em profundidade: mesmo que a API devolva mais que a anon/publishable
        # em alguma resposta futura, este método nunca repassa nada marcado 'secret'.
        if isinstance(keys, list):
            return [k for k in keys if k.get("name") in {"anon", "publishable"} and not k.get("secret", False)]
        return keys

    async def get_cost(self, org_id: str, resource_type: str) -> Any:
        return await self.request_ok(
            "GET", f"/organizations/{org_id}/cost", params={"resource_type": resource_type}
        )

    async def confirm_cost(self, org_id: str, resource_type: str, recurrence: str) -> Any:
        return await self.request_ok(
            "POST",
            f"/organizations/{org_id}/cost",
            json={"resource_type": resource_type, "recurrence": recurrence},
        )

    # --- banco de dados ---

    async def execute_sql(self, ref: str, query: str) -> Any:
        return await self.request_ok("POST", f"/projects/{ref}/database/query", json={"query": query})

    async def list_tables(self, ref: str, schemas: list[str] | None = None) -> Any:
        schema_list = schemas or ["public"]
        placeholders = ", ".join(f"'{s}'" for s in schema_list)
        query = f"""
            select table_schema, table_name
            from information_schema.tables
            where table_schema in ({placeholders})
            order by table_schema, table_name;
        """
        return await self.execute_sql(ref, query)

    async def list_extensions(self, ref: str) -> Any:
        query = "select name, default_version, installed_version, comment from pg_available_extensions order by name;"
        return await self.execute_sql(ref, query)

    async def list_migrations(self, ref: str) -> Any:
        return await self.request_ok("GET", f"/projects/{ref}/database/migrations")

    async def apply_migration(self, ref: str, name: str, query: str) -> Any:
        return await self.request_ok(
            "POST", f"/projects/{ref}/database/migrations", json={"name": name, "query": query}
        )

    async def get_advisors(self, ref: str, advisor_type: str) -> Any:
        return await self.request_ok("GET", f"/projects/{ref}/advisors/{advisor_type}")

    async def query_logs(self, ref: str, service: str, sql: str | None = None) -> Any:
        params = {"sql": sql} if sql else None
        return await self.request_ok("GET", f"/projects/{ref}/analytics/endpoints/logs.all", params=params or {"iso_timestamp_start": "", "sql": f"select * from {service}_logs limit 50"})

    async def generate_typescript_types(self, ref: str) -> Any:
        return await self.request_ok("GET", f"/projects/{ref}/types/typescript")

    # --- branches (experimental — ver 04_SDD seção 9, endpoints não homologados ainda) ---

    async def list_branches(self, ref: str) -> Any:
        return await self.request_ok("GET", f"/projects/{ref}/branches")

    async def create_branch(self, ref: str, name: str) -> Any:
        return await self.request_ok("POST", f"/projects/{ref}/branches", json={"branch_name": name})

    async def delete_branch(self, branch_id: str) -> Any:
        return await self.request_ok("DELETE", f"/branches/{branch_id}")

    async def merge_branch(self, branch_id: str) -> Any:
        return await self.request_ok("POST", f"/branches/{branch_id}/merge")

    async def reset_branch(self, branch_id: str) -> Any:
        return await self.request_ok("POST", f"/branches/{branch_id}/reset")

    async def rebase_branch(self, branch_id: str) -> Any:
        return await self.request_ok("POST", f"/branches/{branch_id}/push")

    # --- edge functions ---

    async def list_edge_functions(self, ref: str) -> Any:
        return await self.request_ok("GET", f"/projects/{ref}/functions")

    async def get_edge_function(self, ref: str, slug: str) -> Any:
        return await self.request_ok("GET", f"/projects/{ref}/functions/{slug}")

    async def deploy_edge_function(self, ref: str, slug: str, body: dict[str, Any]) -> Any:
        return await self.request_ok("POST", f"/projects/{ref}/functions/{slug}/deploy", json=body)

    async def delete_edge_function(self, ref: str, slug: str) -> Any:
        return await self.request_ok("DELETE", f"/projects/{ref}/functions/{slug}")

    # --- break-glass ---

    async def api_call(self, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
        return await self.request_ok(method, path, json=body)


supabase = SupabaseClient()
