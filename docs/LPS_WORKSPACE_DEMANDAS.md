# Workspace de Demandas (fase 1A) — o que é, como ligar e o que ficou de fora

> **Objetivo desta rodada não é construir o Workspace completo. É provar que uma pessoa consegue operar Demandas em um único contexto, sem precisar reaprender a interface ou perder seu estado.**
> Esta é a **fase 1A**: shell único + Lista nova, atrás de uma feature flag. A **1C (Kanban)** foi feita depois, por pedido explícito (§8): o Kanban de Demandas passou a ser o mesmo de Quadros. As fases 1D (Calendário) e 1E (extrair abstrações) **não foram feitas**: dependem do resultado do teste com pessoas (ver `LPS_TESTE_USABILIDADE_DEMANDAS.md`).

## 1. Como ligar e desligar

A flag é `WORKSPACE_V2`, lida das variáveis de ambiente (no Render: *Environment* do serviço web). **Desligada por padrão.**

| Valor | Quem vê o Workspace |
|---|---|
| `off` (padrão; qualquer valor desconhecido também) | ninguém: a tela de Demandas de sempre |
| `allowlist` | só quem estiver em `WORKSPACE_V2_USERS` (e-mails ou nomes de usuário, separados por vírgula, sem diferenciar maiúsculas) |
| `on` | todas as pessoas logadas |

Exemplo para o teste com cinco pessoas: `WORKSPACE_V2=allowlist` e `WORKSPACE_V2_USERS=paulo@biasiengenharia.com.br,ana@...,...`.
**Rollback imediato:** voltar `WORKSPACE_V2` para `off` (ou tirar a pessoa da lista). Não exige novo deploy de código. As rotas são as mesmas (`/demandas/`, `/demandas/kanban/`, `/demandas/calendario/`); só o template muda. Quem está fora da lista continua exatamente na tela antiga, que **não foi alterada**.

## 2. O que a pessoa vê

Cabeçalho, abas e barra são **os mesmos nas três visões**; só a área de conteúdo muda.

- **Cabeçalho:** título, contador do universo filtrado ("6 demandas", igual nas três visões) e **Criar demanda**.
- **Abas:** **Lista · Kanban · Calendário** ("Quadro" ficou de fora: colide com o módulo Quadros). Cada link leva a querystring inteira.
- **Barra:** **Escopo** (Minhas · Do meu setor · Participando · Todas, esta só com `ATIVIDADE_VISUALIZAR_TODAS`) · **Mostrar** (Em aberto · Concluídas) · **Buscar** · **Filtros** · **Agrupar** · **Ordenar** · (**Personalizar**, no Kanban, para quem pode configurar). Agrupar e Ordenar são contextuais (Lista e Kanban); o Calendário não os mostra. Nada aparece desabilitado.
- **Uma regra de interação:** *controles simples aplicam ao escolher; o painel Filtros é um rascunho com um único **Aplicar filtros**; a busca aplica com Enter.* Fechar o painel sem aplicar (Esc ou clicar fora) **descarta** o rascunho.
- **Painel Filtros:** Setor, Responsável (várias pessoas), Etapa, Status, Cliente, Obra, Prazo. Etapa e Status só oferecem as opções do setor escolhido. Cliente e Obra usam o seletor com busca (3 letras; a Obra depende do Cliente; "Todos os clientes" limpa). Os filtros ativos aparecem como **chips** removíveis.
- **Escopo não muda sozinho:** escolher outra pessoa em "Minhas" **não** troca o escopo; aparece o aviso *"Você está vendo só 'Minhas'. Fulano pode não aparecer. [Ver Todas]"* (o botão só existe para quem pode ver Todas).
- **Valor inválido** (ex.: `?cliente=abc`) é ignorado com o aviso *"Ignoramos o filtro inválido: …"* (antes dava erro 500).
- **Lista:** 6 colunas — Demanda (com `código · cliente · obra` e o progresso das tarefas), Setor, Responsável, Prazo, Etapa, Status — mais "abrir". **Agrupar** faz seções. A edição inline é a de sempre. Clicar em *cliente · obra* abre a edição direto no passo 2.
- **Voltar da ficha:** a URL guarda tudo (visão, busca, filtros, escopo, agrupar, ordenar, mês) e a rolagem volta também.
- **Celular:** a Lista vira cartões empilhados e o painel de filtros é uma folha inferior (nunca abre sozinha).
- **Ordenar** põe as demandas sem prazo **sempre no fim** (SQLite e PostgreSQL ordenavam o vazio de formas opostas) e aplica o sentido.

