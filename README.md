# LPS — Plataforma de Gestão do Trabalho

Aplicação Django que implementa o núcleo D0 da LPS: uma plataforma de gestão do
trabalho **multi-organização** que organiza atividades e tarefas, torna filas e
responsabilidades visíveis, registra o que acontece durante a execução e
transforma esse histórico em informação para gestão.

- **O produto** (regras de negócio e telas) está em [`Regras/`](Regras/00_INDICE_LPS.md) e [`Telas/`](Telas/).
- **O código** (como essas regras foram implementadas) está documentado em [`docs/`](#documentação-técnica).

## Stack

| Item | Versão / escolha |
|---|---|
| Framework | Django 5.2 (LTS) |
| Python | 3.14 no desenvolvimento local · 3.12.7 no Render |
| Banco | SQLite (dev) · PostgreSQL via `DATABASE_URL` (prod) |
| Servidor | `runserver` (dev) · gunicorn + whitenoise (prod) |
| Frontend | Templates Django + CSS/JS estáticos, sem bundler |
| Dependências | `django-environ`, `nh3` (sanitização de HTML), `gunicorn`, `whitenoise`, `psycopg` — ver [`requirements.txt`](requirements.txt) |

## Início rápido (Windows / PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env          # e defina SECRET_KEY
python manage.py migrate
python manage.py seed_lps_demo  # organização "Biasi", setores, ações e perfis
python manage.py createsuperuser
python manage.py runserver
```

Antes de usar as telas, **vincule seu usuário a uma organização** (Admin do
Django → Accounts → Perfis → campo "organização"); sem isso toda tela redireciona para o
perfil. Detalhes em [`docs/02_AMBIENTE_LOCAL.md`](docs/02_AMBIENTE_LOCAL.md).

O login é feito **por e-mail**, não por nome de usuário.

## Documentação técnica

| # | Documento | Conteúdo |
|---|---|---|
| 01 | [Arquitetura](docs/01_ARQUITETURA.md) | Apps, camadas, multi-tenancy, convenções do código |
| 02 | [Ambiente local](docs/02_AMBIENTE_LOCAL.md) | Instalação, dados de demonstração, management commands |
| 03 | [Configuração](docs/03_CONFIGURACAO.md) | Settings dev/prod, variáveis de ambiente, estáticos e anexos |
| 04 | [Modelos de dados](docs/04_MODELOS_DE_DADOS.md) | Todos os models por app, enums, constraints, diagrama ER |
| 05 | [Autorização](docs/05_AUTORIZACAO.md) | Motor de acessos: ações, perfis, escopos, `AuthorizationService` |
| 06 | [Atividades e tarefas](docs/06_ATIVIDADES_E_TAREFAS.md) | Ciclos de vida, fila, prazos, sessões, processos |
| 07 | [Contas e autenticação](docs/07_CONTAS_E_AUTENTICACAO.md) | Cadastro, confirmação de e-mail, login, senha |
| 08 | [Notificações e auditoria](docs/08_NOTIFICACOES_E_AUDITORIA.md) | O que gera notificação, e-mail e registro de auditoria |
| 09 | [Rotas](docs/09_ROTAS.md) | Referência de todas as URLs |
| 10 | [Frontend](docs/10_FRONTEND.md) | Templates, JS, CSS, context processors, template tags |
| 11 | [Testes](docs/11_TESTES.md) | Como rodar, organização, helpers, teste JS |
| 12 | [Deploy no Render](docs/12_DEPLOY_RENDER.md) | `render.yaml`, primeiro deploy, limitações do plano free |
| 13 | [Pendências conhecidas](docs/13_PENDENCIAS_CONHECIDAS.md) | Defeitos e dívidas técnicas mapeados |
