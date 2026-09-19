# 01 — RAG CANÔNICO — VerticalParts Supabase MCP

Versão: 2026-09-19
Classificação: conhecimento operacional canônico
Objetivo: recuperação contextual para LLMs, agentes MCP, Claude, Claude Code e automações que administram o Supabase da VerticalParts.

---

## RAG-000 — Regra de uso

Consultas que devem recuperar este RAG incluem: Supabase, projeto Supabase, `project_ref`, banco de dados, Postgres, migração, SQL, RLS, Edge Function, branch de desenvolvimento (Supabase), organização Supabase, PAT do Supabase, advisor de segurança/performance, chave publishable/anon, service role key.

---

## RAG-001 — Missão

O VerticalParts Supabase MCP transforma intenção operacional sobre o Supabase da organização `VerticalParts` em ação segura, auditável e reversível quando possível — a mesma missão dos dois MCPs irmãos, aplicada ao Supabase.

## RAG-002 — Hierarquia de verdade

1. Estado vivo observado via Management API real do Supabase.
2. `config/projects.yaml` do runtime (criticidade/contexto, não cache de estado).
3. Código do MCP.
4. Documentação canônica numerada da raiz.
5. Memória de conversa.

## RAG-003 — Topologia

Supabase MCP:
- rodando em produção: serviço dedicado na VPS, usuário de serviço `supabase-mcp`;
- endpoint público ativo: `https://supabase-mcp.vpsistema.com/mcp` (Nginx + TLS Let's Encrypt, expira 2026-12-18);
- transporte: Streamable HTTP;
- autenticação pública: X-API-Key no gateway/Nginx;
- bind interno: `127.0.0.1:8022` (depois de `8020` infra-mcp e `8021` github-mcp);
- serviço: `verticalparts-supabase-mcp.service`;
- autenticação com o Supabase: Management API (`https://api.supabase.com/v1`) via Personal Access Token (PAT), não via app/instalação — ver RAG-003A.

Organizações administradas (confirmado via `sb_list_organizations` real em 2026-09-19 — não é só `VerticalParts`): `VerticalParts` (`cdcqhcogckjfttevtoev`), `VerticalParts (LOW)` (`hbxwejjlgxxhxzaksnvm`) e `ESCAMAX` (`tfxgxfybhxtpqyxtdyhu`). 14 projetos ao todo em 2026-09-19 (ver `00_READ_FIRST` seção 6 e `config/projects.example.yaml` para a lista real e atual — não copiar essa contagem para o futuro sem reconferir via `sb_list_projects`).

## RAG-003A — Autenticação do Supabase é por PAT, não por app/instalação

Diferença estrutural em relação ao github-mcp (GitHub App, permissões granulares por recurso, instalável em subconjunto de repositórios): a Management API do Supabase (`api.supabase.com/v1`) autentica com um **Personal Access Token** gerado na conta de um usuário humano (`https://supabase.com/dashboard/account/tokens`). Esse token:

- herda **todo** o acesso que o usuário que o gerou tem — todas as organizações, todos os projetos visíveis a ele;
- não tem escopo granular nativo por projeto ou por operação (ao contrário das *Permissions* configuráveis de um GitHub App);
- não expira automaticamente por padrão (diferente do installation token do GitHub App, que expira em ~1h).

Implicações práticas para este MCP:
- o `.env` deste MCP guarda um segredo estruturalmente mais poderoso que o do github-mcp — trate a rotação (`05_RUNBOOK` PARTE F) com mais prioridade, não menos;
- a **única** camada real de escopo/limite de dano é a governança deste próprio MCP (classificação de risco + confirmação + auditoria) — não existe um "instalar só em projetos X e Y" do lado do Supabase;
- se o operador perguntar "dá para limitar esse token a um projeto só", a resposta honesta é: não nativamente na Management API — a mitigação é usar `config/projects.yaml` para julgamento de risco e nunca pular a etapa de confirmação, não uma limitação técnica do token em si.

**Confirmado na prática, não só em teoria** (homologação real de 2026-09-19): o PAT gerado pelo operador enxerga **3 organizações** (`VerticalParts`, `VerticalParts (LOW)`, `ESCAMAX`) e 14 projetos — o conector Supabase oficial (OAuth) via o qual esta documentação foi inicialmente escrita só mostrava 1 organização e 11 projetos, porque aquele conector foi autorizado com escopo mais estreito. Isso não é uma inconsistência entre os dois: são dois mecanismos de auth diferentes com blast radius diferente para a mesma conta humana. Antes de operar um projeto de uma organização "nova" (ex.: `ESCAMAX`), confirme com o operador que ela é legítima — ver `01_RAG` RAG-008 e `00_READ_FIRST` seção 6.

## RAG-004 — Diferença entre este MCP e os conectores Supabase oficiais

Já existem dois conectores Supabase oficiais conectados a esta conta Claude (`@supabase/mcp-server-supabase`, listado oficialmente como conector do Claude): um de conta inteira (todas as orgs/projetos, inclui `create_project`/`pause_project`/`get_cost`) e um escopado a um projeto (`project_ref` fixo, sem tools de conta). Nenhum dos dois tem modelo de confirmação por risco — `list_tables` e uma instrução SQL destrutiva chegam pela mesma tool (`execute_sql`), sem distinção de fricção. Isso é documentado oficialmente pela própria Supabase como um risco conhecido ("Most MCP clients ask you to accept each tool call before it runs... keep manual approval enabled"), mas depende inteiramente do cliente MCP pedir aprovação — não é uma garantia do servidor.

Não confundir os dois ao decidir qual usar: para exploração casual de dados/schema em uma sessão de desenvolvimento, os conectores oficiais continuam fazendo sentido; para operações administrativas de maior risco (migração de schema, `execute_sql` que grava, criar/pausar/apagar projeto, deploy de Edge Function em produção), prefira este MCP quando homologado.

## RAG-005 — Catálogo de tools (33, ver README.md para a lista com uma linha por tool)

Categorias: contexto, organizações, projetos, banco de dados (tabelas/extensões/migrações/SQL/advisors/logs/types), branches de desenvolvimento (experimental), Edge Functions, break-glass.

Padrão de tool combinada com `method` (mesmo idioma do github-mcp/infra-mcp): `sb_get_advisors(ref, type=security|performance)`.

## RAG-006 — Política de risco

READ: sem confirmação. Exemplos: `sb_list_organizations`, `sb_get_organization`, `sb_list_projects`, `sb_get_project`, `sb_get_project_url`, `sb_get_publishable_keys`, `sb_get_cost`, `sb_list_tables`, `sb_list_extensions`, `sb_list_migrations`, `sb_get_advisors`, `sb_query_logs`, `sb_generate_typescript_types`, `sb_list_branches`, `sb_list_edge_functions`, `sb_get_edge_function`, `sb_whoami`, `sb_list_registered_projects`.

CRITICAL (`CONFIRMO`): `sb_create_project`, `sb_pause_project`, `sb_restore_project`, `sb_confirm_cost`, `sb_apply_migration`, `sb_create_branch`, `sb_merge_branch`, `sb_rebase_branch`, `sb_deploy_edge_function`.

DESTRUCTIVE (`CONFIRMO_DESTRUTIVO`): `sb_delete_project`, `sb_delete_branch`, `sb_reset_branch`, `sb_delete_edge_function`.

**Risco dinâmico**: `sb_execute_sql` não tem risco fixo — é classificado pelo conteúdo da instrução SQL (ver RAG-006A). Isso é diferente de todas as outras tools deste catálogo e dos dois MCPs irmãos, onde a classificação é sempre estática por tool.

BREAK_GLASS: `sb_api_call` para qualquer chamada de management API sem tool semântica equivalente. GET sem confirmação; qualquer outro método exige `SUPABASE_ALLOW_BREAK_GLASS=true` e `confirmation='BREAK_GLASS'`.

## RAG-006A — Classificação dinâmica de `sb_execute_sql`

`sb_execute_sql` roda contra o Postgres real de um projeto — não há como fixar um risco único para "SQL arbitrário" sem ou superproteger leituras legítimas, ou subproteger gravações. A tool classifica pelo texto da instrução (`sql_risk.py`):

- contém `DROP`, `DELETE`, `TRUNCATE`, `REVOKE` (ou variantes como `ALTER ... DROP`) em qualquer lugar da string → **DESTRUCTIVE**, exige `CONFIRMO_DESTRUTIVO`;
- senão contém `INSERT`, `UPDATE`, `CREATE`, `ALTER`, `GRANT`, `MERGE`, `UPSERT`, `REPLACE` → **CRITICAL**, exige `CONFIRMO`;
- senão começa por `SELECT`, `EXPLAIN`, `SHOW`, `WITH` e nenhum dos termos acima aparece → **READ**, sem confirmação;
- qualquer outro formato não reconhecido → default **CRITICAL** (nunca assume leitura por engano).

Isso é um heurístico de segurança, não um parser de SQL completo — na dúvida, ele erra para o lado de pedir mais confirmação, nunca menos. Uma LLM não deve tentar "converter" uma instrução destrutiva em uma sequência de chamadas para escapar da classificação (ex.: dividir um `DROP TABLE` em múltiplas chamadas menores) — isso é exatamente o tipo de contorno que RAG-009 proíbe.

## RAG-007 — Segredos

Segredo nunca é conteúdo de RAG nem de resposta ao usuário.

- Personal Access Token do Supabase: fica no host, fora do Git, permissão restrita (600) — ver RAG-003A sobre por que esse segredo é estruturalmente mais sensível que o do github-mcp.
- `X-API-Key` do gateway: mesmo padrão dos dois MCPs irmãos.
- `service_role key` (secret key) de qualquer projeto: **este MCP nunca expõe esse valor**, mesmo que a Management API permita obtê-lo — só `sb_get_publishable_keys` (chave `anon`/pública) é exposta. Essa é uma decisão de design deliberada (defesa em profundidade contra um vazamento que daria bypass total de RLS em qualquer projeto), não uma limitação técnica.
- Senha de banco de dados (`db_pass`) usada em `sb_create_project`: nunca logada nem retornada; auditoria redige o campo.

## RAG-008 — Projetos conhecidos (ver `config/projects.yaml` para a lista real e atualizada)

`VP CLICK` (`sfpnjwllcmentoocylow`) e `vprequisicao` (`vvgcrhtmzvssfdazkkzk`): inferidos como produção direta, mesmo domínio de `005_vpclick`/`003_requisicoes` no github-mcp — tratar como `critical` até confirmação em contrário.

`bd_Omie` (`kgecbycsyrtdhmdziuul`): inferido como integração financeira/ERP — tratar como `critical`.

Os demais 11 projetos têm criticidade **inferida do nome apenas**, não confirmada pelo operador — ver `00_READ_FIRST` seção 6. Antes de qualquer operação `CRITICAL`/`DESTRUCTIVE` em um desses, confirme a criticidade real com o operador se `config/projects.yaml` ainda estiver com a inferência original.

`Aprovacao` (`hhgvlcskxopryqvhofsg`) merece atenção redobrada: está na organização `ESCAMAX`, não `VerticalParts` — confirme com o operador que essa organização é legítima antes de qualquer operação crítica/destrutiva ali, não só a criticidade do projeto.

`VISITAS E BRINDES` (`bvvnoapdclxhuygptbza`) foi o projeto usado para a homologação real de 2026-09-19 (criar/validar/apagar uma tabela de teste) — está limpo, sem resíduo, mas é o projeto de referência para qualquer novo teste futuro por já ter esse histórico.

## RAG-009 — Anti-padrões

Nunca como padrão:
- apagar projeto sem confirmar 2x o `project_ref`/nome exato e o motivo — `sb_delete_project` é irreversível e apaga banco, Auth, Storage e Edge Functions juntos;
- rodar `sb_execute_sql` destrutivo dividido em partes menores para tentar escapar da classificação de risco (ver RAG-006A);
- ler ou tentar reconstruir a `service_role key` por qualquer caminho indireto (ex.: via `sb_api_call` break-glass) só porque a tool dedicada não expõe;
- tratar `sb_pause_project`/`sb_create_project` como operação sem custo — projetos Supabase têm custo financeiro real em planos pagos; `sb_get_cost`/`sb_confirm_cost` existem por isso;
- assumir que branching (`sb_create_branch`/`sb_merge_branch`/etc.) está tão maduro/homologado quanto o resto do catálogo — é uma feature experimental da própria Supabase (plano pago), ver `04_SDD` seção 9;
- usar `sb_api_call` (break-glass) quando existe tool semântica equivalente;
- declarar este MCP "em produção" sem evidência de chamada real contra a Management API.

## RAG-010 — Quando parar

Pedir clarificação se:
- o `project_ref`/organização é ambíguo e a leitura (`sb_list_projects`) não resolve;
- uma operação destrutiva não tem alvo exato confirmado pelo operador;
- `sb_execute_sql` foi classificado como CRITICAL/DESTRUCTIVE mas a intenção do operador parecia ser só leitura — reconfirme a instrução antes de assumir que é isso mesmo que ele quer rodar;
- não há estratégia de recuperação (ex.: apagar projeto sem backup/snapshot recente conhecido);
- o pedido contradiz `config/projects.yaml` (ex.: pedir para apagar um projeto marcado `critical`) sem justificativa explícita.

Não perguntar o que pode ser descoberto por leitura segura da API.