## 3. Parâmetros da URL

Mantidos: `tab`, `q`, `setor`, `pessoa` (repetível), `estagio`, `condicao`, `cliente`, `obra`, `tag`, `prazo`, `status`, `urgencia`, `ordem`, `dir`, `next`. Os apelidos antigos (`responsavel`, `grupo`, `sector`, `sort`) continuam funcionando e **todo link novo escreve o nome canônico**. Novos: `agrupar` (`stage`, `condition`, `sector`, `owner`, `urgency`) e `mes`. `page`, `view` e `visao` nunca são levados adiante.
O link antigo `tab=concluidas` continua respondendo: a tela o lê como *Escopo "Minhas" + Mostrar "Concluídas"*.

## 4. Arquitetura (o mínimo)

Nenhuma abstração nova foi criada "porque estava previsto". O que existe:

| Arquivo | Papel |
|---|---|
| `core/feature_flags.py` | `workspace_v2_enabled(user)` (lê as settings a cada chamada) |
| `boards/work_views.py` | `DemandWorkBoardView` escolhe o template pela flag e recebe 3 ganchos pequenos (`arrange_activities`, `requested_group_by`, `workspace_context`); **a consulta é a de sempre** (`filtered_activities_queryset`, com o request real) |
| `boards/demand_workspace.py` | monta o contexto `ws` da barra: abas, escopo, mostrar, agrupar, ordenar, chips, painel, avisos; `query_with`/`hidden_fields` (nada se perde ao filtrar) |
| `activities/filtering.py` | `normalize_workspace_filters` só aceita ids numéricos (o resto vai para `invalid`) |
| `templates/workspace/*` | `demandas.html` + parciais da barra; `_lista*.html` é o renderizador novo; `_kanban.html` usa o kit `templates/kanban/*` (§8); o Calendário **reusa o conteúdo antigo dentro do shell** |
| `static/js/workspace.js`, `static/css/workspace.css` | comportamento e estilo da barra |
| `static/js/person-picker.js` | `data-allow-empty` vale para qualquer seletor (Cliente/Obra) |

A tela antiga (`templates/boards/demand_work_board.html`) e tudo o que ela usa ficam **intactos**, para o rollback e para a comparação.

## 5. O que ficou de fora de propósito

- **Calendário novo** (fase 1D): hoje usa o conteúdo antigo (lista de prazos) dentro do shell. A grade mensal depende do teste com pessoas. (O Kanban novo existe, para todos: §8.)
- **Personalizar da Lista** (colunas) e o **padrão salvo com governança** (permissão própria, pré-visualizar, confirmar, auditar, restaurar): fase 1E.
- **Extrair `WorkspaceState`/contratos genéricos**: só se houver pelo menos dois consumidores reais ou duplicação comprovada.
- **Remover o legado**: só depois de uso real, com novo aval.
- **`activities/views.py`**: não foi tocado (a outra sessão o estava editando). A extração da consulta independente de request (`activities/demand_query.py`) continua pendente e é pré-requisito de qualquer necessidade nova na consulta; por isso "Mostrar → Todas" (abertas + concluídas) ainda não existe.

## 6. Capacidades da tela antiga que o Workspace (e a tela atual) não têm

Já listadas, com a decisão de produto pendente, em `LPS_TRIAGEM_TESTES_DEMANDAS.md`: limite de coluna (WIP), menu de ações na linha da Lista (Concluir/Cancelar/Reabrir/Transferir só na ficha), paginação, grade do calendário. A 1B pode revelar quais fazem falta. (O "Mover para…" no Kanban, o "+ Adicionar" por raia e a edição no cartão agora existem: §8.)

