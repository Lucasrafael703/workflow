# 10 — Frontend

> A interface é renderizada no servidor com templates do Django. CSS e
> JavaScript são arquivos estáticos simples — **não há bundler nem etapa de
> build**; o `package.json` da raiz existe só para os testes JavaScript com jsdom
> (`npm run test:js`, ver `11_TESTES.md`). As telas funcionam sem JavaScript sempre
> que possível; o JS melhora a experiência (arrastar, modais, busca), mas envia os
> mesmos formulários que já existem na página. Identidade visual em
> `Telas/Elementos/` e `Telas/MENU_E_SUBMENUS_LPS.md`.

**Estado em 03/10/2026.** Na interface "Atividade" virou **Demanda** (código segue
`Activity`), "Situação" virou **Etapa** e "Condição" virou **Status**. As telas
operacionais passaram a ser **quadros dinâmicos** (`boards`): `/demandas/` (Lista,
Kanban e Calendário) e `/tarefas/` (painel do que está nos quadros de Demanda) usam o
motor de Quadros. Desde 02/10/2026 `/fila/`, `/processos/*`, `/conflitos/*`, `/prazos/*`
e `/tarefas/<pk>/…` respondem **410** (`RetiredFeatureView`), e `/entrada/` fica inativa
por padrão (`INTAKE_ENABLED=False`). Muitos templates e scripts dessas telas continuam no
repositório; as tabelas abaixo marcam o que está **ativo** e o que é **legado**
(arquivo presente, sem rota ou sem script que o carregue). Ver também
`LPS_ELEMENTOS_SUBELEMENTOS_PROCESSOS.md` e `LPS_VISUALIZACAO_CALENDARIO.md`.

---

## 1. Templates (`templates/`)

| Pasta / arquivo | Conteúdo |
|---|---|
| `base.html` | Casca da aplicação: menu lateral (recolhível), barra superior com cronômetro e sino, mensagens, blocos `{% block %}` (`content`, `scripts`). Carrega a fonte Inter (Google Fonts), todos os CSS globais e, para quem está autenticado, os scripts de uso geral (`shell`, `modal`, `activity-steps`, `person-picker`, `person-multi-picker`, `tag-picker`, `rich-text`, `mention`, `workflow-picker`, `color-utils`, `color-palette-picker`, `activity-workspace`, `workspace-filters`); os scripts de cada tela entram pelo bloco `scripts` |
| `_icon.html`, `_icons.html`, `_logo.html` | Ícones SVG (sprite em `_icons.html`) e logo, incluídos com `{% include %}` |
| `_sector_badge.html`, `_sector_picker.html`, `_sheet_progress.html`, `_sheet_status.html` | Componentes compartilhados na raiz: selo colorido de setor (variantes `table`, `compact`, `inline`; cores em `--sector-color`/`--sector-text-color`), seletor de setor (`data-picker-kind="sector"`, usa `api/setores/`), progresso compacto "N de M" e selo de status das listas legadas (`lps-sheet-*`) |
| `accounts/` | Login, criar conta, confirmar e-mail, trocar e-mail, perfil, recuperação de senha |
| `activities/` | 67 arquivos. **Ativos:** `home.html` (`/`), `activity_detail.html` (ficha da Demanda, com a conversa e a prévia do Quadro), `activity_form.html` (janela de 4 etapas, criar e editar), `activity_wizard_step2/3.html`, janelas de ação da Demanda (`activity_cancel/reopen/change_owner/change_deadline/finalize_form/pending_form/approve_pendency_form.html`), `management.html` (`/gestao/`), `history.html` (`/historico/`) e os parciais de campo (`_form_field(s)`, `_activity_field`, `_activity_modal_field`, `_task_field`). **Legado (view existe, rota fixa desativada ou substituída pelo quadro):** lista e Kanban antigos (`activity_list.html` em `/demandas/lista-legada/`, `activity_kanban.html` em `/demandas/kanban-legado/`, `activity_calendar.html`, `_activity_row/_toolbar/_view_tabs/_scope_tabs`, `_kanban_*.html`), tudo de tarefa (`task_detail/list/calendar/kanban/edit_form/quick_form(_standalone)/action_form/retroactive_form/change_responsavel.html`, `_task_*.html`, `_tasks_block.html`, `_timeline.html`), `queue.html` (`/fila/`), `conflict_resolve.html` e o processo aplicado (`activity_process_apply.html`, `_process_panel.html`). A barra de filtros compartilhada é `_workspace_filter_toolbar.html` |
| `core/` | 13 arquivos: cadastros (`cadastros.html`, `cadastro_form.html`), configurações (`settings.html`, `prioridades.html`, **`etapas_e_status.html`** — Etapas e Status por setor, com `flow-config.js`), usuários (`user_list/user_form/user_access.html`, `_access_fields.html`), permissões (`permissions.html`), perfil (`profile_form.html`) e parciais `_field.html`, `_toggle_form.html` |
| `notifications/` | Caixa de notificações, textos de e-mail em `email/*.txt` |
| `boards/` | Quadros: `board_list.html`, `board_detail.html` (a tabela), `board_history.html`, **`board_kanban.html`** (a visualização Kanban), **`board_calendar.html`** (a visualização Calendário; o corpo, que o servidor redesenha, é `_calendar_body.html`, com `_calendar_day.html` e `_calendar_card.html`), `_item_drawer.html` (a gaveta do item) e os parciais `_board_head.html` e `_board_view_tabs.html` (cabeçalho e abas, compartilhados pela tabela e pelo Kanban), `_kanban_lanes.html` e `_kanban_card.html` (o cartão reaproveita `_cell.html`: o campo do cartão é o mesmo desenho da célula da tabela), `_group.html`, `_item_row.html`, `_cell_td.html` (`<td>` com `data-cell`, `data-value` cru para o editor), `_cell.html` (o desenho por tipo) e `_column_header.html`. O servidor desenha tudo; o JS só liga comportamento e troca fragmentos que o servidor devolve (`header_html`, `cell_html`, `row_html`, `group_html`). Filtros e tags em `boards/templatetags/lps_board.py` (ver seção 3). |
| `boards/` (superfícies de domínio) | Telas de Demandas e Tarefas sobre o motor de Quadros: **`demand_work_board.html`** (`/demandas/`, `/demandas/kanban/`, `/demandas/calendario/`: a Lista usa a edição inline; o Kanban usa `work-board.js`), `work_board.html` (visualização genérica de domínio), **`task_center.html`** (`/tarefas/`, `/tarefas/kanban/`, `/tarefas/calendario/`: painel do que está nos quadros de Demanda em que a pessoa é responsável, com "+ Adicionar"), `task_board.html` (escolha de uma Demanda para abrir o respectivo quadro) e `_board_workspace.html` (corpo compartilhado de `board_detail.html` e `task_board.html`). Parciais `_work_toolbar.html`, `_work_table.html`, `_work_cell.html`, `_work_kanban.html`, `_work_kanban_card.html`, `_work_calendar.html` e `_demand_kanban_settings.html` (painel "Adicionar campo" / configurar cartões do Kanban de Demandas) |
| `intake/` | Caixa de Entrada: `intake_list.html`, `intake_detail.html`, as janelas `intake_capture/_edit/_convert/_ignore.html` e os parciais `_item_card`, `_facts`, `_actions`, `_source_icon`, `_modal_head`, `_modal_foot`, `_form_errors`. As janelas reaproveitam o casco `activity-modal` e os campos de `activities/_activity_modal_field.html` |
| `processes/` | `process_list.html`, `process_new.html`, `process_edit.html` — **desativado**: todas as rotas de `/processos/` respondem 410 e as telas não são alcançáveis; os arquivos ficam como referência |
| `painel/em_construcao.html` | Tela em branco dos itens de menu ainda não construídos |
| `registration/` | Assunto e corpo do e-mail de recuperação de senha |

