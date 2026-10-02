# 10 — Frontend

> A interface é renderizada no servidor com templates do Django. CSS e
> JavaScript são arquivos estáticos simples — **não há `package.json`,
> bundler nem etapa de build**. As telas funcionam sem JavaScript sempre que
> possível; o JS melhora a experiência (arrastar, modais, busca), mas envia os
> mesmos formulários que já existem na página. Identidade visual em
> `Telas/Elementos/` e `Telas/MENU_E_SUBMENUS_LPS.md`.

O `package.json` desta etapa Ã© somente para os testes JavaScript com jsdom; o Render continua sem bundler ou etapa Node de build.

---

## 1. Templates (`templates/`)

| Pasta / arquivo | Conteúdo |
|---|---|
| `base.html` | Casca da aplicação: menu lateral (recolhível), barra superior com cronômetro e sino, mensagens, blocos `{% block %}` |
| `_icon.html`, `_icons.html`, `_logo.html` | Ícones SVG e logo, incluídos com `{% include %}` |
| `accounts/` | Login, criar conta, confirmar e-mail, trocar e-mail, perfil, recuperação de senha |
| `activities/` | Início, listas, Kanban, calendários, ficha da atividade, ficha da tarefa, wizard, fila, gestão, histórico |
| `core/` | Cadastros, configurações, usuários, permissões, etapas e status, prioridades |
| `notifications/` | Caixa de notificações, textos de e-mail em `email/*.txt` |
| `boards/` | Quadros: `board_list.html`, `board_detail.html` (a tabela), `board_history.html`, **`board_kanban.html`** (a visualização Kanban), **`board_calendar.html`** (a visualização Calendário; o corpo, que o servidor redesenha, é `_calendar_body.html`, com `_calendar_day.html` e `_calendar_card.html`), `_item_drawer.html` (a gaveta do item) e os parciais `_board_head.html` e `_board_view_tabs.html` (cabeçalho e abas, compartilhados pela tabela e pelo Kanban), `_kanban_lanes.html` e `_kanban_card.html` (o cartão reaproveita `_cell.html`: o campo do cartão é o mesmo desenho da célula da tabela), `_group.html`, `_item_row.html`, `_cell_td.html` (`<td>` com `data-cell`, `data-value` cru para o editor), `_cell.html` (o desenho por tipo) e `_column_header.html`. O servidor desenha tudo; o JS só liga comportamento e troca fragmentos que o servidor devolve (`header_html`, `cell_html`, `row_html`, `group_html`). Filtros em `boards/templatetags/lps_board.py` (`cell_of`, `contrast`, `initials`, `raw_value`, `is_overdue`, `type_icon`). |
| `intake/` | Caixa de Entrada: `intake_list.html`, `intake_detail.html`, as janelas `intake_capture/_edit/_convert/_ignore.html` e os parciais `_item_card`, `_facts`, `_actions`, `_source_icon`, `_modal_head`, `_modal_foot`, `_form_errors`. As janelas reaproveitam o casco `activity-modal` e os campos de `activities/_activity_modal_field.html` |
| `processes/` | Lista, criação e edição de processo |
| `painel/em_construcao.html` | Tela em branco dos itens de menu ainda não construídos |
| `registration/` | Assunto e corpo do e-mail de recuperação de senha |

Convenção: arquivos que começam com `_` são **parciais** incluídos em outras
telas ou devolvidos por Ajax — ex.: `activities/_task_drawer.html`, `_task_checklist.html`, `_timeline.html`,
`_tasks_block.html`, `_process_panel.html`, os parciais do quadro `_kanban_*.html` e `_workflow_*.html`.

Processo aplicado: `activities/_process_panel.html` é o cartão **Processo** da
ficha (entradas, etapas, critérios; sem processo, o convite "Aplicar processo") e
`activities/activity_process_apply.html` é o popup de aplicação. Os estilos novos
(`proc-panel`, `proc-block`, `proc-item`, `proc-step`, `apply-*`) ficam no fim de
`static/css/app.css` e só usam variáveis, cards e tags que já existiam.
`activities/_form_fields.html` renderiza qualquer formulário campo a campo e é
reutilizado por várias telas.

As pastas `templates/demands/` e `templates/workflows/` estão vazias (restos).

---

## 2. Context processors