## 7. Testes

- `activities/test_workspace_demandas.py` (40): flag; mesmo shell nas três visões; estado preservado entre abas; escopo e mostrar; aviso de escopo; filtro inválido; chips; painel; Lista (6 colunas, contrato da edição inline, vazios); ordenação (vazio no fim); consultas constantes.
- `activities/test_demand_filters.py`: filtros, escopos e vazamento entre setores, rodados **duas vezes** (tela de sempre e Workspace) para provar que o recorte não muda de tela para tela.
- `core/test_feature_flags.py`: a flag.
- `tests/workspace.test.cjs` (18, jsdom): a regra de interação da barra, Esc, clicar fora, Etapa/Status por setor, foco, celular, rolagem.
- Chrome real (Playwright, cópia do banco, 41 verificações): o cenário *Setor + Responsável + Cliente* na Lista, no Kanban e no Calendário; rascunho do painel; Agrupar/Ordenar/Mostrar; aviso de escopo; Cliente/Obra; voltar da ficha; edição inline; arrastar no Kanban; quem está fora da lista; celular.
- Kanban (§8): `boards/test_kanban_kit.py` (36: contrato v2 da marcação e **Quadros renderizado pelo mesmo kit**), `boards/test_demand_kanban.py` (93: regras do construtor, página, quem pode arrastar, fragmento, renomear no lugar, Configurar cartões, editar campos no cartão, "+ Adicionar"/⋮ da raia e os **três contratos cliente × servidor**), `activities/test_activity_modal.py` (`NewDemandFromALaneTests`: valores iniciais da janela), `activities/test_inline_edit.py` (prioridade e versão), `tests/kanban-core.test.cjs` (49, jsdom), `tests/demand-kanban.test.cjs` (37), `tests/activity-inline-cards.test.cjs` (19: o editor da Lista sobre cartões) e `tests/boards-kanban.test.cjs` (Quadros sobre o mesmo núcleo).

## 8. Kanban de Demandas = o Kanban de Quadros (um componente só)

**O que o usuário pediu:** *"A tela do Kanban que fica em Quadros precisa ser o modelo para todos os outros Kanban"* (03/10/2026) e, ao ver que a tela ainda era a antiga, *"Tem como pegar o mesmo Kanban que está na tela de Quadros e colocar na de Demandas? O mesmíssimo?"* (05/10/2026). Respostas dele: trocar o Kanban da tela atual **sem flag**; igualar **tudo** (editar campos no cartão, "Configurar cartões", ⋮ da raia e "+ Adicionar", e **um código só**); clicar no título **renomeia no lugar**, como em Quadros.

**Estado:** **no ar para todos**, com ou sem `WORKSPACE_V2` (a flag só liga a barra do Workspace e os cinco agrupamentos; sem ela o Kanban agrupa por Etapa). **Quadros usa exatamente o mesmo componente** (mesma marcação, mesmo JS): não há mais cópia.

**O que a pessoa vê (igual em Quadros e em Demandas):** raias de 292px (84vw no celular) com cabeçalho sólido na cor da etapa/status e texto por contraste, pílula de contagem, corpo com rolagem própria, vazio tracejado, cartão com borda esquerda de 4px na cor da raia e campos tipados (avatar + nome, selo do setor, pílulas de prioridade/etapa/status, prazo com selo **vencido**, progresso das tarefas). Atraso é **selo na data**, nunca fundo do cartão. O nome dos campos fica oculto até a visão pedir (`show_field_names`).

**No cartão de Demandas:**