Convenção: arquivos que começam com `_` são **parciais** incluídos em outras
telas ou devolvidos por Ajax — ex.: `boards/_item_drawer.html`, `boards/_calendar_body.html`,
`activities/_task_drawer.html`, `_task_checklist.html`, `_timeline.html`, `_tasks_block.html`, os
parciais `_kanban_*.html` e `_workflow_*.html` (`_workflow_controls.html`, `_workflow_picker_attrs.html`).
No total há 154 arquivos em `templates/` (raiz 8, `accounts` 9, `activities` 67, `boards` 30, `core` 13,
`intake` 13, `notifications` 5 (mais 3 de e-mail em `notifications/email/`), `painel` 1, `processes` 3, `registration` 2).

Processo aplicado (**legado**: `/demandas/<pk>/processo/aplicar/` responde 410): `activities/_process_panel.html` é o cartão **Processo** da
ficha (entradas, etapas, critérios; sem processo, o convite "Aplicar processo") e
`activities/activity_process_apply.html` é o popup de aplicação. Os estilos novos
(`proc-panel`, `proc-block`, `proc-item`, `proc-step`, `apply-*`) ficam no fim de
`static/css/app.css` e só usam variáveis, cards e tags que já existiam.
`activities/_form_fields.html` renderiza qualquer formulário campo a campo e é
reutilizado por várias telas.

As antigas pastas `templates/demands/` e `templates/workflows/` não existem mais.

---

## 2. Context processors

Disponíveis em todo template:

| Processor | Variáveis | Uso |
|---|---|---|
| `notifications.context_processors.unread_notifications_count` | contador de não lidas | sino |
| `acessos.context_processors.navigation` | `lps_nav` (flags `management`, `cadastros`, `users`, `security`, `intake`, `intake_can_view`, `boards`), `lps_org`, `lps_open_tasks` (contador do menu Tarefas), `lps_intake_new` (solicitações novas que a pessoa enxerga; uma avaliação de permissão e um `COUNT` por página), `nav_active`, `nav_active2`, `nav_cadastros_tab` | o que o menu mostra e qual item está ativo — só UX |
| `activities.context_processors.my_active_sessions` | `my_active_sessions`, `my_active_sessions_count` | cronômetro da barra superior (menu `[data-timer-menu]` tratado em `shell.js`) |

Os três estão em `TEMPLATES[...]['OPTIONS']['context_processors']` de `config/settings/base.py`, depois dos padrões `request`, `auth` e `messages`. Com `INTAKE_ENABLED=False` a flag `lps_nav.intake` fica falsa e o menu não mostra "Entrada".

---

## 3. Template tags

Duas bibliotecas. `{% load lps %}` (`activities/templatetags/lps.py`) só tem **filtros**:

