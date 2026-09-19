# 02 — SPEC — VerticalParts Supabase MCP

Versão: 2026-09-19
Status: canônico
Escopo: requisitos funcionais, não funcionais, contratos operacionais e critérios de aceite.

---

## 1. Objetivo

Permitir que uma LLM administre o Supabase da organização `VerticalParts` por intenção — organizações, projetos, banco de dados (tabelas, extensões, migrações, SQL, advisors, logs), branches de desenvolvimento e Edge Functions — com confirmação proporcional ao risco, auditoria e sem expor segredos.

## 2. Fora de escopo por padrão

Não assumir autorização implícita para:
- apagar projeto sem confirmação explícita do `project_ref` exato;
- rodar SQL destrutivo sem que a classificação dinâmica de risco (RAG-006A) seja respeitada;
- expor a `service_role key` de qualquer projeto, por qualquer caminho, inclusive break-glass;
- administrar membros da organização Supabase (convite/remoção) — fora de escopo da v1, pode ser adicionado depois se necessário;
- administrar Storage buckets — fora de escopo da v1 (mesma decisão do servidor oficial, que desliga esse grupo por padrão);
- chamada de API arbitrária fora das tools semânticas (isso é break-glass, contingência).

## 3. Requisitos funcionais

### FR-001 — Descoberta antes de mutação
Nenhuma mutação deve depender de `project_ref`, organização, nome de branch ou slug de Edge Function inventados. Descobrir por leitura antes.

### FR-002 — Registro de projetos
`config/projects.yaml` deve permitir registrar por projeto: `criticality`, `description`, `org_id`, `notes`. Não é fonte de verdade de estado — é contexto para julgamento de risco.

### FR-003 — Organizações e projetos
Suportar: list/get organizações; list/get/create/pause/restore/delete projetos; `get_cost`/`confirm_cost` antes de operações com custo.

Critério de aceite: `sb_delete_project` deve exigir que o `project_ref` seja passado explicitamente (nunca um "projeto padrão" implícito) e `CONFIRMO_DESTRUTIVO`.

### FR-004 — Banco de dados
`sb_list_tables`, `sb_list_extensions`, `sb_list_migrations` via introspecção SQL somente-leitura; `sb_apply_migration` (grava e rastreia como migração); `sb_execute_sql` (SQL livre, risco dinâmico — ver `01_RAG` RAG-006A).

### FR-005 — Advisors e logs
`sb_get_advisors` (tipo `security` ou `performance`) e `sb_query_logs` (por serviço: `api`, `postgres`, `auth`, `storage`, `edge-function`, conforme disponibilidade da Management API) — sempre leitura.

### FR-006 — Chaves e URL do projeto
`sb_get_project_url`, `sb_get_publishable_keys` (só a chave `anon`/pública). Nunca implementar uma tool que retorne `service_role key`.

### FR-007 — TypeScript types
`sb_generate_typescript_types` — leitura, útil para integração de frontend.

### FR-008 — Branches de desenvolvimento (experimental)
List/get/create/delete/merge/reset/rebase. Marcar explicitamente como não homologado enquanto os endpoints reais não forem validados contra a API (feature paga/experimental da própria Supabase) — ver `04_SDD` seção 9.

### FR-009 — Segredos de projeto
Este MCP **não** implementa nenhuma tool que retorne `service_role key`/secret API key, mesmo que a Management API do Supabase permita — decisão de design permanente, não uma lacuna a ser preenchida depois.

### FR-010 — Edge Functions
List/get/deploy/delete. Deploy é uma operação crítica mesmo em ambiente de desenvolvimento, porque Edge Functions frequentemente têm efeito em produção assim que publicadas (sem "staging" automático).

### FR-011 — Break-glass
`sb_api_call` para qualquer endpoint da Management API ainda sem wrapper semântico. GET sem confirmação; qualquer outro método exige `SUPABASE_ALLOW_BREAK_GLASS=true` e `confirmation='BREAK_GLASS'`.

