# 09 — Rotas

> Referência de todas as URLs. A coluna "Ação" indica a ação do catálogo
> verificada **na view** (`ActionRequiredMixin` ou `dispatch`); em
> `activities`, a maioria das verificações acontece dentro do serviço chamado —
> ver [06_ATIVIDADES_E_TAREFAS.md](06_ATIVIDADES_E_TAREFAS.md). Toda view da LPS
> exige login e organização (`OrganizationRequiredMixin`), exceto login,
> cadastro, confirmação de e-mail e recuperação de senha.
>
> **Atualizado em 03/10/2026**, sobre o commit `add5acd`. Em 02/10/2026 as
> tarefas operacionais (`Task`), a fila, o prazo negociado, o cronômetro e os
> processos foram **desativados**: as rotas continuam declaradas para links e
> favoritos antigos, mas respondem **410 Gone** (texto simples). As tarefas
> passaram a ser itens do Quadro de cada Demanda (`/quadros/…`).

## Legenda e totais

- **410** — rota desativada: a view devolve `410 Gone` e não executa nada
  (`RetiredFeatureView` em `activities/views.py`, `RetiredProcessView` em
  `processes/views.py`, `MovedActivityFileView` em `core/legacy_redirects.py`).
  **Sombreada** — o padrão segue declarado, mas um `re_path` de captura declarado
  antes (`^tarefas/.+$`, `^checklist/.+$`, `^prazos/.+$`, `^conflitos/.+$`,
  `^fila(?:/.*)?$`, `^.*$` em `processes`) responde primeiro: a view original não é
  mais alcançada.
- **301 / 308** — redireciona para o endereço novo (308 em POST, que mantém o método).
- **404** — Caixa de Entrada inativa (`INTAKE_ENABLED` desligado) ou objeto de outra organização.
- **Total: 247 padrões** `path()`/`re_path()` (fora 9 `include`), distribuídos assim:

| Arquivo | Padrões | Observação |
|---|---|---|
| `config/urls.py` | 9 | + 8 `include` (`accounts`, `notificacoes`, `processos`, `painel`, `entrada`, `quadros`, `core`, `activities`) |
| `accounts/urls.py` | 5 | |
| `core/urls.py` | 52 | |
| `activities/urls.py` | 90 | + 1 `include` (`kanban_urls`); **50** respondem 410 (11 diretas + 39 sombreadas) |
| `activities/kanban_urls.py` | 7 | |
| `boards/urls.py` | 41 | 36 `board-*` + 5 `workboard-*` |
| `intake/urls.py` | 7 | 404 se a caixa está inativa |
| `notifications/urls.py` | 3 | |
| `painel/urls.py` | 16 | |
| `processes/urls.py` | 17 | **todas** respondem 410 |

Contando `legacy-activity-files` (410), **68 padrões** estão desativados (17 + 50 + 1).

---

## 1. Raiz (`config/urls.py`)

| Caminho | Nome | Destino |
|---|---|---|
| `admin/` | — | Admin do Django |
| `accounts/login/` | `login` | `LoginView` + `EmailAuthenticationForm` |
| `accounts/logout/` | `logout` | `LogoutView` |
| `accounts/esqueci-senha/`, `.../enviado/` | `password_reset`, `password_reset_done` | views nativas |
| `accounts/redefinir-senha/<uidb64>/<token>/`, `.../concluido/` | `password_reset_confirm`, `password_reset_complete` | views nativas |
| `accounts/` | | `accounts.urls` |
| `notificacoes/` | | `notifications.urls` |
| `processos/` | | `processes.urls` — **tudo responde 410** (seção 5) |
| `painel/` | | `painel.urls` |
| `entrada/` | | `intake.urls` (só com `INTAKE_ENABLED`; desligado, 404 em todas as rotas) |
| `quadros/` | | `boards.urls` (seção 6.2) |
| `` | | `core.urls`, depois `activities.urls` |
| `atividade-arquivos/<path>` | `legacy-activity-files` | **410** (`MovedActivityFileView`): "Este link de arquivo expirou. Abra a demanda para baixar o anexo com segurança." Antes de 02/10/2026 redirecionava para `demanda-arquivos/`; hoje o anexo só sai por `demandas/<pk>/anexos/<attachment_pk>/download/` (seção 4) |
| `media/<path>` | | `static.serve` de `MEDIA_ROOT`, **só com `DEBUG`** (sem login) |

Não existe rota para `ACTIVITY_FILES_URL` (`/demanda-arquivos/`): os anexos ficam em
`ACTIVITY_FILES_ROOT` e são entregues pela view de download, que confere login,
organização e acesso à demanda.

## 2. `accounts` (`/accounts/`)

| Caminho | Nome | Função |
|---|---|---|
| `me/` | `profile` | Meu perfil (telefone, setor principal) |
| `criar-conta/` | `signup` | Autocadastro |
| `confirmar-email/` | `verify-email` | Digitar o código |
| `confirmar-email/reenviar/` | `verify-email-resend` | Reenviar código (POST) |
| `confirmar-email/alterar/` | `verify-email-change` | Trocar o e-mail pendente |

## 3. `core` (`/`)

**APIs de busca** (JSON, filtradas pela organização, só login e organização): `api/pessoas/`
(`person-search`, aceita `?sector=`), `api/clientes/` (`client-search`),
`api/setores/` (`sector-search`), `api/empresas/` (`company-search`),
`api/obras/` (`site-search`, aceita `?client=`), `api/centros-de-custo/` (`costcenter-search`, aceita `?site=`),
`api/tags/` (`tag-search`) e as **opções do fluxo de um setor**:
`api/setores/<sector_pk>/etapas/` (`sector-stage-options`) e
`api/setores/<sector_pk>/condicoes/` (`sector-condition-options`) — GET com
`?dominio=demanda|tarefa` obrigatório (outro valor: 400) devolvem
`{sector, items: [{id, name, color, is_default}]}` das etapas/status ativos do setor, para os seletores
do editor de Demanda e dos quadros.

