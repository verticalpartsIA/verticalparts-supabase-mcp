# 05 — RUNBOOK COPY/PASTE — Setup, Deploy e Recuperação

Versão: 2026-09-19
Status: canônico
Objetivo: permitir reconstrução operacional por uma LLM ou humano autorizado, do zero (PAT ainda não existe) até homologado.

IMPORTANTE: comandos abaixo não contêm segredos; alguns passos geram/exibem segredos na tela do Supabase — nunca cole esse conteúdo em chat, issue ou Git.

---

# PARTE A — GERAR O PERSONAL ACCESS TOKEN (passo humano, obrigatório antes de tudo)

## A1. Gerar o PAT

Dashboard do Supabase → ícone da conta (canto superior direito) → **Account** → **Access Tokens** → **Generate new token**.

URL direta: `https://supabase.com/dashboard/account/tokens`

Dar um nome descritivo ao token (ex.: `verticalparts-supabase-mcp`) para poder identificá-lo depois na lista e revogar seletivamente sem afetar outros tokens.

## A2. Guardar o token com segurança

O token só aparece **uma vez** na tela, na hora da geração. Copiar imediatamente para o local final (PARTE B), nunca deixar só na área de transferência ou em um arquivo temporário.

## A3. Confirmar a organização

O PAT herda o acesso do usuário que o gerou — confirmar (via dashboard, ou depois via `sb_list_organizations` já configurado) que a organização `VerticalParts` (`cdcqhcogckjfttevtoev`) está entre as visíveis.

---

# PARTE B — CONFIGURAR O AMBIENTE

## B1. Levar o token para o host de execução

~~~bash
sudo mkdir -p /opt/verticalparts-supabase-mcp/secrets
sudo chmod 700 /opt/verticalparts-supabase-mcp/secrets
# criar o arquivo com o token gerado no passo A1, uma linha, sem quebras extras:
# /opt/verticalparts-supabase-mcp/secrets/supabase-access-token
sudo chmod 600 /opt/verticalparts-supabase-mcp/secrets/supabase-access-token
~~~

## B2. Preencher `.env`

~~~bash
cp .env.example .env
~~~

Preencher `SUPABASE_ACCESS_TOKEN_PATH` apontando para o arquivo do passo B1 (ou, em ambiente de desenvolvimento local apenas, `SUPABASE_ACCESS_TOKEN` diretamente — nunca em produção).

## B3. Preencher `config/projects.yaml`

~~~bash
cp config/projects.example.yaml config/projects.yaml
~~~

O arquivo de exemplo já vem pré-preenchido com os 11 `project_ref` reais descobertos em 2026-09-19 via `sb_list_projects`/conector oficial (ver `00_READ_FIRST` seção 5/6). **Revisar a criticidade de cada um com o operador antes de considerar `config/projects.yaml` definitivo** — a do exemplo é inferida do nome, não confirmada.

## B4. Instalar dependências

~~~bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
~~~

---

# PARTE C — PRIMEIRO TESTE REAL (local, stdio)

## C1. Rodar localmente

~~~bash
MCP_TRANSPORT=stdio verticalparts-supabase-mcp
~~~

(ou configurar um cliente MCP local — Claude Desktop/Claude Code — apontando para o binário, para testar via tools/call de verdade)

## C2. Primeiro teste de integração real

Chamar `sb_whoami`. Esperado: retorna a organização `VerticalParts` (`cdcqhcogckjfttevtoev`), confirmando que o PAT é válido.

Se falhar: revisar se o token foi colado sem espaços/quebras extras, se o arquivo tem a permissão certa, e se o token não foi revogado no dashboard.

## C3. Segundo teste: uma leitura real

`sb_list_projects()` — deve bater com os 11 projetos conhecidos (ou o conjunto atual, se algo mudou desde então).

## C4. Terceiro teste: uma tool crítica real, em projeto de baixa criticidade

Em um projeto marcado `low`/`medium` em `config/projects.yaml` (nunca em `VP CLICK`/`vprequisicao`/`bd_Omie`), rodar `sb_apply_migration` criando uma tabela de teste claramente nomeada (ex.: `_mcp_homologacao_teste`), com `confirmation="CONFIRMO"`. Validar com `sb_list_tables` que a tabela apareceu. Depois, limpar rodando `sb_execute_sql` com `DROP TABLE _mcp_homologacao_teste;` e `confirmation="CONFIRMO_DESTRUTIVO"` (a classificação dinâmica deve exigir exatamente essa confirmação).

## C5. Quarto teste: classificação dinâmica de `sb_execute_sql`

Confirmar na prática que:
- `SELECT 1;` executa sem `confirmation`;
- `INSERT INTO ...` é recusado sem `confirmation="CONFIRMO"`;
- `DROP TABLE ...`/`DELETE FROM ...`/`TRUNCATE ...` é recusado sem `confirmation="CONFIRMO_DESTRUTIVO"`.

Só depois desses 5 testes reais este MCP pode ser considerado "homologado" — atualizar `00_READ_FIRST` e `README.md` com a evidência, no mesmo formato usado pelo github-mcp.

---

# PARTE D — DEPLOY EM PRODUÇÃO (mesmo padrão dos dois MCPs irmãos)

## D1. Clonar no host