| Filtro | O que faz |
|---|---|
| `text\|conversation_body` | (autoescape) Corpo de mensagem da conversa da Demanda: escapa o HTML e destaca `@menções` |
| `entry\|audit_phrase` | Converte um `AuditLog` em frase em português ("iniciou a tarefa") |
| `name\|field_label` | Nome amigável de um campo auditado |
| `timedelta\|duration_hm` | `4h20`, `35min` |
| `user\|avatar_color` | Cor do avatar (uma de 6, por `pk`) |

`{% load lps_board %}` (`boards/templatetags/lps_board.py`), usada pelos templates de `boards/`:

| Item | Tipo | O que faz |
|---|---|---|
| `item\|cell_of:column_id` | filtro | A célula do item para uma coluna |
| `mapping\|get_item:key` | filtro | Acesso a dicionário por chave dinâmica |
| `color\|contrast` | filtro | Cor de texto (claro/escuro) por luminância do fundo |
| `user\|initials`, `user\|person_name` | filtros | Iniciais e nome de exibição da pessoa |
| `column_type\|type_icon` | filtro | Ícone do tipo de coluna |
| `{% raw_value cell column %}` | `simple_tag` | Valor cru da célula (para `data-value`, lido pelo editor do JS) |
| `{% is_overdue cell column %}` | `simple_tag` | Se a célula de prazo está vencida |

---|---|
| `entry\|audit_phrase` | Converte um `AuditLog` em frase em português ("iniciou a tarefa") |
| `name\|field_label` | Nome amigável de um campo auditado |
| `timedelta\|duration_hm` | `4h20`, `35min` |
| `user\|avatar_color` | Cor do avatar (uma de 6, por `pk`) |

---

## 4. JavaScript (`static/js/`)