Disponíveis em todo template:

| Processor | Variáveis | Uso |
|---|---|---|
| `notifications.context_processors.unread_notifications_count` | contador de não lidas | sino |
| `acessos.context_processors.navigation` | `lps_nav` (flags `management`, `cadastros`, `users`, `security`, `intake`, `intake_can_view`, `boards`), `lps_org`, `lps_open_tasks`, `lps_intake_new` (solicitações novas que a pessoa enxerga; uma avaliação de permissão e um `COUNT` por página), `nav_active`, `nav_active2`, `nav_cadastros_tab` | o que o menu mostra e qual item está ativo — só UX |
| `activities.context_processors.my_active_sessions` | `my_active_sessions`, `my_active_sessions_count` | cronômetro da barra superior |

---

## 3. Template tags (`{% load lps %}`)

Todos são **filtros**, em `activities/templatetags/lps.py`:

| Filtro | O que faz |
|---|---|
| `entry\|audit_phrase` | Converte um `AuditLog` em frase em português ("iniciou a tarefa") |
| `name\|field_label` | Nome amigável de um campo auditado |
| `timedelta\|duration_hm` | `4h20`, `35min` |
| `user\|avatar_color` | Cor do avatar (uma de 6, por `pk`) |

---

## 4. JavaScript (`static/js/`)