| Ação | Como |
|---|---|
| Renomear | clicar no título (ou Enter com o foco nele, ou ⋯ → Renomear): edição no lugar, com a versão do cartão (`updated_at`; 409 se mudou) |
| Abrir a ficha | clicar no **código** (`DEM-…`) ou ⋯ → **Abrir demanda** |
| Editar um campo | clicar nele: **Responsável, Prazo, Setor, Etapa, Status e Prioridade** abrem o **mesmo editor da Lista** (`activity-inline-edit.js`/`-options.js`, que reconhecem o cartão pela raiz `[data-kanban]`). Só é editável o que a pessoa pode editar (o servidor é quem decide; a tela só oferece o que ele aceita). Se o campo muda a **raia** do cartão (o agrupamento é ele, ou trocar o setor refaz etapa e status), as raias são pedidas de novo ao servidor |
| Mover | arrastar ou ⋯ → *Mover para…* (única forma em toque e no teclado) |

**"Configurar cartões" (botão do cabeçalho, só para quem configura o quadro):** o mesmo diálogo de Quadros — mostrar/ocultar e ordenar os campos do cartão (gravam sozinhos, uma vez depois de uma pausa), "Mostrar raias vazias", "Mostrar o nome de cada campo", com **pré-visualização** do primeiro cartão. Substituiu o painel *Personalizar* do Kanban (o "Adicionar campo" continua no painel de sempre).

**"+ Adicionar demanda" por raia:** abre a janela **Nova demanda** (a de sempre, por cima do Kanban) **já preenchida com o que a raia diz**: raia de Etapa → etapa **e** setor; de Status → status e setor; de Setor → setor; de Responsável → a pessoa; de Prioridade → a prioridade. Em Responsável/Prioridade o setor vem do filtro de setor quando há um só. Ao criar, a pessoa volta ao mesmo Kanban (`next`). Só aparece onde a demanda pode mesmo ficar: **não** na raia "sem valor" nem em etapa/status desativado, e **só se a pessoa pode criar naquele setor** (e, no agrupamento por responsável, para aquela pessoa) — mesma regra da janela, não a do botão geral. Valores inválidos na URL (`?setor=&etapa=&condicao=&urgencia=&pessoa=`) são ignorados em silêncio e a janela abre como sempre; só valem para demanda **nova** (editar ou retomar rascunho não os lê).

**⋮ da raia:** em raia de **Etapa** ou **Status**, para quem gere as etapas/status daquele setor (`ETAPA_GERIR`/`CONDICAO_GERIR`), abre *Editar as etapas do setor* / *Editar os status do setor* → a tela *Configurações → Etapas e status* já no setor. Renomear/recolorir a etapa **não** é feito na raia (diferente de Quadros, onde a etiqueta é do quadro): etapa e status são cadastro do setor e valem para **todas** as demandas dele, então ficam na tela própria. Nas demais raias o botão não existe.

**Mover:** o cartão vai na hora e volta ao lugar, com a mensagem do servidor, se ele recusar. Depois de gravar, as raias são redesenhadas pelo servidor **preservando rolagem lateral, rolagem de cada raia, rolagem da página e foco**. Mudar o **setor** pede confirmação (*etapa e status voltam ao padrão do setor novo*).

**Quem pode soltar onde (a tela adianta, o servidor decide):**

| Agrupar por | Raia em branco | Restrições |
|---|---|---|
| Etapa / Status | aceita (limpa o valor) | cada raia pertence a **um setor**: só recebe cartões desse setor; com setores misturados a raia mostra o setor sob o título; raia de etapa/status **desativado** aparece (tem cartão) mas não recebe |
| Setor | **fechada** (setor é obrigatório) | demanda em rascunho não muda de setor |
| Responsável | **fechada** | demanda em rascunho não muda de responsável |
| Prioridade | **fechada** | — |

Demanda **concluída ou cancelada** nunca se move nem se edita. Cartão sem destino possível (ou sem permissão) não tem arrastar nem ⋯ de mover — nada é "desabilitado só para parecer igual". A permissão da etapa aceita `ATIVIDADE_MOVER_ESTAGIO` **ou** `ATIVIDADE_DEFINIR_ETAPA` (como o serviço). O que a tela **não** adivinha: a permissão de editar no setor de **destino**, pendência aguardando aprovação e versão velha — o servidor recusa e a tela mostra a mensagem dele. Três **contratos cliente × servidor** nos testes (a tela oferece ⇔ o servidor aceita): soltar (cada cartão × cada raia × 5 agrupamentos), editar campo (cada campo × cada cartão × quem edita/lê) e **criar na raia** (cada raia × quem cria em qualquer setor/em um setor/não cria; foi ele que pegou o "+ Adicionar" sumindo para quem só cria em um setor).