| Arquivo | Papel |
|---|---|
| `shell.js` | Casca: menu no celular, recolher o menu lateral, menu do cronômetro da barra superior, janelas de ação |
| `modal.js` | Busca um formulário existente via `fetch` e abre por cima da tela |
| `task-drawer.js` | **Legado (nenhum template carrega).** Painel lateral da tarefa sobre a ficha da atividade |
| `checklist.js` | **Legado (nenhum template carrega; coberto por `tests/checklist.test.cjs`).** Checklist da tarefa (página e painel), sem recarregar |
| `timer.js` | **Legado (nenhum template carrega).** Cronômetro da sessão; conta localmente, o servidor é a referência |
| `queue.js` | **Legado** (`queue.html`; `/fila/` responde 410). Arrastar para reordenar a fila (preenche o formulário de posição existente) |
| `kanban.js` | **Kanban legado** de Demandas e Tarefas por setor (carregado por `activity_kanban.html` e `task_kanban.html`; só `/demandas/kanban-legado/` responde — `/tarefas/kanban-legado/` cai no 410; o Kanban atual é o de `boards.js` e `work-board.js`): filtros que se aplicam ao escolher, menus, arrastar entre etapas (grava só a etapa), criar demanda na coluna, limite da coluna, gaveta ao clicar no cartão e cartões/contadores sempre em dia |
| `workflow-picker.js` | Seletor de Etapa e de Condição (cartão, menu "Mover para etapa", gaveta; carregado em todas as telas): opções do setor, "+ Nova etapa/condição" para quem gere o catálogo; avisa o quadro com `lps:workflow-changed` |
| `task-stage-reorder.js` | **Legado (nenhum template carrega).** Reordenar estágios de tarefa |
| `person-picker.js`, `person-multi-picker.js` | Seletor de pessoa (responsável) e de várias pessoas (participantes), usando `api/pessoas/` |
| `tag-picker.js` | Seletor de tags com chips |
| `mention.js` | Autocomplete de `@menção` em campos marcados |
| `rich-text.js` | Editor de descrição (`contenteditable`); o HTML é sanitizado no servidor por `core/sanitize.py` |
| `form-summary.js` | **Legado (nenhum template carrega).** Resumo ao lado do formulário, atualizado ao digitar |
| *(ações da tarefa)* | Os itens de Mais ações e o botão Editar tarefa usam `data-activity-action` (`activity-workspace.js` + `LPSModal`): abrem a janela, recarregam a ficha ao salvar e, se a janela falhar, navegam para a página. O menu `<details class="menu-more">` fecha ao escolher um item, ao clicar fora e com Esc (script inline em `task_detail.html`) |
| `activity-steps.js` | Janela de demanda em 4 etapas — **criar e editar são a mesma** — e o diálogo de confirmação ao trocar o quadro (ver seção 6). Registra-se em `window.LPSWidgets`; o teste `tests/activity-steps.test.cjs` exercita o fluxo com o `modal.js` real |
| `retroactive-work.js` | **Legado** (`task_retroactive_form.html`; rota `/tarefas/<pk>/ja-realizei/` responde 410). Popup “Já realizei este trabalho”: avisa quando a data é de um dia anterior e mostra o comentário só quando é necessário (motivo *Outro* ou trabalho de mais de 7 dias atrás). Nenhuma regra mora aqui — o servidor valida tudo; sem JavaScript o comentário fica sempre visível. Registra-se em `window.LPSWidgets` |
| `process-apply.js` | **Legado** (processos desativados; `/demandas/<pk>/processo/aplicar/` responde 410). Popup "Aplicar processo": 4 passos num só formulário (Processo → Responsáveis → Entradas → Confirmar). Mostra/habilita só os campos da versão escolhida; nenhuma regra de negócio (o servidor valida tudo). Registra-se em `window.LPSWidgets` para funcionar dentro do `LPSModal` |
| `process-editor.js` | **Legado** (`process_edit.html`; `/processos/*` responde 410). Editor de processo: no "Adicionar etapa", sugere primeiro as pessoas do setor escolhido para o responsável padrão (as de outros setores ficam atrás de "Mostrar pessoas de outros setores") |
| `color-utils.js`, `color-palette-picker.js` | Paleta de 36 cores (espelha `core/colors.py`) e seletor |
| `task-modal.js` | **Legado (nenhum template carrega).** Janela de tarefa: troca o seletor de atividade pelo cartão da atividade escolhida e liga o botão “Alterar”. Registra-se em `window.LPSWidgets`. Teste: `tests/task-modal.test.cjs` (inclui o `person-picker.js` real) |
| `activity-inline-edit.js` | **Edição inline da lista de Demandas** (`/demandas/`, só em `boards/demand_work_board.html`): clicar no título, no responsável ou no prazo edita ali mesmo. Eventos delegados em `[data-activity-list]`; endereços em `data-*` da tabela (id fictício trocado por `fillUrl`). Cada célula tem um **modelo estruturado** e é redesenhada a partir dele (nunca por cópia de `innerHTML`; todo texto de usuário entra por `textContent`), **uma requisição por vez por célula** (`aria-busy`) e um número de revisão. **Otimista**: a célula muda na hora e volta ao último valor *confirmado* se o servidor recusar; **sucesso é silencioso** (só um realce `is-saved`), **erro** mostra um aviso curto (`.lps-toast.is-error`, `role="alert"`). Um único pop-over, na camada global `#activity-inline-overlay-root` (`position:fixed`), que acompanha scroll e resize e fecha por clique fora ou Esc; busca de pessoas em `api/pessoas/` (debounce 250 ms, descarta resposta velha). Título: Enter/blur salva, Esc cancela, vazio nunca salva. Prazo: data + hora opcional, Limpar/Aplicar. Só quem pode recebe os atributos `data-inline-field` (a lista decide por `inline_flags`; o servidor confere de novo). Editores mais ricos entram por **plugins** (`LPSInlineEdit.use`), que recebem a mesma infraestrutura (estado por célula, `save` otimista com revisão, `getJSON`/`postJSON`, pop-over único, `onSaved`, células ligadas que ficam travadas até a resposta). Exporta `window.LPSInlineEdit` (`helpers`, `init`, `boot`, `use`) para os testes. O CSS (`.activity-inline-*`) fica em `demand-board.css`: em repouso a tabela é idêntica (verificado por geometria e pixels contra o HEAD). |
| `task-center.js` | Tela Tarefas (`/tarefas/`): "+ Adicionar" no fim da Lista e de cada coluna do Kanban. Abre um formulário inline (nome + Demanda, só as Demandas onde a pessoa pode criar item, vindas em `#task-center-add`) e cria o item pelo endpoint `board-item-create` (JSON, CSRF): responsável = a pessoa e Status = etiqueta da coluna (A fazer usa a padrão do quadro). Erro 403/400 e queda de conexão aparecem no formulário; sucesso recarrega mantendo os filtros. Todo texto entra por `textContent`. Exporta `window.LPSTaskCenter` (`buildBody`, `init`). CSS em `task-center.css` (inclui a prévia do Quadro na ficha da Demanda). |
| `activity-inline-options.js` | Plugin do anterior (só em `boards/demand_work_board.html`, modo Lista): as células **coloridas Setor, Estágio e Status** viram pop-over na tela, sem janela. Lista de botões coloridos de largura total (cor e cor do texto vêm do servidor; só `#RRGGBB` entra), opção atual com ✓ e anel, busca local (sem acento) acima de 8 opções, setas/Enter/Esc. **Setor**: trocar e **criar** (nome + 36 cores da paleta oficial, `LPSColors.PALETTE`) com “Criar e aplicar” numa só gravação; trocar redefine Estágio e Status (as duas células ficam travadas e são redesenhadas com o `derived` do servidor). **Estágio/Status**: escolher, limpar (só Status, “Sem condição”), criar (“Criar e aplicar” = cria a opção e depois a aplica) e, para quem gere as opções do setor, **editar nome e cor** ali mesmo, com propagação para todas as linhas da página que mostram a mesma opção; link “Gerenciar estágios e status” (só endereço do próprio site). Erros de criar/editar aparecem no próprio pop-over. Mantém a segunda linha “Vencida há N dias” do Status (derivada do prazo) em dia quando o Prazo é editado. O CSS fica em `demand-board.css` (`.activity-inline-color-*`, `.activity-inline-swatch*`, `.activity-inline-edit-*`, `.demand-board__inline-cell`). |
| `boards.js` | Quadros (`static/js/boards.js`, sem dependências): seletor de tipo de coluna, criar coluna/item/grupo **sem recarregar**, renomear no lugar (Enter salva, Esc cancela), redimensionar (arrastar a borda ou setas, 96–640), reordenar colunas e mover itens **por arraste** (envia os dois vizinhos), editores de célula dos 8 tipos (texto/número inline, data nativa, etiquetas, busca de pessoa, checkbox), gerenciador de etiquetas, configurações da coluna, conversão de tipo com confirmação, menu de coluna/item/grupo, grupos recolhíveis (guardado no `localStorage`), teclado nas células (setas, Enter/F2, Delete, Espaço). **Autosave otimista**: a célula muda na hora e volta ao valor anterior, com aviso, se o servidor recusar; o indicador "Salvando…/Salvo/Erro ao salvar" fica no topo. Pop-overs e janelas têm foco devolvido ao botão, Escape e (janelas) Tab preso. Como cada grupo repete os títulos, mexer numa coluna atualiza **todos** os títulos (`thAll`): criar insere em cada grupo, renomear/configurar troca em cada grupo, mover reordena em cada grupo e excluir remove de todos; redimensionar vale para todos (a largura é do `<colgroup>`). Exporta `window.LPSBoards` (`helpers`, `init`) para os testes. **Modo Kanban** (`[data-kanban-lanes]` na página): arrastar o cartão entre raias grava a etiqueta da coluna agrupadora pelo endpoint da célula (otimista; recusa devolve o cartão), e depois pede as raias de novo (`board-view-lanes`) para o servidor redistribuir e recalcular as somas; campos do cartão editam com os mesmos editores da tabela (`[data-cell]` serve a `<td>` e a `<dd>`); criar na raia manda `initial` junto; menu do cartão ("Mover para", Renomear, Excluir) como alternativa ao arrastar; renomear/recolorir raia e "Editar etiquetas" mexem na etiqueta; janela "Configurar cartões" (agrupar, raia em branco, soma, nomes dos campos, campos do cartão com ↑↓ e pré-visualização) **salva sozinha** a cada mudança; abas: "+" (nova visualização: Kanban ou Calendário; o Calendário num quadro sem coluna de Data oferece criar a coluna ali mesmo), renomear e excluir. **Modo Calendário** (`[data-cal-body]` na página): passar o mouse no dia mostra "+ Adicionar" (sempre visível sem mouse), que abre a janela de criar **por cima do calendário** com a data do dia (e título, grupo, horário opcional e os campos do cartão), mandando tudo em um `initial` só; arrastar o cartão para outro dia grava **só** a célula de data (mantém a hora; otimista, volta com aviso "O item voltou para dd/mm/aaaa" se o servidor recusar; dia que a coluna não aceita não é alvo); clicar no cartão abre a **gaveta** (`board-item-detail`) e clicar num campo do cartão edita o campo (com `[data-cell]`, os mesmos editores da tabela); a data se edita num pop-over próprio (data nativa, horário opcional por botões ou digitado, "Limpar horário", "Limpar data"; quem gere colunas liga "Exibir horário" ali mesmo); "+ N mais", "Sem data" e "Atrasados" abrem listas em pop-over; Hoje/anterior/próximo trocam o mês **sem recarregar** (`board-view-calendar`, a busca e a pessoa seguem e o endereço é atualizado com `?mes=`); "Configurar calendário" (data utilizada, colorir por, escala, fins de semana, concluídos e campos do cartão com ↑↓ e pré-visualização) salva sozinha a cada mudança. `request(endpoint, body, {quiet: true})` não mexe no indicador "Salvando…" (navegar e abrir a gaveta não são gravações). Escape fecha primeiro o pop-over e só depois a gaveta. |
| `activity-workspace.js` | Carregado em todas as telas autenticadas. Liga os links `data-activity-action` ao modal compartilhado, remove anexos sem descartar o texto não salvo do editor e expõe `window.LPSAjax` (`applyResult`: remove/troca cartão, segue `redirect_url` ou recarrega). Teste: `tests/activity-workspace.test.cjs` |
| `workspace-filters.js` | Barra de filtros compartilhada (`_workspace_filter_toolbar.html`, `data-workspace-filters`): um pop-over aberto por vez (`[data-workspace-popover]`, Esc e clique fora fecham), troca de setor reenvia o formulário (`data-workspace-sector`) e trava o envio duplo. Teste: `tests/workspace-filters.test.cjs` |
| `work-board.js` | Visualizações de domínio (`work_board.html`, Kanban de `demand_work_board.html`): arrastar o cartão entre raias grava pelo serviço do domínio (otimista; volta o cartão se o servidor recusar), editor inline de célula (`data-work-cell`), painel "Adicionar campo" (`workboard-field-create`), configuração do cartão e "agrupar por" (`workboard-view-settings`), aviso `[data-work-board-toast]`. Teste: `tests/work-board.test.cjs` |
| `demand-conversation.js` | Conversa da Demanda (`activity_detail.html`): rótulo do anexo escolhido e inserção no cursor (menções/respostas); publicar, reagir e responder são formulários HTML normais |
| `flow-config.js` | Tela Etapas e Status (`core/etapas_e_status.html`): arrastar e soltar para reordenar (`[data-flow-reorder]`); só move a linha depois que o servidor confirma a ordem (`flow-config-reorder`) |
| `demand-board.js` | **Legado (nenhum template carrega).** Criação rápida de tarefa no Quadro de Demanda (`[data-demand-task-composer]`); a criação passou ao `boards.js` e ao `task-center.js` |
| `intake.js` | Caixa de Entrada: abre as ações (`a[data-intake-action]`) em `LPSModal` e aplica a resposta (`LPSAjax.applyResult`: remove o cartão, troca o cartão, segue `redirect_url` ou recarrega); o formulário `form[data-intake-restore]` envia por `fetch`, com trava de envio duplo. Depende só de `LPSModal.open` e `LPSAjax`; sem eles, ou se a janela falhar, o link abre a página completa. Teste: `tests/intake.test.cjs` |
| `access-editor.js` | Telas de acesso (usuário e grupo): escolher um grupo marca as telas; o que sobe acima do grupo vira "Ajuste individual" (com "Voltar ao padrão do grupo"); "Nenhuma / Todas: ver / Todas: editar" por seção; prévia do menu e contagens na hora; aviso quando uma tela só funciona com a organização inteira; equipes (papel e principal) e senha provisória. O servidor decide tudo — sem o script a página ainda envia o formulário. Teste: `tests/access-editor.test.cjs` |
| `notifications.js` | Evita que o cache do navegador mostre contador/lista antigos |
| `auth.js` | Mostrar/ocultar senha nas telas de conta |