| Arquivo | Papel |
|---|---|
| `shell.js` | Casca: menu no celular, janelas de ação |
| `modal.js` | Busca um formulário existente via `fetch` e abre por cima da tela |
| `task-drawer.js` | Painel lateral da tarefa sobre a ficha da atividade |
| `checklist.js` | Checklist da tarefa (página e painel), sem recarregar |
| `timer.js` | Cronômetro da sessão; conta localmente, o servidor é a referência |
| `queue.js` | Arrastar para reordenar a fila (preenche o formulário de posição existente) |
| `kanban.js` | Quadro Kanban (só nas telas do quadro): filtros que se aplicam ao escolher, menus, arrastar entre etapas (grava só a etapa), criar demanda na coluna, limite da coluna, gaveta ao clicar no cartão e cartões/contadores sempre em dia |
| `workflow-picker.js` | Seletor de Etapa e de Condição (cartão, menu "Mover para etapa", gaveta; carregado em todas as telas): opções do setor, "+ Nova etapa/condição" para quem gere o catálogo; avisa o quadro com `lps:workflow-changed` |
| `task-stage-reorder.js` | Reordenar estágios de tarefa |
| `person-picker.js`, `person-multi-picker.js` | Seletor de pessoa (responsável) e de várias pessoas (participantes), usando `api/pessoas/` |
| `tag-picker.js` | Seletor de tags com chips |
| `mention.js` | Autocomplete de `@menção` em campos marcados |
| `rich-text.js` | Editor de descrição (`contenteditable`); o HTML é sanitizado no servidor por `core/sanitize.py` |
| `form-summary.js` | Resumo ao lado do formulário, atualizado ao digitar |
| *(ações da tarefa)* | Os itens de Mais ações e o botão Editar tarefa usam `data-activity-action` (`activity-workspace.js` + `LPSModal`): abrem a janela, recarregam a ficha ao salvar e, se a janela falhar, navegam para a página. O menu `<details class="menu-more">` fecha ao escolher um item, ao clicar fora e com Esc (script inline em `task_detail.html`) |
| `activity-steps.js` | Janela de atividade em 3 etapas (ver seção 6). Registra-se em `window.LPSWidgets`; o teste `tests/activity-steps.test.cjs` exercita o fluxo com o `modal.js` real |
| `retroactive-work.js` | Popup “Já realizei este trabalho”: avisa quando a data é de um dia anterior e mostra o comentário só quando é necessário (motivo *Outro* ou trabalho de mais de 7 dias atrás). Nenhuma regra mora aqui — o servidor valida tudo; sem JavaScript o comentário fica sempre visível. Registra-se em `window.LPSWidgets` |
| `process-apply.js` | Popup "Aplicar processo": 4 passos num só formulário (Processo → Responsáveis → Entradas → Confirmar). Mostra/habilita só os campos da versão escolhida; nenhuma regra de negócio (o servidor valida tudo). Registra-se em `window.LPSWidgets` para funcionar dentro do `LPSModal` |
| `process-editor.js` | Editor de processo: no "Adicionar etapa", sugere primeiro as pessoas do setor escolhido para o responsável padrão (as de outros setores ficam atrás de "Mostrar pessoas de outros setores") |
| `color-utils.js`, `color-palette-picker.js` | Paleta de 36 cores (espelha `core/colors.py`) e seletor |
| `task-modal.js` | Janela de tarefa: troca o seletor de atividade pelo cartão da atividade escolhida e liga o botão “Alterar”. Registra-se em `window.LPSWidgets`. Teste: `tests/task-modal.test.cjs` (inclui o `person-picker.js` real) |
| `activity-inline-edit.js` | **Edição inline da lista de Demandas** (`/demandas/`, só em `boards/demand_work_board.html`): clicar no título, no responsável ou no prazo edita ali mesmo. Eventos delegados em `[data-activity-list]`; endereços em `data-*` da tabela (id fictício trocado por `fillUrl`). Cada célula tem um **modelo estruturado** e é redesenhada a partir dele (nunca por cópia de `innerHTML`; todo texto de usuário entra por `textContent`), **uma requisição por vez por célula** (`aria-busy`) e um número de revisão. **Otimista**: a célula muda na hora e volta ao último valor *confirmado* se o servidor recusar; **sucesso é silencioso** (só um realce `is-saved`), **erro** mostra um aviso curto (`.lps-toast.is-error`, `role="alert"`). Um único pop-over, na camada global `#activity-inline-overlay-root` (`position:fixed`), que acompanha scroll e resize e fecha por clique fora ou Esc; busca de pessoas em `api/pessoas/` (debounce 250 ms, descarta resposta velha). Título: Enter/blur salva, Esc cancela, vazio nunca salva. Prazo: data + hora opcional, Limpar/Aplicar. Só quem pode recebe os atributos `data-inline-field` (a lista decide por `inline_flags`; o servidor confere de novo). Editores mais ricos entram por **plugins** (`LPSInlineEdit.use`), que recebem a mesma infraestrutura (estado por célula, `save` otimista com revisão, `getJSON`/`postJSON`, pop-over único, `onSaved`, células ligadas que ficam travadas até a resposta). Exporta `window.LPSInlineEdit` (`helpers`, `init`, `boot`, `use`) para os testes. O CSS (`.activity-inline-*`) fica em `demand-board.css`: em repouso a tabela é idêntica (verificado por geometria e pixels contra o HEAD). |
| `activity-inline-options.js` | Plugin do anterior (só em `boards/demand_work_board.html`, modo Lista): as células **coloridas Setor, Estágio e Status** viram pop-over na tela, sem janela. Lista de botões coloridos de largura total (cor e cor do texto vêm do servidor; só `#RRGGBB` entra), opção atual com ✓ e anel, busca local (sem acento) acima de 8 opções, setas/Enter/Esc. **Setor**: trocar e **criar** (nome + 36 cores da paleta oficial, `LPSColors.PALETTE`) com “Criar e aplicar” numa só gravação; trocar redefine Estágio e Status (as duas células ficam travadas e são redesenhadas com o `derived` do servidor). **Estágio/Status**: escolher, limpar (só Status, “Sem condição”), criar (“Criar e aplicar” = cria a opção e depois a aplica) e, para quem gere as opções do setor, **editar nome e cor** ali mesmo, com propagação para todas as linhas da página que mostram a mesma opção; link “Gerenciar estágios e status” (só endereço do próprio site). Erros de criar/editar aparecem no próprio pop-over. Mantém a segunda linha “Vencida há N dias” do Status (derivada do prazo) em dia quando o Prazo é editado. O CSS fica em `demand-board.css` (`.activity-inline-color-*`, `.activity-inline-swatch*`, `.activity-inline-edit-*`, `.demand-board__inline-cell`). |
| `boards.js` | Quadros (`static/js/boards.js`, sem dependências): seletor de tipo de coluna, criar coluna/item/grupo **sem recarregar**, renomear no lugar (Enter salva, Esc cancela), redimensionar (arrastar a borda ou setas, 96–640), reordenar colunas e mover itens **por arraste** (envia os dois vizinhos), editores de célula dos 8 tipos (texto/número inline, data nativa, etiquetas, busca de pessoa, checkbox), gerenciador de etiquetas, configurações da coluna, conversão de tipo com confirmação, menu de coluna/item/grupo, grupos recolhíveis (guardado no `localStorage`), teclado nas células (setas, Enter/F2, Delete, Espaço). **Autosave otimista**: a célula muda na hora e volta ao valor anterior, com aviso, se o servidor recusar; o indicador "Salvando…/Salvo/Erro ao salvar" fica no topo. Pop-overs e janelas têm foco devolvido ao botão, Escape e (janelas) Tab preso. Como cada grupo repete os títulos, mexer numa coluna atualiza **todos** os títulos (`thAll`): criar insere em cada grupo, renomear/configurar troca em cada grupo, mover reordena em cada grupo e excluir remove de todos; redimensionar vale para todos (a largura é do `<colgroup>`). Exporta `window.LPSBoards` (`helpers`, `init`) para os testes. **Modo Kanban** (`[data-kanban-lanes]` na página): arrastar o cartão entre raias grava a etiqueta da coluna agrupadora pelo endpoint da célula (otimista; recusa devolve o cartão), e depois pede as raias de novo (`board-view-lanes`) para o servidor redistribuir e recalcular as somas; campos do cartão editam com os mesmos editores da tabela (`[data-cell]` serve a `<td>` e a `<dd>`); criar na raia manda `initial` junto; menu do cartão ("Mover para", Renomear, Excluir) como alternativa ao arrastar; renomear/recolorir raia e "Editar etiquetas" mexem na etiqueta; janela "Configurar cartões" (agrupar, raia em branco, soma, nomes dos campos, campos do cartão com ↑↓ e pré-visualização) **salva sozinha** a cada mudança; abas: "+" (nova visualização: Kanban ou Calendário; o Calendário num quadro sem coluna de Data oferece criar a coluna ali mesmo), renomear e excluir. **Modo Calendário** (`[data-cal-body]` na página): passar o mouse no dia mostra "+ Adicionar" (sempre visível sem mouse), que abre a janela de criar **por cima do calendário** com a data do dia (e título, grupo, horário opcional e os campos do cartão), mandando tudo em um `initial` só; arrastar o cartão para outro dia grava **só** a célula de data (mantém a hora; otimista, volta com aviso "O item voltou para dd/mm/aaaa" se o servidor recusar; dia que a coluna não aceita não é alvo); clicar no cartão abre a **gaveta** (`board-item-detail`) e clicar num campo do cartão edita o campo (com `[data-cell]`, os mesmos editores da tabela); a data se edita num pop-over próprio (data nativa, horário opcional por botões ou digitado, "Limpar horário", "Limpar data"; quem gere colunas liga "Exibir horário" ali mesmo); "+ N mais", "Sem data" e "Atrasados" abrem listas em pop-over; Hoje/anterior/próximo trocam o mês **sem recarregar** (`board-view-calendar`, a busca e a pessoa seguem e o endereço é atualizado com `?mes=`); "Configurar calendário" (data utilizada, colorir por, escala, fins de semana, concluídos e campos do cartão com ↑↓ e pré-visualização) salva sozinha a cada mudança. `request(endpoint, body, {quiet: true})` não mexe no indicador "Salvando…" (navegar e abrir a gaveta não são gravações). Escape fecha primeiro o pop-over e só depois a gaveta. |
| `intake.js` | Caixa de Entrada: abre as ações (`a[data-intake-action]`) em `LPSModal` e aplica a resposta (`LPSAjax.applyResult`: remove o cartão, troca o cartão, segue `redirect_url` ou recarrega); o formulário `form[data-intake-restore]` envia por `fetch`, com trava de envio duplo. Depende só de `LPSModal.open` e `LPSAjax`; sem eles, ou se a janela falhar, o link abre a página completa. Teste: `tests/intake.test.cjs` |
| `notifications.js` | Evita que o cache do navegador mostre contador/lista antigos |
| `auth.js` | Mostrar/ocultar senha nas telas de conta |