~~~bash
git clone https://github.com/verticalpartsIA/verticalparts-supabase-mcp.git /opt/verticalparts-supabase-mcp
cd /opt/verticalparts-supabase-mcp
python3 -m venv .venv
.venv/bin/pip install -e .
~~~

## D2. Usuário dedicado

~~~bash
sudo useradd --system --home /opt/verticalparts-supabase-mcp --shell /usr/sbin/nologin supabase-mcp
sudo chown -R supabase-mcp:supabase-mcp /opt/verticalparts-supabase-mcp
~~~

Este MCP, como o github-mcp, não opera SSH/Docker/systemd de outro host — só faz chamadas HTTPS para `api.supabase.com`. Em princípio não precisa de nenhum privilégio `sudo`.

## D3. Instalar o systemd unit

~~~bash
sudo cp systemd/verticalparts-supabase-mcp.service.example /etc/systemd/system/verticalparts-supabase-mcp.service
# editar paths se necessário
sudo systemctl daemon-reload
sudo systemctl enable --now verticalparts-supabase-mcp.service
sudo systemctl is-active verticalparts-supabase-mcp.service
~~~

## D4. Nginx + TLS

~~~bash
sudo cp nginx/supabase-mcp.vpsistema.com.example.conf /etc/nginx/sites-available/supabase-mcp.vpsistema.com
# gerar uma X-API-Key forte:
openssl rand -hex 32
# substituir SUBSTITUA_PELA_CHAVE_REAL_NUNCA_COMMITAR no arquivo pelo valor gerado
# salvar o valor real em /root/supabase-mcp-auth-token (600, root:root) no host, fora do Git
sudo ln -s /etc/nginx/sites-available/supabase-mcp.vpsistema.com /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
certbot --nginx -d supabase-mcp.vpsistema.com
~~~

## D5. Validar endpoint público

~~~bash
curl -i https://supabase-mcp.vpsistema.com/mcp
# esperado: 401 sem X-API-Key
~~~

## D6. Conectar no Claude

Nome: `VerticalParts Supabase`
URL: `https://supabase-mcp.vpsistema.com/mcp`
Autenticação: Sem login
Header: `X-API-Key`

---

# PARTE E — ATUALIZAR O PRÓPRIO SUPABASE MCP

Mesmo padrão do `verticalparts-github-mcp/05_RUNBOOK` PARTE E / `verticalparts-infrastructure-mcp/05_RUNBOOK` PARTE G — se `/opt/verticalparts-supabase-mcp` acabar sendo `root:root`, as mesmas ressalvas de ownership do Git se aplicam.

Passos:
1. `sudo git -C /opt/verticalparts-supabase-mcp pull --ff-only`;
2. `sudo /opt/verticalparts-supabase-mcp/.venv/bin/pip install -e /opt/verticalparts-supabase-mcp` (se `pyproject.toml` mudou);
3. `sudo /opt/verticalparts-supabase-mcp/.venv/bin/python3 -m py_compile src/verticalparts_supabase_mcp/*.py`;
4. `sudo systemctl restart verticalparts-supabase-mcp.service`;
5. `sudo systemctl is-active verticalparts-supabase-mcp.service`;
6. validar `tools/list` e uma tool de leitura real.

---

# PARTE F — ROTACIONAR O PERSONAL ACCESS TOKEN

Prioridade mais alta que a rotação equivalente do github-mcp, porque o PAT não tem escopo granular (ver `01_RAG` RAG-003A):

1. Gerar um novo PAT (PARTE A1), sem revogar o antigo ainda;
2. copiar o novo token para o host, sobrescrevendo o arquivo do passo B1 (com backup do antigo, fora do Git);
3. reiniciar o serviço;
4. validar com `sb_whoami`;
5. só depois de confirmar que o novo token funciona, voltar no dashboard e revogar o token antigo.

---

# PARTE G — ROTACIONAR A X-API-KEY DO GATEWAY

Mesmo procedimento dos dois MCPs irmãos (`verticalparts-infrastructure-mcp/05_RUNBOOK` PARTE Y / `verticalparts-github-mcp/05_RUNBOOK` PARTE G).

---

# PARTE H — INCIDENTE: `sb_whoami` FALHA COM 401

1. conferir se o token em `SUPABASE_ACCESS_TOKEN_PATH`/`SUPABASE_ACCESS_TOKEN` foi colado sem espaço/quebra extra;
2. conferir se o token não foi revogado em `https://supabase.com/dashboard/account/tokens`;
3. conferir se `SUPABASE_API_BASE` está correto (`https://api.supabase.com/v1` por padrão — não confundir com a URL de um projeto específico, `https://<ref>.supabase.co`, que é outra API);
4. só depois de eliminar essas hipóteses, investigar o código.

---

# PARTE I — CRITÉRIO DE SUCESSO

Nunca declare "pronto" só porque um comando rodou. Para este MCP:
- `sb_whoami` funciona e mostra a organização `VerticalParts`;
- `tools/list` retorna as 33 tools;
- uma tool READ real bate com o que se vê no dashboard do Supabase;
- uma tool CRITICAL real, com confirmação, executa e o efeito é validado por leitura;
- `sb_execute_sql` classifica corretamente os três níveis de risco na prática (PARTE C5);
- nenhuma tool retornou `service_role key` em nenhuma circunstância;
- auth pública funciona (quando publicado);
- nenhum segredo apareceu em nenhuma resposta.