**Cadastros** — os nomes de rota seguem `<recurso>-create` / `<recurso>-edit` (`sector`, `company`, `site`, `costcenter`, `client`, `returnreason`, `taskstage`, `tag`; `profile` em `perfis/…`):

| Caminho | View | Ação |
|---|---|---|
| `cadastros/` (`?tab=`) | `CadastroHomeView` (`cadastros`) | — |
| `cadastros/setores/novo/`, `<pk>/` | `SectorFormView` | `setor.editar` |
| `cadastros/empresas/nova/`, `<pk>/` | `CompanyFormView` | `empresa.gerir` |
| `cadastros/obras/nova/`, `<pk>/` | `SiteFormView` | `obra.gerir` |
| `cadastros/centros-de-custo/novo/`, `<pk>/` | `CostCenterFormView` | `centro_custo.gerir` |
| `cadastros/clientes/novo/`, `<pk>/` | `ClientFormView` (também em popup) | `cliente.gerir` |
| `cadastros/motivos/novo/`, `<pk>/` | `ReturnReasonFormView` | `motivo_devolucao.gerir` |
| `cadastros/estagios-de-tarefa/novo/`, `<pk>/` | `TaskStageFormView` | `etapa.gerir` |
| `cadastros/estagios-de-tarefa/reordenar/` | `TaskStageReorderView` (`taskstage-reorder`) | `etapa.gerir` |
| `cadastros/tags/novo/`, `<pk>/` | `TagFormView` | `tag.gerir` |
| `cadastros/<tab>/<pk>/situacao/` | `CadastroToggleActiveView` (`cadastro-toggle`) | por aba: `setor.inativar` (setores), `empresa.gerir`, `obra.gerir`, `centro_custo.gerir`, `cliente.gerir`, `motivo_devolucao.gerir` (motivos), `etapa.gerir` (estagios-de-demanda / estagios-de-tarefa), `condicao.gerir` (status-configuravel), `tag.gerir` |
| `cadastros/<tab>/<pk>/cor/` | `SwatchColorSaveView` (`cadastro-color-save`) | `tag.gerir` (tags) ou `etapa.gerir` (estagios-de-demanda, estagios-de-tarefa); outra aba: 404 |

**Configurações**

| Caminho | View | Ação |
|---|---|---|
| `configuracoes/` | `SettingsView` (`settings`) — preferências de notificação (guardadas na sessão) | — |
| `configuracoes/estagios-de-demanda/novo/`, `<pk>/` | `ActivityStageFormView` (`activitystage-create`, `activitystage-edit`) | `etapa.gerir` (no setor da etapa) |
| `configuracoes/estagios-de-atividade/<resto>` | `legacy-activity-stages` | Endereço antigo: redireciona (301; 308 em POST) para `estagios-de-demanda/<resto>` |
| `configuracoes/status/<domain>/novo/`, `<pk>/` | `WorkflowStatusFormView` (`workflowstatus-create`, `workflowstatus-edit`); `domain` = `activity` ou `task` (outro: 404) | `condicao.gerir` (no setor do status) |
| `configuracoes/status/<domain>/<code>/editar/` | `EnumColorLabelFormView` (`enumcolor-label-edit`); `domain` = `activity_status` ou `task_status` (outro, ou `code` desconhecido: 404) — nome, descrição e visibilidade de um status nativo (`Activity.Status`/`Task.Status`; o `code` não muda) | `cor_status.gerir` |
| `configuracoes/cores/<domain>/salvar/` | `EnumColorSaveView` (`enumcolor-save`) | `cor_status.gerir` (`activity_status`, `task_status`) ou `cor_prioridade.gerir` (`activity_urgency`, `task_priority`) |
| `configuracoes/cores/<domain>/restaurar/` | `EnumColorResetView` (`enumcolor-reset`) | a mesma de `salvar/`, por domínio |
| `configuracoes/fluxo/<kind>/<pk>/excluir/` | `FlowConfigDeleteView` (`flow-config-delete`) | `etapa.gerir` (`kind` = `activity-stage`, `task-stage`) ou `condicao.gerir` (`workflow-status`); outro `kind`: 404 |
| `configuracoes/fluxo/<kind>/<pk>/situacao/` | `FlowConfigToggleActiveView` (`flow-config-toggle`) | ativa/inativa a opção sem apagar o histórico; mesma ação por `kind` |
| `configuracoes/fluxo/<kind>/reordenar/` | `FlowConfigReorderView` (`flow-config-reorder`) | POST `item_id` (lista na ordem final): persiste a ordem; mesma ação por `kind` |

**Usuários e segurança**

| Caminho | View | Ação |
|---|---|---|
| `usuarios/` | `UserListView` (`user-list`) | `usuario.visualizar` |
| `usuarios/novo/`, `<pk>/` | `UserFormView` (`user-create`, `user-edit`) | `usuario.editar` |
| `usuarios/<pk>/acessos/` | `UserAccessView` (`user-access`) | `seguranca.gerir_autorizacoes` |
| `usuarios/<pk>/acessos/<assignment_pk>/remover/` | `UserAccessRemoveView` (`user-access-remove`) | `seguranca.gerir_autorizacoes` |
| `usuarios/<pk>/concessoes/` | `UserGrantActionView` (`user-grant`) | `seguranca.gerir_autorizacoes` |
| `usuarios/<pk>/concessoes/<grant_pk>/remover/` | `UserGrantRemoveView` (`user-grant-remove`) | `seguranca.gerir_autorizacoes` |
| `permissoes/` | `PermissionMatrixView` (`permissions`) | `seguranca.gerir_perfis` |
| `permissoes/<pk>/salvar/` | `PermissionUpdateView` (`permissions-update`) | `seguranca.gerir_autorizacoes` |
| `perfis/novo/`, `<pk>/` | `ProfileFormView` | `seguranca.gerir_perfis` |

