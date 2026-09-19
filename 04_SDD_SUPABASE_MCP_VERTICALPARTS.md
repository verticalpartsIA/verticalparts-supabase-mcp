# 04 — SDD — VerticalParts Supabase MCP

Versão: 2026-09-19
Status: canônico
Objetivo: descrever arquitetura, componentes, fluxos, contratos técnicos, segurança e evolução.

---

## 1. Visão geral

~~~text
Claude / Claude Code / outro cliente MCP
                |
                | HTTPS + MCP Streamable HTTP (quando publicado)
                v
        Nginx / Gateway público
        TLS + X-API-Key
                |
                | loopback
                v
     VerticalParts Supabase MCP (FastMCP)
                |
                v
      Personal Access Token (Bearer, direto)
                |
                v
        api.supabase.com/v1 (Management API)
                |
                v
   Organização VerticalParts (projetos, banco,
   Edge Functions, branches)
~~~

## 2. Componentes

### 2.1 FastMCP server — `src/verticalparts_supabase_mcp/server.py`
Registra as 33 tools, valida argumentos, aplica classificação de risco (fixa ou dinâmica), chama o client Supabase, escreve auditoria.

### 2.2 Settings — `config.py`
Carrega `.env`: transporte/bind MCP, PAT, base da Management API, organização padrão, paths de registro/políticas/auditoria, flag de break-glass.

### 2.3 Autenticação — `supabase_auth.py`
Diferente do github-mcp (`github_app.py`, JWT → installation token com cache/expiração), aqui não há troca de token: o PAT configurado é usado diretamente como `Authorization: Bearer <PAT>` em toda chamada. Módulo mantido separado (em vez de embutir no client) por dois motivos: (1) simetria de estrutura com os MCPs irmãos, facilitando manutenção cruzada; (2) ponto único de futura evolução caso o Supabase venha a suportar OAuth App / tokens escopados por projeto (ver seção 9).

### 2.4 Supabase client — `supabase_client.py`
Wrapper semântico sobre a Management API (`https://api.supabase.com/v1`), um método por operação (mesmo idioma do `hostinger.py`/`github_client.py`). Não há retry automático de 401 por expiração (o PAT não expira como um installation token) — um 401 aqui normalmente significa PAT inválido/revogado, e deve ser reportado como tal, não silenciosamente re-tentado.

Introspecção de banco (`list_tables`, `list_extensions`, `list_migrations`) é implementada como instruções SQL somente-leitura contra `pg_catalog`/`information_schema`/`supabase_migrations.schema_migrations`, enviadas via `POST /v1/projects/{ref}/database/query` — a Management API não expõe um endpoint REST dedicado para "listar tabelas" fora de SQL, mesma abordagem usada pelo servidor oficial da Supabase.

`apply_migration` usa `POST /v1/projects/{ref}/database/migrations` (fica rastreado no histórico de migrações do Supabase); `execute_sql` usa `POST /v1/projects/{ref}/database/query` (não fica rastreado como migração — ver `03_INSTRUCTIONS` seção 8 sobre quando usar cada um).

### 2.5 SQL risk — `sql_risk.py`
Único componente novo sem equivalente nos MCPs irmãos. Classifica uma instrução SQL em `READ`/`CRITICAL`/`DESTRUCTIVE` por busca de palavras-chave (não é um parser SQL completo — ver `01_RAG` RAG-006A para a lista de palavras e a regra de default seguro). Usado por `sb_execute_sql` (a única tool com risco dinâmico) e indiretamente documentado para `sb_apply_migration` (que é sempre tratado como CRITICAL fixo, porque seu propósito declarado é sempre uma mudança de schema).

Auditoria de `sb_execute_sql`/`sb_apply_migration`: o **texto da instrução SQL em si não é redigido** (é necessário para reconstruir "o que mudou" depois, já que o Postgres não audita DDL/DML por padrão) — mas se a instrução contiver um literal que pareça senha/token (heurística adicional, mesmos marcadores de `audit.py`), esse literal específico é redigido antes de gravar.

### 2.6 Registry — `registry.py`
Lê `config/projects.yaml` (privado, ignorado pelo Git): criticidade e notas por projeto. Não é cache de estado — é contexto para julgamento de risco.

