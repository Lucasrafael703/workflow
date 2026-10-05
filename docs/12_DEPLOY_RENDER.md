# 12 — Deploy no Render

> A aplicação é publicada no Render pelo Blueprint `render.yaml`, no plano
> free: um Web Service (`lps-web`) e um PostgreSQL (`lps-db`). Este documento
> explica o arquivo, o primeiro deploy, as limitações do plano gratuito e o
> histórico de correções de deploy.
> Atualizado em 03/10/2026 (código no commit `add5acd`).

---

## 1. `render.yaml`

| Chave | Valor | Por quê |
|---|---|---|
| `databases[0]` | `lps-db`, free, banco `lps`, usuário `lps` | Postgres gerenciado |
| `services[0].type` / `runtime` / `plan` | `web` / `python` / `free` | |
| `buildCommand` | `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate && python manage.py seed_acoes && python manage.py ensure_superuser` | Instala, coleta estáticos para o whitenoise, aplica migrations, sincroniza o catálogo de ações (idempotente: uma ação nova do código passa a existir em produção sem precisar de Shell) e cria o superusuário (se configurado) |
| `startCommand` | `gunicorn config.wsgi:application` | `wsgi.py` já usa `config.settings.prod` |
| `DJANGO_SETTINGS_MODULE` | `config.settings.prod` | Necessário porque o build usa `manage.py`, que sozinho usaria dev |
| `SECRET_KEY` | `generateValue: true` | O Render gera um valor aleatório no primeiro deploy |
| `ALLOWED_HOSTS` | `.onrender.com` | Qualquer subdomínio do Render |
| `CSRF_TRUSTED_ORIGINS` | `https://*.onrender.com` | Formulários sob HTTPS |
| `DATABASE_URL` | `fromDatabase: lps-db` | String de conexão injetada pelo Render |
| `PYTHON_VERSION` | `3.12.7` | Versão do Python no build |
| `DJANGO_SUPERUSER_USERNAME/EMAIL/PASSWORD` | `sync: false` | Preenchidos à mão no dashboard; nunca vão para o Git |

O Blueprint **não** define `INTAKE_ENABLED` (a Caixa de Entrada fica inativa;
para ligar, crie a variável em Environment — ver
[03_CONFIGURACAO.md](03_CONFIGURACAO.md)) nem as variáveis `EMAIL_*`
(seção 3). O Render injeta `RENDER_EXTERNAL_HOSTNAME`, que `prod.py` acrescenta
a `CSRF_TRUSTED_ORIGINS`. O Blueprint também não tem Cron Job (ver seção 4).

As configurações de produção que tornam isso possível estão em
`config/settings/prod.py`: whitenoise com `CompressedManifestStaticFilesStorage`
e `SECURE_PROXY_SSL_HEADER` (o Render termina o TLS no proxy; sem essa linha,
`SECURE_SSL_REDIRECT` entra em loop).

---

## 2. Primeiro deploy

1. Render → **New +** → **Blueprint** → conecte o repositório
   `Lucasrafael703/workflow`. O Render lê o `render.yaml` e cria banco e
   serviço.
2. No serviço `lps-web` → **Environment**, preencha
   `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL` (obrigatório na
   prática: o login é por e-mail) e `DJANGO_SUPERUSER_PASSWORD`. Salvar
   dispara novo deploy, e o build cria o usuário.
3. Entre em `https://<serviço>.onrender.com/admin/` com esse e-mail e senha.
4. O banco de produção começa **vazio de dados de negócio**. Pelo Admin:
   1. crie a **Organização**;
   2. em **Accounts → Perfis**, vincule seu usuário a ela.
   Os quadros padrão de Demandas e Tarefas são criados na primeira vez que a
   tela é aberta; não há `seed_default_boards` no build (ver
   [02_AMBIENTE_LOCAL.md](02_AMBIENTE_LOCAL.md), seção 6).
