# 03 — Configuração

> Como os settings estão divididos, todas as variáveis de ambiente que o código
> lê, e como arquivos estáticos e anexos são guardados e servidos.

---

## 1. Settings

```
config/settings/
├── base.py   # comum: apps, middleware, templates, auth, i18n, estáticos, e-mail
├── dev.py    # DEBUG=True, SQLite, e-mail no console
└── prod.py   # DEBUG=False, Postgres via DATABASE_URL, whitenoise, HTTPS
```

`base.py` lê o arquivo `.env` na raiz do projeto (`environ.Env.read_env`).
Variáveis já definidas no ambiente têm prioridade sobre o `.env`.

Qual settings é usado depende de **como** o Django é iniciado:

| Entrada | Default de `DJANGO_SETTINGS_MODULE` |
|---|---|
| `manage.py` | `config.settings.dev` |
| `config/wsgi.py` (gunicorn) | `config.settings.prod` |
| `config/asgi.py` | `config.settings.prod` |

Por isso, no Render, `DJANGO_SETTINGS_MODULE=config.settings.prod` precisa
estar definido: o build roda `manage.py` (`collectstatic`, `migrate`), que
sozinho usaria dev.

---

## 2. Variáveis de ambiente

| Variável | Default | Lida em | Observação |
|---|---|---|---|
| `SECRET_KEY` | — **obrigatória** | `base.py` | Sem ela o Django não inicia. |
| `ALLOWED_HOSTS` | `[]` | `base.py` | Lista separada por vírgula. Em dev com `DEBUG=True`, `localhost` já é aceito. |
| `ACTIVITY_FILES_ROOT` | `<projeto>/atividade_arquivos` | `base.py` | Pasta dos anexos das demandas (seção 4). O nome `atividade_arquivos` não mudou com a troca para "Demanda": é local de armazenamento, não endereço. |
| `INTAKE_ENABLED` | `false` | `base.py` | Liga a Caixa de Entrada (`/entrada/`). Desligada, o item "Entrada" some do menu e todas as rotas dela dão 404; o código, as tabelas e as permissões `entrada.*` continuam. Para reativar: `INTAKE_ENABLED=true` (no Render, em Environment do serviço web; não está no `render.yaml` para um novo deploy não desfazer o valor do painel). |
| `EMAIL_HOST` | `""` | `base.py` | |
| `EMAIL_PORT` | `587` | `base.py` | |
| `EMAIL_HOST_USER` | `""` | `base.py` | |
| `EMAIL_HOST_PASSWORD` | `""` | `base.py` | |
| `EMAIL_USE_TLS` | `True` | `base.py` | |
| `DEFAULT_FROM_EMAIL` | `no-reply@example.com` | `base.py` | Remetente dos e-mails. |
| `ADMIN_GROUP_NAME` | `ADMIN` | `base.py` | Lida, mas **não usada** por nenhum código hoje. |
| `EMAIL_BACKEND` | console (dev) · SMTP (prod) | `dev.py`, `prod.py` | |
| `DATABASE_URL` | — **obrigatória em prod** | `prod.py` | Ex.: `postgres://user:senha@host:5432/banco`. |
| `SECURE_SSL_REDIRECT` | `True` | `prod.py` | Redireciona HTTP → HTTPS. |
| `SECURE_HSTS_SECONDS` | `3600` | `prod.py` | |
| `CSRF_TRUSTED_ORIGINS` | `[]` | `prod.py` | Com esquema: `https://*.onrender.com`; o hostname público do Render também é incluído automaticamente por `RENDER_EXTERNAL_HOSTNAME`. |
| `DJANGO_SUPERUSER_USERNAME` | — | `ensure_superuser` | |
| `DJANGO_SUPERUSER_EMAIL` | `""` | `ensure_superuser` | Preencha: o login é por e-mail. |
| `DJANGO_SUPERUSER_PASSWORD` | — | `ensure_superuser` | |
| `DJANGO_SETTINGS_MODULE` | ver seção 1 | Django | |

Todas estão listadas (as opcionais comentadas) em [`.env.example`](../.env.example).

---

## 3. Outras configurações relevantes

| Setting | Valor | Por quê |
|---|---|---|
| `LANGUAGE_CODE` / `TIME_ZONE` | `pt-br` / `America/Sao_Paulo` | |
| `USE_TZ` | `True` | Datas gravadas em UTC, exibidas no fuso local. |
| `AUTHENTICATION_BACKENDS` | `accounts.auth_backends.EmailBackend` | Login por e-mail (`Telas/09_01_LOGIN.md`). Único backend: `ModelBackend` por username não está ativo. |
| `LOGIN_URL` / `LOGIN_REDIRECT_URL` / `LOGOUT_REDIRECT_URL` | `login` / `home` / `login` | |
| `DEFAULT_AUTO_FIELD` | `BigAutoField` | |
| Context processors próprios | `notifications...unread_notifications_count`, `acessos...navigation`, `activities...my_active_sessions` | Ver [10_FRONTEND.md](10_FRONTEND.md). |
| `SECURE_PROXY_SSL_HEADER` (prod) | `("HTTP_X_FORWARDED_PROTO", "https")` | O Render termina o TLS no proxy. Sem isso, `SECURE_SSL_REDIRECT` entra em loop de redirecionamento. |
| Cookies (prod) | `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` | |
| HSTS (prod) | `INCLUDE_SUBDOMAINS` e `PRELOAD` ligados | |

---

## 4. Arquivos estáticos, mídia e anexos

| Tipo | Pasta de origem | URL | Quem serve |
|---|---|---|---|
| Estáticos do projeto | `static/` (`STATICFILES_DIRS`) | `/static/` | dev: `runserver` · prod: **whitenoise** a partir de `staticfiles/` |
| Estáticos coletados | `staticfiles/` (`STATIC_ROOT`, gerado por `collectstatic`, ignorado pelo Git) | `/static/` | whitenoise |
| Mídia | `media/` (`MEDIA_ROOT`) | `/media/` | `django.views.static.serve` |
| Anexos das demandas | `ACTIVITY_FILES_ROOT` | `/demanda-arquivos/` | `django.views.static.serve` |

- Em prod, `STORAGES["staticfiles"]` usa
  `whitenoise.storage.CompressedManifestStaticFilesStorage` (nomes com hash e
  compressão). Por isso é preciso rodar `collectstatic` no build. Em dev o
  storage padrão é mantido para não exigir `collectstatic`.
- Anexos são gravados pelo storage `activity_files_storage()`
  (`activities/models.py`) no caminho `<empresa>/<código da demanda>/<arquivo>` (`DEM-AAAA-NNNNN`)
  (Regras 12 e 13); sem empresa, vai para `sem-empresa/`.
- `/media/` e `/demanda-arquivos/` são servidos pelo próprio Django **em
  todos os ambientes** (`config/urls.py`), porque no Render não há nginx na
  frente. Essas rotas **não exigem login** — ver
  [13_PENDENCIAS_CONHECIDAS.md](13_PENDENCIAS_CONHECIDAS.md).
- No plano free do Render o disco não é persistente: anexos enviados se perdem
  a cada deploy ou reinício.