### 2.7 Safety — `safety.py`
Idêntico em espírito aos dois MCPs irmãos: `Risk` (READ/OPERATIONAL/CRITICAL/DESTRUCTIVE/BREAK_GLASS) e `require_confirmation`. `sb_execute_sql` chama `require_confirmation` com o risco retornado por `sql_risk.classify()`, não com um risco fixo.

### 2.8 Audit — `audit.py`
Idêntico em espírito aos dois MCPs irmãos: um registro JSONL por mutação, com redação automática de campos cujo nome sugira segredo (`TOKEN`, `SECRET`, `PASSWORD`, `API_KEY`, `PRIVATE_KEY`, `AUTHORIZATION`, `DB_PASS`). `VALUE` foi trocado por `DB_PASS` na lista de marcadores em relação ao github-mcp porque este domínio não tem "valor de secret" no mesmo sentido — tem senha de banco.

### 2.9 Gateway Nginx (quando publicado)
Mesmo padrão dos dois MCPs irmãos: HTTPS, X-API-Key, proxy para loopback, porta interna nunca publicada diretamente.

### 2.10 systemd (quando publicado)
`verticalparts-supabase-mcp.service`, usuário dedicado `supabase-mcp`, `EnvironmentFile=.env`.

## 3. Dados de configuração

### 3.1 `.env`
Nunca versionar. Contém o Personal Access Token do Supabase, base da Management API, id da organização padrão.

### 3.2 `config/projects.yaml`
Ver `02_SPEC` seção 5 para o contrato.

### 3.3 `config/policies.yaml`
Strings de confirmação e notas operacionais (ex.: `sb_delete_project` exige `project_ref` explícito).

## 4. Fluxo de autenticação (detalhado)

~~~text
Tool call chega no server.py
  |
  v
supabase_client.request()
  |
  v
supabase_auth.headers()  -- Authorization: Bearer <PAT do .env>, sem cache/expiração
  |
  v
Requisição real à Management API
  |
  v
Se 401 -> não há refresh possível (PAT não é trocado por outro token);
          reportar como PAT inválido/revogado, não repetir silenciosamente.
~~~

## 5. Fluxo — aplicar uma migração

~~~text
sb_apply_migration(ref, name, query, confirmation="CONFIRMO")
  |
  v
require_confirmation(CRITICAL, "CONFIRMO")
  |
  v
POST /v1/projects/{ref}/database/migrations  {name, query}
  |
  v
audit: {"ref": ref, "name": name, "query": query, "ok": true}  -- query não é redigida (necessária para reconstrução), só literais que pareçam segredo dentro dela
~~~

## 6. Fluxo — `sb_execute_sql` (risco dinâmico)

~~~text
sb_execute_sql(ref, query, confirmation=None)
  |
  v
risk = sql_risk.classify(query)   -- READ | CRITICAL | DESTRUCTIVE
  |
  v
require_confirmation(risk, confirmation)
  |
  v
POST /v1/projects/{ref}/database/query  {query}
  |
  v
se risk != READ: audit: {"ref": ref, "query": query, "risk": risk, "ok": true}
~~~

## 7. Segurança em camadas

1. HTTPS (quando publicado);
2. X-API-Key no gateway (quando publicado);
3. Personal Access Token do Supabase, fora do Git, permissão 600 (sem escopo granular nativo — ver seção 8, T-001);
4. tool semântica com validação de input;
5. classificação de risco (fixa ou dinâmica);
6. confirmação explícita;
7. bloqueio de tool para `service_role key` (nenhuma implementada, por design);
8. audit com redação automática (incluindo literais suspeitos dentro de SQL);
9. break-glass off por padrão.

## 8. Threat model

### T-001 — Personal Access Token do Supabase vazado
Risco: acesso total a **todas** as organizações/projetos visíveis à conta que gerou o PAT — sem escopo granular nativo do lado do Supabase (diferente do GitHub App do github-mcp). É o segredo estruturalmente mais poderoso dos três MCPs desta família.
Mitigação: arquivo fora do Git, permissão 600, rotação possível (gerar novo PAT, revogar o antigo — `05_RUNBOOK` PARTE F), nunca logar. A governança deste MCP (risco/confirmação/auditoria) é a única camada de limite de dano além da rotação — reforçar isso ao operador sempre que o tema de segurança do Supabase MCP for discutido.