5. O build roda `seed_acoes`, então o catálogo de ações é criado/atualizado a
   cada deploy. Ele **não** cria perfis de acesso nem os atribui: para usuários
   comuns, monte os perfis em **/permissoes/** (o superusuário funciona porque
   ignora o motor) ou, só numa organização de demonstração, use
   `seed_lps_demo --org-name "..."`. Ação nova do catálogo (ex.: `tarefa.reabrir`)
   aparece em `/permissoes/`, mas **não** entra sozinha em perfis já existentes:
   marque-a nos perfis que devem ter.

Deploys seguintes acontecem a cada push na branch `main`.

Cada deploy roda `migrate` no PostgreSQL. As migrations de dados mais
sensíveis do histórico recente: `core/0012_sector_scoped_stages_conditions`
(etapas e status por setor), `activities/0020_codigo_da_demanda` (renomeia
`ATV-…` para `DEM-…` e as pastas de anexos) e `boards/0008_centralize_demand_board_items`
(converte as tarefas operacionais em itens de quadro e **cancela** as `Task`
operacionais; o histórico é preservado). Teste migrations de dados num
PostgreSQL com dados antes de publicar: o SQLite é mais tolerante (seção 6).

---

## 3. E-mail em produção

Nenhuma variável `EMAIL_*` está no `render.yaml`, então produção usa o backend
SMTP com host vazio. Enquanto não configurar (`EMAIL_HOST`, `EMAIL_PORT`,
`EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL` no dashboard):

- **Criar conta** dá erro 500: o código de confirmação é enviado por
  `send_mail` sem tratamento de erro (`accounts/views.py`), depois que o
  usuário inativo já foi gravado;
- **Esqueci minha senha** mostra a tela de "enviado", mas o e-mail não sai (o
  Django só registra a falha no log);
- os e-mails de notificação (`EmailService`) também só registram a falha no
  log, sem quebrar a tela.

---

## 4. Limitações do plano free

| Limitação | Efeito na LPS |
|---|---|
| Serviço hiberna após ~15 min sem acesso | Primeira requisição depois disso demora para responder |
| Postgres free expira (é apagado) após o período de gratuidade | Será preciso recriar o banco e rodar as migrations de novo |
| Disco não persistente | Anexos (`ACTIVITY_FILES_ROOT`) e mídia enviados somem a cada deploy/reinício |
| Sem Shell (recurso pago) | Não dá para rodar `manage.py` manualmente — por isso o superusuário é criado no build |
| Sem Cron Job gratuito | `check_overdue_tasks` não roda sozinho; avisos de atraso não são disparados (com o fluxo operacional de Tarefas desativado, o comando hoje tende a não encontrar nada) |

---

## 5. Python local × Render

O desenvolvimento local usa Python 3.13 ou 3.14 (o `.venv` atual é 3.13); o
Render, 3.12.7 (fixado em `PYTHON_VERSION`). As versões em `requirements.txt`
(Django 5.2.17, `django-environ`, `nh3`, `gunicorn`, `whitenoise`,
`psycopg[binary]==3.2.13` etc.) foram escolhidas para ter wheels nas duas (a
`psycopg` 3.2.3 não tinha wheel para 3.14). Ao atualizar dependências, confira se a versão nova tem
wheel para as duas versões de Python — ou alinhe `PYTHON_VERSION` com a versão
local.

---

## 6. Histórico de correções de deploy

| Data | Commit | Problema → correção |
|---|---|---|
| 26/09/2026 | `862338e` | Preparação do deploy gratuito: `gunicorn`, `whitenoise` e `psycopg` no `requirements.txt`, storage de manifest só em produção, `render.yaml` (Web Service + Postgres; a versão inicial trazia um Cron Job). |
| 26/09/2026 | `79d7ff7` | Loop infinito de redirecionamento atrás do proxy TLS → `SECURE_PROXY_SSL_HEADER`; formulários rejeitados por CSRF → `CSRF_TRUSTED_ORIGINS` por variável (`https://*.onrender.com`); `/media/` e anexos davam 404 com `DEBUG=False` (o helper `static()` não gera rota nesse caso) → rotas explícitas; `ACTIVITY_FILES_ROOT` passou a ficar dentro do projeto; `psycopg` 3.2.3 → 3.2.13 (wheel para Python 3.14). Depois, em 01/10, os anexos deixaram de ter rota pública (ver [03_CONFIGURACAO.md](03_CONFIGURACAO.md) §4). |
| 26/09/2026 | `30dc7f2` | Blueprint recusado: o Render não tem Cron Job no plano free → removido (`check_overdue_tasks` fica para execução manual/agendada fora do Render). |
| 26/09/2026 | `a65a49d` | Sem Shell no plano free para `createsuperuser` → comando `ensure_superuser` no fim do `buildCommand`, idempotente, com as três variáveis `DJANGO_SUPERUSER_*`. |
| 30/09/2026 | `0c55d22` | `seed_acoes` entra no `buildCommand`: ações novas do catálogo passam a existir em produção sem Shell. |
| 01/10/2026 | `901d67e` | `prod.py` passa a incluir `RENDER_EXTERNAL_HOSTNAME` em `CSRF_TRUSTED_ORIGINS`, para o login não ser rejeitado se a variável do Blueprint estiver dessincronizada com o hostname do serviço. |
| 02/10/2026 | `cdff812` | **Todo deploy desde `a756be2` falhava no `migrate`**: `core/0012` gravava linhas com FK e, na mesma transação, fazia `AlterField`/`AddConstraint` nas mesmas tabelas; no PostgreSQL com dados isso dava "cannot ALTER TABLE core_taskstage because it has pending trigger events" (no SQLite e em banco vazio passa). Correção: ao fim da função de dados, só no PostgreSQL, `SET CONSTRAINTS ALL IMMEDIATE` e depois `DEFERRED`. Bancos que já tinham aplicado a 0012 não rodam de novo. Até a correção, o Kanban por setor, os quadros dinâmicos, o Calendário e a tela de Demandas não tinham subido em produção. |
