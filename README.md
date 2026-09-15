# LPS — Plataforma de Gestão do Trabalho

Aplicação Django que implementa o núcleo D0 da LPS (ver `Regras/`): uma
plataforma de gestão do trabalho multi-organização que organiza atividades e
tarefas, torna filas e responsabilidades visíveis, registra o que acontece
durante a execução e transforma esse histórico em informação para gestão.

Construída apenas com recursos nativos do Django (auth, ORM, CBVs, Forms,
Admin, `django.core.mail`, `django.contrib.messages`, signals, management
commands) — a única dependência externa é `django-environ`, usada só para
o parsing tipado de variáveis de ambiente.

## Setup local

```bash
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env         # e ajuste os valores
python manage.py migrate
python manage.py seed_lps_demo
python manage.py createsuperuser
python manage.py runserver
```

`DJANGO_SETTINGS_MODULE` já aponta para `config.settings.dev` via
`manage.py` (SQLite + e-mail no console). Para produção, use
`config.settings.prod` (requer `DATABASE_URL` no ambiente).

## Apps

- `core` — estrutura multi-tenant: `Organization`, `Company`, `Sector` (configurável, nunca fixo no código), `Site` (obra), `CostCenter`.
- `accounts` — `Profile` (1:1 com `User`, vinculado a uma única `Organization`), `UserSector` (participação operacional em setores, separada de permissões).
- `activities` — núcleo operacional da LPS: `Activity` (dono único), `Task` (setor, executores, sessões de trabalho), fila por setor (`QueueEntry`/`QueuePositionChange`), devolução (`TaskReturn`/`ReturnReason`), negociação de prazo (`DeadlineProposal`/`DeadlineConflict`), `ActivityService`/`TaskService`/`QueueService`/`DeadlineService`.
- `notifications` — `Notification`, inbox in-app, `EmailService` (e-mail restrito ao evento de tarefa atrasada).
- `audit` — `AuditLog`, histórico de todos os eventos relevantes (criação, mudança de dono, execução, devolução, fila, prazo, conclusão).

## Management commands

- `seed_lps_demo` — cria (idempotentemente) uma organização de demonstração, empresa, setores básicos e perfis (`Administrador`, `Gestor`, `Colaborador`) com as permissões correspondentes.
- `check_overdue_tasks` — verifica tarefas com prazo comprometido vencido e dispara notificação in-app + e-mail. **Deve ser agendado** periodicamente (Task Scheduler no Windows, cron no Linux) — o MVP não usa Celery/Redis, então este comando substitui um worker assíncrono.

## Testes

```bash
python manage.py test
```

Cobre as regras centrais do núcleo D0: dono único da atividade e auditoria
de troca de dono, múltiplos executores com tempo individual (horas-homem),
pausa automática de sessão ao iniciar outra tarefa, devolução com motivo
obrigatório preservando histórico, posição e total de fila com reordenação
auditada, negociação de prazo solicitado x comprometido com conflito
registrado na recusa, e isolamento entre organizações.
