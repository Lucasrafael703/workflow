# 10 — Frontend

> A interface é renderizada no servidor com templates do Django. CSS e
> JavaScript são arquivos estáticos simples — **não há `package.json`,
> bundler nem etapa de build**. As telas funcionam sem JavaScript sempre que
> possível; o JS melhora a experiência (arrastar, modais, busca), mas envia os
> mesmos formulários que já existem na página. Identidade visual em
> `Telas/Elementos/` e `Telas/MENU_E_SUBMENUS_LPS.md`.

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
| `processes/` | Lista, criação e edição de processo |
| `painel/em_construcao.html` | Tela em branco dos itens de menu ainda não construídos |
| `registration/` | Assunto e corpo do e-mail de recuperação de senha |

Convenção: arquivos que começam com `_` são **parciais** incluídos em outras
telas ou devolvidos por Ajax — ex.: `activities/_task_drawer.html`, `_task_checklist.html`, `_timeline.html`,
`_tasks_block.html`, `_activity_kanban_card.html`, `_process_panel.html`.

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
| `acessos.context_processors.navigation` | `lps_nav` (flags `management`, `cadastros`, `users`, `security`), `lps_org`, `lps_open_tasks`, `nav_active`, `nav_active2`, `nav_cadastros_tab` | o que o menu mostra e qual item está ativo — só UX |
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
| `task-kanban.js`, `activity-kanban.js` | Kanban com arrastar; ao soltar, só atualiza `stage` |
| `task-stage-reorder.js` | Reordenar estágios de tarefa |
| `person-picker.js`, `person-multi-picker.js` | Seletor de pessoa (responsável) e de várias pessoas (participantes), usando `api/pessoas/` |
| `tag-picker.js` | Seletor de tags com chips |
| `mention.js` | Autocomplete de `@menção` em campos marcados |
| `rich-text.js` | Editor de descrição (`contenteditable`); o HTML é sanitizado no servidor por `core/sanitize.py` |
| `form-summary.js` | Resumo ao lado do formulário, atualizado ao digitar |
| `process-apply.js` | Popup "Aplicar processo": 4 passos num só formulário (Processo → Responsáveis → Entradas → Confirmar). Mostra/habilita só os campos da versão escolhida; nenhuma regra de negócio (o servidor valida tudo). Registra-se em `window.LPSWidgets` para funcionar dentro do `LPSModal` |
| `process-editor.js` | Editor de processo: no "Adicionar etapa", sugere primeiro as pessoas do setor escolhido para o responsável padrão (as de outros setores ficam atrás de "Mostrar pessoas de outros setores") |
| `color-utils.js`, `color-palette-picker.js` | Paleta de 36 cores (espelha `core/colors.py`) e seletor |
| `notifications.js` | Evita que o cache do navegador mostre contador/lista antigos |
| `auth.js` | Mostrar/ocultar senha nas telas de conta |

Ao mudar a paleta, altere **os dois**: `core/colors.py` e
`static/js/color-utils.js`.

---

## 5. CSS e imagens

- `static/css/app.css`: todo o estilo da aplicação.
- `static/css/auth.css`: telas de conta (login, cadastro, confirmação).
- `static/img/`: favicon e logos da LPS (completo, completo escuro, símbolo).

Em produção os arquivos são coletados por `collectstatic` em `staticfiles/` e
servidos pelo whitenoise com nome versionado por hash — ao editar um CSS/JS,
basta fazer deploy; não é preciso trocar a URL no template (use sempre
`{% static %}`).

## 6. Experiência unificada de atividades

O editor de criação/edição é `activities/activity_form.html`, com os campos
agrupados em `ActivityEditorForm` e estilo em `static/css/activity-workspace.css`.
A antiga ficha lateral foi retirada; lista, quadro e calendário abrem a mesma ficha.

`static/js/activity-workspace.js` liga os links `data-activity-action` ao modal
compartilhado e remove anexos sem descartar o texto ainda não salvo no editor.
`modal.js` preserva a janela anterior ao abrir um cadastro auxiliar, impede envio
duplicado, mostra erros de validação/rede, controla foco por teclado e devolve
foco ao elemento de origem ao fechar.
