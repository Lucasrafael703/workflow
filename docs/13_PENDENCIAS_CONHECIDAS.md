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
| S3 | Média | `acessos/catalog.py` × views | Outras ações sem verificação: `usuario.criar` (só decide se o botão "criar pessoa" aparece; `/usuarios/novo/` exige `usuario.editar`), `usuario.inativar`, `setor.criar`. (`processo.aplicar` passou a ser verificada em `ProcessApplicationService.apply`.) |
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

## 3. Funcionalidades incompletas

| # | Onde | Situação |
|---|---|---|
| F2 | `notifications/recipients.py`, `ADMIN_GROUP_NAME` | A setting é lida mas não usada; `resolve_sector_and_admins` devolve só membros e gestores do setor. O help de `check_overdue_tasks` ainda fala em "administradores". |
| F3 | Autocadastro | Conta criada em "Criar conta" nunca recebe organização pelo app; é preciso o Admin do Django. A tela `/usuarios/` só lista quem já está na organização. |
| F4 | `painel/` | Vários itens do menu são telas em branco (equipe, filas e gargalos, insights, resultados, integrações...). |
| F5 | Escalonamento de prazo | Conflitos só são registrados e notificados; o motor de escalonamento é D1 (Regras 10 §57). |
| F6 | Processo aplicado — inputs `ARQUIVO` e `SELECAO` | O modelo não tem onde guardar o conteúdo com segurança: não há vínculo entre `ActivityInputValue` e `ActivityAttachment` (Regras 08:1280 pede que o valor referencie o mecanismo de anexos) nem lista de opções em `ProcessInput`. Hoje só se registra a confirmação de recebimento e uma observação livre. Solução: FK opcional de `ActivityInputValue` para `ActivityAttachment` (dentro de `activities`, sem ciclo de models) e `options` em `ProcessInput`. |
| F7 | Processo aplicado — evidência do output | A entrega esperada e o tipo de evidência (`ARQUIVO`/`LINK`/`CHECKLIST`/`CONFIRMACAO`) aparecem na ficha, mas não há onde registrar a evidência (Regras 08:1298 prevê `atividade_outputs` 1:1). A conclusão não confere "output registrado" (Regras 12 §32), só os critérios obrigatórios. |
| F8 | Processo aplicado — etapa cuja predecessora foi cancelada | Só `CONCLUIDA` libera a sucessora (decisão consciente; as Regras não definem o caso). Se a predecessora é cancelada, a sucessora fica `DISPONIVEL` fora da fila até alguém remover a dependência em "Editar tarefa" ou cancelá-la; não há aviso automático ao dono. |
| F9 | Processo aplicado — `Activity.company` | Nas Regras a empresa da atividade é obrigatória (08:1204); no código é opcional. Atividade sem empresa não recebe processo (a tela explica). Tornar a empresa obrigatória ao publicar o rascunho resolveria. |
| F10 | Processo aplicado — momento da aplicação | As Regras se contradizem: "ao criar a atividade" (02:1313, 08:2583) × "aplicar em uma atividade" (05:990, 10:309). Foi implementado o segundo (botão na ficha). O editor de "Nova atividade" ainda não oferece o processo. |
| F11 | Reabertura | Só tarefa e atividade **concluídas** reabrem; cancelada não (as Regras não definem). Ao reabrir a atividade, `completion_outcome` continua com o valor antigo (ex.: `SUCESSO`) até a próxima finalização. Tarefas seguintes que voltam a esperar por causa de uma reabertura só ficam na auditoria — os responsáveis delas não são avisados. |
| F12 | Reabertura — permissões em organizações já implantadas | `seed_acoes` cria `tarefa.reabrir` mas não a acrescenta a perfis existentes; é preciso marcá-la em `/permissoes/` (doc 05 §6). `atividade.reabrir` continua só no Administrador. |
| F13 | “Já realizei este trabalho” — trabalho anterior à criação da tarefa | O fim informado não pode ser anterior à criação da tarefa (a mensagem explica). Quem fez o trabalho antes de a tarefa existir não consegue registrá-lo assim; se isso atrapalhar na prática, a trava pode ser relaxada. Por desenho, `first_action_at`, a saída da fila e o tempo de espera na fila usam o momento do registro, não o trabalho informado. |
| F14 | Tempo informado — correção | O cartão da tarefa separa cronometrado × informado e a gestão mostra a origem das horas por motivo (F17), mas não há política de correção de um período já registrado (Regras 04 §114). |
| F15 | Editor da tarefa — prazo pedido | O prazo pedido pelo solicitante é editável por quem tem `tarefa.editar` (hoje o Gestor de Setor; o Colaborador não tem). Restringi-lo ao dono da atividade / `atividade.editar` evitaria que a própria equipe mexa no prazo contra o qual é medida (Regras 04 §64), mas tiraria do gestor do setor a correção de um erro de digitação. Decisão de produto em aberto. |
| F16 | Convites de participante | Um convite pendente (`TaskAssignment`) não pode ser cancelado por quem convidou — só aceito ou recusado pela pessoa convidada. O editor mostra o convite como “aguardando aceite” e não o duplica. |
| F17 | Origem do tempo — alcance | O quadro “Origem do tempo registrado” da gestão segue os filtros da tela (período da atividade, cliente, responsável...), como os demais indicadores, e conta só sessões encerradas. Não há ainda tela de auditoria do tempo informado por pessoa nem correção de um período já registrado (Regras 04 §114). |
| F18 | Editor de atividade — campos que saíram | A janela de 3 etapas não tem marcadores, solicitante interno (`requested_by`), anotações internas (`internal_notes`) nem envio de arquivos. Os dados antigos continuam no banco e na ficha, mas não há mais onde **editar** marcadores e anotações internas de uma atividade. Se isso fizer falta, o caminho é um bloco opcional na etapa 2 ou 3. |
| F19 | Editor de atividade — “Organização” | O campo “Organização” grava `Activity.company` (cadastro de empresas). Se a intenção era outra coisa (ex.: um agrupamento parecido com setor), o rótulo e a origem dos dados precisam ser revistos. |
| F20 | Editor de atividade — limite do texto | O contador “0/2000” das observações é só orientação: não há corte nem erro acima de 2000 caracteres (descrições antigas maiores continuam editáveis). |
| F21 | Cliente → Obra → Centro de custo | Obra sem cliente e centro de custo sem obra valem para qualquer escolha no servidor; na busca, ao escolher um cliente somem as obras sem cliente. Não há cadastro que force o vínculo. |

## 4. Deploy

| # | Onde | Situação |
|---|---|---|
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