## 4. `activities` (`/`)

Padrões em `activities/urls.py` (90) e `activities/kanban_urls.py` (7, via `include` no fim). A **ordem
importa**: os `re_path` de captura de rotas desativadas vêm antes das rotas antigas e as sombreiam (ver
a legenda). Nomes de rota (`activity-*`) seguem em inglês; o endereço é `/demandas/…` desde 01/10/2026.

**Início e visões gerais**

| Caminho | Nome | Função |
|---|---|---|
| `` | `home` | "O que precisa da minha atenção agora?" |
| `fila/`, `fila/<sector_pk>/`, `fila/entrada/<pk>/reordenar/` | `queue-legacy-retired` (captura `^fila(?:/.*)?$`); sombreadas: `queue`, `queue-sector`, `queue-reorder` | **410** — a Fila foi desativada em 02/10/2026 |
| `gestao/` | `management` | Gestão por exceção (`metricas.visualizar` em algum escopo; 403 sem ela). Os blocos de fila e tarefas leem `Task`/`QueueEntry` históricos |
| `historico/` | `history` | Histórico de auditoria (`?event=`) |

**Demandas** (`Activity`; o endereço era `demandas/…` até 01/10/2026)

| Caminho | Função |
|---|---|
| `atividades/<resto>` (`legacy-activities`) | Redireciona (301; **308** em POST, que mantém o método) para `demandas/<resto>`, com a consulta (`?tab=…`). Sem login. Cobre todas as rotas abaixo |
| `demandas/` (`activity-list`) | **Superfície operacional de Demandas** (`boards/work_views.py::DemandWorkBoardView`, sobre o quadro de domínio): visão **Lista**. Abas `?tab=` `minhas` (padrão) \| `grupo` \| `participando` \| `concluidas` \| `todas` (esta só com `demanda.visualizar_todas`). Filtros: `q` (título, cliente, obra; a busca por código aceita o antigo `ATV-2026-00007` para achar `DEM-2026-00007`), `setor` (aliases `sector`, `grupo`), `pessoa` (alias `responsavel`), `estagio`, `condicao`, `cliente`, `obra`, `tag`, `prazo` (`atrasadas`, `hoje`, `7_dias`, `30_dias`, `sem_prazo`), `filtro`, `ordem`/`sort` (`prazo`, `recentes`, `titulo`) e `dir`; `?visao=`/`?view=` escolhe a visão salva. Valor inválido é ignorado. Só mostra demandas com `demanda.visualizar` |
| `demandas/lista-legada/` (`activity-list-legacy`) | Lista anterior (`ActivityListView`), mantida por compatibilidade |
| `demandas/nova/` (`activity-create`) | Janela de 4 etapas de criação (1 Informações principais, 2 Cliente e obra, 3 **Quadro de tarefas** — `board_setup_mode` `BLANK` \| `TEMPLATE` + `board_template` —, 4 Descrição e arquivos) e rascunho antigo; exige `demanda.criar` em algum escopo (403 sem ela). JSON no Ajax: `{redirect_url}` ou `400 {errors}` |
| `demandas/<pk>/nova/contexto/` (`activity-wizard-contexto`), `.../detalhes/` (`activity-wizard-detalhes`), `.../descartar/` (`activity-wizard-discard`) | GET das etapas antigas redireciona ao editor; POST legado compatível; descartar rascunho |
| `demandas/nova-rapida/` (`activity-mini-create`) | Mesmo editor no seletor de Demanda; resposta JSON em Ajax (`{id, name, summary}`) |
| `demandas/busca/` (`activity-search`) | Busca de demandas abertas por título ou código (JSON `{results: [{id, name, summary}]}`, até 20), para o seletor de Demanda |
| `demandas/kanban/` (`activity-kanban`), `demandas/calendario/` (`activity-calendar`) | Mesma superfície (`DemandWorkBoardView`) com a visão forçada: **Quadro por etapas** (Kanban do quadro de domínio, raias pelo campo de agrupamento, padrão Etapa) e **Calendário de prazos** (pelo prazo solicitado). Mesmos filtros e abas de `demandas/`. Gravar um campo vem de `quadros/dominio/…/valor/` (seção 6.2) |
| `demandas/kanban-legado/` (`activity-kanban-legacy`) | Kanban por **setor** anterior (`activities/kanban.py::ActivityKanbanView`, `?setor=`), mantido por compatibilidade; usa as ações `kanban/…` abaixo |
| `demandas/<pk>/` (`activity-detail`) | Ficha da atividade (rascunho redireciona ao editor) |
| `demandas/<pk>/painel/` (`activity-drawer`) | Compatibilidade: redireciona à ficha completa |
| `demandas/<pk>/editar/` (`activity-edit`), `prazo/` (`activity-change-deadline`), `dono/` (`activity-change-owner`), `assumir/` (`activity-claim`) | **Ações:** `demanda.editar` (já no GET, 403 sem ela), `demanda.editar` (prazo, pelo serviço), `demanda.alterar_dono`, `demanda.assumir`. Editar (a mesma janela de 4 etapas; `?passo=2` abre direto em “Cliente e obra”, como o clique em Cliente / Obra da lista de Demandas; o passo 3 troca o quadro de tarefas e, se a escolha mudou, exige `confirm_board_replace`: sem ele `400 {errors: {board_setup_mode}}` e nada é gravado), prazo, trocar dono, assumir |
| `demandas/<pk>/inline/` (`activity-inline-update`) | **Edição inline da lista de Demandas** (só JSON, POST). `field` = `title` (+ `value`), `owner` (+ `value` = id da pessoa), `sector` (+ `value` = id do setor, **ou** `new_name` + `new_color` para criar o setor e aplicá-lo numa só transação; criar exige `setor.editar`), `stage` (+ `value`; não limpável), `condition` (+ `value`; vazio = sem condição) ou `requested_deadline` (+ `date` `YYYY-MM-DD` e `time` `HH:MM` opcional; sem data retira o prazo; sem hora vale 23:59). Resposta `{ok, field, value, display, derived?}` (dados estruturados, nunca HTML). **403** = permissão negada (`ActivityPermissionError`), **400** = regra de negócio/valor inválido (inclui `field` desconhecido ou `status`), **404** = outra organização ou rascunho. É um adapter fino: toda regra, autorização, auditoria e notificação vive no `ActivityService` (`update_activity`, `change_owner`, `set_stage`, `set_condition`); a troca de setor confere a autorização também **no setor de destino** (e o destino ativo), e estágio/status de demanda concluída ou cancelada é recusado em qualquer tela |
| `demandas/<pk>/inline/opcoes/` (`activity-inline-options`) | Opções dos pop-overs da lista de Demandas, sempre no contexto da demanda (o cliente nunca informa o setor). **GET** `?campo=sector\|stage\|condition` → `{ok, current_id, allow_clear, can_create, items:[{id,name,color,text_color}]}` (+ `can_manage`, `manage_url`, `sector_name` em estágio/status); só devolve a lista a quem poderia gravar. **POST** `campo=stage\|condition`, `acao=criar\|editar`, `name`, `color` (paleta oficial), `option_id` (editar) cria ou edita nome/cor de uma etapa ou condição **do setor da demanda**; exige `etapa.gerir`/`condicao.gerir` nesse setor (201 ao criar). **403** permissão, **400** regra (nome vazio/repetido, cor fora da paleta, campo sem lista, sem setor, demanda concluída), **404** outra organização ou rascunho |
| `demandas/<pk>/finalizar/` (`activity-finalize`), `concluir/` (`activity-complete`), `cancelar/` (`activity-cancel`), `reabrir/` (`activity-reopen`) | Encerramento e reabertura. `finalizar/` (`?outcome=` pré-seleciona) é o popup único: `demanda.concluir` (Sucesso, Concluído com pendências) ou `demanda.cancelar` (Declinado, Cancelado), comentário obrigatório. `concluir/` (POST) e `cancelar/` (POST com motivo; o GET redireciona a `finalizar/?outcome=CANCELADO`) são os caminhos antigos. `reabrir/`: `demanda.reabrir` (só demanda concluída; motivo obrigatório; janela ou página, JSON no Ajax) |
| `demandas/<pk>/processo/aplicar/` (`activity-process-apply`) | **410** — "Aplicar processo" desativado em 02/10/2026 |
| `demandas/<pk>/processo/inputs/<input_pk>/` (`activity-input-update`) | **410** — registrar/reabrir input do processo |
| `demandas/<pk>/processo/criterios/<check_pk>/` (`activity-criterion-update`) | **410** — marcar/desmarcar critério de aceite |
| `demandas/<pk>/pendente/` (`activity-mark-pending`), `pendencia/aprovar/` (`activity-approve-pendency`) | Pendência: `demanda.marcar_pendente` (motivo e comentário; prazo de decisão nos motivos com aprovação) e `demanda.aprovar_pendencia` (só a pendência com aprovação; a simples não tem rota — o serviço `resolve_pendency` existe, mas nenhuma view o chama). Janela ou página, JSON no Ajax |
| `demandas/<pk>/mensagem/` (`activity-message`), `continuar/` (`activity-continue`) | Mensagem; comentário + anexo num envio (`body`, `file`, `parent` para responder, `kind`, `visibility`). `comunicacao.participar` no serviço |
| `demandas/<pk>/mensagens/<message_pk>/reagir/` (`activity-message-reaction`) | POST `emoji` (👍 👏 🎉 ✅ 👀): alterna a reação, só em mensagem visível à pessoa; `comunicacao.participar` |
| `demandas/<pk>/anexos/` (`activity-attachment-upload`) | POST `file`: anexa (`demanda.editar`, ou o criador no próprio rascunho; audita `UPDATE` "anexo") |
| `demandas/<pk>/anexos/<attachment_pk>/download/` (`activity-attachment-download`) | GET: entrega o arquivo (`FileResponse`, como anexo) depois de conferir organização e `demanda.visualizar`, e a visibilidade da mensagem a que o anexo pertence; 403 sem acesso, 404 sem arquivo. É a única forma de baixar um anexo |
| `demandas/<pk>/anexos/<attachment_pk>/remover/` (`activity-attachment-delete`) | POST: remove e apaga o arquivo (`demanda.editar`); JSON no Ajax |
| `demandas/<pk>/mover-estagio/` (`activity-move-stage`), `demandas/<pk>/condicao/` (`activity-set-condition`) | POST: gravam só a **Etapa** (`stage`; `demanda.definir_etapa` ou, na falta, `demanda.mover_estagio`) ou só o **Status** (`condition`; `demanda.definir_condicao`) pelo `ActivityService`. Recusa em demanda concluída ou cancelada |
| `demandas/<pk>/gaveta/` (`activity-kanban-drawer`) | Gaveta da demanda aberta a partir do Kanban por setor (fragmento; `demanda.editar` e `comunicacao.participar` só definem o que a gaveta oferece; rascunho e outra organização dão 404) |
| `demandas/<activity_pk>/tarefas/rapida/` (`task-quick-create`) | **410** — a tarefa nasce no Quadro da Demanda (`board-item-create`) |