Ao mudar a paleta, altere **os dois**: `core/colors.py` e
`static/js/color-utils.js`.

---

## 5. CSS e imagens

- `static/css/app.css`: todo o estilo da aplicação.
- `static/css/auth.css`: telas de conta (login, cadastro, confirmação).
- `static/css/activity-workspace.css`: janela de atividade e utilitários da área de atividades
  (classes `activity-*`); a Caixa de Entrada reaproveita o casco e os campos.
- `static/css/task-modal.css`: janela de tarefa (`.task-*`: seções numeradas, cartão da atividade,
  grade de prazo, participantes); o casco vem de `activity-workspace.css`.
- `static/css/kanban.css`: quadro Kanban (`.kanban-*`, `.condition-chip`) e o seletor de Etapa/Condição (`.workflow-*`); carregado em
  todas as telas porque a gaveta também usa o seletor. O CSS do quadro antigo (`.activities-kanban-*`, `.tasks-kanban-*`,
  `.kanban-*` antigos) saiu do `app.css`.
- `static/css/boards.css`: Quadros e Kanban (`board-*`, `boards-*`, `kanban-*`; a cor da raia é `--lane-color`, vinda da etiqueta, e o texto `--lane-text` por luminância): tabela de largura fixa por coluna (`table-layout: fixed` + `<colgroup>`; **cada grupo tem a sua linha de títulos das colunas** logo abaixo do nome do grupo, como no Monday: `tr.board-cols-row` dentro de cada `tbody[data-group]`, fixa no topo ao rolar; a primeira coluna também fica fixa), faixa de cor do grupo (`--group-color`), pop-overs, janelas, avisos. Etiqueta sempre com o **texto** escrito (nunca só cor) e o texto claro/escuro escolhido por luminância. O Calendário usa `cal-*` (grade, dia, cartão com a cor da etiqueta em `--card-color`, listas e janela de criar) e a gaveta `board-drawer*`; o "+ Adicionar" do dia só aparece no hover/foco (e sempre em tela sem mouse). Carregado em `base.html`.
- `static/css/intake.css`: Caixa de Entrada (`intake-*`, selos `tag--NOVO|CONVERTIDO|IGNORADO` e
  `intake-confidence--alta|media|baixa`). Estado nunca é só cor: todo selo traz texto.
