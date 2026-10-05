# 08 — Notificações e auditoria

> O que cada evento gera: registro de auditoria (`audit.AuditLog`),
> notificação in-app (`notifications.Notification`) e e-mail. Regras de produto
> em `Regras/04_AUDITORIA_TEMPO_E_METRICAS.md` e
> `Regras/06_NOTIFICACOES_E_COMUNICACAO.md`. Atualizado em 03/10/2026 (commit
> `add5acd`): "atividade" é **Demanda** na interface (os identificadores
> seguem `ACTIVITY_*` / `activity`), e fila, processos, prazos e telas de tarefa
> foram desativados em 02/10 — ver "Quais eventos ainda são gerados" na seção 2.

---

## 1. Pontos de entrada

| Para | Use | Onde |
|---|---|---|
| Auditar | `AuditService.log(user=, action=, activity=, task=, target_user=, field_name=, old_value=, new_value=, reason=, target_type=, target_id=, metadata=)` | `audit/services.py` — único caminho de escrita; converte valores em texto. `target_type`/`target_id`/`metadata` servem aos eventos que não pertencem a uma demanda ou tarefa (quadros) |
| Notificar in-app | `NotificationService.notify(users=, event_type=, title=, message=, activity=, task=, url=, actor=)` | `notifications/services.py` — remove duplicados e grava em lote |
| Enviar e-mail | `EmailService.send_task_overdue`, `send_activity_approval_needed`, `send_client_information_request` | `notifications/services.py` — renderiza `templates/notifications/email/<nome>.txt`; falha de envio é logada e **não** interrompe o fluxo |
| Resolver destinatários | `resolve_sector_members`, `resolve_sector_managers`, `resolve_sector_and_admins` | `notifications/recipients.py` |

E-mails são **síncronos** (enviados durante a requisição) via
`django.core.mail`. Não há fila.

---

## 2. Evento → auditoria → notificação → e-mail