**Tarefas** — desde 02/10/2026 só existe o **Painel Tarefas** (leitura). Todo o resto de `tarefas/` responde 410.

| Caminho | Função |
|---|---|
| `tarefas/` (`task-list`), `tarefas/kanban/` (`task-kanban`), `tarefas/calendario/` (`task-calendar`) | **Painel Tarefas** (`boards/task_center_views.py::TaskCenterView`, só leitura; login e organização): o que está nos Quadros de Demanda em que a pessoa é responsável (célula Pessoa). Lista única (ordenada por prazo, concluídas ocultas por padrão), Kanban (A fazer / Em andamento / Concluídas, derivados da etiqueta de Status) e Calendário semanal (`?semana=YYYY-MM-DD`). Filtros `q`, `status` (`todo`/`doing`/`done`), `prazo` (`overdue`/`today`/`week`/`none`), `pessoa` (`todas` ou id; **ignorado sem `quadro.visualizar`/`demanda.visualizar_todas`**). `?demanda=<id>` (endereço antigo) redireciona ao Quadro da Demanda (404 sem acesso). "+ Adicionar" cria o item pelo `board-item-create` |
| `tarefas/lista-legada/` (`task-list-legacy`), `tarefas/nova-rapida/` (`task-quick-create-standalone`) | **410** |
| `tarefas/<resto>` (captura `^tarefas/.+$`, `task-legacy-retired`) | **410** para tudo o que não é uma das três telas acima |
| `tarefas/kanban-legado/` | **410** (sombreada; `task-kanban-legacy`) |
| `tarefas/<pk>/` (`task-detail`), `painel/` (`task-drawer`), `editar/` (`task-edit`), `dependencia/` (`task-dependency`), `mover-estagio/` (`task-move-stage`), `condicao/` (`task-set-condition`) | **410** (sombreadas) |
| `tarefas/<pk>/assumir/`, `iniciar/`, `pausar/`, `retomar/`, `concluir/`, `desbloquear/` (`task-assume`, `task-start`, `task-pause`, `task-resume`, `task-complete`, `task-unblock`) e as variantes JSON `iniciar/ajax/`, `pausar/ajax/`, `concluir/ajax/` (`task-start-ajax`, `task-pause-ajax`, `task-complete-ajax`) | **410** (sombreadas) |
| `tarefas/<pk>/bloquear/` (`task-block`), `devolver/` (`task-return`), `mover/` (`task-move`), `cancelar/` (`task-cancel`), `reabrir/` (`task-reopen`), `ja-realizei/` (`task-retroactive`), `tempo/` (`task-manual-time`), `mensagem/` (`task-message`) | **410** (sombreadas) |
| `tarefas/<pk>/executores/`, `executores/<user_pk>/remover/`, `alterar-responsavel/`, `atribuicoes/<assignment_pk>/aceitar/`, `.../recusar/` (`task-executor-add`, `task-executor-remove`, `task-change-responsavel`, `task-assignment-accept`, `task-assignment-reject`) | **410** (sombreadas) |
| `tarefas/<pk>/checklist/` (`task-checklist-add`), `checklist/<pk>/alternar/` (`task-checklist-toggle`), `checklist/<pk>/remover/` (`task-checklist-remove`); captura `^checklist/.+$` (`task-checklist-legacy-retired`) | **410** (sombreadas) |
| `tarefas/<pk>/prazo/propor/` (`deadline-propose`), `prazos/<pk>/aceitar/` (`deadline-accept`), `prazos/<pk>/recusar/` (`deadline-reject`), `conflitos/<pk>/resolver/` (`conflict-resolve`); capturas `^prazos/.+$` (`deadline-legacy-retired`) e `^conflitos/.+$` (`conflict-legacy-retired`) | **410** — o prazo negociado e o escalonamento foram desativados (sombreadas) |