- Ícones novos no sprite (`_icons.html`): `mail` e `chat`.
- `static/img/`: favicon e logos da LPS (completo, completo escuro, símbolo).

Em produção os arquivos são coletados por `collectstatic` em `staticfiles/` e
servidos pelo whitenoise com nome versionado por hash — ao editar um CSS/JS,
basta fazer deploy; não é preciso trocar a URL no template (use sempre
`{% static %}`).

## 6. Experiência unificada de atividades

O editor de criação/edição é `activities/activity_form.html`: uma janela de **três
etapas** (Informações principais → Informações do cliente → Descrição e arquivos) com
cabeçalho, indicador de progresso e rodapé fixos e só o miolo rolando. Os campos são
agrupados em `ActivityEditorForm` (`STEP_FIELDS`, `steps`) e o estilo está em
`static/css/activity-workspace.css` (classes `activity-*`, sobre os tokens de `app.css`).

`static/js/activity-steps.js` mostra uma etapa por vez, marca o progresso (✓ nas
concluídas), valida nome/atribuído a/setor antes de sair da etapa 1 e leva o Enter dos
campos de texto para “Continuar”. Todos os painéis são do **mesmo formulário** e só
ficam `hidden`, então nada se perde ao avançar ou voltar. Escuta o envio em captura
(antes do `LPSModal`) para que só o botão final envie e, quando o servidor devolve
erros, abre a etapa do primeiro erro. Sem o script as três etapas aparecem empilhadas.
A janela de **criar** tem 4 etapas (Informações principais, Cliente e obra, **Quadro de tarefas** — começar em branco ou usar um quadro existente, e o campo “Modelo de quadro” só aparece e só é exigido no segundo caso —, Descrição e arquivos, sem upload); a de **editar** tem 3, sem o quadro (a demanda já tem o seu). Erro ao montar o quadro (`BoardError`) volta como erro do formulário no passo 3. Ao **editar**, o botão “Salvar alterações” existe em qualquer etapa (`data-submit-anywhere`: tudo já
vem preenchido, e o envio ainda confere as três etapas); ao criar continua só na última. A janela de
edição aceita `?passo=N` (o clique em Cliente / Obra da lista de Demandas abre a etapa 2).
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
