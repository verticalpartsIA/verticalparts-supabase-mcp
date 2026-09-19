# VerticalParts Supabase MCP

MCP corporativo para administração do Supabase da VerticalParts por LLMs — organizações, projetos, banco de dados (tabelas, extensões, migrações, SQL), branches de desenvolvimento e Edge Functions — com confirmação proporcional ao risco, auditoria e autenticação via Personal Access Token dedicado.

Status: **homologado em produção**. Endpoint público no ar em `https://supabase-mcp.vpsistema.com/mcp` (Nginx + TLS + X-API-Key), serviço systemd `verticalparts-supabase-mcp.service`. Código completo (33 tools), testado de ponta a ponta contra `api.supabase.com` com o Personal Access Token do operador: autenticação, leitura, escrita crítica com confirmação, classificação dinâmica de risco de `sb_execute_sql`, um ciclo real criar→validar→reverter (tabela de teste em projeto de baixa criticidade, sem resíduo), e o protocolo MCP em si testado via HTTPS público real (`initialize`, `tools/list` com as 33 tools, auth 401/200). A homologação revelou que o PAT enxerga **3 organizações** e **14 projetos** — mais do que o conector Supabase oficial mostrava antes disso. Edge Functions já homologadas (ciclo completo criar→ler→atualizar→apagar contra a API real, um bug real encontrado e corrigido no processo). Falta só testar branches de desenvolvimento contra a API real. Ver `00_READ_FIRST_SUPABASE_MCP.md` seções 5 e 7 para o relato completo.