As views correspondentes (`TaskDetailView`, `TaskActionView`, `DeadlineProposeView`…) continuam no código, sem rota
alcançável; os serviços (`TaskService`, `DeadlineService`) também — ver a seção 2 de
[06_ATIVIDADES_E_TAREFAS.md](06_ATIVIDADES_E_TAREFAS.md).

**Quadro Kanban por setor — ações** (`activities/kanban_urls.py`, incluído no fim de `activities/urls.py`; `<dom>` é `demandas` ou `tarefas`, outro valor dá 404). Servem ao Kanban por setor (`demandas/kanban-legado/` e à gaveta); `<dom>=tarefas` só enxerga `Task` históricas. Todas exigem login e organização e respondem JSON; as que gravam passam pelos services e devolvem o cartão novo em `card_html`:

| Caminho | Nome | Função |
|---|---|---|
| `kanban/<dom>/<pk>/cartao/` | `kanban-card` | GET: o cartão como está agora, ou `{"visible": false}` se saiu do quadro. Usa a consulta da URL (setor e filtros) |
| `kanban/<dom>/<pk>/etapa/` | `kanban-set-stage` | POST `stage_id`: grava só a etapa. 403 se o serviço recusa (outro setor, inativa, sem ação); 400 se vazio; 404 se a etapa é de outro tipo ou organização |
| `kanban/<dom>/<pk>/condicao/` | `kanban-set-condition` | POST `condition_id` (vazio remove a condição): grava só a condição |
| `kanban/demandas/criar/` | `kanban-create-card` | POST `title`, `sector_id`, `stage_id`: cria a demanda na coluna (201). Tarefa não se cria aqui (400) |
| `kanban/<dom>/limite/` | `kanban-column-limit` | POST `stage_id`, `limit` (1 a 999; vazio remove): exige `etapa.gerir` no setor |
| `kanban/<dom>/opcoes/` | `kanban-create-option` | POST `kind` (`stage` \| `condition`), `name`, `color`, `sector_id`: nova etapa/condição do setor; exige `etapa.gerir` / `condicao.gerir` |

