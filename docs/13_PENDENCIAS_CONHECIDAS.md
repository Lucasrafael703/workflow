# 13 — Pendências conhecidas

> Defeitos, lacunas e dívidas técnicas encontrados ao documentar o código
> (29/09/2026). Cada item foi conferido no código-fonte. Nada aqui foi
> corrigido — a lista serve para priorizar. Ao resolver um item, remova-o
> daqui.

Legenda de severidade: **Alta** (segurança ou quebra em produção) ·
**Média** (comportamento errado para o usuário) · **Baixa** (limpeza).

---

## 1. Segurança

| # | Sev. | Onde | Problema |
|---|---|---|---|
| S1 | **Alta** | `config/urls.py` | `/atividade-arquivos/<path>` e `/media/<path>` são servidos por `django.views.static.serve` **sem exigir login nem autorização**. Quem souber (ou adivinhar) `<empresa>/<código ATV-...>/<arquivo>` baixa o anexo. Solução típica: uma view que carrega o `ActivityAttachment`, verifica acesso à atividade e devolve o arquivo. |
| S2 | Média | `acessos/catalog.py` × views | Ações de **visualização** nunca são verificadas: `atividade.visualizar`, `tarefa.visualizar`, `auditoria.visualizar`, `fila.visualizar_posicao_propria`. A ficha da atividade, a da tarefa e o histórico (`/historico/`) são limitados só pela organização — qualquer pessoa da organização abre qualquer atividade pelo link. |
| S3 | Média | `acessos/catalog.py` × views | Outras ações sem verificação: `usuario.criar` (só decide se o botão "criar pessoa" aparece; `/usuarios/novo/` exige `usuario.editar`), `usuario.inativar`, `setor.criar`, `processo.aplicar`. |
| S4 | Média | `activities/views.py` (`ActivityMoveStageView`, `TaskMoveStageView`) | Mover card no Kanban não verifica ação nenhuma e não é auditado — qualquer pessoa da organização muda o estágio de qualquer atividade/tarefa. |

## 2. Defeitos

| # | Sev. | Onde | Problema |
|---|---|---|---|
| D1 | **Alta** | `acessos/services.py`, `ResourceContext.of` (ramo `site`) | Lê `resource.company_id`, mas `core.Site` não tem mais `company` (migration `core/0010_remove_site_company_site_client`). Verificar autorização passando uma obra como recurso levanta `AttributeError`. |
| D2 | **Alta** (prod) | `accounts/views.py`, `_send_verification_email` | `send_mail` sem tratamento de erro. Sem SMTP configurado, "Criar conta" dá 500 depois de já ter gravado o usuário inativo. |
| D3 | Média | `activities/services.py`, `return_task` | Grava `DEVOLVIDA` e logo chama `move_to_sector` → `enqueue`, que sobrescreve para `EM_FILA`. Nenhuma tarefa fica `DEVOLVIDA`; a notificação `TASK_RETURNED` sai da aba "Ação necessária" imediatamente (ela checa `status == DEVOLVIDA`). |
| D4 | Média | `activities/services.py`, `TaskService.block` | Só recusa se a tarefa já está bloqueada; permite bloquear tarefa **concluída ou cancelada**. |
| D5 | Média | `activities/services.py` | Atividade nunca passa de `ABERTA` para `EM_ANDAMENTO` pelo trabalho (iniciar tarefa só marca `first_action_at`). `EM_ANDAMENTO` só vem de reabertura ou aprovação de pendência. |
| D6 | Média | `activities/services.py` | Pendência **sem** aprovação (`MATERIAL`, `INFORMACOES_CLIENTE`) não tem como ser resolvida: a atividade fica `PENDENTE` até ser finalizada. |
| D7 | Baixa | `activities/models.py`, `TaskResponsavelChangeLog` | Dois `__str__`; o segundo (vence) usa `self.user`, que não existe — `str()` levanta erro (aparece no Admin). Parece ter sido escrito para `TaskExecutor`, que ficou sem `__str__`. |
| D8 | Baixa | `activities/models.py` | `Activity.Status.BLOQUEADA` e `Task.Status.NAO_INICIADA` existem, mas nenhum fluxo os usa. `AuditLog.Action.SESSION_RESUMED` nunca é gravado. |
| D9 | Baixa | `core/tests.py`, `UserFormAjaxTests` | 2 testes falham: o payload não envia `password1`/`password2`, obrigatórios ao criar usuário. O teste está desatualizado. |

## 3. Funcionalidades incompletas

| # | Onde | Situação |
|---|---|---|
| F1 | `processes/` | Processos são criados, versionados e publicados, mas **não são aplicados** a atividades: nada preenche `Activity.process_version`, gera tarefas das etapas ou grava `ActivityInputValue`/`ActivityCriterionCheck`. |
| F2 | `notifications/recipients.py`, `ADMIN_GROUP_NAME` | A setting é lida mas não usada; `resolve_sector_and_admins` devolve só membros e gestores do setor. O help de `check_overdue_tasks` ainda fala em "administradores". |
| F3 | Autocadastro | Conta criada em "Criar conta" nunca recebe organização pelo app; é preciso o Admin do Django. A tela `/usuarios/` só lista quem já está na organização. |
| F4 | `painel/` | Vários itens do menu são telas em branco (equipe, filas e gargalos, insights, resultados, integrações...). |
| F5 | Escalonamento de prazo | Conflitos só são registrados e notificados; o motor de escalonamento é D1 (Regras 10 §57). |

## 4. Deploy

| # | Onde | Situação |
|---|---|---|
| P1 | `render.yaml` | O build não roda `seed_acoes`: em produção o catálogo de ações fica vazio e não dá para montar perfis de acesso. Adicionar `&& python manage.py seed_acoes` ao `buildCommand` (é idempotente). |
| P2 | `render.yaml` | Sem variáveis de e-mail: ver D2 e [12_DEPLOY_RENDER.md](12_DEPLOY_RENDER.md#3-e-mail-em-produção). |
| P3 | Plano free | Anexos se perdem a cada deploy; `check_overdue_tasks` não roda (sem cron nem Shell). |

## 5. Limpeza do repositório

| # | Item |
|---|---|
| L1 | `demands/`, `workflows/`, `templates/demands/`, `templates/workflows/`: restos de apps removidos (fora de `INSTALLED_APPS`, sem código). |
| L2 | `venv/`: ambiente virtual quebrado de outra máquina (aponta para `C:\Users\saulo\...\Python313`). Ignorado pelo Git, mas `.claude/launch.json` ainda usa `venv/Scripts/python.exe` — deveria ser `.venv`. |
| L3 | `tests/README.md` e o cabeçalho de `tests/checklist.test.cjs` mandam rodar "a partir da pasta `workflow`" (nome antigo); o certo é a raiz do repositório. |
| L4 | `Regras/12_...` e `Regras/13_...` têm "11 —" no título, inconsistente com o nome do arquivo. |
| L5 | Docstring de `ActivityAttachmentService` cita `MEDIA_ROOT`; o storage real é `ACTIVITY_FILES_ROOT`. |
| L6 | `Activity`, `Task` e `DeadlineConflict` ainda declaram `Meta.permissions` do Django (`can_change_owner` etc.), sem uso — a autorização é o motor do `acessos`. |