Ao mudar a paleta, altere **os dois**: `core/colors.py` e
`static/js/color-utils.js`.

**Quem carrega o quê.** `base.html` carrega o conjunto geral (seção 1). `boards.js` só entra em
`board_detail.html`, `board_kanban.html`, `board_calendar.html` e `task_board.html`; `work-board.js` em `work_board.html` e,
no modo Kanban, em `demand_work_board.html`; `activity-inline-edit.js` e `activity-inline-options.js` na Lista de
`demand_work_board.html`; `task-center.js` em `task_center.html`; `demand-conversation.js` em `activity_detail.html`;
`flow-config.js` em `etapas_e_status.html`; `auth.js` nas telas de conta. Namespaces globais usados entre scripts:
`LPSModal`, `LPSWidgets`, `LPSAjax`, `LPSColors`, `LPSBoards`, `LPSInlineEdit`, `LPSTaskCenter`. Testes de cada
script em `11_TESTES.md`. No total há 35 arquivos `.js` em `static/js/` (cerca de 8,7 mil linhas; `boards.js` sozinho tem ~2,6 mil).

---

## 5. CSS e imagens

- `static/css/app.css` (~4,5 mil linhas): tokens (`:root`), casca, formulários, listas, cartões, selos e componentes gerais; os blocos `proc-*` e `lps-sheet-*` são do processo e das listas legadas.
- `static/css/auth.css`: telas de conta (login, cadastro, confirmação).
- `static/css/activity-workspace.css`: janela de atividade e utilitários da área de atividades
  (classes `activity-*`); a Caixa de Entrada reaproveita o casco e os campos.