## 5. `processes` (`/processos/`)

**Desativado em 02/10/2026.** `processes/urls.py` abre com `re_path(r"^.*$", RetiredProcessView, name="process-retired")`,
que captura **qualquer** caminho sob `processos/` (inclusive a raiz) e responde `410 Gone` com o texto "Processos foram
desativados. Use o quadro da Demanda." Os dados (processos, versões, inputs, critérios, etapas) ficam preservados; não se
cria nem se aplica processo. Os 16 padrões abaixo seguem declarados, **sombreados** pela captura, e as views
(`ProcessListView`, `ProcessCreateView`…) não são mais alcançadas:

`` (`process-list`), `novo/` (`process-create`), `<pk>/` (`process-edit`),
`<pk>/informacoes/` (`process-basic-info`), `<pk>/output/` (`process-output`), `<pk>/inputs/` (`process-input-add`;
+ `<input_pk>/remover/`, `process-input-remove`), `<pk>/criterios/` (`process-criterion-add`; + `<criterion_pk>/remover/`,
`process-criterion-remove`), `<pk>/fluxo/` (`process-step-add`; + `reordenar/` `process-step-reorder`,
`<step_pk>/remover/` `process-step-remove`, `<step_pk>/responsavel/` `process-step-responsavel`),
`<pk>/publicar/` (`process-publish`), `<pk>/nova-versao/` (`process-new-version`), `<pk>/ativo/` (`process-toggle-active`).
Autorização que seria exigida nos serviços (`processo.*`). **Aplicar** um processo era uma rota de demanda
(`demandas/<pk>/processo/aplicar/`, seção 4), também **410**.

## 6. `notifications` (`/notificacoes/`)

| Caminho | Nome | Função |
|---|---|---|
| `` | `notification-list` | Caixa com abas (`?filter=`), busca e paginação |
| `<pk>/read/` | `notification-mark-read` | Marca lida e redireciona para um destino interno validado |
| `mark-all-read/` | `notification-mark-all-read` | Marca todas |

## 6.1 `intake` (`/entrada/`) — Caixa de Entrada

**Inativa por padrão:** com `INTAKE_ENABLED` desligado (ver [03_CONFIGURACAO.md](03_CONFIGURACAO.md)) toda rota abaixo
responde 404 (o decorador `only_when_enabled`, em `intake/urls.py`, olha a chave a cada pedido; vale até para quem tem `entrada.*`) e o item "Entrada" não
aparece no menu. Foi inativada em 01/10/2026 (commit `0135cc0`).

Nomes de rota são globais (o projeto não usa `app_name`), por isso o prefixo `intake-`. Todas
exigem login e organização; item de outra organização dá 404, sem a ação dá 403 (seção 4.2 de
[05_AUTORIZACAO.md](05_AUTORIZACAO.md)). As telas de formulário abrem em janela (`LPSModal`) e
também funcionam como página; com `X-Requested-With: XMLHttpRequest` respondem JSON.

| Caminho | Nome | Método | Ação | Resposta |
|---|---|---|---|---|
| `` | `intake-list` | GET | `entrada.visualizar` (em algum lugar) | Abas `?status=novos\|convertidos\|ignorados`, busca `?q=`, `?page=` (25 por página) |
| `registrar/` | `intake-capture` | GET/POST | `entrada.registrar` (em algum lugar) | Sucesso: `{"message", "redirect_url"}` |
| `<pk>/` | `intake-detail` | GET | `entrada.visualizar` no item | Texto original, o que a LPS entendeu e histórico |
| `<pk>/editar/` | `intake-edit` | GET/POST | `entrada.triar` no item | Sucesso: `{"message", "html" (cartão novo), "target": "#intake-item-<pk>"}` |
| `<pk>/criar-demanda/` | `intake-convert` | GET/POST | `entrada.triar` no item (+ `demanda.criar` no serviço) | Sucesso: `{"message", "redirect_url": atividade}` |
| `<pk>/ignorar/` | `intake-ignore` | GET/POST | `entrada.triar` no item | Sucesso: `{"message", "remove": "#intake-item-<pk>"}` |
| `<pk>/restaurar/` | `intake-restore` | só POST | `entrada.triar` no item | Sucesso: `{"message", "remove"}`; erro: `400 {"error"}` |

- Formulário inválido: `400 {"errors": {campo: [mensagens]}}`; erro de regra aparece em `__all__`.
- Editar, criar demanda e ignorar numa solicitação que já foi tratada redireciona para o detalhe
  com a mensagem "Esta solicitação já foi tratada.".
- Todos os nomes `intake-*` estão em `_NAV_BY_URL_NAME` (item "Entrada" ativo no menu); um teste
  confere.

## 6.2 `boards` (`/quadros/`) — Quadros dinâmicos

Nomes de rota globais com o prefixo `board-`. Todas exigem login e organização; objeto de outra organização dá **404**, sem a
ação dá **403** (seção 4.3 de [05_AUTORIZACAO.md](05_AUTORIZACAO.md)). As gravações são **POST com corpo JSON** (CSRF no
cabeçalho `X-CSRFToken`) e respondem `{"ok": true, ...}`; erro de regra: `400 {"ok": false, "error", "needs_confirmation"}`;
pede confirmação: **409** com `needs_confirmation: true`; sem permissão: 403; JSON inválido (ou que não é objeto): 400
"JSON inválido.". Os ids de grupo, coluna, etiqueta e item vão no caminho.

