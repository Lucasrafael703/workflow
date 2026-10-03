# Triagem dos testes vermelhos ligados a Demandas (Fase 0.2)

Gerada em 03/10/2026 rodando `boards`, `activities.test_activity_workspace`, `test_kanban`, `test_reopen`, `test_inline_edit` e `test_views` no estado atual da árvore.
Resultado: **787 testes; 99 testes distintos vermelhos** (118 ocorrências, porque alguns têm subtestes). `boards` e `test_inline_edit` estão 100% verdes.

| Bloco | Ação proposta | Quantidade |
|---|---|---|
| **D** — Bug real (corrigir) | corrigir | 1 |
| **A** — Comportamento que ainda vale (reescrever na tela atual) | reescrever | 11 |
| **B** — Tela de Demandas morta (remover junto) | remover (com aval) | 30 |
| **C** — Tarefas legadas, rotas respondem 410 (fora do escopo de Demandas) | não mexer; registrar | 57 |

Nada será apagado antes do seu aval. `activities/test_activity_workspace.py` e `activities/test_reopen.py` estão sendo editados por outra sessão e **não serão tocados** até ela terminar.

## Bloco D — Bug real (corrigir)

Valor inválido em filtro derruba a tela com erro 500. É defeito de produção, não de teste.

**activities.test_kanban.FilterTests**
- `test_invalid_values_are_ignored` — ValueError: Field 'id' expected a number but got 'x'.

## Bloco A — Comportamento que ainda vale (reescrever na tela atual)

A tela mudou, mas a regra continua valendo; vira teste da tela atual (ou já está coberta e o teste antigo sai).

**activities.test_activity_workspace.ActivityWorkspaceTests**
- `test_filter_toolbar_searches_title_client_site_and_code` — AssertionError: False is not true : Material na obra: Couldn't find 'id="activity-1"' in the following respons
**activities.test_kanban.FilterTests**
- `test_blocked_filter_uses_the_operational_status` — KeyError: 'columns'
- `test_clear_link_keeps_only_the_sector` — AssertionError: False is not true : Couldn't find 'href="/demandas/kanban/?setor=1"' in the following response
- `test_client_and_site_filters` — KeyError: 'columns'
- `test_condition_filter` — KeyError: 'columns'
- `test_deadline_filters` — KeyError: 'columns'
- `test_deadline_ordering_puts_the_empty_deadline_last` — KeyError: 'columns'
- `test_ordering_by_title_in_both_directions` — KeyError: 'columns'
- `test_person_filter` — KeyError: 'columns'
- `test_search_matches_title_client_site_and_the_old_code` — KeyError: 'columns'
**activities.test_reopen.ReopenViewTests**
- `test_activity_list_offers_it_for_concluded_activities_only` — AssertionError: False is not true : Couldn't find '/demandas/1/reabrir/' in the following response

## Bloco B — Tela de Demandas morta (remover junto)

Descrevem a lista, o Kanban por setor ou o calendário em grade antigos, que a tela atual substituiu. O código antigo (`activities/kanban.py`, `activity_list.html`…) nem renderiza mais.