### FR-012 — Confirmação por risco
READ sem confirmação; CRITICAL exige `CONFIRMO`; DESTRUCTIVE exige `CONFIRMO_DESTRUTIVO`; BREAK_GLASS exige flag + `BREAK_GLASS`; `sb_execute_sql` usa classificação dinâmica (FR-004, RAG-006A) em vez de risco fixo por tool.

### FR-013 — Auditoria
Toda mutação registrada (timestamp, tool, alvo, outcome) sem segredo — PAT, `X-API-Key`, `service_role key`, senha de banco e valor de instrução SQL potencialmente sensível sempre redigidos por nome de campo (a própria instrução SQL de `sb_execute_sql`/`sb_apply_migration` é auditada por padrão — ver `04_SDD` seção 2.5 sobre o que é ou não redigido).

### FR-014 — Autenticação Management API
O MCP deve autenticar toda chamada com `Authorization: Bearer <PAT>` contra `https://api.supabase.com/v1`. Diferente do github-mcp, não há troca de token nem cache de expiração — o PAT é usado diretamente (ver `01_RAG` RAG-003A para a implicação de segurança disso).

### FR-015 — Gateway público
Quando exposto publicamente: HTTPS + Nginx + `X-API-Key`, upstream em loopback, mesmo padrão dos dois MCPs irmãos.

## 4. Requisitos não funcionais

- **Segurança**: PAT fora do Git; break-glass off por padrão; nenhuma tool expõe `service_role key`.
- **Auditabilidade**: toda mutação rastreável, incluindo o texto da instrução SQL executada (para permitir reconstrução de "o que mudou", já que Postgres não tem um log de auditoria de DDL/DML habilitado por padrão).
- **Reversibilidade**: priorizar operações reversíveis (`pause_project` em vez de `delete_project` quando a intenção permitir); quando a operação for inerentemente irreversível (delete de projeto/branch, `TRUNCATE`/`DROP` via `execute_sql`), isso deve estar claro na descrição da tool e na resposta antes da confirmação.
- **Determinismo**: mesma operação + mesmo estado → mesma classificação de risco, exceto `sb_execute_sql`, cujo risco é função determinística do conteúdo da instrução (mesma instrução → sempre a mesma classificação).
- **Portabilidade de LLM**: documentação suficiente para qualquer LLM autorizada operar sem depender de memória de conversa anterior.

## 5. Contrato de `config/projects.yaml`

~~~yaml
projects:
  nome-do-projeto:
    ref: "project_ref_real"
    org_id: "cdcqhcogckjfttevtoev"
    criticality: critical | high | medium | low
    description: "..."
    notes:
      - "..."
~~~

## 6. Critérios de aceite do MCP

1. `sb_whoami` retorna a organização `VerticalParts` e confirma que o PAT é válido — primeiro teste real de integração;
2. `initialize` e `tools/list` funcionam via protocolo MCP real (local e, quando publicado, via HTTPS);
3. uma tool READ real retorna dado correto (ex.: `sb_list_projects` bate com os 11 projetos conhecidos);
4. uma tool CRITICAL real, com confirmação, executa e o efeito é validado por uma leitura subsequente (ex.: `sb_apply_migration` cria uma tabela de teste em um projeto de baixa criticidade, validada por `sb_list_tables`);
5. `sb_delete_project` sem confirmação é recusado; com `CONFIRMO` (errado) é recusado; só com `CONFIRMO_DESTRUTIVO` executaria (este teste específico **não deve ser executado de verdade** contra um projeto real durante homologação — validar só a recusa das confirmações erradas);
6. `sb_execute_sql` classifica corretamente pelo menos um exemplo de cada categoria (`SELECT 1` → READ; `INSERT INTO ...` → CRITICAL; `DROP TABLE ...` → DESTRUCTIVE) sem exigir confirmação real de destrutivo em produção;
7. nenhuma tool retorna `service_role key` em nenhuma circunstância;
8. auth pública (X-API-Key) funciona quando publicado;
9. break-glass permanece off por padrão.

## 7. Definition of Done

Qualquer feature deste MCP só está concluída quando: implementada, classificada por risco (fixo ou dinâmico), auditada, testada (pelo menos localmente; idealmente também contra a API real), documentada, sem segredo no Git, e incorporada ao RAG/Instructions se alterar comportamento.