| Caminho | Nome | Método | Ação | Corpo → resposta |
|---|---|---|---|---|
| `` | `board-list` | GET | `quadro.visualizar` | Lista os quadros **modelo** da organização (`kind=TEMPLATE`; o quadro de cada Demanda não aparece aqui) e, com `quadro.criar`, o formulário "Criar um quadro" |
| `novo/` | `board-create` | POST (form) | `quadro.criar` | `name`, `sector_id` (**obrigatório**, setor ativo da organização), `template` (`orcamentos`, opcional) → cria um quadro modelo e redireciona a ele |
| `<id>/` | `board-detail` | GET | `quadro.visualizar` | A tabela. `?sort=<coluna>&dir=asc\|desc`, `?q=` (nome, texto, etiqueta, pessoa), `?pessoa=<id>` |
| `<id>/historico/` | `board-history` | GET | `quadro.visualizar` | `AuditLog` do quadro, 50 por página |
| `visoes/<id>/` | `board-view-detail` | GET | `quadro.visualizar` | A visualização escolhida na aba: **Kanban** (as raias com os cartões) ou **Calendário** (a grade do mês, `?mes=AAAA-MM`; mês inválido = o atual). `?q=` e `?pessoa=` como na tabela; ordem, agrupamento, coluna de Data e cor vêm da configuração salva |
| `<id>/visoes/novo/` | `board-view-create` | POST | `quadro.editar` | `{name, type: "KANBAN"\|"CALENDAR", settings}` → `{view, redirect_url}`; Calendário num quadro sem coluna de Data: 400 |
| `visoes/<id>/editar/` | `board-view-update` | POST | `quadro.editar` | `{name?, settings?}` (só as chaves enviadas mudam; valida e audita uma a uma) → `{view, settings}` completo |
| `visoes/<id>/excluir/` | `board-view-delete` | POST | `quadro.editar` | Exclusão lógica → `{redirect_url}` (a tabela). Os itens não são afetados |
| `visoes/<id>/lanes/` | `board-view-lanes` | POST | `quadro.visualizar` | Só de visualização Kanban (outra: 404). `{q, pessoa}` → `{lanes_html, total_items, columns, settings, group_column_id, sum_column_id, card_column_ids}`: o servidor redistribui os cartões e o navegador troca o HTML |
| `visoes/<id>/calendario/` | `board-view-calendar` | POST | `quadro.visualizar` | Só de visualização Calendário (outra: 404). `{mes, q, pessoa}` → `{body_html, title, month, prev, next, today, columns, settings, date_column_id, color_kind, color_column_id, card_column_ids}`: o servidor posiciona os cartões e o navegador troca o HTML (trocar de mês, depois de mover/criar/editar, ao configurar) |
| `<id>/renomear/` | `board-rename` | POST | `quadro.editar` | `{name, description}` → `{name, description}` |
| `<id>/excluir/` | `board-delete` | POST | `quadro.excluir` | → `{redirect_url}` |
| `<id>/grupos/novo/` | `board-group-create` | POST | `quadro.editar` | `{name, color}` → `{group, group_html}` |
| `grupos/<id>/editar/` · `mover/` · `excluir/` | `board-group-update` · `-reorder` · `-delete` | POST | `quadro.editar` | `{name, color}` · `{before_id, after_id}` · recusa se houver itens |
| `<id>/colunas/novo/` | `board-column-create` | POST | `quadro.gerir_colunas` | `{type, after_column_id}` → `{column, header_html, cells: {item_id: td}, after_column_id}` |
| `colunas/<id>/renomear/` · `largura/` · `mover/` | `board-column-rename` · `-resize` · `-reorder` | POST | `quadro.gerir_colunas` | `{name}` → `{column, header_html}` · `{width}` → `{width}` (limitada a 96–640) · `{before_id, after_id}` |
| `colunas/<id>/configuracoes/` | `board-column-settings` | POST | `quadro.gerir_colunas` | `{description, is_required, settings}` → coluna + cabeçalho + células |
| `colunas/<id>/ocultar/` · `duplicar/` · `excluir/` | `board-column-hide` · `-duplicate` · `-delete` | POST | `quadro.gerir_colunas` | `{visible}` · cópia ao lado · exclusão lógica |
| `colunas/<id>/tipo/` | `board-column-type` | POST | `quadro.gerir_colunas` | `{type, preview}` → `{plan: {mode, filled, lost}}`; sem `confirm` e fora de `safe`: **409**; `{type, confirm: true}` converte |
| `colunas/<id>/fragmento/` | `board-column-fragment` | POST | `quadro.visualizar` | Redesenha cabeçalho e células de uma coluna (depois de editar etiquetas) |
| `colunas/<id>/etiquetas/novo/` · `etiquetas/<id>/editar/` · `mover/` · `excluir/` | `board-option-create` · `-update` · `-reorder` · `-delete` | POST | `quadro.gerir_colunas` | `{label, color}` · `{label, color, is_default, is_done}` · `{before_id, after_id}` · `{cleared_cells}` |
| `<id>/itens/novo/` | `board-item-create` | POST | `quadro.criar_item` | `{group_id, name, initial: {column_id, value} ou [{column_id, value}, …]}` → `{item, row_html}` (grupo de outro quadro: 404). `initial` preenche já uma ou várias colunas (até 30) **na mesma transação** (o Kanban cria o cartão dentro de uma raia; o Calendário, no dia clicado, com a data e os demais campos): valor inválido ou sem `editar_item` desfaz tudo |
| `itens/<id>/renomear/` · `mover/` · `excluir/` | `board-item-rename` · `-move` · `-delete` | POST | `quadro.editar_item` · `quadro.editar_item` · `quadro.excluir_item` | `{name}` · `{group_id, before_id, after_id}` |
| `itens/<id>/detalhe/` | `board-item-detail` | POST | `quadro.visualizar` | → `{drawer_html}`: a gaveta do item (todos os campos, os ocultos também, editáveis no lugar pelos mesmos editores da tabela, e as últimas 8 mudanças do item). Só lê, então a permissão é conferida na view |
| `itens/<id>/colunas/<id>/valor/` | `board-cell-update` | POST | `quadro.editar_item` | `{value}` → `{display, cell_html}`; sem `value` limpa a célula |

