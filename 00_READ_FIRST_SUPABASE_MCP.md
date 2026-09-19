# 00 — LEIA PRIMEIRO — VerticalParts Supabase MCP

Versão documental: 2026-09-19
Status: canônico, **homologado contra a API real** (autenticação, leitura, escrita crítica com confirmação, classificação dinâmica de risco de SQL, ciclo completo criar→validar→reverter)
Escopo: administração do Supabase das organizações visíveis ao Personal Access Token configurado (ver seção 5 — são 3, não 1)

## 1. Finalidade deste conjunto

Este repositório contém o MCP de administração do Supabase da VerticalParts. Ele existe para permitir que uma LLM opere projetos, banco de dados, migrações, Edge Functions e branches de desenvolvimento do Supabase com confirmação proporcional ao risco, sem depender de memória humana sobre `project_ref`, strings de conexão ou comandos de API.

Irmãos deste projeto:
- `verticalpartsIA/verticalparts-infrastructure-mcp` (VPS + Hostinger, já homologado em produção);
- `verticalpartsIA/verticalparts-github-mcp` (GitHub, já homologado em produção).

Mesma filosofia de governança nos três: classificação de risco, confirmação proporcional, auditoria sem segredo. Em caso de dúvida sobre convenção, os dois repositórios irmãos (já homologados) são a referência de como esse padrão amadurece.

## 2. Por que este MCP existe apesar de já haver conectores Supabase oficiais

Nesta conta Claude já existem **dois conectores Supabase oficiais** (`@supabase/mcp-server-supabase`, mantido pela própria Supabase, listado como conector oficial do Claude):
- um com acesso à **conta inteira** (todas as organizações/projetos visíveis ao usuário que autorizou o OAuth — inclui `create_project`, `pause_project`, `list_organizations`, `get_cost`);
- um **escopado a um projeto específico** ("Gestão Importação" — `project_ref` fixo, sem tools de conta).

Esses conectores são bons e reais, mas têm **exatamente a mesma limitação que o conector GitHub genérico tinha antes deste projeto (ver `01_RAG` RAG-004 do github-mcp)**: não existe modelo de confirmação por risco. `list_tables` e uma instrução SQL que faz `DROP TABLE` chegam pela mesma tool (`execute_sql`), com a mesma fricção — nenhuma. O mesmo vale para `sb_delete_project`-equivalente: apagar um projeto Supabase inteiro (banco, Auth, Storage, Edge Functions, tudo) tem a mesma fricção que listar projetos.

Este MCP não substitui os conectores oficiais para uso exploratório casual (perguntar "quantas linhas tem a tabela X" continua fazendo sentido por ali). Ele existe para dar governança às operações que merecem confirmação explícita e auditoria — sobretudo qualquer coisa que grave, apague ou tenha custo financeiro.

## 3. Ordem obrigatória de leitura para LLMs

1. `00_READ_FIRST_SUPABASE_MCP.md` — mapa e precedência.
2. `03_INSTRUCTIONS_LLM_SUPABASE_MCP_VERTICALPARTS.md` — regras de comportamento.
3. `01_RAG_SUPABASE_MCP_VERTICALPARTS.md` — conhecimento operacional e roteamento.
4. `02_SPEC_SUPABASE_MCP_VERTICALPARTS.md` — requisitos e contratos.
5. `04_SDD_SUPABASE_MCP_VERTICALPARTS.md` — desenho técnico.
6. `05_RUNBOOK_COPY_PASTE_SETUP_AND_RECOVERY.md` — execução, geração do Personal Access Token e recuperação.
7. `README.md`, `config/*.example.yaml` e código-fonte para detalhes complementares.

## 4. Hierarquia de verdade

1. Estado vivo observado por leitura segura da Management API do Supabase (`sb_list_projects`, `sb_get_project`, `sb_list_tables`, etc.).
2. `config/projects.yaml` do ambiente de execução — registro de criticidade/contexto por projeto, **não** um cache de estado.
3. Código em `src/verticalparts_supabase_mcp/`.
4. Documentos canônicos numerados na raiz.
5. Memória de conversa ou suposição humana.