| Evento (serviço) | `AuditLog.Action` | `Notification.EventType` → destinatários | E-mail |
|---|---|---|---|
| Demanda criada/publicada | `CREATE` | `ACTIVITY_CREATED` → dono, criador | — |
| Campo da demanda editado (editor, lista inline, quadro de domínio) | `UPDATE` (um por campo) | menções, se a descrição mudou | — |
| Mudar etapa da demanda (Kanban, lista inline) | `UPDATE` com `field_name="etapa"` (nomes antes e depois, "Sem etapa" se vazio) | — | — |
| Mudar status (condição) da demanda | `UPDATE` com `field_name="status"` (nome do status; "Sem status") | — | — |
| Trocar o setor da demanda | `UPDATE` de setor **mais** o reinício de etapa e status do setor novo (três registros na mesma transação) | — | — |
| Primeira tarefa em andamento (`_mark_in_progress`) | `UPDATE` de `status` `ABERTA`→`EM_ANDAMENTO` | — | — |
| Troca de dono / assumir | `OWNER_CHANGED` | `OWNER_CHANGED` → antigo e novo dono | — |
| Finalizar como concluída | `COMPLETE` | `ACTIVITY_COMPLETED` → dono | — |
| Finalizar como cancelada | `CANCEL` | `ACTIVITY_CANCELLED` → dono | — |
| Reabrir | `REOPEN` | `ACTIVITY_REOPENED` → dono | — |
| Marcar pendente | `PENDENCY_OPENED` (+ `OWNER_CHANGED` se há aprovação) | `ACTIVITY_APPROVAL_NEEDED` → gestores do setor; `ACTIVITY_PENDING` → dono anterior (ou dono) | aprovação → gestores; pedido de informação → cliente, se marcado |
| Aprovar pendência | `PENDENCY_APPROVED` | `ACTIVITY_APPROVED` → dono | — |
| Resolver pendência sem aprovação (`ActivityService.resolve_pendency`; **sem rota**) | grava `AuditLog.Action.PENDENCY_RESOLVED`, que **não existe** no enum (levantaria `AttributeError`; doc 13) | `ACTIVITY_APPROVED` ("Pendência resolvida") → dono, se não foi ele | — |
| Anexo incluído/removido | `UPDATE` (campo "anexo") | — | — |
| Tarefa criada | `TASK_CREATED` | `TASK_ASSIGNED` → membros e gestores do setor | — |
| Tarefa editada (editor) | `UPDATE` (um por campo: título, descrição, prazo pedido e `tags`, com antes e depois); `RESPONSAVEL_CHANGED`, `EXECUTOR_ADDED/REMOVED` e `ASSIGNMENT_CREATED` quando o editor mexe em responsável e participantes | menções; `TASK_RESPONSAVEL_CHANGED`; `TASK_ASSIGNMENT_PENDING` → convidado | — |
| Mudar a dependência | `UPDATE` de `depends_on` (títulos antes e depois); `UPDATE` de `status` (`EM_FILA`→`DISPONIVEL`) se a tarefa passou a esperar; `TASK_RELEASED` se deixou de esperar | `TASK_ASSIGNED` (“Tarefa liberada para a fila”) quando é liberada | — |
| Assumir / aceitar atribuição | `EXECUTOR_ADDED` (+ `ASSIGNMENT_ACCEPTED`) | `TASK_ASSIGNED` → quem aceitou | — |
| Atribuir a outra pessoa | `ASSIGNMENT_CREATED` | `TASK_ASSIGNMENT_PENDING` → atribuído | — |
| Recusar atribuição | `ASSIGNMENT_REJECTED` | `TASK_ASSIGNMENT_REJECTED` → quem atribuiu | — |
| Remover participante | `EXECUTOR_REMOVED` | — | — |
| Trocar responsável | `RESPONSAVEL_CHANGED` | `TASK_RESPONSAVEL_CHANGED` → antigo e novo | — |
| Iniciar / retomar / tempo manual | `SESSION_STARTED` | — | — |
| Pausar | `SESSION_PAUSED` | — | — |
| Concluir tarefa | `COMPLETE` | `TASK_COMPLETED` → dono da atividade, responsável | — |
| “Já realizei este trabalho” | `RETROACTIVE_LOGGED` (`new_value` = período trabalhado; `reason` = “Informado em … · motivo · comentário”) e em seguida o `COMPLETE` normal; `TASK_RELEASED` nas sucessoras liberadas | `TASK_COMPLETED` → dono da atividade, responsável; `TASK_ASSIGNED` (“Tarefa liberada para a fila”) nas sucessoras | — |
| Cancelar tarefa | `CANCEL` | — | — |
| Reabrir tarefa concluída | `REOPEN` da tarefa (`old_value=CONCLUIDA`, `new_value=EM_FILA` ou `DISPONIVEL`, motivo); `REOPEN` da atividade junto, se ela estava concluída; `UPDATE` de `status` (`EM_FILA`→`DISPONIVEL`) em cada tarefa seguinte que voltou a esperar | `TASK_ASSIGNED` ("Tarefa reaberta") → setor, responsável e dono da atividade; `ACTIVITY_REOPENED` → dono, se a atividade reabriu junto | — |
| Bloquear / desbloquear | `BLOCK` / `UNBLOCK` | `TASK_BLOCKED` / `TASK_UNBLOCKED` → dono da atividade | — |
| Enviar a outro setor | `SECTOR_MOVED` | `TASK_ASSIGNED` → novo setor | — |
| Devolver | `RETURNED` (+ `SECTOR_MOVED`) | `TASK_RETURNED` → os dois setores, dono | — |
| Aplicar processo | `PROCESS_APPLIED` (`new_value` = "Processo vN"; `reason` = contagens) + um `TASK_CREATED` por etapa + `INPUT_UPDATED` por input já informado | `TASK_ASSIGNED` → setor e responsável de cada tarefa **que já nasceu na fila** (etapas que esperam não avisam); `PROCESS_APPLIED` → dono da atividade, se não foi quem aplicou | — |
| Etapa liberada (predecessora concluída) | `TASK_RELEASED` (`new_value` = setor da fila; `reason` = etapa que liberou) | `TASK_ASSIGNED` ("Tarefa liberada para a fila") → setor e responsável | — |
| Input do processo registrado/corrigido/reaberto | `INPUT_UPDATED` (`field_name` = nome do input; antes e depois: `não recebido` / `recebido: valor`) | — | — |
| Critério de aceite marcado/reaberto | `CRITERION_UPDATED` (`field_name` = critério; `pendente` ↔ `atendido`) | — | — |
| Reordenar fila | `QUEUE_POSITION_CHANGED` (por entrada afetada) | `QUEUE_POSITION_CHANGED` → dono da atividade | — |
| Propor prazo | `DEADLINE_PROPOSED` | `DEADLINE_PROPOSED` → dono | — |
| Aceitar prazo | `DEADLINE_ACCEPTED` | `DEADLINE_ACCEPTED` → quem propôs | — |
| Recusar prazo | `DEADLINE_REJECTED` + `CONFLICT_OPENED` | `DEADLINE_CONFLICT` → setor, dono | — |
| Resolver conflito | `CONFLICT_RESOLVED` | menções | — |
| Mensagem | — | `MESSAGE_POSTED` → envolvidos (menos autor e mencionados); `MENTIONED` → mencionados | — |
| Tarefa atrasada (`check_overdue_tasks`) | — | `TASK_OVERDUE` → setor, dono, responsável | sim |
| Segurança (`AccessService`, `UserFormView`) | `PROFILE_CREATED`, `PROFILE_UPDATED`, `PROFILE_ACTIONS_CHANGED`, `PROFILE_ASSIGNED`, `PROFILE_REVOKED`, `ACTION_GRANTED`, `ACTION_REVOKED`, `SECTORS_CHANGED`, `USER_CREATED`, `PASSWORD_RESET` (com `target_user`) | — | — |

