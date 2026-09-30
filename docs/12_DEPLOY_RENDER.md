# 12 — Deploy no Render

> A aplicação é publicada no Render pelo Blueprint `render.yaml`, no plano
> free: um Web Service (`lps-web`) e um PostgreSQL (`lps-db`). Este documento
> explica o arquivo, o primeiro deploy e as limitações do plano gratuito.

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
5. O build roda `seed_acoes`, então o catálogo de ações é criado/atualizado a
   cada deploy. Ele **não** cria perfis de acesso nem os atribui: para usuários
   comuns, monte os perfis em **/permissoes/** (o superusuário funciona porque
   ignora o motor) ou, só numa organização de demonstração, use
   `seed_lps_demo --org-name "..."`. Ação nova do catálogo (ex.: `tarefa.reabrir`)
   aparece em `/permissoes/`, mas **não** entra sozinha em perfis já existentes:
   marque-a nos perfis que devem ter.

Deploys seguintes acontecem a cada push na branch `main`.

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
| Sem Cron Job gratuito | `check_overdue_tasks` não roda sozinho; avisos de atraso não são disparados |

---

## 5. Python local × Render

O desenvolvimento local usa Python 3.14; o Render, 3.12.7 (fixado em
`PYTHON_VERSION`). As versões em `requirements.txt` foram escolhidas para ter
wheels nas duas (por exemplo, `psycopg[binary]==3.2.13`; a 3.2.3 não tinha
wheel para 3.14). Ao atualizar dependências, confira se a versão nova tem
wheel para as duas versões de Python — ou alinhe `PYTHON_VERSION` com a versão
local.