- `static/css/task-modal.css`: janela de tarefa (`.task-*`: seções numeradas, cartão da atividade,
  grade de prazo, participantes); o casco vem de `activity-workspace.css`.
- `static/css/kanban.css`: quadro Kanban (`.kanban-*`, `.condition-chip`) e o seletor de Etapa/Condição (`.workflow-*`); carregado em
  todas as telas porque a gaveta também usa o seletor. O CSS do quadro antigo (`.activities-kanban-*`, `.tasks-kanban-*`,
  `.kanban-*` antigos) saiu do `app.css`.
- `static/css/boards.css`: Quadros e Kanban (`board-*`, `boards-*`, `kanban-*`; a cor da raia é `--lane-color`, vinda da etiqueta, e o texto `--lane-text` por luminância): tabela de largura fixa por coluna (`table-layout: fixed` + `<colgroup>`; **cada grupo tem a sua linha de títulos das colunas** logo abaixo do nome do grupo, como no Monday: `tr.board-cols-row` dentro de cada `tbody[data-group]`, fixa no topo ao rolar; a primeira coluna também fica fixa), faixa de cor do grupo (`--group-color`), pop-overs, janelas, avisos. Etiqueta sempre com o **texto** escrito (nunca só cor) e o texto claro/escuro escolhido por luminância. O Calendário usa `cal-*` (grade, dia, cartão com a cor da etiqueta em `--card-color`, listas e janela de criar) e a gaveta `board-drawer*`; o "+ Adicionar" do dia só aparece no hover/foco (e sempre em tela sem mouse). Carregado em `base.html`.
- `static/css/access.css`: telas de acesso (`access-*`, `seg*` — controle Sem acesso/Ver/Editar sobre radios —, `group-card*`, `team-table*`, `menu-preview*`, `compare-table*`, `group-badge--*`, `state--*`). Estado nunca é só cor: todo selo e nível traz texto.
- `static/css/intake.css`: Caixa de Entrada (`intake-*`, selos `tag--NOVO|CONVERTIDO|IGNORADO` e
  `intake-confidence--alta|media|baixa`). Estado nunca é só cor: todo selo traz texto.
- `static/css/work-board.css`: visualizações de domínio (`.work-board*`, `.work-toolbar*`, `.work-table*`, `.work-kanban*`, `.work-card*`, `.work-calendar*`, `.work-card-settings`, aviso `.work-board__toast`); o arquivo está minificado em uma linha.
- `static/css/demand-board.css`: Tela de Demandas (`.demand-board__*`: abas de visão e de escopo, filtros rápidos, tabela, cartão do calendário) e a edição inline (`.activity-inline-*`, `.activity-inline-color-*`, `.demand-board__inline-cell`).
- `static/css/task-center.css`: tela Tarefas (`.task-center__*`: abas, tabela, semana/dia) e a prévia do Quadro na ficha da Demanda (`.task-preview__*`).
- `static/css/demand-conversation.css`: conversa da Demanda (`.demand-conversation`, `.conversation-*`: mensagens, reações, respostas, anexos).
- `static/css/notification-page.css`: página de Notificações (`.notification-*`).
- Ícones novos no sprite (`_icons.html`): `mail` e `chat`.
- Todos os CSS acima, exceto `auth.css` (carregado só nas telas de conta), são carregados por `base.html` com `?v=` de versão manual.
- `static/img/`: `favicon.svg` e logos da LPS (`logo-lps-full.png`, `logo-lps-full-dark.png`, `logo-lps-symbol.png`, `logo-lps.jpeg`).

