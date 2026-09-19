# CLAUDE.md — VerticalParts Supabase MCP

Versão operacional: 2026-09-19
Status: **homologado em produção** — endpoint público ativo em `https://supabase-mcp.vpsistema.com/mcp`. Validado com auth, leitura, escrita crítica com confirmação, classificação dinâmica de risco de SQL, ciclo completo criar→validar→reverter, e o protocolo MCP em si (initialize/tools/list via HTTPS real), tudo contra a API real do Supabase. Falta homologar Edge Functions/branches. Ver `00_READ_FIRST` seções 5 e 7 para o relato completo.

## Leitura obrigatória

Antes de operar este repositório, leia nesta ordem:

1. `00_READ_FIRST_SUPABASE_MCP.md`
2. `03_INSTRUCTIONS_LLM_SUPABASE_MCP_VERTICALPARTS.md`
3. `01_RAG_SUPABASE_MCP_VERTICALPARTS.md`
4. `02_SPEC_SUPABASE_MCP_VERTICALPARTS.md`
5. `04_SDD_SUPABASE_MCP_VERTICALPARTS.md`
6. `05_RUNBOOK_COPY_PASTE_SETUP_AND_RECOVERY.md`

Depois consulte: `README.md`, `config/*.example.yaml`, `src/verticalparts_supabase_mcp/*`.

Irmãos deste repositório: `verticalpartsIA/verticalparts-infrastructure-mcp` e `verticalpartsIA/verticalparts-github-mcp` — mesma filosofia de governança (classificação de risco, confirmação proporcional, auditoria sem segredo), aplicada ao Supabase em vez de VPS/Hostinger/GitHub. Em caso de dúvida sobre convenção, os dois repositórios irmãos (já homologados em produção) são a referência mais madura.

## Missão

Administrar o Supabase da organização `VerticalParts` por tools semânticas, com confirmação proporcional ao risco, proteção de segredos (Personal Access Token, `service_role key` nunca exposta) e auditoria — sem exigir que o operador use o dashboard do Supabase ou memorize `project_ref`/comandos de API.

## Hierarquia de verdade

1. estado vivo observado (chamada real à Management API do Supabase);
2. `config/projects.yaml` do runtime — registro de criticidade/contexto por projeto;
3. código em execução;
4. documentos canônicos numerados;
5. memória de conversa.

`config/projects.yaml` é um registro de **contexto operacional** (criticidade, notas), não um cache de estado — sempre confirme o estado real via API antes de mutações, nunca confie só no registro.

## Estado atual (2026-09-19)

- código completo: 33 tools, todas com validação de input e classificação de risco (fixa, exceto `sb_execute_sql`, que é dinâmica — ver `01_RAG` RAG-006A);
- **homologado contra `api.supabase.com` real**: PAT do operador configurado em `/opt/verticalparts-supabase-mcp/secrets/supabase-access-token` (nunca visto por esta LLM), testes reais de auth/leitura/escrita crítica/reversão/classificação dinâmica de SQL — ver `00_READ_FIRST` seção 5 para o relato completo;
- **descoberta real**: o PAT enxerga 3 organizações (`VerticalParts`, `VerticalParts (LOW)`, `ESCAMAX`) e 14 projetos — mais do que o conector oficial (escopado, OAuth) mostrava antes de gerar o PAT. Todos os 14 estão em `config/projects.example.yaml` — ver `00_READ_FIRST` seção 6;
- **ainda não testado**: Edge Functions e branches de desenvolvimento (feature experimental da própria Supabase) — ver `04_SDD` seção 9;
- deploy público concluído: `verticalparts-supabase-mcp.service` (systemd, usuário `supabase-mcp`, `127.0.0.1:8022`) atrás de Nginx + TLS (Let's Encrypt, expira 2026-12-18) em `https://supabase-mcp.vpsistema.com/mcp`, protegido por `X-API-Key`;
- protocolo MCP testado via HTTPS público de verdade: `initialize` (200), `tools/list` (33 tools), auth (401 sem chave / 401 chave errada);
- break-glass (`sb_api_call` para métodos != GET) desabilitado por padrão (`SUPABASE_ALLOW_BREAK_GLASS=false`).

## Nota de topologia: autenticação por PAT, não por app/instalação

A Management API do Supabase não tem um conceito equivalente ao GitHub App (permissões granulares por recurso, instalação por subconjunto de repositórios). Autentica por Personal Access Token, que herda todo o acesso da conta que o gerou. Isso torna a governança deste próprio MCP a única camada real de limite de escopo — ver `01_RAG` RAG-003A para o detalhe e a implicação de segurança.

## Regras obrigatórias

- Não invente `project_ref`, organização, nome de branch ou slug de Edge Function — descubra por leitura (`sb_list_projects`, `sb_get_project`, `sb_list_branches`, `sb_list_edge_functions`) antes de mutar.
- Nunca mostre segredos: PAT, `X-API-Key` do gateway, `service_role key` de qualquer projeto, senha de banco definida em `sb_create_project`. Nenhuma tool deste MCP retorna `service_role key` — se algo parecer retornar, é bug, não confie nele.
- `sb_execute_sql` tem risco dinâmico (ver `01_RAG` RAG-006A) — nunca assuma READ por padrão; classifique pelo conteúdo antes de decidir se precisa de confirmação.
- `sb_delete_project` é a operação mais destrutiva do catálogo — apaga banco, Auth, Storage e Edge Functions juntos, sem lixeira. Exigir `project_ref` explícito e `CONFIRMO_DESTRUTIVO`, nunca um projeto "padrão" implícito.
- Operação crítica: `CONFIRMO`. Operação destrutiva: `CONFIRMO_DESTRUTIVO`. Break-glass: `BREAK_GLASS` e `SUPABASE_ALLOW_BREAK_GLASS=true`.
- Antes de qualquer `CONFIRMO_DESTRUTIVO` em projeto, consultar `config/projects.yaml` para saber a criticidade declarada — um projeto `critical` (produção direta) merece mais uma pausa de confirmação explícita com o operador do que um projeto `low`, mesmo que o mecanismo técnico de confirmação seja o mesmo.
- `sb_create_project`/`sb_restore_project` têm custo financeiro real — mostrar `sb_get_cost` antes de pedir `CONFIRMO` quando disponível.
- Depois de mutação, valide o estado final com uma leitura (ex.: `sb_get_project`, `sb_list_tables`, `sb_list_migrations`).
- Mudança estrutural (novo projeto crítico, novo padrão de migração, endpoint de branching validado pela primeira vez) exige atualização de `config/projects.yaml` e desta documentação.

## Continuidade operacional

Setup do zero (geração do PAT, configuração, primeiro deploy) está em `05_RUNBOOK_COPY_PASTE_SETUP_AND_RECOVERY.md`.

Nunca deixe uma mudança arquitetural registrada somente em conversa.