**activities.test_activity_workspace.ActivityWorkspaceTests**
- `test_filter_changes_do_not_keep_pagination` — AssertionError: False is not true : Couldn't find 'href="?q=Material&amp;ordem=titulo"' in the following respo
- `test_list_cancellation_uses_same_finalization_as_detail` — AssertionError: False is not true : Couldn't find '/demandas/1/finalizar/?outcome=CANCELADO' in the following 
- `test_list_rows_and_links_have_one_destination` — AssertionError: False is not true : Couldn't find 'id="activity-1"' in the following response
- `test_shared_filter_toolbar_exposes_manual_controls` — AssertionError: False is not true : Couldn't find 'data-workspace-filters' in the following response
**activities.test_kanban.BoardSectorTests**
- `test_a_member_of_two_sectors_switches_and_the_choice_is_remembered` — KeyError: 'sector'
- `test_a_person_without_sector_or_items_sees_an_explanation` — KeyError: 'sector'
- `test_a_sector_the_person_cannot_open_is_ignored_not_leaked` — KeyError: 'sector'
- `test_a_sector_without_stages_explains_and_offers_setup_only_to_managers` — AssertionError: False is not true : Couldn't find 'ainda n�o tem etapas para demandas' in the following respon
- `test_old_group_parameter_still_selects_the_sector` — KeyError: 'sector'
- `test_the_board_is_always_of_one_sector_with_its_own_stages` — KeyError: 'columns'
- `test_the_main_sector_of_the_person_is_the_default` — KeyError: 'sector'
**activities.test_kanban.BoardVisibilityTests**
- `test_a_member_of_the_sector_sees_every_item_of_it` — KeyError: 'columns'
- `test_drafts_and_finished_items_are_hidden_until_asked` — KeyError: 'columns'
- `test_nothing_from_another_organization_ever_shows` — KeyError: 'columns'
- `test_someone_outside_the_sector_sees_only_what_they_work_on` — KeyError: 'columns'
**activities.test_kanban.ColumnTests**
- `test_a_column_within_the_limit_is_not_flagged` — KeyError: 'columns'
- `test_an_inactive_stage_sends_its_items_to_sem_etapa` — KeyError: 'columns'
- `test_cards_the_person_cannot_move_are_not_draggable` — AssertionError: False is not true : Couldn't find 'draggable="false"' in the following response
- `test_items_are_grouped_by_stage_and_counted` — KeyError: 'columns'
- `test_sem_etapa_only_appears_when_something_needs_classifying` — KeyError: 'unassigned'
- `test_the_column_limit_only_warns` — KeyError: 'columns'
- `test_the_column_menu_offers_limit_and_edit_only_to_managers` — AssertionError: False is not true : Couldn't find 'Definir limite da coluna' in the following response
**activities.test_kanban.SetConditionTests**
- `test_the_card_offers_the_condition_picker_only_to_who_can_change_it` — AssertionError: False is not true : Couldn't find 'data-workflow-picker' in the following response
**activities.test_kanban.WiringTests**
- `test_garbage_in_the_initial_values_is_ignored` — AssertionError: 410 != 200
- `test_the_kanban_addresses_use_the_new_views` — AssertionError: 'boards.work_views' != 'activities.kanban'
**activities.test_views.ActivityKanbanAndCalendarViewTests**
- `test_calendar_returns_ok_with_week_grid` — AssertionError: 'weeks' not found in [[{'True': True, 'False': False, 'None': None}, {'csrf_token': <SimpleLaz
- `test_kanban_shows_stage_columns_and_unassigned_activities` — KeyError: 'columns'
**activities.test_views.SpreadsheetListViewTests**
- `test_custom_status_color_and_label_are_rendered_in_demand_sheet` — AssertionError: False is not true : Couldn't find 'Em an�lise' in the following response
- `test_demand_list_uses_sheet_status_and_progress_components` — AssertionError: False is not true : Couldn't find 'class="activities-table lps-sheet lps-sheet--demand"' in th
- `test_tasks_grouped_by_demand_use_the_same_sheet_status` — AssertionError: False is not true : Couldn't find 'class="responsive lps-sheet lps-sheet--grouped"' in the fol

## Bloco C — Tarefas legadas, rotas respondem 410 (fora do escopo de Demandas)

Testam `/tarefas/<id>/...`, que a centralização das tarefas em Quadros aposentou (410). Não tocam Demandas/Workspace: ficam registradas, sem mexer, até uma limpeza própria de Tarefas.

**activities.test_kanban.BoardSectorTests**
- `test_tasks_board_uses_the_task_stages_of_the_sector` — KeyError: 'columns'
**activities.test_kanban.BoardVisibilityTests**
- `test_finished_tasks_are_hidden_until_asked` — KeyError: 'columns'
- `test_participating_in_a_task_makes_the_demand_visible_to_an_outsider` — KeyError: 'columns'
- `test_tasks_of_an_outsider_are_limited_to_their_own` — KeyError: 'columns'
**activities.test_kanban.ColumnTests**
- `test_task_columns_open_the_new_task_window_already_in_the_sector_and_stage` — AssertionError: False is not true : Couldn't find 'sector=1&amp;stage=1' in the following response
**activities.test_kanban.DrawerTests**
- `test_the_task_drawer_controls_are_read_only_without_permission` — AssertionError: 410 != 200
- `test_the_task_drawer_gets_stage_and_condition_controls` — AssertionError: 410 != 200
**activities.test_kanban.FilterTests**
- `test_task_participant_filter` — KeyError: 'columns'
- `test_task_search_matches_the_demand_of_the_task` — KeyError: 'columns'
**activities.test_kanban.WiringTests**
- `test_the_new_task_window_opens_already_in_the_sector_and_stage` — AssertionError: 410 != 200
**activities.test_reopen.ReopenViewTests**
- `test_ajax_post_reopens_and_answers_json` — AssertionError: 410 != 200
- `test_business_refusal_comes_back_as_a_form_error` — AssertionError: 410 != 400
- `test_concluded_tab_of_the_task_list_has_the_menu_item` — AssertionError: False is not true : Couldn't find '/tarefas/1/reabrir/' in the following response
- `test_missing_reason_is_reported_on_the_field` — AssertionError: 410 != 400
- `test_other_tenant_gets_404` — AssertionError: 410 != 404
- `test_popup_explains_and_asks_for_the_reason` — AssertionError: 410 != 200 : Couldn't retrieve content: Response code was 410 (expected 200)
- `test_popup_needs_the_permission` — AssertionError: 410 != 403
- `test_post_without_javascript_redirects_to_the_task` — AssertionError: 410 != 302 : Response didn't redirect as expected: Response code was 410 (expected 302)
- `test_side_panel_offers_it_too` — AssertionError: 410 != 200 : Couldn't retrieve content: Response code was 410 (expected 200)
- `test_task_page_hides_it_from_others_and_for_open_tasks` — AssertionError: 410 != 200 : Couldn't retrieve content: Response code was 410 (expected 200)
- `test_task_page_shows_the_button_to_someone_who_can_reopen` — AssertionError: 410 != 200 : Couldn't retrieve content: Response code was 410 (expected 200)
**activities.test_views.OrganizationIsolationViewTests**
- `test_user_from_another_organization_cannot_open_task` — AssertionError: 410 != 404
**activities.test_views.QueuePrivacyViewTests**
- `test_full_queue_requires_the_action` — AssertionError: 410 != 200 : Couldn't retrieve content: Response code was 410 (expected 200)
- `test_position_total_is_recalculated_after_completion` — AssertionError: 410 != 200 : Couldn't retrieve content: Response code was 410 (expected 200)
- `test_queue_permission_does_not_leak_across_sectors` — AssertionError: 410 != 200 : Couldn't retrieve content: Response code was 410 (expected 200)
- `test_requester_never_sees_other_task_titles` — AssertionError: 410 != 200
- `test_requester_sees_own_position_and_live_total` — AssertionError: 410 != 200 : Couldn't retrieve content: Response code was 410 (expected 200)
**activities.test_views.QueueReorderViewTests**
- `test_reorder_granted_in_one_sector_does_not_apply_to_another` — AssertionError: 410 != 200 : Couldn't retrieve content: Response code was 410 (expected 200)
- `test_reorder_requires_the_action` — AssertionError: 410 != 200 : Couldn't retrieve content: Response code was 410 (expected 200)
- `test_reorder_with_the_action_succeeds` — AssertionError: 2 != 1
**activities.test_views.SpreadsheetListViewTests**
- `test_task_list_uses_sheet_markup_without_nonfunctional_selection` — AssertionError: False is not true : Couldn't find 'class="responsive lps-sheet lps-sheet--task"' in the follow
**activities.test_views.TaskActionViewTests**
- `test_assume_requires_the_action` — AssertionError: 410 != 200 : Couldn't retrieve content: Response code was 410 (expected 200)
- `test_assume_then_start_flow` — AssertionError: 'EM_FILA' != Task.Status.EM_EXECUCAO
- `test_non_executor_cannot_start_even_with_the_action` — AssertionError: 410 != 200 : Couldn't retrieve content: Response code was 410 (expected 200)
**activities.test_views.TaskAssignmentViewTests**
- `test_assigning_another_person_does_not_create_executor_immediately` — activities.models.TaskAssignment.DoesNotExist: TaskAssignment matching query does not exist.
- `test_member_accepts_assignment_and_becomes_executor` — activities.models.TaskAssignment.DoesNotExist: TaskAssignment matching query does not exist.
- `test_member_rejects_assignment_with_reason` — activities.models.TaskAssignment.DoesNotExist: TaskAssignment matching query does not exist.
- `test_someone_else_cannot_accept_another_persons_assignment` — activities.models.TaskAssignment.DoesNotExist: TaskAssignment matching query does not exist.
**activities.test_views.TaskAuthorizationTests**
- `test_authorized_user_may_block` — AssertionError: 410 != 200
- `test_manual_time_only_for_executors` — AssertionError: 410 != 200 : Couldn't retrieve content: Response code was 410 (expected 200)
- `test_relational_scope_does_not_reach_other_peoples_activities` — AssertionError: 410 != 403
- `test_relational_scope_lets_the_owner_act_on_own_activity` — AssertionError: 410 != 200
- `test_stranger_cannot_block_task` — AssertionError: 410 != 403
- `test_stranger_cannot_open_block_form` — AssertionError: 410 != 403
- `test_stranger_cannot_reach_other_task_actions` — AssertionError: 410 != 403 : task-return
**activities.test_views.TaskChecklistViewTests**
- `test_active_executor_can_toggle_but_not_add_or_remove` — AssertionError: 410 != 200
- `test_csrf_is_required_and_rendered_token_is_accepted` — KeyError: 'csrftoken'
- `test_editor_can_add_with_action_urls_and_persist_trimmed_text` — AssertionError: 410 != 200
- `test_editor_can_toggle_and_remove_without_being_executor` — AssertionError: 410 != 200
- `test_invalid_toggle_values_do_not_change_saved_state` — AssertionError: 410 != 400
- `test_other_organization_cannot_mutate_even_with_edit_grant` — AssertionError: 410 != 404
- `test_page_and_drawer_render_persisted_checklist_and_correct_controls` — AssertionError: 410 != 200
- `test_removed_executor_cannot_toggle` — AssertionError: 410 != 400
- `test_text_is_validated_on_server` — AssertionError: 410 != 400
- `test_unauthorized_user_cannot_mutate` — AssertionError: 410 != 400
**activities.test_views.TaskFilterViewTests**
- `test_old_visao_and_sort_values_still_work` — AssertionError: 'list' != 'demanda'
- `test_task_activity_view_uses_shared_task_toolbar` — AssertionError: False is not true : Couldn't find 'class="activities-filters task-filters workspace-filters"' 

---

## Execução (03/10/2026)

**Commit 1 — bloco D e bloco A.** O erro 500 por valor inválido em filtro foi corrigido na origem (`normalize_workspace_filters` só aceita ids numéricos e anota o resto em `invalid`; `DemandWorkBoardView` lê o setor já normalizado). As regras do bloco A passaram a ser testadas na tela atual, em `activities/test_demand_filters.py` (busca por título, cliente, obra e código antigo; pessoa; etapa, status e setor; cliente e obra; prazos; bloqueada; valores inválidos). Os 7 testes antigos migrados saíram de `test_kanban.py`.

**Commit 2 — bloco B.** Antes de apagar, cada teste foi lido: o que era regra de negócio foi migrado para `test_demand_filters.py`; o que sobrou descrevia só a estrutura da tela antiga. Removidos **24** testes:

| Teste removido | Regra de negócio? | Onde a regra continua testada |
|---|---|---|
| `BoardSectorTests`: setor lembrado na sessão, setor principal como padrão, explicação "sem setor", explicação "sem etapas" com atalho, "um quadro por setor" | só da tela antiga (Kanban de um setor só) | não se aplica: a tela atual não tem "quadro de um setor" |
| `BoardSectorTests`: setor que a pessoa não pode abrir é ignorado, sem vazar | **sim** (segurança) | `test_the_all_scope_without_the_permission_shows_only_my_own_and_never_leaks_a_sector` |
| `BoardSectorTests`: parâmetro antigo `grupo` escolhe o setor | **sim** (compatibilidade) | `test_the_old_sector_names_still_select_the_sector` |
| `BoardVisibilityTests` (4): quem vê o quê, rascunhos e concluídas, outra organização, quem é de fora | **sim** | `DemandScopeTests` (escopos Minhas / Do meu setor / Participando / Todas) e `DemandFilterTests` |
| `ColumnTests`: itens agrupados e contados; "Sem etapa" só quando precisa; etapa inativa; arrastar só quem pode | **sim** | `test_the_no_stage_lane_only_appears_when_a_demand_needs_classifying`, `test_the_kanban_never_loses_a_demand_when_its_stage_stops_being_active`, `test_a_card_is_draggable_only_for_who_can_move_it` e `test_domain_workboards` (raias vazias, arrastar) |
| `ColumnTests`: limite de coluna só avisa (2 testes) e menu da coluna (limite/editar) só para gestores | capacidade **que a tela atual não tem** (ver abaixo) | — |
| `SetConditionTests`: seletor de status no cartão só para quem pode | capacidade que a tela atual não tem | — |
| `WiringTests`: endereços apontam para `activities.kanban` | só estrutura | `DemandRoutingTests` (as três rotas são a mesma view) |
| `ActivityKanbanAndCalendarViewTests`: colunas por etapa + "sem etapa"; calendário em grade semanal | estrutura da tela antiga | itens acima; a grade volta com a fase do Calendário |
| `SpreadsheetListViewTests`: status customizado com rótulo e cor | **sim** | `test_a_custom_status_shows_its_label_and_color_in_the_list` |
| `SpreadsheetListViewTests`: classes `lps-sheet` | só estrutura | — |

**Reclassificados para o bloco C (não mexer):** `WiringTests.test_garbage_in_the_initial_values_is_ignored` (é a janela de nova tarefa, rota 410) e `SpreadsheetListViewTests.test_tasks_grouped_by_demand_use_the_same_sheet_status` (lista de tarefas).

**Pendente, porque os arquivos estão com a outra sessão:** 4 testes do bloco B em `activities/test_activity_workspace.py` (paginação da lista antiga, cancelar pela lista, ids das linhas, barra de filtros antiga), 1 do bloco A no mesmo arquivo (busca na barra; a regra já está testada em `test_demand_filters.py`) e 1 do bloco A em `activities/test_reopen.py` (a lista atual não oferece "Reabrir"; ver abaixo). Voltam à pauta quando a outra sessão terminar.

**Ficam para a fase 1A** (dependem da ordenação nova): `test_ordering_by_title_in_both_directions`, `test_deadline_ordering_puts_the_empty_deadline_last` e `test_clear_link_keeps_only_the_sector`.

## Capacidades do Kanban/Lista antigos que a tela atual NÃO tem (decisão de produto, não de teste)

Os testes acima só deixaram de existir porque a tela que eles descreviam foi substituída; mas estas **capacidades também sumiram** e vale uma decisão explícita (reter, redesenhar ou abandonar):

1. **Limite de coluna (WIP)** do Kanban de Demandas (aviso "2 de 1") e o menu da coluna para definir limite/editar etapa.
2. **Seletor de status no cartão** do Kanban (trocar o status sem abrir a demanda).
3. **Menu de ações na linha da Lista**: Concluir, Cancelar, Reabrir e Transferir responsabilidade agora só existem dentro da ficha da demanda.
4. **Setor lembrado** no Kanban e a explicação "este setor ainda não tem etapas" com o atalho "Configurar etapas".
5. **Paginação** da Lista (a atual lista tudo).
6. **Calendário em grade semanal** (o atual é uma lista de prazos; a grade mensal está prevista na fase do Calendário).