"Membros e gestores do setor" vem de `resolve_sector_and_admins`, que, apesar
do nome, **não** inclui nenhum grupo de administradores.

**Por que eventos de auditoria novos e não `UPDATE` + `field_name`:** aplicar um
processo, liberar uma etapa, registrar um input e atender um critério são eventos
que as Regras (04 §178-214) pedem por nome e que a tela precisa ler como frases
("aplicou o processo Orçamento v3", "liberou a tarefa para a fila de Compras",
"marcou o critério “Escopo revisado” como atendido"). Com `UPDATE` o histórico diria
"alterou um campo". As frases estão em `activities/templatetags/lps.py`.

Ao **finalizar como “Concluído com pendências”** com critérios obrigatórios em
aberto, o `reason` do `COMPLETE` e a mensagem "Finalização (…)" na conversa da
atividade listam os critérios que ficaram de fora.

### Quais eventos ainda são gerados (desde 02/10/2026)

A tabela acima descreve o que cada **serviço** grava. Parte dos serviços ficou
sem tela: `/fila/`, `/processos/…`, `/prazos/…`, `/conflitos/…` e `/tarefas/<pk>/…`
respondem 410, e a migração `boards/0008` cancelou as `Task` operacionais (as
tarefas agora são itens de quadro, auditados como `BOARD_*`, abaixo).

| Situação | Eventos |
|---|---|
| **Gerados hoje** | Todos os de **Demanda** (criação, edição, dono, etapa/status, concluir, cancelar, reabrir, pendência, aprovação, anexo), mensagens e menções, **segurança** (`PROFILE_*`, `ACTION_*`, `SECTORS_CHANGED`, `USER_CREATED`, `PASSWORD_RESET`) e **quadros** (`BOARD_*`). |
| **Sem tela (dormentes)** | `TASK_*`, `EXECUTOR_*`, `ASSIGNMENT_*`, `RESPONSAVEL_CHANGED`, `SESSION_*`, `RETROACTIVE_LOGGED`, `BLOCK`/`UNBLOCK`, `SECTOR_MOVED`, `RETURNED`, `QUEUE_POSITION_CHANGED`, `DEADLINE_*`, `CONFLICT_*`, `PROCESS_APPLIED`, `INPUT_UPDATED`, `CRITERION_UPDATED`, `TASK_RELEASED` e as notificações correspondentes. Os serviços e as frases do histórico continuam no código; o histórico antigo continua legível. |
| **Em teoria ainda roda** | `check_overdue_tasks` (`TaskService.mark_overdue_tasks`, `TASK_OVERDUE` + e-mail): olha só `Task`, e as operacionais foram canceladas — na prática não notifica mais nada. |

