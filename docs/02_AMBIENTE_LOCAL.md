# 02 — Ambiente local

> Como colocar a LPS para rodar na sua máquina, do zero, com dados de
> demonstração e um usuário capaz de usar todas as telas.
> Atualizado em 03/10/2026 (código no commit `add5acd`).

---

## 1. Pré-requisitos

- Python 3.12 ou superior (o `.venv` local atual usa 3.13; o Render usa
  3.12.7 — ver [12_DEPLOY_RENDER.md](12_DEPLOY_RENDER.md)).
- Git.
- Node 18+ **apenas** se for rodar os testes JavaScript (`tests/*.test.cjs`,
  com `jsdom`; `npm install` e `npm run test:js` — ver
  [11_TESTES.md](11_TESTES.md)).

Os comandos abaixo são para PowerShell no Windows. Em Linux/macOS, troque
`.venv\Scripts\Activate.ps1` por `source .venv/bin/activate` e `copy` por `cp`.

---

## 2. Instalação

```powershell
git clone https://github.com/Lucasrafael703/workflow.git
cd workflow
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Abra o `.env` e defina ao menos `SECRET_KEY` (qualquer string longa e
aleatória serve em dev). O resto pode ficar como está: em dev o e-mail sai no
console e o banco é SQLite (`db.sqlite3`, ignorado pelo Git). Todas as
variáveis estão em [03_CONFIGURACAO.md](03_CONFIGURACAO.md).

> Use `.venv/`, não `venv/` (a pasta `venv/` antiga, de outra máquina, não
> existe mais, mas `.claude/launch.json` ainda aponta para
> `venv/Scripts/python.exe`; ver
> [13_PENDENCIAS_CONHECIDAS.md](13_PENDENCIAS_CONHECIDAS.md)).

---

## 3. Banco e dados de demonstração

```powershell
python manage.py migrate
python manage.py seed_lps_demo
```

`seed_lps_demo` é idempotente (pode rodar várias vezes) e:

1. roda `seed_acoes`, que grava o catálogo de ações de `acessos/catalog.py`;
2. cria a organização **Biasi** e a empresa **Biasi Engenharia** (mude com
   `--org-name` e `--company-name`);
3. cria os setores Comercial, Engenharia, Compras, Financeiro e Almoxarifado;
4. cria os perfis de acesso sugeridos — **Colaborador**, **Gestor de Setor** e
   **Administrador** — com suas ações.

Ele **não** cria usuários nem quadros. Os quadros padrão de Demandas e Tarefas
(`DomainBoard`) são criados sozinhos na primeira vez que a tela é aberta; para
criá-los de uma vez em todas as organizações, rode `seed_default_boards`
(seção 6).

---

## 4. Primeiro usuário

```powershell
python manage.py createsuperuser
```

Preencha o **e-mail**: o login da LPS é por e-mail
(`accounts.auth_backends.EmailBackend`), então um superusuário sem e-mail não
consegue entrar pela tela de login.

Em seguida, **vincule o usuário a uma organização**. Sem isso, toda tela da LPS
redireciona para `/accounts/me/` com a mensagem "Seu usuário ainda não está
vinculado a uma organização":

1. `python manage.py runserver` e entre em `http://127.0.0.1:8000/admin/`;
2. seção **Accounts** → **Perfis** (não confundir com "Perfis de acesso", do
   app Acessos) → seu usuário → campo **organização** = Biasi → Salvar.

Ou, pelo shell:

```powershell
python manage.py shell -c "from django.contrib.auth import get_user_model; from core.models import Organization; u = get_user_model().objects.get(username='SEU_USUARIO'); u.profile.organization = Organization.objects.get(name='Biasi'); u.profile.save()"
```

Um superusuário ativo passa por todas as verificações de autorização
(`AuthorizationService.is_platform_admin`), então não precisa de perfil de
acesso. Para testar como um usuário comum, crie outra pessoa em `/usuarios/novo/`
e atribua um perfil em `/usuarios/<id>/acessos/`.

---

## 5. Rodando

```powershell
python manage.py runserver
```

Ou dê dois cliques em `iniciar_lps.bat`: ele sobe o servidor em
`127.0.0.1:8000` numa janela minimizada (usando `.venv`) e abre o Chrome.

`manage.py` usa `config.settings.dev` por padrão (DEBUG ligado, SQLite, e-mail
no console).

Duas coisas aparecem **desligadas** num ambiente novo, de propósito:

