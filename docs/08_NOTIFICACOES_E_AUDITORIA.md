# 08 — Notificações e auditoria

> O que cada evento gera: registro de auditoria (`audit.AuditLog`),
> notificação in-app (`notifications.Notification`) e e-mail. Regras de produto
> em `Regras/04_AUDITORIA_TEMPO_E_METRICAS.md` e
> `Regras/06_NOTIFICACOES_E_COMUNICACAO.md`.

---

## 1. Pontos de entrada

| Para | Use | Onde |
|---|---|---|
| Auditar | `AuditService.log(user=, action=, activity=, task=, target_user=, field_name=, old_value=, new_value=, reason=)` | `audit/services.py` — único caminho de escrita; converte valores em texto |
| Notificar in-app | `NotificationService.notify(users=, event_type=, title=, message=, activity=, task=, url=, actor=)` | `notifications/services.py` — remove duplicados e grava em lote |
| Enviar e-mail | `EmailService.send_task_overdue`, `send_activity_approval_needed`, `send_client_information_request` | `notifications/services.py` — renderiza `templates/notifications/email/<nome>.txt`; falha de envio é logada e **não** interrompe o fluxo |
| Resolver destinatários | `resolve_sector_members`, `resolve_sector_managers`, `resolve_sector_and_admins` | `notifications/recipients.py` |

E-mails são **síncronos** (enviados durante a requisição) via
`django.core.mail`. Não há fila.

---

## 2. Evento → auditoria → notificação → e-mail

| Evento (serviço) | `AuditLog.Action` | `Notification.EventType` → destinatários | E-mail |
|---|---|---|---|
| Atividade criada/publicada | `CREATE` | `ACTIVITY_CREATED` → dono, criador | — |
| Campo de atividade editado | `UPDATE` (um por campo) | menções, se a descrição mudou | — |
| Troca de dono / assumir | `OWNER_CHANGED` | `OWNER_CHANGED` → antigo e novo dono | — |
| Finalizar como concluída | `COMPLETE` | `ACTIVITY_COMPLETED` → dono | — |
| Finalizar como cancelada | `CANCEL` | `ACTIVITY_CANCELLED` → dono | — |
| Reabrir | `REOPEN` | `ACTIVITY_REOPENED` → dono | — |
| Marcar pendente | `PENDENCY_OPENED` (+ `OWNER_CHANGED` se há aprovação) | `ACTIVITY_APPROVAL_NEEDED` → gestores do setor; `ACTIVITY_PENDING` → dono anterior (ou dono) | aprovação → gestores; pedido de informação → cliente, se marcado |
| Aprovar pendência | `PENDENCY_APPROVED` | `ACTIVITY_APPROVED` → dono | — |
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

### Não auditado

Movimento de card no Kanban (atividade e tarefa), checklist, CRUD de
cadastros, cores e status configuráveis, criação/publicação/versão de
processo e alteração do responsável padrão de uma etapa (o **molde**;
a *aplicação* do processo e a execução de inputs/critérios são auditadas),
autocadastro e confirmação de e-mail, troca de senha pelo próprio
usuário.

`AuditLog.Action.SESSION_RESUMED` existe mas nunca é gravado (`resume` delega
para `start`, que grava `SESSION_STARTED`).

---

## 3. Onde aparece

- **Histórico** (`/historico/`, `HistoryView`): `AuditLog` ligados a
  atividades da organização, com filtro `?event=` (tarefas, prazos, fila,
  devolucoes, tempo). Eventos de segurança sem atividade **não** aparecem ali.
  O texto de cada linha vem do filtro `{{ entry|audit_phrase }}`
  (`activities/templatetags/lps.py`).
- **Linha do tempo** da atividade/tarefa (`templates/activities/_timeline.html`):
  mesma fonte, filtrada pelo objeto.
- **Caixa de notificações** (`/notificacoes/`, `NotificationListView`):
  - abas `?filter=`: `acao` (padrão), `nao-lidas`, `mencoes`, `alertas`, `todas`;
    busca `q`, ordenação `ordem`, 30 por página;
  - cada evento é classificado em uma categoria (delegação, prazo, menção,
    alerta, conclusão, informativo);
  - a aba **Ação necessária** reconsulta o estado atual
    (`_still_needs_action`): some da lista quando a proposta de prazo foi
    decidida, o conflito resolvido, o bloqueio encerrado, a atribuição
    respondida etc.;
  - abrir uma notificação (`<pk>/read/`) marca como lida e só redireciona para
    destinos internos validados.
- **Contador** do sino: context processor `unread_notifications_count`.