**Arquitetura (um componente, dois anfitriões):**

| Arquivo | Papel |
|---|---|
| `templates/kanban/_lanes.html`, `_lane.html`, `_card.html`, `_fields.html` | **a única marcação**; o contrato de dados (v2) está no cabeçalho de `_lanes.html` (raia: `menu`, `menu_attrs`, `add`, `total`, `option_id`…; cartão: título editável/link, `attrs`, campos `editable`/`template`) |
| `static/css/kanban-core.css` | o que o modelo antigo não tinha (sublinha do setor, progresso, campos editáveis, estados salvando/erro, alvo de toque de 36px no ⋯ do cartão **e** da raia) |
| `static/js/kanban-core.js` | arrastar, menu do cartão e da raia, renomear no lugar, contagem, desfazer, redesenho, confirmação e o diálogo "Configurar cartões" (`LPSKanbanCore.init(root, adapter)`; ganchos do anfitrião: `move`, `reload`, `beforeMove`, `rename`, `menuItems`, `laneMenu`, `addCard`) |
| `static/js/boards.js` | anfitrião **Quadros** (grava na célula agrupadora, etiquetas da raia, excluir, criar item; tabela e calendário continuam aqui) |
| `static/js/demand-kanban.js` | anfitrião **Demandas**: POST em `workboard-value` (`{value, updated_at}`), mensagens por status (400/403/404/409/rede/sessão vencida), recarga das raias, itens do ⋮ da raia, "Configurar cartões" e a reação às gravações do editor inline |
| `static/js/activity-inline-*.js` | o editor da Lista, generalizado por **superfície** (linha de tabela ou cartão) |
| `boards/demand_kanban.py` | transforma as raias de `_group_items` e as células de `build_cells` em raias/cartões do kit: regras de "pode soltar", campos editáveis, "+ Adicionar" e ⋮ por raia |
| `boards/templatetags/lps_board.py` (`board_kanban`) | o mesmo para Quadros |
| `boards/work_views.py` | `kanban_context`; `?fragmento=raias` devolve só `kanban/_lanes.html` (mesma autorização e recorte); permissões por setor com cache por combinação (nunca por cartão) |
| `activities/activity_editor.py` | `creation_presets`: os valores iniciais da janela "Nova demanda" |

**Limites conhecidos / dívida:**
- Sem paginação (igual à tela antiga): com ~320 demandas o fragmento pesa ~710 KB sem compressão; se crescer, o caminho é um teto por raia (como o das Tarefas).
- **Mover a etapa/status não atualiza `updated_at`** no servidor, então o aviso de conflito (409) só aparece quando *outra edição* mexeu na demanda. Pré-existente; não foi alterado.
- O endpoint de edição inline devolve 200 para "mesmo valor" sem checar permissão (pré-existente; a tela nunca o usa assim).
- O botão geral "Nova demanda" do cabeçalho segue a regra antiga (`ATIVIDADE_CRIAR` sem setor): quem só cria em **um** setor não o vê, embora o "+ Adicionar" das raias dele apareça. Fora do escopo desta rodada.
- Limite de coluna (WIP) da tela antiga e renomear/recolorir etapa na raia **não** existem (ver o ⋮ acima).
- `static/js/work-board.js` ainda tem os tratadores do Kanban/painel antigos, hoje sem uso em Demandas (o Kanban de **Tarefas** ainda usa `boards/_work_kanban.html`, a próxima rodada: 3 raias derivadas, sem arrastar). Os primitivos de popover/diálogo existem também em `boards.js` (duplicados do núcleo) até uma rodada de limpeza.