Nunca invente `project_ref`, organização, nome de branch, nome de Edge Function ou conteúdo de migração. Descubra por leitura antes de mutar.

## 5. Estado atual conhecido em 2026-09-19

Este projeto está **homologado contra a API real do Supabase** (`api.supabase.com`), com o PAT gerado pelo operador e configurado no host (`/opt/verticalparts-supabase-mcp/secrets/supabase-access-token`, nunca visto por esta LLM em nenhum momento — ver `05_RUNBOOK` PARTE B1).

Pesquisa preliminar (antes de gerar o PAT), usando os conectores Supabase oficiais já conectados a esta sessão Claude:
- **Organização vista pelo conector oficial**: `VerticalParts` (id/slug `cdcqhcogckjfttevtoev`) — 11 projetos, todos `ACTIVE_HEALTHY`, região `sa-east-1`, Postgres 17.

**Homologação real (2026-09-19), contra `api.supabase.com`, com o PAT do operador** — testes executados na VPS (`/opt/verticalparts-supabase-mcp`), chamando as próprias funções de tool do `server.py` (não só o client HTTP), validando também o gating de confirmação:

- **Teste 1 (auth/whoami)** — `sb_whoami` → `GET /v1/organizations` retornou `200` com **3 organizações**, não 1: `VerticalParts` (`cdcqhcogckjfttevtoev`), `VerticalParts (LOW)` (`hbxwejjlgxxhxzaksnvm`) e `ESCAMAX` (`tfxgxfybhxtpqyxtdyhu`). **Descoberta estrutural importante**: o PAT (gerado por uma conta humana) enxerga todas as organizações que essa conta enxerga, não só a que o conector oficial mostrava — confirma na prática o que `01_RAG` RAG-003A já previa em teoria. Não é bug; é a natureza de um PAT.
- **Teste 2 (leitura)** — `sb_list_projects` → `GET /v1/projects` retornou **14 projetos** (3 a mais que o conector oficial via OAuth escopado): os 11 já conhecidos, mais `Aprovacao` (`hhgvlcskxopryqvhofsg`, org ESCAMAX, região `us-east-1`), `VP CATRACA` (`ipqtbqstasirxlcoapns`, org VerticalParts (LOW)) e `supplierquotation` (`jbwgjegelhoueygcvafq`, org VerticalParts (LOW), status `INACTIVE`). Todos os 14 já estão em `config/projects.example.yaml`.
- **Teste 3 (gating de confirmação)** — `sb_apply_migration` sem `confirmation` → bloqueado (`PermissionError`); com `confirmation="CONFIRMO_DESTRUTIVO"` (errada) → bloqueado; só com `confirmation="CONFIRMO"` → executou.
- **Teste 4 (escrita real + validação + reversão)** — `sb_apply_migration` criou a tabela `_mcp_homologacao_teste` no projeto `VISITAS E BRINDES` (`bvvnoapdclxhuygptbza`, criticidade `low`); `sb_list_tables` confirmou a tabela presente; ao final, `sb_execute_sql` com `DROP TABLE` e `confirmation="CONFIRMO_DESTRUTIVO"` removeu a tabela; `sb_list_tables` confirmou a remoção — ciclo completo criar → validar → reverter, sem resíduo.
- **Teste 5 (classificação dinâmica de `sb_execute_sql`, contra a API real)** — `SELECT count(*) FROM _mcp_homologacao_teste` executou sem `confirmation` (READ); `INSERT ...` foi bloqueado sem `confirmation` (CRITICAL); `DROP TABLE ...` foi bloqueado sem `confirmation` e também bloqueado com `confirmation="CONFIRMO"` (errada), só executando com `confirmation="CONFIRMO_DESTRUTIVO"` — os três níveis de risco de `sql_risk.py` (ver `01_RAG` RAG-006A) validados contra o Postgres real de um projeto, não só em teste unitário isolado.

