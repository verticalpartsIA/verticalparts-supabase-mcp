# 00 — LEIA PRIMEIRO — VerticalParts Supabase MCP

Versão documental: 2026-09-19
Status: canônico, pré-homologação (código completo, App/credencial ainda não gerados)
Escopo: administração do Supabase da organização `VerticalParts` por LLM

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

Este projeto está **em fase de scaffolding, código completo, ainda sem credencial real gerada** — equivalente ao estado do `verticalparts-github-mcp` antes da PARTE A do runbook ser executada. Nenhuma chamada real contra `api.supabase.com` foi feita a partir do código deste MCP ainda.

Pesquisa real feita antes de escrever este projeto (2026-09-19), usando os conectores Supabase oficiais já conectados a esta sessão Claude, sem inventar nada:

- **Organização real**: `VerticalParts` (id/slug `cdcqhcogckjfttevtoev`) — uma única organização, confirmado via `list_organizations`.
- **11 projetos reais** confirmados via `list_projects` (todos `ACTIVE_HEALTHY`, região `sa-east-1`, Postgres 17): `VP CLICK` (`sfpnjwllcmentoocylow`), `vprequisicao` (`vvgcrhtmzvssfdazkkzk`), `vpposvenda360` (`jkbklzlbhhfnamaeislb`), `VP SUPRIMENTOS` (`qumqyhigghclguuihglh`), `bd_Omie` (`kgecbycsyrtdhmdziuul`), `vpsistema` (`ubdkoqxfwcraftesgmbw`), `vpproject` (`udztutvvmnnvfqklucya`), `vpprd` (`jxtqwzmpgofwctqajewt`), `Propostas` (`wfwraicrwazjblyvtzfu`), `VISITAS E BRINDES` (`bvvnoapdclxhuygptbza`), `developer_omie_com_br_service-list` (`hrhwplqlbuwfextznkea`).
- Esses 11 `project_ref` reais foram usados para pré-popular `config/projects.example.yaml` — ver seção 6 abaixo e `05_RUNBOOK` PARTE B3. **A criticidade atribuída em `projects.example.yaml` é uma inferência a partir do nome do projeto, não uma confirmação do operador** — revisar antes de copiar para `config/projects.yaml` real.

Correção de topologia relevante (paralela à descoberta feita no github-mcp): diferente do GitHub App (que tem instalação granular por repositório e permissões por recurso), a Management API do Supabase autentica por **Personal Access Token (PAT)** — um único segredo que herda todo o acesso do usuário/conta que o gerou, sem escopo granular nativo. A governança por risco/confirmação deste MCP é, portanto, a **única** camada de escopo disponível — não existe um "GitHub App equivalente" com permissões por recurso no lado do Supabase. Ver `01_RAG` RAG-003A (aqui reaproveitado para essa observação) e `04_SDD` T-001.

## 6. Projetos conhecidos (ver `config/projects.example.yaml` para o registro completo)

| Nome | `project_ref` | Inferência de criticidade |
|---|---|---|
| VP CLICK | `sfpnjwllcmentoocylow` | critical (produção, mesmo domínio de `005_vpclick` no github-mcp) |
| vprequisicao | `vvgcrhtmzvssfdazkkzk` | critical (produção, mesmo domínio de `003_requisicoes`) |
| bd_Omie | `kgecbycsyrtdhmdziuul` | critical (integração financeira/ERP) |
| vpposvenda360 | `jkbklzlbhhfnamaeislb` | high |
| VP SUPRIMENTOS | `qumqyhigghclguuihglh` | high |
| vpsistema | `ubdkoqxfwcraftesgmbw` | high |
| vpprd | `jxtqwzmpgofwctqajewt` | high (nome sugere produção, mas propósito exato não confirmado) |
| vpproject | `udztutvvmnnvfqklucya` | medium |
| Propostas | `wfwraicrwazjblyvtzfu` | medium |
| developer_omie_com_br_service-list | `hrhwplqlbuwfextznkea` | medium |
| VISITAS E BRINDES | `bvvnoapdclxhuygptbza` | low |

## 7. Próximos passos (bloqueantes, na ordem)

1. Gerar o Personal Access Token do Supabase (`05_RUNBOOK` PARTE A) — passo humano, na conta/organização `VerticalParts`.
2. Preencher `.env` e `config/projects.yaml` reais (PARTE B).
3. Testes locais reais contra `api.supabase.com` (PARTE C): `sb_whoami`, uma leitura (`sb_list_projects`), uma tool crítica com confirmação e validação por leitura.
4. Deploy público (PARTE D): systemd + Nginx + TLS em `https://supabase-mcp.vpsistema.com/mcp`, bind interno `127.0.0.1:8022`.
5. Homologação funcional ampliada, no mesmo padrão do github-mcp: ciclo real de migração/SQL, ciclo real de Edge Function, e uma verificação honesta de quais tools de branching realmente respondem como documentado (branching é uma feature experimental da própria Supabase — ver `04_SDD` seção 9).

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