### T-002 — `sb_execute_sql` classificado incorretamente como READ
Risco: uma instrução de gravação disfarçada (ex.: com comentários, ofuscação de palavra-chave) passa pelo classificador como leitura e executa sem confirmação.
Mitigação: `sql_risk.py` busca por palavra-chave em qualquer posição da string normalizada (case-insensitive, comentários removidos antes da busca), não só no início; default para CRITICAL quando o formato não é reconhecido. Ainda assim, não é um parser SQL completo — tratado como heurística de segurança, não garantia absoluta (ver `01_RAG` RAG-006A).

### T-003 — `service_role key` exposta indiretamente
Risco: mesmo sem uma tool dedicada, alguém tenta obter a `service_role key` via `sb_api_call` (break-glass) contra `GET /v1/projects/{ref}/api-keys`, ou via `sb_execute_sql` lendo alguma tabela interna que a exponha.
Mitigação: `03_INSTRUCTIONS` seção 5 proíbe explicitamente essa tentativa, inclusive por break-glass; a LLM deve recusar esse pedido mesmo vindo do operador, e sugerir o caminho oficial (dashboard do Supabase, autenticado como humano) se ele genuinamente precisar da chave.

### T-004 — LLM apaga projeto/branch errado
Mitigação: descoberta obrigatória antes de mutar, `config/projects.yaml` para criticidade, confirmação explícita com `project_ref` nomeado, aviso de que `sb_delete_project` não tem lixeira.

### T-005 — Custo financeiro não comunicado
Risco: `sb_create_project`/`sb_restore_project` geram cobrança em plano pago sem o operador perceber.
Mitigação: `03_INSTRUCTIONS` seção 7 exige mostrar `sb_get_cost` antes de `CONFIRMO` quando disponível.

### T-006 — Branching tratado como maduro sem ter sido homologado
Risco: LLM promete/assume comportamento de `sb_create_branch`/`sb_merge_branch`/etc. sem esses endpoints terem sido validados contra a API real (são feature paga/experimental da própria Supabase, endpoints menos estáveis que o resto da Management API).
Mitigação: seção 9 abaixo marca branching como não homologado até teste real; `03_INSTRUCTIONS` seção 9 instrui a LLM a avisar o operador antes do primeiro uso em uma sessão.

## 9. Estado de implementação (2026-09-19)

Implementado, não testado contra API real: todas as 33 tools, validação de input, gating de confirmação (fixo e dinâmico), classificador SQL.

**Não homologado ainda** — falta gerar o PAT (`05_RUNBOOK` PARTE A) e rodar os testes reais da PARTE C. Nenhuma chamada real foi feita a partir deste código contra `api.supabase.com`.

Risco adicional identificado antes mesmo da implementação (honestidade arquitetural, não suposição otimista): os endpoints exatos de branching (`/v1/branches/...` vs. `/v1/projects/{ref}/branches/...`, nomes exatos de sub-recursos para merge/reset/rebase) foram inferidos a partir da documentação pública e do comportamento das tools do conector oficial, **não confirmados linha a linha contra a especificação OpenAPI da Management API**. Tratar como primeira prioridade de teste real assim que o PAT existir, antes de declarar essa parte do catálogo homologada — se os paths estiverem errados, o sintoma esperado é 404, não um comportamento inseguro.

## 10. Evolução futura (backlog, não implementado)

- Gerenciar Storage buckets (fora de escopo v1, mesma decisão do servidor oficial de desligar por padrão);
- Gerenciar membros da organização Supabase (convite/remoção) — não solicitado ainda;
- Se o Supabase passar a suportar OAuth App / tokens escopados por projeto, revisitar `supabase_auth.py` para reduzir o blast radius de T-001;
- `sb_api_call` (break-glass) hoje cobre qualquer método REST da Management API — se um padrão de uso recorrente aparecer ali, promover para tool semântica dedicada, mesmo padrão do github-mcp.

## 11. Referências

Supabase Management API: https://supabase.com/docs/reference/api/introduction
Supabase MCP oficial (referência de padrão de tools e feature groups): https://github.com/supabase/mcp
Documentação do conector MCP: https://supabase.com/docs/guides/ai-tools/mcp