Este projeto é o terceiro de uma família de MCPs administrativos da VerticalParts. Os outros dois, já homologados em produção, são [`verticalparts-infrastructure-mcp`](https://github.com/verticalpartsIA/verticalparts-infrastructure-mcp) (VPS + Hostinger) e [`verticalparts-github-mcp`](https://github.com/verticalpartsIA/verticalparts-github-mcp) (GitHub) — mesma filosofia de governança, mesmo padrão de código.

---

## Por que este projeto existe

Já existem dois conectores Supabase **oficiais** conectados a contas Claude da VerticalParts (`@supabase/mcp-server-supabase`, listado oficialmente como conector do Claude desde 2026): um com acesso à conta inteira e um escopado a um projeto específico. Nenhum dos dois tem modelo de confirmação por risco — `list_tables` e uma instrução SQL destrutiva chegam pela mesma tool, com a mesma fricção. Este projeto adiciona essa camada de governança por cima da Management API do Supabase, no mesmo padrão já usado para VPS/Hostinger e GitHub: classificação de risco (`READ`/`CRITICAL`/`DESTRUCTIVE`/`BREAK_GLASS`, com `sb_execute_sql` usando classificação **dinâmica** pelo conteúdo da instrução), confirmação explícita proporcional, auditoria sem segredo e um registro de criticidade por projeto.

## O que o MCP cobre

1. **Organizações e projetos** — listar, consultar, criar, pausar, restaurar, apagar; custo estimado.
2. **Banco de dados** — tabelas, extensões, migrações (aplicar e listar, rastreado no histórico do Supabase), SQL livre (risco classificado pelo conteúdo), advisors de segurança/performance, logs.
3. **Branches de desenvolvimento** — listar, criar, apagar, merge, reset, rebase (feature experimental/paga da própria Supabase — ver nota de homologação abaixo).
4. **Edge Functions** — listar, consultar, deploy, apagar.
5. **Desenvolvimento** — URL do projeto, chave `anon`/publishable, geração de types TypeScript.
6. **Break-glass** — chamada direta à Management API para o que ainda não tem tool semântica, desabilitado por padrão.

**Nunca implementado, por design**: nenhuma tool retorna a `service_role key` (secret API key) de um projeto, mesmo que a Management API permita — essa chave contorna RLS e seu vazamento é o pior cenário possível para qualquer projeto Supabase.

## Leia primeiro

A documentação canônica está na raiz, em ordem:

1. [00_READ_FIRST_SUPABASE_MCP.md](./00_READ_FIRST_SUPABASE_MCP.md)
2. [03_INSTRUCTIONS_LLM_SUPABASE_MCP_VERTICALPARTS.md](./03_INSTRUCTIONS_LLM_SUPABASE_MCP_VERTICALPARTS.md)
3. [01_RAG_SUPABASE_MCP_VERTICALPARTS.md](./01_RAG_SUPABASE_MCP_VERTICALPARTS.md)
4. [02_SPEC_SUPABASE_MCP_VERTICALPARTS.md](./02_SPEC_SUPABASE_MCP_VERTICALPARTS.md)
5. [04_SDD_SUPABASE_MCP_VERTICALPARTS.md](./04_SDD_SUPABASE_MCP_VERTICALPARTS.md)
6. [05_RUNBOOK_COPY_PASTE_SETUP_AND_RECOVERY.md](./05_RUNBOOK_COPY_PASTE_SETUP_AND_RECOVERY.md)

## Catálogo de tools (33)

Contexto: `sb_whoami`, `sb_list_registered_projects`

Organizações: `sb_list_organizations`, `sb_get_organization`

Projetos: `sb_list_projects`, `sb_get_project`, `sb_get_project_url`, `sb_get_publishable_keys`, `sb_create_project`, `sb_pause_project`, `sb_restore_project`, `sb_delete_project`, `sb_get_cost`, `sb_confirm_cost`

Banco de dados: `sb_list_tables`, `sb_list_extensions`, `sb_list_migrations`, `sb_apply_migration`, `sb_execute_sql` (risco dinâmico — ver `01_RAG` RAG-006A), `sb_get_advisors`, `sb_query_logs`, `sb_generate_typescript_types`

Branches de desenvolvimento (experimental — ver nota abaixo): `sb_list_branches`, `sb_create_branch`, `sb_delete_branch`, `sb_merge_branch`, `sb_reset_branch`, `sb_rebase_branch`

Edge Functions: `sb_list_edge_functions`, `sb_get_edge_function`, `sb_deploy_edge_function`, `sb_delete_edge_function`

Break-glass: `sb_api_call`

**Nota sobre branching**: é uma feature paga e explicitamente experimental da própria Supabase. Os endpoints usados por essas 6 tools foram inferidos da documentação pública e do comportamento do conector oficial, não confirmados um a um contra a API real ainda — ver `04_SDD` seção 9. Tratar como não homologado até o teste real da PARTE C do runbook.

## Estado dos projetos administrados

14 projetos reais em 3 organizações (`VerticalParts`, `VerticalParts (LOW)`, `ESCAMAX`), confirmados via `sb_list_projects`/`sb_list_organizations` na homologação de 2026-09-19 — ver `config/projects.example.yaml` e `00_READ_FIRST` seção 6.

## Autenticação — Personal Access Token

Diferente de um GitHub App, a Management API do Supabase não tem conceito de instalação/permissão granular por recurso — um PAT herda todo o acesso da conta que o gerou. Isso torna a governança deste próprio MCP (risco/confirmação/auditoria) a única camada real de limite de escopo. Setup completo em `05_RUNBOOK` PARTE A. Ver `01_RAG` RAG-003A para o detalhe.

## Segurança

Nunca versionar:
- Personal Access Token do Supabase;
- `X-API-Key` do gateway deste MCP;
- `service_role key` de qualquer projeto (nunca exposta por nenhuma tool, de qualquer forma);
- senha de banco de dados definida em `sb_create_project`.

Arquivos reais ignorados pelo Git: `.env`, `config/projects.yaml`, `secrets/`, `data/`.

Confirmações:
- `CONFIRMO` — crítico;
- `CONFIRMO_DESTRUTIVO` — destrutivo (`sb_delete_project`, `sb_delete_branch`, `sb_reset_branch`, `sb_delete_edge_function`, e `sb_execute_sql` quando a instrução for classificada como destrutiva);
- `BREAK_GLASS` — `sb_api_call` em método diferente de GET, com `SUPABASE_ALLOW_BREAK_GLASS=true`.

## Desenvolvimento

~~~bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
cp .env.example .env
cp config/projects.example.yaml config/projects.yaml
verticalparts-supabase-mcp
~~~

## Claude

Conector (já homologado, pronto para uso):

Nome: VerticalParts Supabase
URL: `https://supabase-mcp.vpsistema.com/mcp`
Autenticação: Sem login
Header: `X-API-Key`