### Não auditado

Checklist, CRUD de cadastros, cores configuráveis, criação/edição de etapas e
status do setor e o limite de cartões por coluna do Kanban (doc 13, F30),
criação/publicação/versão de processo e alteração do responsável padrão de
uma etapa (o **molde**), autocadastro e confirmação de e-mail, troca de senha
pelo próprio usuário. (A mudança de etapa/status **de uma demanda** é auditada,
inclusive pelo Kanban; antes de 02/10 o movimento de card não era.)

`AuditLog.Action.SESSION_RESUMED` existe mas nunca é gravado (`resume` delega
para `start`, que grava `SESSION_STARTED`; só a frase do histórico a conhece).
`AuditLog.Action.PENDENCY_RESOLVED`, ao contrário, é **usado e não existe**
(ver a linha "Resolver pendência" acima).

Os valores de `Notification.EventType` e `AuditLog.Action` são os do código
(`notifications/models.py`, `audit/models.py`): 25 tipos de notificação e 63
ações de auditoria, das quais 20 são de quadros e 10 de segurança. Nenhum tipo
de notificação é gerado pelos quadros nem pela Caixa de Entrada.

**Caixa de Entrada (`intake`) — inativa por padrão (`INTAKE_ENABLED=false`, rotas em 404).** Registrar, corrigir sugestões, ignorar, restaurar e converter
uma solicitação **não** geram `AuditLog` nem `Notification`: a trilha é o `IntakeEvent` da
própria solicitação (`AuditLog` só liga a atividade/tarefa, e a solicitação ainda não é
nenhuma das duas). Converter chama `ActivityService`, então a atividade criada tem os efeitos
de sempre: `CREATE` e `ACTIVITY_CREATED` (dono e criador). O texto da solicitação vai para a
descrição com as `@menções` neutralizadas, para um e-mail recebido de fora não notificar
ninguém da equipe. O aviso de item novo é só o contador do menu (doc 13, F23).

**Quadros (`boards`).** Toda alteração do quadro grava `AuditLog` (sem `Notification`, sem e-mail), pelo mesmo
`AuditService.log`, que agora aceita `target_type`, `target_id` e `metadata` (as colunas `activity`/`task` ficam vazias, porque
o alvo não é atividade nem tarefa). Todo registro leva `metadata["board_id"]`; o histórico do quadro é
`AuditLog.objects.filter(metadata__board_id=...)`.

| Evento | `AuditLog.Action` | `target_type` | Campos |
|---|---|---|---|
| Criar / renomear / excluir quadro | `BOARD_CREATED` / `BOARD_UPDATED` / `BOARD_DELETED` | `board` | `field_name`, `old/new_value` |
| Criar / editar / mover / excluir grupo | `BOARD_GROUP_CREATED` / `_UPDATED` / `_MOVED` / `_DELETED` | `board_group` | idem |
| Criar / renomear ou configurar / excluir visualização (Kanban) | `BOARD_VIEW_CREATED` / `_UPDATED` / `_DELETED` | `board_view` | `field_name` = `name` ou a chave da configuração (`group_by`, `card_fields`...), `old/new_value`; um registro por chave que mudou |
| Criar (ou duplicar) / editar / mover / redimensionar / excluir coluna | `BOARD_COLUMN_CREATED` / `_UPDATED` / `_MOVED` / `_RESIZED` / `_DELETED` | `board_column` | idem; troca de tipo grava `type` e `cleared_values` em `metadata`; etiquetas gravam `etiqueta*` e `option_id` |
| Criar / renomear / mover / excluir item | `BOARD_ITEM_CREATED` / `_UPDATED` / `_MOVED` / `_DELETED` | `board_item` | idem |
| Preencher célula | `BOARD_CELL_UPDATED` | `board_cell` | `field_name` = nome da coluna, `old/new_value` = o texto que a tela mostra; `metadata` com `item_id` e `column_id`. **Só quando o valor muda** |

Criar quadro a partir de um modelo grava também `metadata["template"]`.