### Identidade visual

Tokens em `:root` de `app.css`: azuis da marca (`--brand-navy #1b3a63`, `--brand-navy-deep #12294a`, `--brand-blue #1b62c4`,
`--brand-blue-light #61a5f2`) e, desde 30/09/2026, o **verde da marca** (`--brand-green #18B981`, `-hover`, `-soft`, `-border`),
usado em abas ativas, barras de progresso e destaques de sucesso. Menu lateral em navy (`--nav-bg`), ação principal em
`--primary` (azul), superfícies `--bg/--surface/--border`, texto `--text/--text-2/--muted` (contraste mínimo 4,5:1) e estados
`--danger/--warning/--success/--info` — **sempre com texto, nunca só cor**. Fonte **Inter** (Google Fonts). Raios `--radius 10px` e
`--radius-sm 7px`, sombras `--shadow` e `--shadow-lg`. `auth.css`, `boards.css` e `kanban.css` redeclaram `:root` com os tokens que
usam. Etiquetas e setores usam a paleta de 36 cores (`core/colors.py` ↔ `color-utils.js`) com o texto claro/escuro escolhido por
luminância. Não há tema escuro.

Em produção os arquivos são coletados por `collectstatic` em `staticfiles/` e
servidos pelo whitenoise com nome versionado por hash — ao editar um CSS/JS,
basta fazer deploy; não é preciso trocar a URL no template (use sempre
`{% static %}`).

## 6. Experiência unificada de atividades

O editor de criação/edição é `activities/activity_form.html`: uma janela de **quatro
etapas** (Informações principais → Cliente e obra → Quadro de tarefas → Descrição e arquivos) com
cabeçalho, indicador de progresso e rodapé fixos e só o miolo rolando. Os campos são
agrupados em `ActivityEditorForm` (`STEP_FIELDS`, `steps`) e o estilo está em
`static/css/activity-workspace.css` (classes `activity-*`, sobre os tokens de `app.css`).

`static/js/activity-steps.js` mostra uma etapa por vez, marca o progresso (✓ nas
concluídas), valida nome/atribuído a/setor antes de sair da etapa 1 e leva o Enter dos
campos de texto para “Continuar”. Todos os painéis são do **mesmo formulário** e só
ficam `hidden`, então nada se perde ao avançar ou voltar. Escuta o envio em captura
(antes do `LPSModal`) para que só o botão final envie e, quando o servidor devolve
erros, abre a etapa do primeiro erro. Sem o script as quatro etapas aparecem empilhadas.
**Criar e editar são a mesma janela**: as mesmas 4 etapas (Informações principais, Cliente e obra, **Quadro de tarefas** — começar em branco ou usar um quadro existente, e o campo “Modelo de quadro” só aparece e só é exigido no segundo caso —, Descrição e arquivos, sem upload), os mesmos botões (Continuar em toda etapa; “Criar demanda” / “Salvar alterações” só na última) e os mesmos textos. Erro ao montar o quadro (`BoardError`) volta como erro do formulário no passo 3. A janela de
edição aceita `?passo=N` (o clique em Cliente / Obra da lista de Demandas abre a etapa 2).

**Trocar o quadro ao editar.** O passo 3 da edição mostra o quadro **real** da demanda (“Quadro atual: criado em branco / a partir do modelo X · N tarefas”, vindo de `Board.source_template`, não do campo `Activity.board_setup_mode`, que pode estar velho). Escolher outra opção mostra o aviso “Trocar o quadro exclui as tarefas do quadro atual” e, no envio final, o `activity-steps.js` **bloqueia** o envio e abre o diálogo `[data-board-confirm]` (`role="alertdialog"`, foco em “Cancelar”, Esc fecha só o diálogo, Tab preso nele, clicar no fundo cancela, o resto da janela fica `inert`): “As N tarefas do quadro atual serão excluídas definitivamente. Esta ação não pode ser desfeita.” + “Novo quadro: …”. **Trocar quadro e excluir tarefas** marca a caixa `confirm_board_replace` e reenvia pelo botão final (`requestSubmit`, então passa pela validação e pelo `LPSModal` de sempre); **Cancelar** volta ao passo 3 sem enviar. Mudar a escolha de novo, ou o servidor recusar, zera a confirmação. Mesma escolha do quadro atual, criar demanda e demanda sem quadro **nunca** abrem o diálogo. Sem JavaScript a caixa “Confirmo a troca…” fica visível (o servidor exige a confirmação do mesmo jeito, `ConfirmationCheckbox`: só `1`/`true`/`on`). Quem não pode gerir a estrutura do quadro (`DemandBoardAccess.can_manage_structure`) vê o passo 3 somente leitura, com a frase “Só o responsável, quem criou a demanda ou quem gerencia quadros pode trocar o quadro.”
O editor de texto (`RichTextWidget`) ganhou tachado, lista numerada, marcador de
vazio e contador (`limit`); seu HTML passa por `sanitize_description` (permite
`s`/`strike`).
A antiga ficha lateral foi retirada; lista, quadro e calendário abrem a mesma ficha.