- A pesquisa de pessoas da célula reaproveita `person-search` (`/api/pessoas/`).
- **Quadro da Demanda** (`Board.kind = DEMAND`, um por Demanda, ligado por `Activity.task_board`): as mesmas rotas `board-*`
  valem, mas a autorização é relacional (`DemandBoardAccess`, em `boards/demand_services.py`): ver o quadro = participar da
  Demanda (dono, criador ou pessoa em célula Pessoa de um item ativo), `demanda.visualizar` ou `quadro.visualizar`;
  criar e editar item (`quadro.criar_item`, `quadro.editar_item`) = participar ou `quadro.editar_item`; excluir item
  (`quadro.excluir_item`) segue o catálogo; estrutura (`quadro.editar`, `quadro.gerir_colunas`, `quadro.excluir`) = dono,
  criador ou `quadro.gerir_colunas`. A tela de um
  Quadro de Demanda não oferece excluir o quadro. Chega-se a ele por `board-detail` (botão "Abrir quadro" da ficha da Demanda).
  O quadro nasce ao publicar a Demanda e só é trocado no editor da Demanda (seção 4).

**Lentes sobre Demandas e Tarefas** (`boards/work_views.py`; a tela é `demandas/`, seção 4). Não usam `BoardItem`: o alvo é o
objeto operacional (`Activity`; `Task` só histórica). POST com corpo JSON ou formulário (CSRF); respondem
`{success, message, errors, ...}` (400 com `errors`, 409 em conflito de edição, 403 sem permissão):

| Caminho | Nome | Ação | Corpo → resposta |
|---|---|---|---|
| `dominio/<board_pk>/campos/<field_pk>/itens/<object_pk>/valor/` | `workboard-value` | `demanda.visualizar` (`tarefa.visualizar` no domínio Tarefa) na view; a regra do campo no serviço (`ActivityService.update_activity`/`change_owner`/`set_stage`/`set_condition`, `prazo.alterar_solicitado` no prazo, `demanda.editar` nos campos configuráveis) | `{value, updated_at?}` → `{success, html (célula nova), updated_at, target}`. `updated_at` é a versão que a tela leu: se a demanda mudou desde então, **409** "Esta informação foi alterada por outra pessoa" |
| `dominio/visoes/<view_pk>/campos/<field_pk>/layout/` | `workboard-layout` | `quadro.gerir_colunas` | `{width (96–640), position, is_visible}` → `{success}` |
| `dominio/visoes/<view_pk>/cartoes/` | `workboard-card-fields` | `quadro.gerir_colunas` | `{field_ids: [id, …]}` → os campos exibidos nos cartões do Kanban, na ordem enviada; os demais ficam ocultos |
| `dominio/<board_pk>/campos/novo/` | `workboard-field-create` | `quadro.gerir_colunas` | `{label, type}` (`type` ∈ `TEXT`, `NUMBER`, `CURRENCY`, `DATETIME`, `SELECT`, `BOOLEAN`; outro: 400) → `{success, field_id}`: novo campo configurável (valores em `DomainCustomValue`, auditados como `quadro:<chave>`) |
| `dominio/visoes/<view_pk>/configuracao/` | `workboard-view-settings` | `quadro.gerir_colunas` | `{group_by?, show_empty?, show_field_names?}`: `group_by` ∈ `stage`, `condition`, `sector`, `owner`, `responsavel`, `urgency`, `priority` e precisa existir no quadro (senão 400) |
- Todos os nomes `board-*` estão em `_NAV_BY_URL_NAME` (item "Quadros" ativo no menu); um teste confere (36 rotas).
- O endereço dos endpoints chega ao JavaScript pelo `json_script` `#board-meta`, com um id fictício (`999999999`, e
  `999999998` para a coluna na rota da célula) que o script troca pelo real.

---

## 7. `painel` (`/painel/`)

Telas em branco ("em construção") que mantêm o menu completo:
`equipe/pessoas/` (`equipe-pessoas`), `equipe/capacidade/` (`equipe-capacidade`),
`equipe/carga-de-trabalho/` (`equipe-carga-trabalho`), `filas-e-gargalos/filas/` (`gargalos-filas`),
`.../gargalos/` (`gargalos-gargalos`), `.../bloqueios/` (`gargalos-bloqueios`),
`.../devolucoes/` (`gargalos-devolucoes`), `processos/modelos/` (`processos-modelos`),
`insights/` (`insights`), `desenvolvimento/` (`desenvolvimento`), `resultados/` (`resultados`),
`integracoes/` (`integracoes`), `configuracoes/motivos-de-bloqueio/` (`config-motivos-bloqueio`),
`configuracoes/motivos-de-devolucao/` (`config-motivos-devolucao`) — 14 rotas, todas
`TelaEmBrancoView`. Os endereços de filas, bloqueios, devoluções e modelos de processo são só
espaços reservados do menu: a Fila e os Processos estão desativados (410 em `fila/` e `processos/`).

Telas reais, com views de `core`:

| Caminho | Nome | Ação |
|---|---|---|
| `configuracoes/etapas-e-status/` | `config-etapas-status` | `etapa.gerir` ou `condicao.gerir` (a que a pessoa tiver no setor escolhido); a tela mantém Etapas de Demanda, Etapas de Tarefa e Status por setor |
| `configuracoes/prioridades/` | `config-prioridades` | `cor_prioridade.gerir` |

Para listar as rotas de verdade a qualquer momento:

```powershell
python manage.py shell -c "from django.urls import get_resolver; [print(p) for p in get_resolver().reverse_dict.keys() if isinstance(p, str)]"
```