**Quadros de Demanda** (`boards/demand_services.py`): criar o quadro que acompanha uma Demanda grava `BOARD_CREATED`
com `metadata["activity_id"]`; **trocar o quadro** na edição da demanda grava `BOARD_UPDATED` (`field_name="quadro de tarefas"`,
`metadata` com `activity_id`, `items_deleted` e `replaced`). Os itens/células de uma "tarefa" saem como `BOARD_ITEM_*` e
`BOARD_CELL_UPDATED`, como em qualquer quadro, sem `AuditLog.task`. Os quadros de domínio (lista de Demandas) gravam campos
configuráveis como `UPDATE` com `field_name="quadro:<chave>"` ligado à demanda ou tarefa. O histórico do quadro está em
`/quadros/<pk>/historico/` e **não** aparece no Histórico geral (`/historico/` só mostra registros com demanda).

---

## 3. Onde aparece

- **Histórico** (`/historico/`, `HistoryView`): `AuditLog` ligados a
  demandas da organização, com filtro `?event=` (tarefas, prazos, fila,
  devolucoes, tempo; as abas Fila, Devoluções e Tempo hoje só encontram
  histórico antigo — doc 13). Sem verificação de `auditoria.visualizar`.
  Eventos de segurança e de quadro, sem demanda, **não** aparecem ali.
  O texto de cada linha vem do filtro `{{ entry|audit_phrase }}`
  (`activities/templatetags/lps.py`).
- **Linha do tempo** da atividade/tarefa (`templates/activities/_timeline.html`):
  mesma fonte, filtrada pelo objeto.
- **Caixa de notificações** (`/notificacoes/`, `NotificationListView`):
  - abas `?filter=`: `para-mim` (padrão; o alias antigo `acao` continua valendo), `nao-lidas`, `mencoes`,
    `prazos` (propostas, aceite, recusa, conflito e atraso), `sistema` (os eventos informativos) e `todas`;
    `alertas` segue aceito na URL mas não tem aba; busca `q`, ordenação `ordem` (`recentes`/`antigas`),
    30 por página;
  - cada evento é classificado em uma de seis categorias (`EVENT_CATEGORY`):
    delegação, prazo, menção, alerta, conclusão, informativo;
  - a aba **Ação necessária** reconsulta o estado atual
    (`_still_needs_action`): some da lista quando a proposta de prazo foi
    decidida, o conflito resolvido, o bloqueio encerrado, a atribuição
    respondida etc.;
  - abrir uma notificação (`<pk>/read/`, com `mode=open|read`) marca como lida e só redireciona para
    destinos internos validados. Notificação ligada a uma **tarefa** ainda leva a `/tarefas/<pk>/…` e a de
    conflito a `/conflitos/<pk>/resolver/` (ambos 410); as de demanda abrem `/demandas/<pk>/` (doc 13).
  - `markall` (`mark-all-read/`) marca todas as da pessoa como lidas.
- **Contador** do sino: context processor `unread_notifications_count`.

---

## 4. E-mail e configuração

| Setting / env | Padrão | Efeito |
|---|---|---|
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS` | vazio, 587, vazio, vazio, `true` | Servidor SMTP. |
| `DEFAULT_FROM_EMAIL` | `no-reply@example.com` | Remetente de todos os e-mails do sistema. |
| `EMAIL_BACKEND` | dev: console · prod: SMTP | Em dev os e-mails saem no terminal. |
| `ADMIN_GROUP_NAME` | `ADMIN` | Lida em `config/settings/base.py` e não usada (doc 13, F2). |

E-mails que o sistema envia (templates `templates/notifications/email/*.txt`, `EmailService`):
`task_overdue` (tarefa atrasada; dormente, ver acima), `activity_approval_needed` (pendência aguardando aprovação, para os
gestores do setor) e `activity_client_information_request` (pedido de informação ao cliente, só se marcado no pop-up de pendência e
se o cliente tem e-mail). O e-mail de **confirmação de cadastro** (`accounts/views.py`) usa `send_mail` direto, sem
`EmailService`. Não há preferência de notificação por usuário: todo destinatário recebe todo evento previsto.