Nenhuma chamada de teste tocou um projeto `critical`/`high` — todo o ciclo de escrita/reversão foi feito em `VISITAS E BRINDES` (`low`), como o `05_RUNBOOK` PARTE C4 recomenda.

Correção de topologia relevante (paralela à descoberta feita no github-mcp): diferente do GitHub App (que tem instalação granular por repositório e permissões por recurso), a Management API do Supabase autentica por **Personal Access Token (PAT)** — um único segredo que herda todo o acesso do usuário/conta que o gerou, sem escopo granular nativo. A governança por risco/confirmação deste MCP é, portanto, a **única** camada de escopo disponível — não existe um "GitHub App equivalente" com permissões por recurso no lado do Supabase. Ver `01_RAG` RAG-003A e `04_SDD` T-001 — agora com evidência real, não só teoria (Teste 1 acima).

**Deploy público concluído e homologado (2026-09-19)**: `https://supabase-mcp.vpsistema.com/mcp` está no ar, atrás de Nginx + TLS (Let's Encrypt, expira 2026-12-18) + `X-API-Key`, servido pelo `verticalparts-supabase-mcp.service` (systemd, usuário `supabase-mcp`, bind `127.0.0.1:8022`).

Evidência de homologação do protocolo MCP em si (via HTTPS público, requisições reais):
- sem `X-API-Key`: `401` ✓
- com `X-API-Key` errada: `401` ✓
- `initialize` com a chave correta: `200`, `serverInfo.name="VerticalParts Supabase"`, `protocolVersion="2024-11-05"` ✓
- `notifications/initialized`: `202` ✓
- `tools/list`: **33 tools**, sem duplicidade, batendo exatamente com o catálogo do README ✓

Isso fecha todos os critérios de aceite da PARTE I do runbook para a parte de deploy/protocolo. A homologação funcional (chamadas reais de organização/projeto/banco de dados, seção acima) já tinha sido feita antes do deploy, contra o mesmo código, via stdio local na VPS.

## 6. Projetos conhecidos (ver `config/projects.example.yaml` para o registro completo)

14 projetos em 3 organizações, confirmados via `sb_list_projects`/`sb_list_organizations` reais em 2026-09-19 (ver seção 5).

| Nome | `project_ref` | Organização | Inferência de criticidade |
|---|---|---|---|
| VP CLICK | `sfpnjwllcmentoocylow` | VerticalParts | critical (produção, mesmo domínio de `005_vpclick` no github-mcp) |
| vprequisicao | `vvgcrhtmzvssfdazkkzk` | VerticalParts | critical (produção, mesmo domínio de `003_requisicoes`) |
| bd_Omie | `kgecbycsyrtdhmdziuul` | VerticalParts | critical (integração financeira/ERP) |
| vpposvenda360 | `jkbklzlbhhfnamaeislb` | VerticalParts | high |
| VP SUPRIMENTOS | `qumqyhigghclguuihglh` | VerticalParts | high |
| vpsistema | `ubdkoqxfwcraftesgmbw` | VerticalParts | high |
| vpprd | `jxtqwzmpgofwctqajewt` | VerticalParts | high (nome sugere produção, mas propósito exato não confirmado) |
| vpproject | `udztutvvmnnvfqklucya` | VerticalParts | medium |
| Propostas | `wfwraicrwazjblyvtzfu` | VerticalParts | medium |
| Aprovacao | `hhgvlcskxopryqvhofsg` | **ESCAMAX** (não VerticalParts) | medium — confirmar com o operador se essa org é legítima |
| VP CATRACA | `ipqtbqstasirxlcoapns` | VerticalParts (LOW) | medium |
| developer_omie_com_br_service-list | `hrhwplqlbuwfextznkea` | VerticalParts | medium |
| VISITAS E BRINDES | `bvvnoapdclxhuygptbza` | VerticalParts | low — usado como projeto de teste na homologação real |
| supplierquotation | `jbwgjegelhoueygcvafq` | VerticalParts (LOW) | low (status `INACTIVE`) |

## 7. Próximos passos (não-bloqueantes)

Tudo que era pré-requisito para produção está feito: homologação funcional real (auth, leitura, escrita crítica com confirmação, classificação dinâmica de risco de SQL, ciclo completo criar→validar→reverter) e deploy público com protocolo MCP validado via HTTPS real (ver seções 5 e a evidência de deploy logo acima). Itens que ficam para depois:

1. Conectar este endpoint (`https://supabase-mcp.vpsistema.com/mcp`) num cliente MCP real (Claude) e validar por ali — os testes até aqui foram via `curl`/script direto no protocolo, nunca através de um cliente MCP de fato.
2. Homologação de Edge Functions (`sb_deploy_edge_function`/`sb_list_edge_functions`/etc.) — ainda não testado contra a API real, só as tools de projeto/organização/banco de dados foram.
3. Verificação honesta de quais tools de branching realmente respondem como documentado (branching é uma feature experimental/paga da própria Supabase — ver `04_SDD` seção 9) — não testado ainda.
4. Confirmar com o operador se a organização `ESCAMAX` (projeto `Aprovacao`) é legítima antes de qualquer operação crítica ali — descoberta na homologação, não confirmada previamente (nota: existe um site `escamaxcompravp.vpsistema.com` no inventário da VerticalParts, o que sugere que é legítimo, mas o operador deve confirmar explicitamente).
5. Rotacionar o Personal Access Token periodicamente (`05_RUNBOOK` PARTE F) — prioridade mais alta que no github-mcp, ver `01_RAG` RAG-003A.

Nenhum destes passos deve ser marcado como concluído sem evidência de chamada real — mesma regra do github-mcp (`01_RAG` RAG-009 lá: "declarar este MCP em produção sem evidência de chamada real" é anti-padrão).

## 8. MCPs relacionados

Infrastructure MCP (VPS + Hostinger): `https://infra-mcp.vpsistema.com/mcp`
GitHub MCP: `https://github-mcp.vpsistema.com/mcp`
Supabase MCP (este projeto, quando homologado): `https://supabase-mcp.vpsistema.com/mcp` (planejado)

Conectores Supabase oficiais genéricos (já em uso hoje nesta conta Claude, sem modelo de confirmação por risco): não são substituídos por este projeto para exploração casual de dados — este MCP existe para dar governança às operações que merecem confirmação explícita e auditoria, especialmente mutações de schema/dados e qualquer coisa com custo financeiro (criar/apagar projeto).

## 9. Segredos

Nunca versionar nem reproduzir:
- o Personal Access Token do Supabase;
- o `X-API-Key` do gateway deste MCP;
- a `service_role key` (secret key) de qualquer projeto — este MCP **nunca** expõe essa chave por decisão de design, mesmo a Management API permitindo (ver `02_SPEC` FR-009 e `03_INSTRUCTIONS` seção 5);
- senha de banco de dados usada em `sb_create_project`.

É permitido documentar o local seguro de recuperação do segredo e o comando para lê-lo no host autorizado, seguindo exatamente a mesma convenção dos dois repositórios irmãos.

## 10. Confirmações de risco

- leitura: sem confirmação;
- crítico/reversível: `CONFIRMO`;
- destrutivo: `CONFIRMO_DESTRUTIVO`;
- SQL arbitrário via `sb_execute_sql`: classificado dinamicamente pelo conteúdo da instrução (ver `04_SDD` seção 2.6) — não é uma tool BREAK_GLASS, mas seu risco não é fixo como as demais;
- shell/API de management arbitrária: `sb_api_call`, `BREAK_GLASS` e `SUPABASE_ALLOW_BREAK_GLASS=true`.

Break-glass deve permanecer desligado normalmente.

## 11. Regra final

Uma LLM que leia os arquivos canônicos deve conseguir: entender a arquitetura, descobrir o estado real via API, recuperar o conector, administrar projetos e organizações, rodar/reverter uma migração com segurança, administrar Edge Functions, entender por que branching é tratado como experimental, e saber quando parar e pedir confirmação — sem nunca expor um segredo.