- a **Caixa de Entrada** (`/entrada/`): inativa por padrão; as rotas dão 404 e
  o item "Entrada" some do menu. Para ligar, `INTAKE_ENABLED=true` no `.env`
  ([03_CONFIGURACAO.md](03_CONFIGURACAO.md));
- o **fluxo operacional de Tarefas** (`/fila/`, `/processos/`,
  `/tarefas/<id>/…`): foi desativado em 02/10/2026 e responde **410**. As
  tarefas de uma Demanda vivem no quadro dela (`/quadros/…`, painel
  **Tarefas**); ver [06_ATIVIDADES_E_TAREFAS.md](06_ATIVIDADES_E_TAREFAS.md).

---

## 6. Management commands

| Comando | App | O que faz | Quando usar |
|---|---|---|---|
| `seed_acoes` | `acessos` | Sincroniza o catálogo de `acessos/catalog.py` com o banco (`update_or_create`). Ações que saíram do catálogo ficam `is_active=False`; nunca são apagadas. | Sempre que `catalog.py` mudar. Já é chamado por `seed_lps_demo`. |
| `seed_lps_demo` | `core` | Organização, empresa, setores e perfis sugeridos (ver seção 3). Opções `--org-name`, `--company-name`. | Primeiro setup; ambientes de demonstração. |
| `ensure_superuser` | `accounts` | Cria um superusuário a partir de `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL` e `DJANGO_SUPERUSER_PASSWORD`, só se esse username ainda não existir. Sem as variáveis, não faz nada. | Deploy automatizado (roda no build do Render). |
| `check_overdue_tasks` | `activities` | Marca tarefas com prazo comprometido vencido, notifica (in-app + e-mail) uma única vez por tarefa. | Pode ser **agendado** (Agendador de Tarefas do Windows, cron); não há worker assíncrono. Como o fluxo operacional de `Task` foi desativado (a migration `boards/0008` cancela as tarefas operacionais), hoje tende a não encontrar nada. |
| `seed_default_boards` | `boards` | Cria, de forma idempotente, os quadros de domínio padrão de Demandas e de Tarefas (`DomainBoard`) em todas as organizações. | Opcional: a tela `/demandas/` já cria o quadro sob demanda (`ensure_domain_board`). |
| `seed_board_templates` | `boards` | Cria um quadro a partir de um modelo (hoje só `orcamentos`). Opções: `--organization` e `--user` (obrigatórias), `--modelo`, `--nome`, `--exemplos`. Não faz nada se já existir um quadro ativo com o mesmo nome. | Demonstração ou ponto de partida; não roda no deploy. |
| `backfill_demand_boards` | `boards` | **Desativado**: sempre termina com erro orientando a usar a migration `boards/0008`. | Não usar; fica no código só como registro da migração antiga. |

---

## 7. Problemas comuns

| Sintoma | Causa | Solução |
|---|---|---|
| `ImproperlyConfigured: Set the SECRET_KEY environment variable` | `.env` ausente ou sem `SECRET_KEY` | Copie `.env.example` para `.env` e preencha. |
| Toda tela volta para "Meu perfil" com aviso de organização | `Profile.organization` vazio | Seção 4. |
| Login diz que e-mail/senha estão errados para o superusuário | Superusuário criado sem e-mail | Defina o e-mail no Admin ou recrie. |
| Conta criada em "Criar conta" não entra | A conta fica inativa até confirmar o código de e-mail; o código aparece no console do `runserver` em dev | Ver [07_CONTAS_E_AUTENTICACAO.md](07_CONTAS_E_AUTENTICACAO.md). |
| Botões/menus não aparecem para um usuário comum | Falta perfil de acesso com a ação no escopo certo | Ver [05_AUTORIZACAO.md](05_AUTORIZACAO.md). |
| `/entrada/` dá 404 e não há "Entrada" no menu | A Caixa de Entrada está inativa por padrão | `INTAKE_ENABLED=true` no `.env` (seção 5). |
| `/fila/`, `/processos/` ou `/tarefas/<id>/…` respondem 410 | Fluxo operacional de Tarefas e Processos desativado (02/10/2026) | Não é erro: use o quadro da Demanda. |
| `InconsistentMigrationHistory` depois de um `git pull` | Banco local criado com migrations antigas que foram reescritas | Em dev, apague `db.sqlite3` e rode `migrate` + `seed_lps_demo` de novo. |