`static/js/activity-workspace.js` liga os links `data-activity-action` ao modal
compartilhado e remove anexos sem descartar o texto ainda não salvo no editor.
`modal.js` preserva a janela anterior ao abrir um cadastro auxiliar, impede envio
duplicado, mostra erros de validação/rede, controla foco por teclado e devolve
foco ao elemento de origem ao fechar.

### Janelas de tarefa: um padrão só

> **Legado (03/10/2026).** `/tarefas/<pk>/…` e `/demandas/<pk>/tarefas/rapida/` respondem 410; as janelas abaixo
> (`task_quick_form*.html`, `task_edit_form.html`, `_task_drawer.html`) e os scripts `task-modal.js` e `task-drawer.js`
> permanecem no repositório e nos testes de serviço/formulário, mas não são alcançáveis. As tarefas hoje são itens do quadro da
> Demanda (`boards.js`, `task-center.js`).

“Nova tarefa” (dentro de uma atividade, `task_quick_form.html`, e fora dela,
`task_quick_form_standalone.html`) e “Editar tarefa” (`task_edit_form.html`)
incluem o **mesmo corpo**, `activities/_task_editor_fields.html`. É uma tela só,
sem etapas (diferente de “Nova atividade”), em quatro seções numeradas, todas à vista:

    1 Tarefa                 atividade · o que fazer · setor · responsável
    2 Prazo e organização    data do prazo · hora do prazo · marcadores
    3 Participantes          (opcional)
    4 Instruções             (opcional) — editor de texto de `rich-text.js`

O casco (cabeçalho, corpo que rola, rodapé fixo, sobreposição com desfoque) é o da janela de
atividade (`.activity-modal*`, `_task_modal_head.html` e `_task_modal_foot.html`); os blocos
próprios são `.task-*` em `static/css/task-modal.css`. Em telas até 520px a janela vira uma
folha que sobe da base. Cada campo sai de `_task_field.html`, que mantém `.form-row` (é por ela
que o `modal.js` pendura o erro do servidor).

- **Uma fonte de palavras:** `TASK_LABELS`/`TASK_HELP` em `activities/forms.py`
  alimentam `TaskQuickCreateForm` e `TaskEditorForm`; mudar um rótulo muda nas
  duas janelas. (O painel lateral tem texto próprio em modo leitura.)
- **Atividade:** em “Nova tarefa” fora de uma atividade há o seletor; ao escolher, ele dá lugar
  a um cartão (título e “Cliente • Setor: X • N tarefas”) com o botão **Alterar**, que volta ao
  seletor já aberto. Dentro de uma atividade e na edição o cartão é só informação (a tarefa já
  pertence a ela). O resumo vem de `activity_summary()` (`forms.py`): a busca
  (`ActivitySearchView`) e a criação rápida devolvem `summary` e o `person-picker.js` entrega a
  opção escolhida em `event.detail.item`; `static/js/task-modal.js` só troca o seletor pelo
  cartão. Ao reabrir com erro, `TaskQuickCreateStandaloneForm.selected_activity` desenha o cartão
  pelo servidor.
- **Prazo:** dois campos, “Data do prazo” e “Hora do prazo” (`TaskDeadlineField`, que usa o
  `SplitDateOptionalTimeWidget` da atividade; `form.deadline_inputs` entrega os dois `<input>`
  para o template dar um rótulo a cada). Sem hora vale até 23:59, como no prazo da atividade;
  hora sem data é erro (“Informe a data do prazo.”), em vez de ser ignorada.
- **Edição:** o setor e o prazo combinado aparecem como informação
  (`.field-static` e `.task-note`); responsável e participantes também, para quem não tem a
  ação. O convite pendente fica dentro de “Participantes”.
- **Nada recolhível:** as seções ficam sempre abertas; um erro de campo aparece onde o campo está.
  (O painel lateral continua com `<details class="fold">`.)
- **Rótulo dos seletores:** `PersonPickerWidget`, `ClientPickerWidget`,
  `ActivityPickerWidget` e os seletores simples (setor, empresa, obra, centro de
  custo) herdam de `VisibleHiddenInput` (`core/widgets.py`): guardam o valor num
  input `hidden`, mas `is_hidden = False`. Sem isso o Django os tratava como
  campo escondido — sem rótulo nem ajuda em `_form_field.html` e, onde havia um
  laço de `hidden_fields`, desenhados duas vezes (era o que acontecia em
  “Nova tarefa”). Use `_activity_field.html` (aceita `hide_label` e `compact`)
  para campos dentro de janelas.
- **Painel lateral da tarefa** (`_task_drawer.html`): mesmo padrão em modo leitura —
  cabeçalho “Atividade: …” com os botões **Editar** e “Ver todos os detalhes” numa
  linha acima do título, Setor e Responsável em `.field-static`, e os blocos
  “Participantes” (com convites “aguardando aceite” e o link “Gerenciar
  participantes”) e “Prazo e detalhes” (prazo pedido, prazo combinado, instruções e
  marcadores). Checklist e comentários seguem como seções abaixo.
